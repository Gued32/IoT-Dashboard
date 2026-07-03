\# IoT Dashboard – Wichtige Projektschritte und Fehlerbehebung



\## 1. Projektziel



Dieses Projekt zeigt echte Sensordaten von einem ESP32 in einem Online-Dashboard an.



Verwendete Sensoren:



\* BME280 Sensor 1 für Temperatur, Luftfeuchtigkeit und Luftdruck

\* BME280 Sensor 2 für Temperatur, Luftfeuchtigkeit und Luftdruck

\* MQ-2 Sensor für Gas-/Rauch-Erkennung



Die Sensordaten werden per MQTT übertragen und im Dashboard visualisiert.



\---



\## 2. Finale Architektur



Die finale Datenkette lautet:



```text

ESP32 Sensoren → HiveMQ Cloud → Railway Backend → Railway Frontend Dashboard

```



Beschreibung:



\* Der ESP32 liest die echten Sensorwerte.

\* Der ESP32 sendet die Daten per MQTT an HiveMQ Cloud.

\* Das Railway Backend abonniert die MQTT-Topics.

\* Das Backend speichert die Messwerte.

\* Das Railway Frontend zeigt die Daten im Dashboard an.



Wichtige URLs:



```text

Frontend Dashboard:

https://iot-dashboard-production-da48.up.railway.app



Backend API:

https://backend-production-4878.up.railway.app



Sensordaten Endpoint:

https://backend-production-4878.up.railway.app/sensordaten

```



\---



\## 3. Hardware-Aufbau



\### ESP32



Als Mikrocontroller wurde ein ESP32 DevKit verwendet.



\### BME280 Sensoren



Zwei BME280 Sensoren wurden über I2C angeschlossen.



Verkabelung:



```text

BME280 VCC/VIN → ESP32 3V3

BME280 GND     → ESP32 GND

BME280 SDA     → ESP32 GPIO21

BME280 SCL     → ESP32 GPIO22

```



Die erkannten I2C-Adressen waren:



```text

BME280\_1 → 0x76

BME280\_2 → 0x77

```



Im Serial Monitor wurde angezeigt:



```text

I2C Geräte: \[118, 119]

```



Das bedeutet:



```text

118 = 0x76

119 = 0x77

```



Damit wurden beide BME280 Sensoren korrekt erkannt.



\### MQ-2 Sensor



Der MQ-2 Sensor wurde für Gas-/Rauchwerte verwendet.



Verkabelung:



```text

MQ-2 VCC  → ESP32 VIN/5V

MQ-2 GND  → ESP32 GND

MQ-2 AOUT → Spannungsteiler → ESP32 GPIO34

```



Wichtig:



```text

GPIO34 vom ESP32 darf maximal 3.3V bekommen.

MQ-2 AOUT darf nicht direkt mit 5V auf GPIO34 verbunden werden.

```



\---



\## 4. Lokale Docker-Umgebung



Für lokale Tests wurden Docker-Container verwendet:



```text

mqtt      → Mosquitto MQTT Broker

backend   → FastAPI Backend

frontend  → Streamlit Dashboard

sensor    → Docker-Simulator

```



Lokale Services starten:



```powershell

cd C:\\Users\\guedr\\iot-dashboard

docker compose up -d mqtt backend frontend

docker compose stop sensor

docker compose ps

```



Beschreibung:



\* `mqtt`, `backend` und `frontend` müssen laufen.

\* `sensor` muss gestoppt werden, wenn echte ESP32-Daten verwendet werden.

\* Sonst zeigt das Dashboard simulierte Werte statt echte Sensorwerte.



\---



\## 5. MicroPython auf ESP32 installieren



Der ESP32 wurde zuerst gelöscht:



```powershell

py -m esptool --chip esp32 --port COM3 --baud 115200 erase-flash

```



Danach wurde MicroPython installiert:



```powershell

py -m esptool --chip esp32 --port COM3 --baud 115200 write-flash --flash-mode dio --flash-freq 40m --flash-size 4MB -z 0x1000 .\\ESP32\_GENERIC-20260406-v1.28.0.bin

```



Danach wurden die Projektdateien auf den ESP32 kopiert:



