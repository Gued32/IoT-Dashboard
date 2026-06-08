FROM python:3.11

WORKDIR /app

COPY requirements-backend.txt .

RUN pip install --no-cache-dir -r requirements-backend.txt

COPY backend ./backend

CMD ["sh", "-c", "uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-8000}"]