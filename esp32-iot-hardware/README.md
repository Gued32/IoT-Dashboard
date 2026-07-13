# ESP32 IoT Hardware

Dieser Ordner enthaelt den MicroPython-Code fuer den ESP32 mit BME280- und MQ-2-Sensoren.

Vor dem Hochladen auf den ESP32:

1. `config.example.py` kopieren.
2. Die Kopie in `config.py` umbenennen.
3. WLAN- und MQTT-Zugangsdaten in `config.py` eintragen.

`config.py` wird absichtlich nicht versioniert, damit keine Zugangsdaten nach GitHub gelangen.
