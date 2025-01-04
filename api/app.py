import os
import logging
from flask import Flask, request, jsonify, send_file
import yt_dlp
from werkzeug.utils import secure_filename

app = Flask(__name__)

# Set up logging
logging.basicConfig(level=logging.INFO)

# Dynamic Download Directory
DOWNLOAD_DIRECTORY = os.getenv('RAILWAY_FILES_PATH', '/tmp/downloads')

# Ensure the download directory exists
if not os.path.exists(DOWNLOAD_DIRECTORY):
    os.makedirs(DOWNLOAD_DIRECTORY)

# CORS configuration (allowing multiple origins)
from flask_cors import CORS
CORS(app, resources={r"/*": {"origins": ["frontend-fullapplication.vercel.app", "127.0.0.1:5500"]}})

# Health Check Endpoint
@app.route('/')
def health_check():
    return "Server is running!"

# Download Media function
def download_media(url, media_type="video"):
    try:
        ydl_opts = {
            'format': 'bestvideo+bestaudio' if media_type == 'video' else 'bestaudio/best',
            'outtmpl': os.path.join(DOWNLOAD_DIRECTORY, '%(title)s.%(ext)s'),
            'postprocessors': [{
                'key': 'FFmpegAudioConvertor',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }] if media_type == 'audio' else [],
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(url, download=True)
            return info_dict['title'] + '.' + info_dict['ext']  # Return the downloaded file name

    except Exception as e:
        logging.error(f"Error downloading media: {str(e)}")
        return None

# File Serving Endpoint
@app.route('/downloads/<path:filename>')
def download_file(filename):
    try:
        return send_file(os.path.join(DOWNLOAD_DIRECTORY, filename), as_attachment=True)
    except Exception as e:
        logging.error(f"Error serving file {filename}: {str(e)}")
        return jsonify({"error": "File not found!"}), 404

# Main Download Endpoint
@app.route('/download', methods=['POST'])
def download():
    data = request.get_json()
    url = data.get('url')
    media_type = data.get('media_type', 'video')

    if not url:
        return jsonify({"error": "URL is required"}), 400

    logging.info(f"Starting download for {url} as {media_type}")

    # Perform the download
    filename = download_media(url, media_type)

    if filename:
        return jsonify({"message": f"Download started for {filename}. You can access it at /downloads/{filename}."}), 200
    else:
        return jsonify({"error": "Failed to download the media"}), 500

# Error Handlers
@app.errorhandler(500)
def internal_error(error):
    logging.error(f"Internal Server Error: {error}")
    return jsonify({"error": "Internal server error"}), 500

@app.errorhandler(404)
def not_found_error(error):
    logging.error(f"404 Not Found: {error}")
    return jsonify({"error": "Resource not found"}), 404

if __name__ == '__main__':
    app.run(debug=True)


