from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import yt_dlp
import os
import uuid
from werkzeug.utils import safe_join

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
        'ffmpeg_location': ffmpeg_location,
        'outtmpl': os.path.join(DOWNLOAD_DIR, f'%(title)s-{uuid.uuid4()}.%(ext)s'),
        'noplaylist': True,
        'headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        },
        'cookiefile': COOKIES_FILE if os.path.exists(COOKIES_FILE) else None,
        'verbose': True,  # Enable verbose for debugging
    }

    # If audio, download only audio
    if media_type == 'audio':
        ydl_opts['format'] = 'bestaudio/best'
    else:
        ydl_opts['format'] = 'bestvideo+bestaudio/best'

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(link, download=True)
            filename = ydl.prepare_filename(info_dict)
            print(f"Downloaded file: {filename}")  # Log the downloaded file path
            return filename
    except yt_dlp.utils.DownloadError as e:
        print(f"yt-dlp download error: {str(e)}")
        return f"yt-dlp download error: {str(e)}"
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        return f"Unexpected error: {str(e)}"

@app.route('/download', methods=['POST', 'OPTIONS'])
def download():
    if request.method == 'OPTIONS':
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

    # Ensure the file exists in the download directory
    file_path = safe_join(DOWNLOAD_DIR, downloaded_file)
    
    print(f"Checked file path: {file_path}")  # Log the final file path
    
    if not os.path.exists(file_path):
        return jsonify({"error": "File not found after download"}), 404

    try:
        # Send the file as an attachment for download
        print(f"Sending file: {file_path}")  # Log file sending
        response = send_file(file_path, as_attachment=True)
        
        # Clean up after download (optional)
        os.remove(file_path)
        
        return response
    except Exception as e:
        print(f"Error during file download: {str(e)}")  # Log errors during file send
        return jsonify({"error": f"File download failed: {str(e)}"}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