```powershell

cd C:\\Users\\guedr\\esp32-iot-hardware



py -m mpremote connect COM3 fs cp .\\config.py :config.py

py -m mpremote connect COM3 fs cp .\\bme280.py :bme280.py

py -m mpremote connect COM3 fs cp .\\main.py :main.py

```



Wichtig:



```text

Der Serial Monitor muss geschlossen sein, bevor mpremote verwendet wird.

Sonst ist COM3 blockiert.

```



\---



\## 6. ESP32 Konfiguration



Datei:



```text

C:\\Users\\guedr\\esp32-iot-hardware\\config.py

```



Für das Online-Dashboard muss der ESP32 an HiveMQ Cloud senden:



```python

WIFI\_SSID = "ESP32\_TEST"

WIFI\_PASSWORD = "DEIN\_WLAN\_PASSWORT"



MQTT\_BROKER = "ec53cff1a655417a8246e130835c8427.s1.eu.hivemq.cloud"

MQTT\_PORT = 8883

MQTT\_USERNAME = "Sensor\_user"

MQTT\_PASSWORD = "DEIN\_SENSOR\_USER\_PASSWORT"

```



Beschreibung:



\* `Sensor\_user` wird nur vom ESP32 verwendet.

\* Der ESP32 darf MQTT-Nachrichten publishen.

\* Das Backend verwendet einen anderen Benutzer: `Railway\_backend`.



\---



\## 7. MQTT Topics



Der ESP32 sendet an diese Topics:



```text

sensors/bme280\_1

sensors/bme280\_2

sensors/mq2\_1

```



Beschreibung:



\* Jeder Sensor hat ein eigenes MQTT-Topic.

\* Das Backend muss alle Topics unter `sensors/` abonnieren.



\---



\## 8. Problem: Docker-Simulator sendet falsche Werte



\### Beschreibung



Am Anfang wurden im Dashboard Werte angezeigt, obwohl die echten Sensoren noch nicht korrekt verbunden waren.



\### Ursache



Der Docker-Simulator lief noch und sendete künstliche Sensordaten.



\### Lösung



Simulator stoppen:



```powershell

cd C:\\Users\\guedr\\iot-dashboard

docker compose stop sensor

```



Prüfen:



```powershell

docker compose ps

```



Erwartung:



```text

mqtt      läuft

backend   läuft

frontend  läuft

sensor    gestoppt

```



\---



\## 9. Problem: Lokaler MQTT Broker nicht erreichbar



\### Beschreibung



Der ESP32 sollte zuerst lokal an Mosquitto auf Port `1883` senden.



Im Serial Monitor erschien:



```text

MQTT ohne TLS/SSL

OSError: \[Errno 104] ECONNRESET

```



\### Ursache



Der lokale MQTT-Broker war aus dem ESP32-Netzwerk nicht erreichbar. PC und ESP32 waren nicht im gleichen erreichbaren Netzwerk oder Windows Firewall/Hotspot blockierte die Verbindung.



\### Test



```powershell

Test-NetConnection 10.144.74.227 -Port 1883

```



Das Ergebnis war:



```text

TcpTestSucceeded : False

```



\### Lösung



Für das Projekt wurde die stabilere Cloud-Lösung benutzt:



```text

ESP32 → HiveMQ Cloud → Railway Backend → Online Dashboard

```



\---



\## 10. Problem: Railway Backend war bei HiveMQ nicht autorisiert



\### Beschreibung



Railway Backend Logs zeigten:



```text

MQTT connection failed. reason\_code=Not authorized

```



\### Ursache



Die MQTT-Zugangsdaten im Railway Backend waren falsch oder es wurde der falsche HiveMQ-Benutzer verwendet.



\### Lösung



In Railway Backend Variables wurden gesetzt:



```env

MQTT\_BROKER=ec53cff1a655417a8246e130835c8427.s1.eu.hivemq.cloud

MQTT\_PORT=8883

MQTT\_USERNAME=Railway\_backend

MQTT\_PASSWORD=DEIN\_RAILWAY\_BACKEND\_PASSWORT

```



Wichtig:



```text

ESP32 benutzt Sensor\_user.

Backend benutzt Railway\_backend.

```



Danach wurde das Backend neu deployed:



```text

Railway → backend → Deployments → Redeploy

```



\---



\## 11. Problem: Backend abonnierte falsches MQTT Topic



