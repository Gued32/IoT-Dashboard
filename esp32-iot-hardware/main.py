import network
import time
import machine
import ubinascii
import ujson
from machine import Pin, I2C, ADC
from umqtt.simple import MQTTClient

from config import (
    WIFI_SSID,
    WIFI_PASSWORD,
    MQTT_BROKER,
    MQTT_PORT,
    MQTT_USERNAME,
    MQTT_PASSWORD,
)

from bme280 import BME280


# =========================
# Einstellungen
# =========================

I2C_SDA_PIN = 21
I2C_SCL_PIN = 22

BME280_1_ADDRESS = 0x76
BME280_2_ADDRESS = 0x77

MQ2_ADC_PIN = 34

# MQ-2 Grenzwert: bei Fehlalarm höher setzen, z.B. 3000 oder 3500
GAS_WARNING_LIMIT = 1000

SEND_INTERVAL_SECONDS = 10

# Temperatur-Korrektur für BME280 Sensoren
# Beispiel: Wenn Sensor 27.0 °C zeigt, aber real 20.0 °C ist, dann Offset = -7.0
BME280_TEMP_OFFSETS = {
    "bme280_1": -10.0,
    "bme280_2": -10.0,
}


# =========================
# WLAN
# =========================

def connect_wifi():
    wlan = network.WLAN(network.STA_IF)

    print("WLAN wird zurückgesetzt...")
    wlan.active(False)
    time.sleep(2)

    wlan.active(True)
    time.sleep(2)

    try:
        wlan.disconnect()
        time.sleep(1)
    except Exception:
        pass

    print("Verbinde mit WLAN...")
    print("SSID:", WIFI_SSID)

    wlan.connect(WIFI_SSID, WIFI_PASSWORD)

    timeout = 30

    while timeout > 0:
        status = wlan.status()
        print("WLAN Status:", status)

        if wlan.isconnected():
            print("WLAN verbunden:", wlan.ifconfig())
            return wlan

        time.sleep(1)
        timeout -= 1

    print("WLAN konnte nicht verbunden werden.")
    raise OSError("WLAN Verbindung fehlgeschlagen")


# =========================
# MQTT
# =========================

def connect_mqtt():
    client_id = b"esp32-" + ubinascii.hexlify(machine.unique_id())

    print("Verbinde mit MQTT...")
    print("MQTT Broker:", MQTT_BROKER)
    print("MQTT Port:", MQTT_PORT)

    if MQTT_PORT == 8883:
        print("MQTT mit TLS/SSL")
        client = MQTTClient(
            client_id=client_id,
            server=MQTT_BROKER,
            port=MQTT_PORT,
            user=MQTT_USERNAME,
            password=MQTT_PASSWORD,
            ssl=True,
            ssl_params={"server_hostname": MQTT_BROKER},
        )
    else:
        print("MQTT ohne TLS/SSL")
        client = MQTTClient(
            client_id=client_id,
            server=MQTT_BROKER,
            port=MQTT_PORT,
            user=MQTT_USERNAME,
            password=MQTT_PASSWORD,
            ssl=False,
        )

    client.connect()
    print("MQTT verbunden")
    return client


def publish_sensor_data(client, topic, payload):
    message = ujson.dumps(payload)
    client.publish(topic, message)
    print("Gesendet an", topic)
    print(message)


# =========================
# BME280
# =========================

def parse_bme280_values(values):
    """
    Viele MicroPython-BME280-Libraries liefern:
    values = ("24.50C", "1012.34hPa", "45.67%")
    Diese Funktion wandelt das in Zahlen um.
    """
    temperature = float(values[0].replace("C", "").strip())
    pressure = float(values[1].replace("hPa", "").strip())
    humidity = float(values[2].replace("%", "").strip())

    return temperature, pressure, humidity


def apply_temperature_offset(sensor_id, temperature):
    offset = BME280_TEMP_OFFSETS.get(sensor_id, 0)
    return temperature + offset


