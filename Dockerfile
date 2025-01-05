# Use the official Python image as a parent image
FROM python:3.9-slim

# Install FFmpeg and dependencies
RUN apt-get update && apt-get install -y ffmpeg

# Set the working directory inside the container
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY . /app

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Expose port 5000
EXPOSE 5000

# Define the command to run the application
CMD ["python", "app.py"]
