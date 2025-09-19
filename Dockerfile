FROM python:3.11-slim

# Install system deps for chromium + playwright + CA certificates
RUN apt-get update && apt-get install -y \
    curl wget gnupg unzip fonts-liberation libasound2 \
    libatk1.0-0 libatk-bridge2.0-0 libcups2 libdbus-1-3 \
    libnss3 libxkbcommon0 libx11-xcb1 libxcomposite1 \
    libxdamage1 libxrandr2 libgbm1 libgtk-3-0 \
    ca-certificates \ 
    && rm -rf /var/lib/apt/lists/*

# Make sure CA certificates are up to date
RUN update-ca-certificates

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright Chromium
RUN playwright install --with-deps chromium

# Copy app code
COPY . .

# Expose the port (FastAPI)
EXPOSE 8080

# Start Supervisor (runs bot + backend together)
CMD ["supervisord", "-c", "/app/supervisord.conf"]
