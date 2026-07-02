#!/usr/bin/env python3
import json
import logging
import os
import ssl
import sqlite3
from contextlib import closing, contextmanager
from pathlib import Path
from typing import Dict, Generator, List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ValidationError

import paho.mqtt.client as mqtt
import requests


SENSOR_DISPLAY_NAMES = {
    "bme280_1": "BME280_1 - Temperatur/Luftfeuchtigkeit/Luftdruck-Sensor",
    "bme280_2": "BME280_2 - Temperatur/Luftfeuchtigkeit/Luftdruck-Sensor",
    "mq2_1": "MQ2_1 - Gas-/Rauchüberwachung-Sensor",
}


def get_sensor_display_name(sensor_id: str) -> str:
    return SENSOR_DISPLAY_NAMES.get(sensor_id, sensor_id)


BASE_DIR = Path(__file__).resolve().parents[1]
DB_PATH = BASE_DIR / "database" / "iot_dashboard.db"
MQTT_BROKER = os.getenv("MQTT_BROKER", "localhost")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))
MQTT_TOPIC = os.getenv("MQTT_TOPIC", "sensors/data")
MQTT_KEEPALIVE = int(os.getenv("MQTT_KEEPALIVE", "60"))
MQTT_CLIENT_ID = os.getenv("MQTT_CLIENT_ID", "iot-dashboard-backend")
MQTT_USERNAME = os.getenv("MQTT_BACKEND_USERNAME") or os.getenv("MQTT_USERNAME")
MQTT_PASSWORD = os.getenv("MQTT_BACKEND_PASSWORD") or os.getenv("MQTT_PASSWORD")
MQTT_TLS_ENV = os.getenv("MQTT_TLS", "").strip().lower()
MQTT_TLS = (
    MQTT_TLS_ENV in {"1", "true", "yes", "on"}
    if MQTT_TLS_ENV
    else MQTT_PORT == 8883
)

TEMP_LIMIT = 30
HUMIDITY_LIMIT = 70
PRESSURE_HIGH_LIMIT = 1030

logger = logging.getLogger(__name__)

