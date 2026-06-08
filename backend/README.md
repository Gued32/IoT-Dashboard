# Backend (FastAPI + MQTT + SQLite)

The backend subscribes to MQTT sensor messages, stores all received values in SQLite, and exposes REST endpoints for the dashboard.

## Install

```powershell
python -m pip install -r backend\requirements.txt
```

## Run

```powershell
python -m uvicorn backend.main:app --reload
```

MQTT configuration via environment variables:
- `MQTT_BROKER` (default: `localhost`)
- `MQTT_PORT` (default: `1883`)
- `MQTT_TOPIC` (default: `sensors/data`)
- `MQTT_CLIENT_ID` (default: `iot-dashboard-backend`)
- `MQTT_KEEPALIVE` (default: `60`)
- `MQTT_USERNAME` (optional)
- `MQTT_PASSWORD` (optional)
- `MQTT_TLS` (optional, enabled automatically for port `8883` or when `MQTT_USERNAME` is set)

## MQTT payload format

Required JSON keys:
- `sensor_id`
- `timestamp`
- `temperature_c`
- `humidity_percent`

## REST endpoints

- `GET /health`
- `GET /sensor-data` (latest sensor value)
- `GET /history` (all stored sensor values)
- `GET /sensordaten` (all stored sensor values, alias for `/history`)
