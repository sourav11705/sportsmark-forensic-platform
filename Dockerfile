# Use an official lightweight Python image
FROM python:3.10-slim

# Install FFmpeg and OpenCV dependencies (Crucial for SportsMark)
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libsm6 \
    libxext6 \
    && rm -rf /var/lib/apt/lists/*

# Set the working directory
WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of your application code
COPY . .

# Google Cloud Run expects the server to listen on port 8080
EXPOSE 8080

# Start the FastAPI server
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8080"]