from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import yt_dlp
import os
import uuid
from werkzeug.utils import safe_join

app = Flask(__name__)

# Allow requests from specific frontend origins
CORS(app, origins=["https://frontend-fullapplication.vercel.app", "http://127.0.0.1:5500"])

# Directory for saving downloads
DOWNLOAD_DIR = "/tmp/downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# Path to cookies file (optional)
COOKIES_FILE = "/tmp/cookies.txt"

def download_media(link, media_type):
    ffmpeg_location = '/usr/bin/ffmpeg'  # Update if ffmpeg is installed elsewhere

    ydl_opts = {
        'ffmpeg_location': ffmpeg_location,
        'outtmpl': os.path.join(DOWNLOAD_DIR, f'%(title)s-{uuid.uuid4()}.%(ext)s'),
        'noplaylist': True,
        'cookiefile': COOKIES_FILE if os.path.exists(COOKIES_FILE) else None,
        'postprocessors': [{'key': 'FFmpegMetadata'}],
    }

    if media_type == 'audio':
        # Download best audio and convert it to MP3
        ydl_opts['format'] = 'bestaudio/best'
        ydl_opts['postprocessors'].append({
            'key': 'FFmpegAudioConvertor',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        })
    else:
        # Download best video and best audio, merge them into a single MP4 file
        ydl_opts['format'] = 'bestvideo+bestaudio/best'
        ydl_opts['merge_output_format'] = 'mp4'  # Ensure the merged output is in MP4 format

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(link, download=True)
            filename = ydl.prepare_filename(info_dict)
            # If merge is successful, the file extension will be `.mp4`
            if media_type == 'video' and not filename.endswith('.mp4'):
                filename = filename.replace('.webm', '.mp4').replace('.mkv', '.mp4')
            return os.path.basename(filename)
    except yt_dlp.utils.DownloadError as e:
        return f"Download error: {e}"
    except Exception as e:
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
        return jsonify({"error": "File not found"}), 404

    try:
        return send_file(file_path, as_attachment=True)
    except Exception as e:
        return jsonify({"error": f"File download failed: {e}"}), 500
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
