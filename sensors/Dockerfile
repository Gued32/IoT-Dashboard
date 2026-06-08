FROM python:3.11

WORKDIR /app

COPY requirements-backend.txt .
RUN pip install --no-cache-dir -r requirements-backend.txt

COPY sensors ./sensors

CMD ["python", "sensors/sensor_simulator.py"]