\### Beschreibung



Das Backend war mit MQTT verbunden, aber empfing keine ESP32-Daten.



Im Log stand:



```text

MQTT connected successfully

MQTT subscribed to sensors/data

```



\### Ursache



Das Backend abonnierte nur:



```text

sensors/data

```



Der ESP32 sendete aber an:



```text

sensors/bme280\_1

sensors/bme280\_2

sensors/mq2\_1

```



\### Lösung



In der Datei:



```text

C:\\Users\\guedr\\iot-dashboard\\backend\\main.py

```



wurde geändert:



Falsch:



```python

client.subscribe("sensors/data")

```



Richtig:



```python

client.subscribe("sensors/#")

```



Beschreibung:



\* `sensors/#` bedeutet: alle Topics unter `sensors/`.

\* Dadurch empfängt das Backend alle Sensorwerte.



Nach der Änderung stand im Log:



```text

MQTT connected successfully

MQTT subscribed to sensors/#

MQTT message received: topic=sensors/bme280\_1

MQTT message received: topic=sensors/bme280\_2

MQTT message received: topic=sensors/mq2\_1

```



\---



\## 12. Problem: Fehlender Timestamp im Sensor-Payload



\### Beschreibung



Das Backend empfing die MQTT-Nachrichten, aber lehnte sie ab.



Fehlermeldung:



```text

Invalid MQTT payload

timestamp

Field required

```



\### Ursache



Das Backend-Modell `SensorData` verlangte einen `timestamp`.



Der ESP32 sendete aber keinen Timestamp im JSON.



\### Lösung



Der Timestamp wird im Backend automatisch ergänzt.



Datei:



```text

C:\\Users\\guedr\\iot-dashboard\\backend\\main.py

```



Import ergänzen:



```python

from datetime import datetime, timezone

```



In `on\_message()` vor der Validierung:



```python

payload = json.loads(msg.payload.decode())



if "timestamp" not in payload or payload\["timestamp"] is None:

&#x20;   payload\["timestamp"] = datetime.now(timezone.utc).isoformat()



sensor\_data = SensorData(\*\*payload)

```



Beschreibung:



\* Der ESP32 muss keinen Timestamp senden.

\* Das Backend setzt beim Empfang automatisch die aktuelle UTC-Zeit.



\---



\## 13. Problem: Daten wurden empfangen, aber nicht gespeichert



\### Beschreibung



Das Backend zeigte MQTT-Nachrichten im Log, aber `/sensordaten` war leer.



\### Ursache



Die empfangenen Daten wurden nicht in die Datenliste gespeichert.



\### Lösung



In `on\_message()` muss nach der Validierung gespeichert werden:



```python

sensor\_data\_list.append(sensor\_data)

```



oder bei Dictionary-Ausgabe:



```python

sensor\_data\_list.append(sensor\_data.model\_dump())

```



Beispiel:



```python

def on\_message(client, userdata, msg):

&#x20;   print(f"MQTT message received: topic={msg.topic}, payload={msg.payload}")



&#x20;   try:

&#x20;       payload = json.loads(msg.payload.decode())



&#x20;       if "timestamp" not in payload or payload\["timestamp"] is None:

&#x20;           payload\["timestamp"] = datetime.now(timezone.utc).isoformat()



&#x20;       sensor\_data = SensorData(\*\*payload)

&#x20;       sensor\_data\_list.append(sensor\_data)



&#x20;       print(f"Sensor data saved: {sensor\_data.sensor\_id}")



&#x20;   except Exception as e:

&#x20;       print(f"Invalid MQTT payload on topic '{msg.topic}': {e}")

```



\---



\## 14. Backend erfolgreich getestet



Der Backend Endpoint:



```text

https://backend-production-4878.up.railway.app/sensordaten

```



zeigte danach echte Sensordaten.



Beispiel:



```json

{

&#x20; "sensor\_id": "bme280\_1",

&#x20; "sensor\_type": "BME280",

&#x20; "timestamp": "2026-07-03T01:27:49.957043Z",

&#x20; "temperature\_c": 27.27,

&#x20; "humidity\_percent": 40.7,

&#x20; "pressure\_hpa": 1015.11,

&#x20; "gas\_value": null,

&#x20; "smoke\_warning": false,

&#x20; "email\_sent": false

}

```



