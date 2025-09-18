FROM python:3.11-slim

# Install deps for chromium + playwright
RUN apt-get update && apt-get install -y \
    curl wget gnupg unzip fonts-liberation libasound2 \
    libatk1.0-0 libatk-bridge2.0-0 libcups2 libdbus-1-3 \
    libnss3 libxkbcommon0 libx11-xcb1 libxcomposite1 \
    libxdamage1 libxrandr2 libgbm1 libgtk-3-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install playwright + chromium
RUN pip install playwright && playwright install --with-deps chromium

COPY . .

# Use supervisord to run bot + backend together
RUN pip install supervisor
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf

CMD ["supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]
