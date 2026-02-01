FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
# Added stockfish for chess analysis
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    stockfish \
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