app = FastAPI(title="IoT Dashboard Backend", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
mqtt_client: mqtt.Client | None = None


class SensorData(BaseModel):
    sensor_id: str
    sensor_type: str
    timestamp: str
    temperature_c: Optional[float] = None
    humidity_percent: Optional[float] = None
    pressure_hpa: Optional[float] = None
    gas_value: Optional[int] = None
    smoke_warning: Optional[bool] = None
    email_sent: bool = False


class MLAlertEmailRequest(BaseModel):
    sensor_id: str
    prediction_minutes: int
    warnings: List[str]
    current_values: Dict[str, Optional[float]]
    predicted_values: Dict[str, Optional[float]]


def send_email_via_resend(subject: str, body: str) -> bool:
    resend_api_key = os.getenv("RESEND_API_KEY")
    email_from = os.getenv("EMAIL_FROM", "IoT Dashboard <onboarding@resend.dev>")
    email_receiver = os.getenv("EMAIL_RECEIVER")

    if not resend_api_key or not email_receiver:
        print("Email skipped: missing RESEND_API_KEY or EMAIL_RECEIVER")
        return False

    try:
        response = requests.post(
            "https://api.resend.com/emails",
            headers={
                "Authorization": f"Bearer {resend_api_key}",
                "Content-Type": "application/json",
            },
            json={
                "from": email_from,
                "to": [email_receiver],
                "subject": subject,
                "text": body,
            },
            timeout=15,
        )

        if response.status_code in [200, 201]:
            print("ML prediction alert email sent successfully")
            return True

        print(f"Resend email error: {response.status_code} - {response.text}")
        return False

    except Exception as e:
        print(f"Resend email exception: {e}")
        return False


def init_db() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(DB_PATH)) as conn, conn:
        table_info = conn.execute("PRAGMA table_info(sensor_data)").fetchall()
        desired_columns = {
            "id",
            "sensor_id",
            "sensor_type",
            "timestamp",
            "temperature_c",
            "humidity_percent",
            "pressure_hpa",
            "gas_value",
            "smoke_warning",
            "email_sent",
        }

        def create_table(table_name: str) -> None:
            conn.execute(
                f"""
                CREATE TABLE IF NOT EXISTS {table_name} (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    sensor_id TEXT NOT NULL,
                    sensor_type TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    temperature_c REAL,
                    humidity_percent REAL,
                    pressure_hpa REAL,
                    gas_value INTEGER,
                    smoke_warning INTEGER,
                    email_sent INTEGER NOT NULL DEFAULT 0
                )
                """
            )

        if not table_info:
            create_table("sensor_data")
        else:
            columns = {row[1]: row for row in table_info}
            needs_migration = not desired_columns.issubset(columns.keys())
            for column_name in ("temperature_c", "humidity_percent"):
                if column_name in columns and columns[column_name][3] == 1:
                    needs_migration = True
            if "sensor_type" in columns and columns["sensor_type"][3] == 0:
                needs_migration = True

            if needs_migration:
                create_table("sensor_data_new")
                existing_column_names = set(columns.keys())
                select_parts = [
                    "id",
                    "sensor_id" if "sensor_id" in existing_column_names else "'sensor_unknown' AS sensor_id",
                    "sensor_type" if "sensor_type" in existing_column_names else "'unknown' AS sensor_type",
                    "timestamp" if "timestamp" in existing_column_names else "'' AS timestamp",
                    "temperature_c"
                    if "temperature_c" in existing_column_names
                    else "NULL AS temperature_c",
                    "humidity_percent"
                    if "humidity_percent" in existing_column_names
                    else "NULL AS humidity_percent",
                    "pressure_hpa"
                    if "pressure_hpa" in existing_column_names
                    else "NULL AS pressure_hpa",
                    "gas_value" if "gas_value" in existing_column_names else "NULL AS gas_value",
                    "smoke_warning"
                    if "smoke_warning" in existing_column_names
                    else "NULL AS smoke_warning",
                    "email_sent" if "email_sent" in existing_column_names else "0 AS email_sent",
                ]
                conn.execute(
                    f"""
                    INSERT INTO sensor_data_new (
                        id,
                        sensor_id,
                        sensor_type,
                        timestamp,
                        temperature_c,
                        humidity_percent,
                        pressure_hpa,
                        gas_value,
                        smoke_warning,
                        email_sent
                    )
                    SELECT {", ".join(select_parts)}
                    FROM sensor_data
                    """
                )
                conn.execute("DROP TABLE sensor_data")
                conn.execute("ALTER TABLE sensor_data_new RENAME TO sensor_data")
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_sensor_data_sensor_id ON sensor_data(sensor_id)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_sensor_data_timestamp ON sensor_data(timestamp DESC)"
        )
        conn.commit()


@contextmanager
def db_connection() -> Generator[sqlite3.Connection, None, None]:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def on_mqtt_connect(
    client: mqtt.Client,
    userdata: object,
    flags: mqtt.ConnectFlags,
    reason_code: mqtt.ReasonCode,
    properties: mqtt.Properties | None = None,
) -> None:
    del userdata, flags, properties
    if reason_code.value != 0:
        print(f"MQTT connection failed. reason_code={reason_code}")
        return

    print("MQTT connected successfully")
    client.subscribe(MQTT_TOPIC, qos=0)
    print(f"MQTT subscribed to {MQTT_TOPIC}")


