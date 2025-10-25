FROM python:3.10-slim

ENV PYTHONUNBUFFERED=1 \
    WHISPER_MODEL_DIR=/app/whisper-en-finetuned

WORKDIR /app

RUN apt-get update && \
    apt-get install -y --no-install-recommends ffmpeg libsndfile1 libsox-fmt-mp3 && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py .
COPY whisper-en-finetuned ./whisper-en-finetuned

EXPOSE 5000

CMD ["gunicorn", "--bind", "0.0.0.0:5000", "app:app"]
