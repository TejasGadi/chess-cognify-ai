FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
# - stockfish for chess analysis
# - libxcb* for PDF processing (Docling/X11 in headless env)
# - libgl1 for OpenCV (cv2) used by Docling table structure model
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    stockfish \
    libxcb1 \
    libxcb-render0 \
    libxcb-shm0 \
    libxcb-xfixes0 \
    libxcb-shape0 \
    libgl1 \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Copy entrypoint script and make it executable
COPY entrypoint.sh .
RUN chmod +x entrypoint.sh

# Expose port
EXPOSE 8000

# Run application via entrypoint
ENTRYPOINT ["./entrypoint.sh"]