def on_mqtt_message(client: mqtt.Client, userdata: object, msg: mqtt.MQTTMessage) -> None:
    del client, userdata
    print(f"MQTT message received: topic={msg.topic}, payload={msg.payload}")

    try:
        payload = json.loads(msg.payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        logger.error("Invalid MQTT payload on topic '%s': %s", msg.topic, exc)
        return

    try:
        sensor_data = SensorData.model_validate(payload)
    except ValidationError as exc:
        logger.error("Invalid MQTT payload on topic '%s': %s", msg.topic, exc)
        return

    topic = msg.topic
    try:
        smoke_warning_value = None
        if sensor_data.smoke_warning is not None:
            smoke_warning_value = 1 if sensor_data.smoke_warning else 0

        alerts = []

        if sensor_data.temperature_c is not None and sensor_data.temperature_c > TEMP_LIMIT:
            alerts.append(f"Temperatur zu hoch: {sensor_data.temperature_c:.2f} °C")

        if sensor_data.humidity_percent is not None and sensor_data.humidity_percent > HUMIDITY_LIMIT:
            alerts.append(f"Luftfeuchtigkeit zu hoch: {sensor_data.humidity_percent:.2f} %")

        if sensor_data.pressure_hpa is not None and sensor_data.pressure_hpa > PRESSURE_HIGH_LIMIT:
            alerts.append(f"Luftdruck zu hoch: {sensor_data.pressure_hpa:.2f} hPa")

        if sensor_data.smoke_warning is True:
            alerts.append("Rauchwarnung erkannt")

        temperature_text = (
            f"{sensor_data.temperature_c:.2f} °C"
            if sensor_data.temperature_c is not None
            else "-"
        )

        humidity_text = (
            f"{sensor_data.humidity_percent:.2f} %"
            if sensor_data.humidity_percent is not None
            else "-"
        )

        pressure_text = (
            f"{sensor_data.pressure_hpa:.2f} hPa"
            if sensor_data.pressure_hpa is not None
            else "-"
        )

        gas_text = (
            str(sensor_data.gas_value)
            if sensor_data.gas_value is not None
            else "-"
        )

        smoke_text = "Ja" if sensor_data.smoke_warning is True else "Nein"

        email_sent = False

        if alerts:
            body = f"""
IoT Dashboard Warnung: Grenzwert überschritten

Sensortyp: {get_sensor_display_name(sensor_data.sensor_id)}
Zeit: {sensor_data.timestamp}

Messwerte:
Temperatur: {temperature_text}
Luftfeuchtigkeit: {humidity_text}
Luftdruck: {pressure_text}
Gaswert: {gas_text}
Rauchwarnung: {smoke_text}

Ausgelöste Warnungen:
{chr(10).join("- " + alert for alert in alerts)}
"""

            email_sent = send_email_via_resend(
                subject="IoT Dashboard Warnung: Grenzwert überschritten",
                body=body,
            )

        sensor_record = {
            "sensor_id": sensor_data.sensor_id,
            "sensor_type": sensor_data.sensor_type,
            "timestamp": sensor_data.timestamp,
            "temperature_c": sensor_data.temperature_c,
            "humidity_percent": sensor_data.humidity_percent,
            "pressure_hpa": sensor_data.pressure_hpa,
            "gas_value": sensor_data.gas_value,
            "smoke_warning": smoke_warning_value,
            "email_sent": email_sent,
        }

        with db_connection() as conn:
            conn.execute(
                """
                INSERT INTO sensor_data (
                    sensor_id,
                    sensor_type,
                    timestamp,
                    temperature_c,
                    humidity_percent,
                    pressure_hpa,
                    gas_value,
                    smoke_warning,
                    email_sent
                )
                VALUES (
                    :sensor_id,
                    :sensor_type,
                    :timestamp,
                    :temperature_c,
                    :humidity_percent,
                    :pressure_hpa,
                    :gas_value,
                    :smoke_warning,
                    :email_sent
                )
                """,
                sensor_record,
            )
            conn.commit()

    except Exception as e:
        print(f"Failed to persist MQTT payload on topic '{topic}': {e}")


def start_mqtt_listener() -> mqtt.Client | None:
    client = mqtt.Client(
        callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
        client_id=MQTT_CLIENT_ID,
    )
    client.on_connect = on_mqtt_connect
    client.on_message = on_mqtt_message

    if MQTT_USERNAME and MQTT_PASSWORD:
        client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)

    if MQTT_TLS:
        client.tls_set(tls_version=ssl.PROTOCOL_TLS_CLIENT)

    try:
        client.connect(MQTT_BROKER, MQTT_PORT, MQTT_KEEPALIVE)
    except OSError as exc:
        logger.error(
            "MQTT listener not started. Could not connect to %s:%d (%s).",
            MQTT_BROKER,
            MQTT_PORT,
            exc,
        )
        return None
    client.loop_start()
    logger.info("MQTT listener started on %s:%d topic=%s", MQTT_BROKER, MQTT_PORT, MQTT_TOPIC)
    return client


@app.on_event("startup")
def on_startup() -> None:
    global mqtt_client
    init_db()
    mqtt_client = start_mqtt_listener()


@app.on_event("shutdown")
def on_shutdown() -> None:
    global mqtt_client
    if mqtt_client is None:
        return
    mqtt_client.loop_stop()
    mqtt_client.disconnect()
    mqtt_client = None


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


