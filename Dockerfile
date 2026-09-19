FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive \
    PORT=7860

WORKDIR /app

# Install system dependencies for audio processing, OpenCV, and PyTorch
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libgl1 \
    libglib2.0-0 \
    libsndfile1 \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create a non-root user with UID 1000 (standard for Hugging Face Spaces & security best practices)
RUN useradd -m -u 1000 user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH

# Copy backend package configuration
COPY --chown=user:user backend/pyproject.toml backend/README.md /app/backend/
WORKDIR /app/backend
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir ".[ml]"

# Copy backend application source and data models
COPY --chown=user:user backend/ /app/backend/
COPY --chown=user:user data/ /app/data/

# Ensure proper permissions on the data directory for SQLite and uploads
RUN mkdir -p /app/data/uploads /app/data/reports /app/data/models && \
    chown -R user:user /app/data

USER user

EXPOSE 7860

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "7860"]
