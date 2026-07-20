FROM python:3.12-slim

WORKDIR /app

# Install dependencies first so this layer is cached across code changes
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 5000

# app.py binds 0.0.0.0 and runs the warm-up thread when debug is off.
# OLLAMA_BASE_URL defaults to the compose service name so the image also
# works when run directly on the compose network (not just via compose,
# which sets the same values in docker-compose.yml). Without this, the app
# falls back to http://localhost:11434, which points inside this container.
ENV FLASK_DEBUG=false \
    OLLAMA_BASE_URL=http://ollama:11434 \
    CHAT_MODEL=aisingapore/Gemma-SEA-LION-v4-4B-VL \
    OLLAMA_TIMEOUT=180

CMD ["python", "app.py"]