Beschreibung:



\* Die Daten kommen vom ESP32.

\* Das Backend empfängt sie über HiveMQ.

\* Der Endpoint `/sensordaten` gibt sie als JSON zurück.



\---



\## 15. Problem: Online Dashboard leer trotz Backend-Daten



\### Beschreibung



Das Backend zeigte Daten, aber das Frontend-Dashboard blieb leer.



\### Ursache



Das Frontend war wahrscheinlich mit einer falschen Backend-URL konfiguriert.



\### Lösung



In Railway Frontend Variables muss stehen:



```env

BACKEND\_URL=https://backend-production-4878.up.railway.app

```



Falsch wären:



```env

BACKEND\_URL=http://localhost:8000

BACKEND\_URL=http://backend:8000

```



Danach:



```text

Railway → frontend → Deployments → Redeploy

```



Im Browser danach neu laden:



```text

Strg + F5

```



\---



\## 16. Historische Analyse im Dashboard



Im Dashboard gibt es eine historische Analyse.



Beispielwerte:



```text

Ø Temperatur:        24.87 °C

Min Temperatur:      15.06 °C

Max Temperatur:      36.57 °C



Ø Luftfeuchtigkeit:  41.76 %

Min Luftfeuchtigkeit: 28.02 %

Max Luftfeuchtigkeit: 58.29 %

```



Beschreibung:



\* `Ø` bedeutet Durchschnitt.

\* `Min` bedeutet kleinster gespeicherter Wert.

\* `Max` bedeutet größter gespeicherter Wert.

\* Diese Werte beziehen sich auf die gespeicherten Messwerte, nicht nur auf den aktuellsten Messwert.



\---



\## 17. BME280 Temperaturprüfung



\### Beschreibung



Die BME280 Sensoren zeigten teilweise höhere Temperaturen als Handy oder Laptop.



\### Erklärung



Der BME280 misst die Temperatur direkt am Sensor-Chip.



Er misst nicht automatisch dieselbe Temperatur wie:



```text

Handy-Wetter-App

Laptop-Wetteranzeige

CPU-Temperatur

Außentemperatur

```



Mögliche Wärmequellen:



```text

ESP32

MQ-2 Sensor

Laptop

USB-Port

Finger/Hand

Breadboard

schlechte Belüftung

```



Besonders wichtig:



```text

Der MQ-2 wird warm, weil er eine Heizspirale hat.

Der BME280 muss deshalb weit weg vom MQ-2 liegen.

```



Empfohlene Platzierung:



```text

BME280 mindestens 30–50 cm weg vom ESP32

BME280 mindestens 30–50 cm weg vom MQ-2

BME280 nicht anfassen

10–15 Minuten warten

Dann Werte prüfen

```



\---



\## 18. BME280 Temperatur-Offset



\### Beschreibung



Wenn der BME280 etwas zu hohe Temperatur zeigt, kann ein Software-Offset benutzt werden.



Beispiel:



```text

BME280 zeigt:      18 °C

Echte Temperatur:  15 °C

Offset:            15 - 18 = -3

```



Datei:



```text

C:\\Users\\guedr\\esp32-iot-hardware\\main.py

```



Offset-Konfiguration:



```python

BME280\_TEMP\_OFFSETS = {

&#x20;   "bme280\_1": -3.0,

&#x20;   "bme280\_2": -3.0,

}

```



Funktion:



```python

def apply\_temperature\_offset(sensor\_id, temperature):

&#x20;   offset = BME280\_TEMP\_OFFSETS.get(sensor\_id, 0)

&#x20;   return temperature + offset

```



In `read\_bme280()`:



```python

temperature\_corrected = apply\_temperature\_offset(sensor\_id, temperature)



payload = {

&#x20;   "sensor\_type": "BME280",

&#x20;   "sensor\_id": sensor\_id,

&#x20;   "temperature\_c": round(temperature\_corrected, 2),

&#x20;   "humidity\_percent": round(humidity, 2),

&#x20;   "pressure\_hpa": round(pressure, 2),

&#x20;   "gas\_value": None,

&#x20;   "smoke\_warning": False,

}

```



Danach auf den ESP32 kopieren:



