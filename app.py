from flask import Flask, request, send_file, jsonify
from flask_cors import CORS
import subprocess
import os
import uuid
from werkzeug.utils import secure_filename

app = Flask(__name__)

# Allow requests from the frontend URL
CORS(app, origins=["https://frontend-fullapplication.vercel.app", "http://127.0.0.1:5500"])

# Temporary directory for saving downloads
DOWNLOAD_DIR = "/tmp/downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# Path to FFmpeg binary
FFMPEG_PATH = "/usr/bin/ffmpeg"  # Make sure the path to FFmpeg is correct

def convert_media(input_file, output_file, media_type):
    if media_type == 'video':
        # Convert video to MP4 format
        subprocess.run([FFMPEG_PATH, '-i', input_file, '-c:v', 'libx264', '-c:a', 'aac', '-strict', 'experimental', output_file])
    elif media_type == 'audio':
        # Convert audio to MP3 format
        subprocess.run([FFMPEG_PATH, '-i', input_file, '-vn', '-c:a', 'libmp3lame', output_file])

@app.route('/download', methods=['POST'])
def download_media():
    data = request.get_json()
    link = data.get('link')
    media_type = data.get('media_type')

    if not link:
        return jsonify({"error": "No link provided"}), 400

    if not (link.startswith("https://www.youtube.com") or link.startswith("https://youtu.be")):
        return jsonify({"error": "Invalid YouTube link"}), 400

    # Download using yt-dlp
    try:
        output_file = secure_filename(f'{uuid.uuid4()}')
        temp_file = os.path.join(DOWNLOAD_DIR, f'{output_file}.webm' if media_type == 'video' else f'{output_file}.opus')

        # Use yt-dlp to download the media
        subprocess.run(['yt-dlp', '-f', 'bestaudio' if media_type == 'audio' else 'bestvideo+bestaudio', '-o', temp_file, link], check=True)

        # Convert the media to a supported format
        converted_file = os.path.join(DOWNLOAD_DIR, f'{output_file}.mp4' if media_type == 'video' else f'{output_file}.mp3')
        convert_media(temp_file, converted_file, media_type)

        # Clean up the original downloaded file
        os.remove(temp_file)

        return send_file(converted_file, as_attachment=True)

    except Exception as e:
        print(f"Error during download or conversion: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
