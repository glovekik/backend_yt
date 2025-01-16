from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import yt_dlp
import os
import uuid
from werkzeug.utils import safe_join
import subprocess

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
        'merge_output_format': 'mp4',  # Ensure output is MP4 without re-encoding
        'headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        },
        'cookiefile': COOKIES_FILE if os.path.exists(COOKIES_FILE) else None,
        'postprocessors': [
            {'key': 'FFmpegMetadata'},  # Embed metadata
        ],
    }

    if media_type == 'audio':
        ydl_opts['format'] = 'bestaudio/best'
    else:
        ydl_opts['format'] = 'bestvideo+bestaudio/best'

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(link, download=True)
            filename = ydl.prepare_filename(info_dict)
            print(f"Downloaded file: {filename}")

            # If it's audio, convert to MP3 if it's in Opus format
            if media_type == 'audio' and filename.endswith('.webm'):
                # Convert from Opus to MP3
                output_file = os.path.splitext(filename)[0] + '.mp3'
                convert_audio_to_mp3(filename, output_file)
                os.remove(filename)  # Remove the original audio file (Opus)
                filename = output_file

            return os.path.basename(filename)  # Return just the file name
    except yt_dlp.utils.DownloadError as e:
        return f"yt-dlp download error: {str(e)}"
    except Exception as e:
        return f"Unexpected error: {str(e)}"

def convert_audio_to_mp3(input_file, output_file):
    """Convert audio to MP3 using ffmpeg."""
    try:
        subprocess.run([ffmpeg_location, '-i', input_file, '-vn', '-acodec', 'libmp3lame', output_file], check=True)
        print(f"Converted {input_file} to {output_file}")
    except subprocess.CalledProcessError as e:
        print(f"Error converting audio: {str(e)}")
        raise

@app.route('/download', methods=['POST', 'OPTIONS'])
def download():
    if request.method == 'OPTIONS':
        return '', 200

    data = request.get_json()
    link = data.get('link')
    media_type = data.get('media_type', 'video')

    if not link:
        return jsonify({"error": "No link provided"}), 400

    if not (link.startswith("https://www.youtube.com") or link.startswith("https://youtu.be")):
        return jsonify({"error": "Invalid YouTube link"}), 400

    downloaded_file = download_media(link, media_type)
    if "error" in downloaded_file.lower():
        return jsonify({"error": downloaded_file}), 500

    file_path = safe_join(DOWNLOAD_DIR, downloaded_file)

    if not os.path.exists(file_path):
        return jsonify({"error": "File not found after download"}), 404

    try:
        response = send_file(file_path, as_attachment=True)
        os.remove(file_path)  # Clean up the file after sending
        return response
    except Exception as e:
        print(f"Error during file download: {str(e)}")
        return jsonify({"error": f"File download failed: {str(e)}"}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
