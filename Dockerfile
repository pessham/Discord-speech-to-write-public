# Simple production Dockerfile for Discord Speech-to-Write Bot
FROM python:3.11-slim

# Install ffmpeg for audio conversion
RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python deps first for better layer caching
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy source
COPY . .

# Default command
ENTRYPOINT ["python", "bot.py"]
