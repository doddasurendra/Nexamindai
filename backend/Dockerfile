FROM python:3.12-slim
WORKDIR /app
ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 PYTHONDONTWRITEBYTECODE=1

# moviepy needs ffmpeg shims + glib for imageio-ffmpeg
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 libglib2.0-0 curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Cloud Run sets PORT; SQLite + media files live on writable /tmp (ephemeral: use Cloud SQL / Firestore for persistence)
ENV PORT=8080 DATABASE_URL=sqlite+aiosqlite:////tmp/nexamind.db STORAGE_DIR=/tmp/storage

EXPOSE 8080
CMD ["sh", "-c", "python -m uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]
