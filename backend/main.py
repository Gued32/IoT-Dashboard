#!/usr/bin/env python3
import json
import logging
import os
import ssl
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Generator, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ValidationError

import paho.mqtt.client as mqtt
from backend.email_alert import send_email_alert


def format_email_sensor_type(sensor_id: str) -> str:
    sensor_types = {
        "bme280_1": "BME280 1 - Temperatur/Luftfeuchtigkeit/Luftdruck-Sensor (Sensor_1)",
        "bme280_2": "BME280 2 - Temperatur/Luftfeuchtigkeit/Luftdruck-Sensor (Sensor_2)",
        "mq2_1": "MQ2 1 - Gas-/Rauchüberwachung-Sensor (Sensor_3)",
    }

    return sensor_types.get(
        sensor_id,
        sensor_id.upper().replace("_", " "),
    )


BASE_DIR = Path(__file__).resolve().parents[1]
DB_PATH = BASE_DIR / "database" / "iot_dashboard.db"
MQTT_BROKER = os.getenv("MQTT_BROKER", "localhost")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))
MQTT_TOPIC = os.getenv("MQTT_TOPIC", "sensors/data")
MQTT_KEEPALIVE = int(os.getenv("MQTT_KEEPALIVE", "60"))
MQTT_CLIENT_ID = os.getenv("MQTT_CLIENT_ID", "iot-dashboard-backend")
MQTT_USERNAME = os.getenv("MQTT_USERNAME")
MQTT_PASSWORD = os.getenv("MQTT_PASSWORD")
MQTT_TLS_ENV = os.getenv("MQTT_TLS", "").strip().lower()
MQTT_TLS = (
    MQTT_TLS_ENV in {"1", "true", "yes", "on"}
    if MQTT_TLS_ENV
    else MQTT_PORT == 8883 or bool(MQTT_USERNAME)
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


def init_db() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
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
    properties: mqtt.Properties | None,
) -> None:
    del userdata, flags, properties
    if reason_code.value != 0:
        logger.error("MQTT connection failed. reason_code=%s", reason_code)
        return
    client.subscribe(MQTT_TOPIC, qos=0)
    logger.info("Subscribed to MQTT topic '%s'.", MQTT_TOPIC)


def on_mqtt_message(client: mqtt.Client, userdata: object, msg: mqtt.MQTTMessage) -> None:
    del client, userdata
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

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        cursor.execute(
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
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                sensor_data.sensor_id,
                sensor_data.sensor_type,
                sensor_data.timestamp,
                sensor_data.temperature_c,
                sensor_data.humidity_percent,
                sensor_data.pressure_hpa,
                sensor_data.gas_value,
                smoke_warning_value,
                0,
            ),
        )
        inserted_row_id = cursor.lastrowid

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

Sensortyp: {format_email_sensor_type(sensor_data.sensor_id)}
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

            email_sent = send_email_alert(
                subject="IoT Dashboard Warnung: Grenzwert überschritten",
                body=body,
            )

        cursor.execute(
            "UPDATE sensor_data SET email_sent = ? WHERE id = ?",
            (1 if email_sent else 0, inserted_row_id),
        )
        conn.commit()

        conn.close()

    except Exception as e:
        print(f"Failed to persist MQTT payload on topic '{topic}': {e}")


def start_mqtt_listener() -> mqtt.Client | None:
    client = mqtt.Client(
        callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
        client_id=MQTT_CLIENT_ID,
    )
    client.on_connect = on_mqtt_connect
    client.on_message = on_mqtt_message

    if MQTT_USERNAME:
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
