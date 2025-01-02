import os
from flask import Flask, request, jsonify, send_from_directory
import yt_dlp
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Set the specific download directory (use /tmp for Railway)
DOWNLOAD_DIR = os.getenv('RAILWAY_FILES_PATH', '/tmp')  # Default to '/tmp' for Railway environment

# Function to download video or audio
def download_media(link, media_type='video'):
    try:
        # Ensure the download directory exists
        os.makedirs(DOWNLOAD_DIR, exist_ok=True)

        # Define download options
        if media_type == 'video':
            ydl_opts = {
                'format': 'best',  # Download the best available quality for video
                'outtmpl': os.path.join(DOWNLOAD_DIR, '%(title)s.%(ext)s'),  # Save with the video title as filename
                'noplaylist': True,  # Only download a single video, not a playlist
            }
        elif media_type == 'audio':
            ydl_opts = {
                'format': 'bestaudio/best',  # Download the best audio format
                'outtmpl': os.path.join(DOWNLOAD_DIR, '%(title)s.%(ext)s'),  # Save with the video title as filename
                'noplaylist': True,  # Only download a single video, not a playlist
                'postprocessors': [{  # Convert audio to mp3
                    'key': 'FFmpegAudioConvertor',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }]
            }

        # Download the media using yt-dlp
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(link, download=True)
            filename = ydl.prepare_filename(info_dict)  # This gives the filename
            return filename, None  # Return filename and no error
    except Exception as e:
        print(f"Error: {e}")
        return None, str(e)  # Return None for filename and the error message

# Route to handle video/audio download requests
@app.route('/download', methods=['POST'])
def download():
    link = request.json.get('link')  # Get the link from the POST request
    media_type = request.json.get('media_type', 'video')  # Default to 'video' if not provided
    filename, error = download_media(link, media_type)  # Unpack filename and error

    if filename:
        # Return the filename to the client for download
        return jsonify({"filename": filename}), 200
    else:
        return jsonify({"error": error}), 500

# Route to serve the file for download
@app.route('/downloads/<filename>', methods=['GET'])
def serve_file(filename):
    # Serve the file directly from the 'C:/Downloads' folder for download
    return send_from_directory(DOWNLOAD_DIR, filename, as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True)
