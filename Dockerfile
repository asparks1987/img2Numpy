FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV IMG2NUMPY_API_PORT=8585

EXPOSE 8585

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${IMG2NUMPY_API_PORT:-8585}"]
