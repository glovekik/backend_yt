import os
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import yt_dlp

app = Flask(__name__)

# Enable CORS for Vercel frontend
CORS(app, resources={r"/*": {"origins": "https://frontend-fullapplication.vercel.app"}})

# Set the directory for downloads
DOWNLOAD_DIR = os.getenv('RAILWAY_FILES_PATH', '/tmp')  # Use '/tmp' for Railway or default

# Function to download video or audio
def download_media(link, media_type='video'):
    try:
        # Ensure the download directory exists
        os.makedirs(DOWNLOAD_DIR, exist_ok=True)

        # Define yt-dlp options based on media type
        if media_type == 'video':
            ydl_opts = {
                'format': 'best',
                'outtmpl': os.path.join(DOWNLOAD_DIR, '%(title)s.%(ext)s'),
                'noplaylist': True,
            }
        elif media_type == 'audio':
            ydl_opts = {
                'format': 'bestaudio/best',
                'outtmpl': os.path.join(DOWNLOAD_DIR, '%(title)s.%(ext)s'),
                'noplaylist': True,
                'postprocessors': [{
                    'key': 'FFmpegAudioConvertor',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }],
            }

        # Download media using yt-dlp
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(link, download=True)
            filename = ydl.prepare_filename(info_dict)
            return os.path.basename(filename), None
    except Exception as e:
        print(f"Error: {e}")
        return None, "Failed to process the request. Ensure the link is valid."

# Route to handle download requests
@app.route('/download', methods=['POST'])
def download():
    data = request.json
    link = data.get('link')
    media_type = data.get('media_type', 'video')

    if not link:
        return jsonify({"error": "No link provided"}), 400

    filename, error = download_media(link, media_type)

    if filename:
        return jsonify({"filename": filename}), 200
    else:
        return jsonify({"error": error}), 500

# Route to serve downloaded files
@app.route('/downloads/<path:filename>', methods=['GET'])
def serve_file(filename):
    filepath = os.path.join(DOWNLOAD_DIR, filename)
    if os.path.isfile(filepath):
        return send_from_directory(DOWNLOAD_DIR, filename, as_attachment=True)
    else:
        return jsonify({"error": "File not found"}), 404

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
