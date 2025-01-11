from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import yt_dlp
import os
import uuid

app = Flask(__name__)

# Allow requests from the frontend URL
CORS(app, origins=["https://frontend-fullapplication.vercel.app", "http://127.0.0.1:5500"])

# Directory for saving downloads (temporary folder)
DOWNLOAD_DIR = "/tmp/downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# Path to cookies file (make sure this file is correctly placed on your server)
COOKIES_FILE = "/tmp/cookies.txt"  # Adjust this path based on where you store the cookies file

# Function to download audio or video from YouTube
def download_media(link, media_type):
    ffmpeg_location = '/usr/bin/ffmpeg'  # Adjust the path if necessary

    ydl_opts = {
        'ffmpeg_location': ffmpeg_location,  # Point to the ffmpeg binary
        'outtmpl': os.path.join(DOWNLOAD_DIR, f'%(title)s-{uuid.uuid4()}.%(ext)s'),
        'noplaylist': True,
        'headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        },
        'cookiefile': COOKIES_FILE if os.path.exists(COOKIES_FILE) else None,  # Use cookies if file exists
        'verbose': True,  # Enable verbose for debugging
    }

    # If audio, download only audio
    if media_type == 'audio':
        ydl_opts['format'] = 'bestaudio/best'
    # If video, download without postprocessing (skip format conversion)
    else:
        ydl_opts['format'] = 'bestvideo+bestaudio/best'

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(link, download=True)
            filename = ydl.prepare_filename(info_dict)
            return filename  # Return full file path of the downloaded media
    except Exception as e:
        print(f"Download error: {e}")
        return f"Unexpected error: {e}"

@app.route('/download', methods=['POST', 'OPTIONS'])
def download():
    if request.method == 'OPTIONS':
        # Handle preflight request
        return '', 200

    data = request.get_json()
    link = data.get('link')
    media_type = data.get('media_type', 'video')  # Default to video if no media_type provided

    if not link:
        return jsonify({"error": "No link provided"}), 400

    if not (link.startswith("https://www.youtube.com") or link.startswith("https://youtu.be")):
        return jsonify({"error": "Invalid YouTube link"}), 400

    downloaded_file = download_media(link, media_type)
    if "Error" in downloaded_file:
        return jsonify({"error": downloaded_file}), 500

    try:
        # Use send_file to directly serve the downloaded file
        return send_file(downloaded_file, as_attachment=True)
    except Exception as e:
        return jsonify({"error": f"File download failed: {str(e)}"}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
