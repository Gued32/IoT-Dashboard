import json
import os
import random
import ssl
import time
from datetime import datetime
from zoneinfo import ZoneInfo

import paho.mqtt.client as mqtt

MQTT_BROKER = os.getenv("MQTT_BROKER", "localhost")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))
MQTT_TOPIC = os.getenv("MQTT_TOPIC", "sensors/data")
MQTT_KEEPALIVE = int(os.getenv("MQTT_KEEPALIVE", "60"))
MQTT_USERNAME = os.getenv("MQTT_SENSOR_USERNAME") or os.getenv("MQTT_USERNAME")
MQTT_PASSWORD = os.getenv("MQTT_SENSOR_PASSWORD") or os.getenv("MQTT_PASSWORD")
MQTT_TLS_ENV = os.getenv("MQTT_TLS", "").strip().lower()
MQTT_TLS = (
    MQTT_TLS_ENV in {"1", "true", "yes", "on"}
    if MQTT_TLS_ENV
    else MQTT_PORT == 8883
)

PUBLISH_INTERVAL = 5  # Sekunden
mqtt_connected = False


def on_connect(client, userdata, flags, rc):
    global mqtt_connected

    if rc == 0:
        mqtt_connected = True
        print("Sensor MQTT connected successfully", flush=True)
    elif rc == 4:
        mqtt_connected = False
        print("Sensor MQTT connection failed: bad username or password", flush=True)
    elif rc == 5:
        mqtt_connected = False
        print("Sensor MQTT connection failed: not authorized", flush=True)
    else:
        mqtt_connected = False
        print(f"Sensor MQTT connection failed with code {rc}", flush=True)


def on_disconnect(client, userdata, rc):
    global mqtt_connected

    mqtt_connected = False
    if rc != 0:
        print(f"Sensor MQTT disconnected with code {rc}", flush=True)


def generate_bme280_data(sensor_id: str) -> dict:
    return {
        "sensor_id": sensor_id,
        "sensor_type": "BME280",
        "temperature_c": round(random.uniform(18.0, 35.0), 2),
        "humidity_percent": round(random.uniform(30.0, 85.0), 2),
        "pressure_hpa": round(random.uniform(980.0, 1030.0), 2),
        "timestamp": datetime.now(ZoneInfo("Europe/Berlin")).isoformat(),
    }


def generate_mq2_data(sensor_id: str) -> dict:
    gas_value = random.randint(200, 2500)

    return {
        "sensor_id": sensor_id,
        "sensor_type": "MQ2",
        "gas_value": gas_value,
        "smoke_warning": gas_value > 1800,
        "timestamp": datetime.now(ZoneInfo("Europe/Berlin")).isoformat(),
    }


def main():
    client = mqtt.Client()
    client.on_connect = on_connect
    client.on_disconnect = on_disconnect

    if MQTT_USERNAME and MQTT_PASSWORD:
        client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)

    if MQTT_TLS:
        client.tls_set(tls_version=ssl.PROTOCOL_TLS_CLIENT)

    while True:
        try:
            client.connect(MQTT_BROKER, MQTT_PORT, MQTT_KEEPALIVE)
            client.loop_start()
            print("MQTT connection request sent.", flush=True)
            break
        except Exception as e:
            print(f"MQTT broker not ready yet: {e}", flush=True)
            time.sleep(2)

    print("Sensor simulator started...")

    while True:
        if not mqtt_connected:
            print("Sensor not connected. Data not sent.", flush=True)
            time.sleep(PUBLISH_INTERVAL)
            continue

        sensor_messages = [
            generate_bme280_data("bme280_1"),
            generate_bme280_data("bme280_2"),
            generate_mq2_data("mq2_1"),
        ]

        for data in sensor_messages:
            client.publish(MQTT_TOPIC, json.dumps(data))
            print("Sent:", data)

        time.sleep(PUBLISH_INTERVAL)


if __name__ == "__main__":
    main()
