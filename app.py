from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import yt_dlp
import os
import uuid
from werkzeug.utils import safe_join

app = Flask(__name__)

# Allow requests from the frontend
CORS(app, origins=["https://frontend-fullapplication.vercel.app", "http://127.0.0.1:5500"])

# Directory for saving downloads
DOWNLOAD_DIR = "/tmp/downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# Function to download audio or video from YouTube
def download_media(link, media_type):
    ffmpeg_location = '/usr/bin/ffmpeg'  # Adjust based on your server configuration

    ydl_opts = {
        'ffmpeg_location': ffmpeg_location,
        'outtmpl': os.path.join(DOWNLOAD_DIR, f'%(title)s-{uuid.uuid4()}.%(ext)s'),
        'noplaylist': True,
        'cookiesfrombrowser': ('chrome',),  # Fetch cookies from Chrome. Replace with 'firefox' or 'edge' if needed.
        'postprocessors': [{'key': 'FFmpegMetadata'}],
    }

    if media_type == 'audio':
        ydl_opts['format'] = 'bestaudio/best'
        ydl_opts['postprocessors'].append({
            'key': 'FFmpegAudioConvertor',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        })
    else:
        ydl_opts['format'] = 'bestvideo+bestaudio/best'
        ydl_opts['merge_output_format'] = 'mp4'

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(link, download=True)
            filename = ydl.prepare_filename(info_dict)
            return os.path.basename(filename)  # Return only the filename
    except yt_dlp.utils.DownloadError as e:
        print(f"Download error: {e}")
        return f"Download error: {e}"
    except Exception as e:
        print(f"Unexpected error: {e}")
        return f"Unexpected error: {e}"

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
        # Send the file as a download response
        response = send_file(file_path, as_attachment=True)
        os.remove(file_path)  # Clean up the file after sending
        return response
    except Exception as e:
        print(f"Error during file download: {str(e)}")
        return jsonify({"error": f"File download failed: {str(e)}"}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