```powershell

cd C:\\Users\\guedr\\esp32-iot-hardware

py -m mpremote connect COM3 fs cp .\\main.py :main.py

py -m mpremote connect COM3 reset

```



\---



\## 19. MQ-2 Test



\### Beschreibung



Der MQ-2 wurde für Gas-/Rauchwerte verwendet.



Ein Test mit offenem Feuer wurde nicht empfohlen.



\### Sichererer Test



```text

1\. MQ-2 5–10 Minuten aufwärmen lassen

2\. Desinfektionsmittel oder Alkohol auf ein Tuch geben

3\. Tuch 2–5 cm vor den MQ-2 halten

4\. gas\_value beobachten

```



Erwartung:



```text

gas\_value steigt deutlich

```



Beispiel:



```text

100 → 300 → 800 → 1500

```



\---



\## 20. MQ-2 Rauchwarnung



\### Beschreibung



Die Rauchwarnung wird über einen Grenzwert berechnet.



Beispiel im Code:



```python

GAS\_WARNING\_LIMIT = 3000

```



Logik:



```text

gas\_value <= 3000 → smoke\_warning = false

gas\_value > 3000  → smoke\_warning = true

```



Für eine Demonstration kann der Grenzwert niedriger gesetzt werden:



```python

GAS\_WARNING\_LIMIT = 1000

```



oder:



```python

GAS\_WARNING\_LIMIT = 500

```



Beschreibung:



\* Für echte Nutzung sollte der Grenzwert durch Tests kalibriert werden.

\* Für eine Demo ist ein niedriger Grenzwert einfacher sichtbar.



\---



\## 21. Finaler Testablauf



Bei Problemen sollte immer in dieser Reihenfolge getestet werden.



\### Schritt 1: ESP32 Serial Monitor



Erwartung:



```text

Gesendet an sensors/bme280\_1

Gesendet an sensors/bme280\_2

Gesendet an sensors/mq2\_1

ESP32 läuft...

```



\### Schritt 2: Railway Backend Logs



Erwartung:



```text

MQTT connected successfully

MQTT subscribed to sensors/#

MQTT message received: topic=sensors/bme280\_1

MQTT message received: topic=sensors/bme280\_2

MQTT message received: topic=sensors/mq2\_1

```



\### Schritt 3: Backend Endpoint



Öffnen:



```text

https://backend-production-4878.up.railway.app/sensordaten

```



Erwartung:



```text

JSON-Daten mit Sensorwerten werden angezeigt.

```



\### Schritt 4: Online Dashboard



Öffnen:



```text

https://iot-dashboard-production-da48.up.railway.app

```



Wenn Backend Daten hat, aber Dashboard leer ist:



```text

BACKEND\_URL im Railway Frontend prüfen

Frontend redeployen

Browser mit Strg + F5 neu laden

```



\---



\## 22. Aktueller finaler Status



Am Ende funktionierte:



```text

ESP32 läuft

BME280\_1 wird erkannt

BME280\_2 wird erkannt

MQ-2 wird erkannt

ESP32 sendet an HiveMQ Cloud

Railway Backend verbindet sich mit HiveMQ

Railway Backend subscribed auf sensors/#

Railway Backend empfängt MQTT-Nachrichten

Railway Backend speichert Sensordaten

/sensordaten zeigt echte Daten

Dashboard kann diese Daten anzeigen

```



Damit ist der wichtigste Teil des Projekts erfolgreich umgesetzt:



```text

Echte ESP32-Sensordaten werden im Railway Backend empfangen und können im Online-Dashboard angezeigt werden.

```



\---



\## 23. Wichtige Befehle



\### ESP32 Dateien hochladen



```powershell

cd C:\\Users\\guedr\\esp32-iot-hardware

py -m mpremote connect COM3 fs cp .\\main.py :main.py

py -m mpremote connect COM3 fs cp .\\config.py :config.py

py -m mpremote connect COM3 reset

```



\### Docker lokal starten



```powershell

cd C:\\Users\\guedr\\iot-dashboard

docker compose up -d mqtt backend frontend

docker compose stop sensor

docker compose ps

```



\### Backend Daten testen



```powershell

Invoke-RestMethod https://backend-production-4878.up.railway.app/sensordaten | Select-Object -Last 10

```





