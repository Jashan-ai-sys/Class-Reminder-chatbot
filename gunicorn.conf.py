# gunicorn.conf.py
import os

# Use uvicorn worker for FastAPI (ASGI)
worker_class = "uvicorn.workers.UvicornWorker"

# Bind to the port defined in environment variable
port = os.getenv("PORT", "8080")
bind = f"0.0.0.0:{port}"

# Worker settings
workers = 2
timeout = 120
keepalive = 5
