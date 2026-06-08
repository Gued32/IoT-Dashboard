FROM python:3.11

WORKDIR /app

COPY requirements-frontend.txt .
RUN pip install --no-cache-dir -r requirements-frontend.txt

COPY frontend ./frontend

CMD ["sh", "-c", "streamlit run frontend/dashboard.py --server.port=${PORT:-8501} --server.address=0.0.0.0"]