ML_EMAIL_SENSOR_NAMES = {
    "bme280_1": "BME280_1 - Temperatur/Luftfeuchtigkeit/Luftdruck-Sensor (Sensor_1)",
    "bme280_2": "BME280_2 - Temperatur/Luftfeuchtigkeit/Luftdruck-Sensor (Sensor_2)",
    "mq2_1": "MQ2_1 - Gas-/Rauchüberwachung-Sensor (Sensor_3)",
}


def get_ml_email_sensor_name(sensor_id: str) -> str:
    return ML_EMAIL_SENSOR_NAMES.get(sensor_id, sensor_id)


@app.post("/ml-alert-email")
def send_ml_alert_email(alert: MLAlertEmailRequest) -> dict:
    warnings_text = "\n".join([f"- {warning}" for warning in alert.warnings])
    current_values = alert.current_values
    predicted_values = alert.predicted_values

    body = f"""
IoT Dashboard ML-Warnung: Vorhersage-Grenzwert überschritten

Sensortyp: {get_ml_email_sensor_name(alert.sensor_id)}
Vorhersagezeitraum: in {alert.prediction_minutes} Minuten

Aktuelle Messwerte:
Temperatur: {current_values.get("temperature_c")} °C
Luftfeuchtigkeit: {current_values.get("humidity_percent")} %
Luftdruck: {current_values.get("pressure_hpa")} hPa
Gaswert: {current_values.get("gas_value")}

ML-Vorhersage:
Temperatur in {alert.prediction_minutes} Minuten: {predicted_values.get("temperature_c")} °C
Luftfeuchtigkeit in {alert.prediction_minutes} Minuten: {predicted_values.get("humidity_percent")} %
Luftdruck in {alert.prediction_minutes} Minuten: {predicted_values.get("pressure_hpa")} hPa
Gaswert in {alert.prediction_minutes} Minuten: {predicted_values.get("gas_value")}

Ausgelöste ML-Warnungen:
{warnings_text}
"""
    subject = "IoT Dashboard ML-Warnung: Vorhersage-Grenzwert überschritten"
    email_sent = send_email_via_resend(subject, body)

    return {
        "email_sent": email_sent,
        "message": "ML alert email sent" if email_sent else "ML alert email not sent",
    }


@app.get("/sensor-data", response_model=SensorData)
def get_latest_sensor_data() -> SensorData:
    with db_connection() as conn:
        row = conn.execute(
            """
            SELECT sensor_id,
                   sensor_type,
                   timestamp,
                   temperature_c,
                   humidity_percent,
                   pressure_hpa,
                   gas_value,
                   smoke_warning,
                   email_sent
            FROM sensor_data
            ORDER BY timestamp DESC, id DESC
            LIMIT 1
            """
        ).fetchone()

    if row is None:
        raise HTTPException(status_code=404, detail="No sensor data available.")

    return SensorData(
        sensor_id=row["sensor_id"],
        sensor_type=row["sensor_type"],
        timestamp=row["timestamp"],
        temperature_c=row["temperature_c"],
        humidity_percent=row["humidity_percent"],
        pressure_hpa=row["pressure_hpa"],
        gas_value=row["gas_value"],
        smoke_warning=(
            bool(row["smoke_warning"]) if row["smoke_warning"] is not None else None
        ),
        email_sent=bool(row["email_sent"]),
    )


@app.get("/history", response_model=list[SensorData])
@app.get("/sensordaten", response_model=list[SensorData])
def get_sensor_history() -> list[SensorData]:
    with db_connection() as conn:
        rows = conn.execute(
            """
            SELECT sensor_id,
                   sensor_type,
                   timestamp,
                   temperature_c,
                   humidity_percent,
                   pressure_hpa,
                   gas_value,
                   smoke_warning,
                   email_sent
            FROM sensor_data
            ORDER BY timestamp DESC, id DESC
            """
        ).fetchall()

    return [
        SensorData(
            sensor_id=row["sensor_id"],
            sensor_type=row["sensor_type"],
            timestamp=row["timestamp"],
            temperature_c=row["temperature_c"],
            humidity_percent=row["humidity_percent"],
            pressure_hpa=row["pressure_hpa"],
            gas_value=row["gas_value"],
            smoke_warning=(
                bool(row["smoke_warning"]) if row["smoke_warning"] is not None else None
            ),
            email_sent=bool(row["email_sent"]),
        )
        for row in rows
    ]
