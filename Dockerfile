FROM python:3.11-slim

# Install deps for chromium + playwright
RUN apt-get update && apt-get install -y \
    curl wget gnupg unzip fonts-liberation libasound2 \
    libatk1.0-0 libatk-bridge2.0-0 libcups2 libdbus-1-3 \
    libnss3 libxkbcommon0 libx11-xcb1 libxcomposite1 \
    libxdamage1 libxrandr2 libgbm1 libgtk-3-0 supervisor \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install playwright + chromium
RUN playwright install --with-deps chromium

# Copy everything
COPY . .

# Run bot + backend together
CMD ["supervisord", "-c", "/app/supervisord.conf"]