def read_bme280(sensor, sensor_id):
    temperature = None
    pressure = None
    humidity = None

    # Variante 1: sensor.values, z.B. ("24.50C", "1012.34hPa", "45.67%")
    try:
        values = sensor.values
        temperature, pressure, humidity = parse_bme280_values(values)
    except Exception:
        pass

    # Variante 2: read_compensated_data() mit automatischer Skalierung
    if temperature is None:
        try:
            raw = sensor.read_compensated_data()

            temperature = float(raw[0])
            pressure = float(raw[1])
            humidity = float(raw[2])

            # Temperatur korrigieren
            # Manche Libraries liefern 2450 für 24.50 °C
            if abs(temperature) > 100:
                temperature = temperature / 100

            # Luftdruck korrigieren
            # Manche Libraries liefern Pa, z.B. 101325
            # Dashboard braucht hPa, z.B. 1013.25
            if pressure > 20000:
                pressure = pressure / 100
            elif pressure > 2000000:
                pressure = pressure / 25600

            # Luftfeuchtigkeit korrigieren
            # Manche Libraries liefern 51200 für 50 %
            if humidity > 1000:
                humidity = humidity / 1024

        except Exception as e:
            print("BME280 Lesefehler:", e)
            temperature = 0
            pressure = 0
            humidity = 0

    temperature_corrected = apply_temperature_offset(sensor_id, temperature)

    payload = {
        "sensor_type": "BME280",
        "sensor_id": sensor_id,
        "temperature_c": round(temperature_corrected, 2),
        "humidity_percent": round(humidity, 2),
        "pressure_hpa": round(pressure, 2),
        "gas_value": None,
        "smoke_warning": False,
    }

    return payload


# =========================
# MQ-2
# =========================

def setup_mq2():
    mq2 = ADC(Pin(MQ2_ADC_PIN))
    mq2.atten(ADC.ATTN_11DB)      # Messbereich bis ca. 3.3V
    mq2.width(ADC.WIDTH_12BIT)    # Wertebereich 0 bis 4095
    return mq2


def read_mq2_average(mq2, samples=20):
    total = 0

    for _ in range(samples):
        total += mq2.read()
        time.sleep(0.05)

    return total // samples


def read_mq2(mq2):
    gas_value = read_mq2_average(mq2)
    smoke_warning = gas_value > GAS_WARNING_LIMIT

    payload = {
        "sensor_type": "MQ2",
        "sensor_id": "mq2_1",
        "temperature_c": None,
        "humidity_percent": None,
        "pressure_hpa": None,
        "gas_value": gas_value,
        "smoke_warning": smoke_warning,
    }

    return payload


# =========================
# Hauptprogramm
# =========================

def main():
    print("MAIN.PY STARTET")

    connect_wifi()

    i2c = I2C(
        0,
        sda=Pin(I2C_SDA_PIN),
        scl=Pin(I2C_SCL_PIN),
        freq=100000,
    )

    print("I2C Geräte:", i2c.scan())

    bme280_1 = None
    bme280_2 = None

    try:
        bme280_1 = BME280(i2c=i2c, address=BME280_1_ADDRESS)
        print("BME280_1 gefunden auf Adresse 0x76")
    except Exception as e:
        print("BME280_1 Fehler:", e)

    try:
        bme280_2 = BME280(i2c=i2c, address=BME280_2_ADDRESS)
        print("BME280_2 gefunden auf Adresse 0x77")
    except Exception as e:
        print("BME280_2 Fehler:", e)

    mq2 = setup_mq2()
    print("MQ-2 ADC bereit auf GPIO34")

    client = connect_mqtt()

    while True:
        try:
            if bme280_1 is not None:
                data_1 = read_bme280(bme280_1, "bme280_1")
                publish_sensor_data(client, "sensors/bme280_1", data_1)

            if bme280_2 is not None:
                data_2 = read_bme280(bme280_2, "bme280_2")
                publish_sensor_data(client, "sensors/bme280_2", data_2)

            data_mq2 = read_mq2(mq2)
            publish_sensor_data(client, "sensors/mq2_1", data_mq2)

            print("ESP32 läuft...")
            time.sleep(SEND_INTERVAL_SECONDS)

        except Exception as e:
            print("Fehler im Hauptloop:", e)
            print("Versuche MQTT neu zu verbinden...")
            time.sleep(5)

            try:
                client = connect_mqtt()
            except Exception as mqtt_error:
                print("MQTT reconnect fehlgeschlagen:", mqtt_error)
                time.sleep(10)


main()
