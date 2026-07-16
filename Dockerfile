FROM python:3.12-slim

WORKDIR /app

# Install dependencies first so this layer is cached across code changes
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 5000

# app.py binds 0.0.0.0 and runs the warm-up thread when debug is off
ENV FLASK_DEBUG=false

CMD ["python", "app.py"]
