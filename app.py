from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import yt_dlp
import os
import uuid
from threading import Timer

app = Flask(__name__)

# Allow requests from specific frontend URLs
CORS(app, origins=["https://frontend-fullapplication.vercel.app", "http://127.0.0.1:5500", "*"])

# Directory for saving downloads (temporary folder)
DOWNLOAD_DIR = "/tmp/downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# Path to your cookies file (update this to the actual location of your cookies file)
COOKIES_FILE = "/tmp/cookies.txt"

# Ensure the cookies file exists before starting the app
if not os.path.exists(COOKIES_FILE):
    raise FileNotFoundError(f"Cookies file not found: {COOKIES_FILE}")

# Function to clean up temporary files
def cleanup_file(file_path, delay=3600):
    Timer(delay, lambda: os.remove(file_path) if os.path.exists(file_path) else None).start()

# Function to download audio or video from YouTube
def download_media(link, media_type):
    ffmpeg_location = '/usr/bin/ffmpeg'  # Adjust the path if necessary

    ydl_opts = {
        'ffmpeg_location': ffmpeg_location,
        'outtmpl': os.path.join(DOWNLOAD_DIR, f'%(title)s-{uuid.uuid4()}.%(ext)s'),
        'noplaylist': True,
        'quiet': True,
        'cookiefile': COOKIES_FILE,  # Include authentication cookies
    }

    if media_type == 'audio':
        ydl_opts['format'] = 'bestaudio/best'
    else:
        ydl_opts['format'] = 'bestvideo+bestaudio/best'
        ydl_opts['postprocessors'] = [{
            'key': 'FFmpegVideoConvertor',
            'preferedformat': 'mp4',
        }]

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(link, download=True)
            filename = ydl.prepare_filename(info_dict)
            return filename  # Full path of the downloaded file
    except yt_dlp.utils.DownloadError as e:
        print(f"Download error: {e}")
        return f"Download failed: {e}"
    except Exception as e:
        print(f"Unexpected error: {e}")
        return f"Unexpected error: {e}"

@app.route('/download', methods=['POST', 'OPTIONS'])
def download():
    if request.method == 'OPTIONS':
        # Handle preflight request
        return '', 200

    data = request.get_json()
    link = data.get('link')
    media_type = data.get('media_type', 'video')  # Default to video if not provided

    if not link:
        return jsonify({"error": "No link provided"}), 400

    if not (link.startswith("https://www.youtube.com") or link.startswith("https://youtu.be")):
        return jsonify({"error": "Invalid YouTube link"}), 400

    downloaded_file = download_media(link, media_type)
    if "Error" in downloaded_file:
        return jsonify({"error": downloaded_file}), 500

    try:
        # Use send_file to serve the downloaded file
        response = send_file(downloaded_file, as_attachment=True)
        cleanup_file(downloaded_file)  # Schedule file cleanup after serving
        return response
    except Exception as e:
        print(f"File serving error: {e}")
        return jsonify({"error": f"File download failed: {str(e)}"}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
