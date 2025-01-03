import os
import uuid
import logging
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import yt_dlp

# Set up logging
logging.basicConfig(level=logging.INFO)

app = Flask(__name__)

# Enable CORS for the frontend (replace with the actual frontend URL)
CORS(app, resources={r"/*": {"origins": ["https://frontend-fullapplication.vercel.app", "http://127.0.0.1:5500"]}})

# Set the directory for downloads (use '/tmp' for production environments like Railway)
DOWNLOAD_DIR = os.getenv('RAILWAY_FILES_PATH', '/tmp/downloads')
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# Function to download video or audio
def download_media(link, media_type='video'):
    try:
        # Define yt-dlp options based on media type
        ydl_opts = {
            'outtmpl': os.path.join(DOWNLOAD_DIR, f'%(title)s-{uuid.uuid4()}.%(ext)s'),
            'noplaylist': True,  # Only download a single video
        }
        if media_type == 'video':
            ydl_opts['format'] = 'best'  # Best available quality for video
        elif media_type == 'audio':
            ydl_opts['format'] = 'bestaudio/best'
            ydl_opts['postprocessors'] = [{
                'key': 'FFmpegAudioConvertor',  # Convert audio to mp3
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }]

        # Download media using yt-dlp
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(link, download=True)
            filepath = ydl.prepare_filename(info_dict)
            logging.info(f"Downloaded: {filepath}")
            return filepath, None
    except Exception as e:
        logging.error(f"Error downloading media: {e}")
        return None, "Failed to process the request. Ensure the link is valid."

# Health check route
@app.route("/", methods=["GET"])
def health_check():
    return jsonify({"message": "Server is running!"}), 200

# Route to handle download requests
@app.route('/download', methods=['POST', 'OPTIONS'])
def download():
    if request.method == 'OPTIONS':
        # Handle preflight requests for CORS
        return '', 200

    try:
        data = request.get_json()
        link = data.get('link')
        media_type = data.get('media_type', 'video')

        if not link:
            return jsonify({"error": "No link provided"}), 400

        filepath, error = download_media(link, media_type)

        if filepath:
            return send_file(filepath, as_attachment=True)
        else:
            return jsonify({"error": error}), 500
    except Exception as e:
        logging.error(f"Error in /download route: {e}")
        return jsonify({"error": "Internal Server Error"}), 500

# Route to serve downloaded files
@app.route('/downloads/<path:filename>', methods=['GET'])
def serve_file(filename):
    try:
        filepath = os.path.join(DOWNLOAD_DIR, filename)
        if os.path.isfile(filepath):
            return send_file(filepath, as_attachment=True)
        else:
            return jsonify({"error": "File not found"}), 404
    except Exception as e:
        logging.error(f"Error serving file: {e}")
        return jsonify({"error": "Failed to serve the file"}), 500

# Error handling for 500 errors
@app.errorhandler(500)
def internal_error(error):
    logging.error(f"Internal error: {error}")
    return jsonify({"error": "Internal Server Error", "message": str(error)}), 500

# Error handling for 404 errors
@app.errorhandler(404)
def not_found_error(error):
    logging.error(f"Not Found: {error}")
    return jsonify({"error": "Resource not found"}), 404

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)

