# **IoT-Dashboard – Projektablauf, wichtige Schritte und Fehlerbehebung**

## **1. Projektziel**

Dieses Projekt implementiert ein verteiltes IoT-System zur Erfassung, Verarbeitung, Speicherung und Visualisierung von Sensordaten in Echtzeit.

Das System verwendet echte ESP32-Hardware mit mehreren Sensoren. Die Daten werden per MQTT übertragen, vom Backend über eine REST API bereitgestellt und im Online-Dashboard visualisiert.

Ziel ist es, zentrale Konzepte verteilter Systeme praktisch umzusetzen:

* MQTT-Kommunikation
* REST API
* verteilte Komponenten
* Echtzeitdaten
* Cloud Deployment
* Docker Deployment
* Authentifizierung
* historische Analyse
* Machine-Learning-Vorhersage

---

## **2. Finale Systemarchitektur**

Die finale Architektur des Projekts lautet:

```text
ESP32 mit echten Sensoren
        ↓
HiveMQ Cloud MQTT Broker
        ↓
Railway Backend
        ↓
REST API
        ↓
Railway Frontend Dashboard
```

### **Kurze Beschreibung**

Der ESP32 liest echte Sensordaten und sendet diese per MQTT an HiveMQ Cloud. Das Railway Backend empfängt die MQTT-Nachrichten als Subscriber, verarbeitet die Daten und stellt sie über eine REST API bereit. Das Online-Dashboard ruft die Daten ab und zeigt sie live, historisch und grafisch an.

### **Systemablauf**

1. Die Sensoren erfassen Messwerte.
2. Der ESP32 erstellt JSON-Datenpakete.
3. Die Daten werden über MQTT veröffentlicht.
4. Der MQTT-Broker verteilt die Nachrichten.
5. Das Backend empfängt die Daten als Subscriber.
6. Das Backend validiert und speichert die Messwerte.
7. Die REST API stellt die Daten bereit.
8. Das Dashboard lädt die Daten automatisch.
9. Die Messwerte werden grafisch und tabellarisch angezeigt.
10. Warnungen, historische Analyse und Vorhersagen werden berechnet.

### **Verwendete Technologien**

* Python - Backend, Sensorlogik und Datenverarbeitung
* MicroPython - Programmierung des ESP32
* FastAPI - REST API und Backend-Server
* Streamlit - Web-Dashboard
* MQTT - Publish/Subscribe-Kommunikation
* HiveMQ Cloud - Cloud MQTT Broker
* Mosquitto - lokaler MQTT Broker für Tests
* Docker - Containerisierung der Anwendung
* Railway - Cloud Deployment von Backend und Frontend
* SQLite / Backend-Speicherung - Speicherung historischer Sensordaten
* CSV/PDF Export - Export von Messwerten
* Machine Learning - Vorhersage zukünftiger Sensorwerte

---

## **3. Echte ESP32-Sensordaten**

### **Wichtige Schritte**

1. ESP32 mit MicroPython flashen.
2. `main.py`, `config.py` und `bme280.py` auf den ESP32 kopieren.
3. WLAN-Zugangsdaten in `config.py` setzen.
4. MQTT-Zugangsdaten für HiveMQ Cloud eintragen.
5. Sensorwerte im Serial Monitor prüfen.
6. Prüfen, ob Daten im Backend-Endpoint `/sensordaten` erscheinen.

### **Kurze Beschreibung**

Der ESP32 ist die echte Datenquelle. Er liest Temperatur, Luftfeuchtigkeit, Luftdruck und Gaswerte aus und sendet sie regelmäßig an den MQTT-Broker.

### **Wichtige Dateien**

```text
C:\Users\guedr\esp32-iot-hardware\main.py
C:\Users\guedr\esp32-iot-hardware\config.py
C:\Users\guedr\esp32-iot-hardware\bme280.py
```

### **Wichtige Befehle**

```powershell
cd C:\Users\guedr\esp32-iot-hardware

py -m mpremote connect COM3 fs cp .\config.py :config.py
py -m mpremote connect COM3 fs cp .\bme280.py :bme280.py
py -m mpremote connect COM3 fs cp .\main.py :main.py
py -m mpremote connect COM3 reset
```

### **Wichtiges Problem**

Der Serial Monitor zeigte manchmal keine Verbindung oder COM3 war blockiert.

### **Lösung**

Der Serial Monitor muss geschlossen werden, bevor `mpremote` benutzt wird.

---

## **4. Mehrere Sensoren**

### **Verwendete Sensoren**

```text
BME280_1 → Temperatur, Luftfeuchtigkeit, Luftdruck
BME280_2 → Temperatur, Luftfeuchtigkeit, Luftdruck
MQ2_1    → Gas-/Rauchüberwachung
```

### **Wichtige Schritte**

1. Beide BME280 über I2C anschließen.
2. MQ-2 an ADC-Pin GPIO34 anschließen.
3. I2C-Adressen prüfen.
4. Sensoren im ESP32-Code getrennt auslesen.
5. Jeden Sensor an ein eigenes MQTT-Topic senden.

### **BME280 Verkabelung**

```text
BME280 VCC/VIN → ESP32 3V3
BME280 GND     → ESP32 GND
BME280 SDA     → ESP32 GPIO21
BME280 SCL     → ESP32 GPIO22
```

### **MQ-2 Verkabelung**

```text
MQ-2 VCC  → ESP32 VIN/5V
MQ-2 GND  → ESP32 GND
MQ-2 AOUT → Spannungsteiler → ESP32 GPIO34
```

### **Wichtiges Problem**

Ein BME280 wurde gedrückt oder bewegt und der ESP32 hat die Verbindung verloren.

### **Ursache**

Wahrscheinlich gab es einen Wackelkontakt oder Kurzschluss auf dem Breadboard.

### **Lösung**

Sensoren nicht drücken, Kabel feststecken und jeden Sensor einzeln testen.

---

## **5. MQTT-Kommunikation**

### **Wichtige MQTT-Topics**

Der ESP32 sendet an:

```text
sensors/bme280_1
sensors/bme280_2
sensors/mq2_1
```

Das Backend abonniert:

```text
sensors/#
```

### **Kurze Beschreibung**

MQTT arbeitet nach dem Publish/Subscribe-Prinzip. Der ESP32 veröffentlicht Daten, das Backend abonniert die passenden Topics.

### **Wichtige Schritte**

1. ESP32 veröffentlicht Sensordaten.
2. HiveMQ Cloud empfängt die Nachrichten.
3. Backend verbindet sich mit HiveMQ.
4. Backend subscribed auf `sensors/#`.
5. Backend empfängt MQTT-Nachrichten.

### **Wichtiges Problem**

Das Backend abonnierte zuerst nur:

```text
sensors/data
```

Der ESP32 sendete aber an:

```text
sensors/bme280_1
sensors/bme280_2
sensors/mq2_1
```

### **Lösung**

In `backend/main.py` ändern:

```python
client.subscribe("sensors/#")
```

---

## **6. MQTT Authentication**

### **Kurze Beschreibung**

MQTT Authentication schützt das System vor unautorisierten Geräten. Nur gültige Benutzer dürfen MQTT-Nachrichten senden oder empfangen.

### **Verwendete MQTT-Benutzer**

```text
Sensor_user      → ESP32 sendet Sensordaten
Railway_backend  → Backend empfängt Sensordaten
```

### **Wichtige Schritte**

1. In HiveMQ Cloud zwei Benutzer erstellen.
2. `Sensor_user` für ESP32 verwenden.
3. `Railway_backend` für das Backend verwenden.
4. Benutzerrechte passend setzen.
5. Railway Backend Variables setzen.
6. Backend neu deployen.

### **Railway Backend Variables**

```env
MQTT_BROKER=ec53cff1a655417a8246e130835c8427.s1.eu.hivemq.cloud
MQTT_PORT=8883
MQTT_USERNAME=Railway_backend
MQTT_PASSWORD=DEIN_RAILWAY_BACKEND_PASSWORT
```

### **ESP32 config.py**

```python
MQTT_BROKER = "ec53cff1a655417a8246e130835c8427.s1.eu.hivemq.cloud"
MQTT_PORT = 8883
MQTT_USERNAME = "Sensor_user"
MQTT_PASSWORD = "DEIN_SENSOR_USER_PASSWORT"
```

### **Wichtiges Problem**

Railway Backend zeigte:

```text
MQTT connection failed. reason_code=Not authorized
```

### **Ursache**

Falscher MQTT-Benutzer oder falsches Passwort im Railway Backend.

### **Lösung**

Backend muss `Railway_backend` verwenden, nicht `Sensor_user`.

---

## **7. REST API**

### **Kurze Beschreibung**

Die REST API stellt gespeicherte Sensordaten für das Frontend bereit.

### **Wichtige Endpoints**

```text
GET /health
GET /sensordaten
```

### **Online Backend**

```text
https://backend-production-4878.up.railway.app
```

### **Sensordaten Endpoint**

```text
https://backend-production-4878.up.railway.app/sensordaten
```

### **Wichtige Schritte**

1. Backend starten.
2. MQTT-Daten empfangen.
3. Sensordaten speichern.
4. Daten über `/sensordaten` bereitstellen.
5. Frontend ruft diese API regelmäßig ab.

### **Test mit PowerShell**

```powershell
Invoke-RestMethod https://backend-production-4878.up.railway.app/sensordaten | Select-Object -Last 10
```

### **Wichtiges Problem**

`/sensordaten` zeigte zuerst:

```json
[]
```

### **Ursache**

Das Backend empfing noch keine MQTT-Daten oder speicherte sie nicht.

### **Lösung**

Prüfen:

```text
MQTT connected successfully
MQTT subscribed to sensors/#
MQTT message received
```

und in `on_message()` speichern:

```python
sensor_data_list.append(sensor_data)
```

---

## **8. Online Dashboard**

### **Kurze Beschreibung**

Das Online-Dashboard zeigt aktuelle Messwerte, Tabellen, Diagramme, Warnungen, Exportfunktionen und historische Analyse.

### **Online Dashboard URL**

```text
https://iot-dashboard-production-da48.up.railway.app
```

### **Wichtige Schritte**

1. Frontend auf Railway deployen.
2. Backend URL im Frontend setzen.
3. Frontend neu deployen.
4. Browser mit `Strg + F5` neu laden.

### **Benutzer-Login**

Das Dashboard enthält einen Benutzer-Login. Dadurch ist der Zugriff auf die Visualisierung geschützt.

Vorteile:

* Nicht jeder Benutzer kann sofort auf das Dashboard zugreifen.
* Die Oberfläche ist besser für Präsentation und Projektabgabe geeignet.
* Sensordaten werden nicht ohne Anmeldung angezeigt.

### **Railway Frontend Variable**

```env
BACKEND_URL=https://backend-production-4878.up.railway.app
```

### **Wichtiges Problem**

Backend hatte Daten, aber Dashboard blieb leer.

### **Ursache**

Frontend verwendete falsche Backend URL.

### **Lösung**

In Railway Frontend Variables setzen:

```env
BACKEND_URL=https://backend-production-4878.up.railway.app
```

Danach Frontend redeployen.

---

## **9. Auto Refresh**

### **Kurze Beschreibung**

Auto Refresh aktualisiert das Dashboard automatisch in festen Zeitintervallen.

### **Wichtige Schritte**

1. Auto Refresh im Streamlit Dashboard aktivieren.
2. Aktualisierungsintervall setzen.
3. Daten regelmäßig vom Backend abrufen.
4. Manuelle Aktualisierung überflüssig machen.

### **Beispiel**

```text
Auto Refresh: alle 5 Sekunden
```

### **Nutzen**

* neue Daten erscheinen automatisch
* Dashboard wirkt wie ein Live-Monitor
* bessere Bedienbarkeit bei Präsentationen

### **Wichtiges Problem**

Am Anfang musste das Dashboard manuell aktualisiert werden.

### **Lösung**

Auto Refresh einbauen und den manuellen Aktualisieren-Button entfernen oder reduzieren.

---

## **10. Historische Analyse**

### **Kurze Beschreibung**

Die historische Analyse berechnet statistische Werte aus gespeicherten Sensordaten.

### **Angezeigte Werte**

```text
Ø Temperatur
Min Temperatur
Max Temperatur

Ø Luftfeuchtigkeit
Min Luftfeuchtigkeit
Max Luftfeuchtigkeit
```

### **Beispiel**

```text
Ø Temperatur:        24.87 °C
Min Temperatur:      15.06 °C
Max Temperatur:      36.57 °C

Ø Luftfeuchtigkeit:  41.76 %
Min Luftfeuchtigkeit: 28.02 %
Max Luftfeuchtigkeit: 58.29 %
```

### **Wichtige Schritte**

1. Sensordaten speichern.
2. Historische Daten aus Backend laden.
3. BME280-Daten filtern.
4. Durchschnitt, Minimum und Maximum berechnen.
5. Werte im Dashboard anzeigen.

### **Wichtiges Problem**

Es war unklar, ob die Werte aktuell oder historisch sind.

### **Erklärung**

Die historische Analyse zeigt Statistik aus gespeicherten Messwerten, nicht nur den letzten aktuellen Wert.

---

## **11. Diagramme**

### **Kurze Beschreibung**

Diagramme zeigen Messwerte über Zeit. Dadurch werden Trends und Veränderungen sichtbar.

### **Wichtige Diagramme**

* Temperaturverlauf
* Luftfeuchtigkeitsverlauf
* Luftdruckverlauf
* Gaswertverlauf
* Rauchwarnung für MQ-2

### **Wichtige Schritte**

1. Daten aus `/sensordaten` laden.
2. Timestamp in deutsche Zeit umwandeln.
3. Daten nach Sensor filtern.
4. Diagramme im Dashboard anzeigen.
5. MQ-2 separat mit Gaswert und Rauchwarnung darstellen.

### **Wichtiges Problem**

MQ-2 zeigte zuerst falsche Spalten wie Temperatur und Luftfeuchtigkeit.

### **Lösung**

Wenn MQ-2 ausgewählt ist, im Dashboard Gaswert und Rauchwarnung anzeigen.

---

## **12. Grenzwertwarnungen**

### **Kurze Beschreibung**

Grenzwertwarnungen zeigen kritische Sensorwerte direkt im Dashboard an.

### **Beispiele**

* Temperatur zu hoch
* Gaswert zu hoch
* Rauchwarnung aktiv

### **MQ-2 Grenzwert**

```python
GAS_WARNING_LIMIT = 3000
```

### **Logik**

```text
gas_value <= 3000 → smoke_warning = false
gas_value > 3000  → smoke_warning = true
```

### **Wichtige Schritte**

1. Grenzwert im ESP32-Code definieren.
2. MQ-2 Gaswert lesen.
3. `smoke_warning` berechnen.
4. Warnung per MQTT senden.
5. Warnung im Dashboard farbig anzeigen.

### **Wichtiges Problem**

Für Demo war der Grenzwert teilweise zu hoch.

### **Lösung**

Für Tests oder Präsentation kann der Grenzwert niedriger gesetzt werden:

```python
GAS_WARNING_LIMIT = 1000
```

oder:

```python
GAS_WARNING_LIMIT = 500
```

---

## **13. E-Mail-Alerts**

### **Kurze Beschreibung**

E-Mail-Alerts informieren den Benutzer automatisch, wenn kritische Werte erkannt werden.

### **Mögliche Auslöser**

* hohe Temperatur
* hoher Gaswert
* Rauchwarnung
* ML-Vorhersage mit kritischem Wert

### **Wichtige Schritte**

1. E-Mail-Service konfigurieren.
2. Empfängeradresse setzen.
3. Warnlogik im Backend prüfen.
4. E-Mail bei kritischem Messwert senden.
5. Status `email_sent` speichern.
6. Im Dashboard anzeigen, dass E-Mail gesendet wurde.

### **Wichtige Umgebungsvariablen**

```env
RESEND_API_KEY=DEIN_RESEND_API_KEY
EMAIL_FROM=DEINE_ABSENDER_EMAIL
EMAIL_RECEIVER=DEINE_EMPFAENGER_EMAIL
```

### **Wichtiges Problem**

SMTP funktionierte auf Railway nicht zuverlässig.

### **Lösung**

Resend API über HTTPS verwenden, statt SMTP.

### **Dashboard-Anzeige**

Das Dashboard zeigt bei Warnungen eine Meldung wie:

```text
Warnung erkannt – E-Mail-Warnung wurde erfolgreich gesendet
```

---

## **14. CSV/PDF Export**

### **Kurze Beschreibung**

Der Export ermöglicht das Herunterladen der aktuellen Messwerttabelle oder historischer Daten.

### **Exportformate**

* CSV
* PDF

### **Wichtige Schritte**

1. Aktuelle Tabelle im Dashboard vorbereiten.
2. Daten mit Zeilennummern versehen.
3. CSV-Datei erzeugen.
4. PDF-Datei erzeugen.
5. Download-Buttons anzeigen.

### **Wichtiges Problem**

Die exportierten Dateien sollten dieselben Werte zeigen wie die aktuelle Messtabelle.

### **Lösung**

Export muss auf derselben gefilterten Tabelle basieren, die im Dashboard angezeigt wird.

### **Button-Farben**

```text
PDF herunterladen → Blau
CSV herunterladen → Orange
```

---

## **15. Docker Deployment**

### **Kurze Beschreibung**

Docker verpackt die Anwendung in Container. Dadurch läuft die Anwendung auf verschiedenen Rechnern gleich.

### **Wichtige Services**

```text
mqtt
backend
frontend
sensor
```

### **Lokaler Start**

```powershell
cd C:\Users\guedr\iot-dashboard
docker compose up -d mqtt backend frontend
docker compose stop sensor
docker compose ps
```

### **Wichtige Regel**

Wenn echte ESP32-Daten verwendet werden:

```text
sensor-Container stoppen
```

### **Wichtiges Problem**

Der Docker-Simulator sendete Fake-Daten.

### **Lösung**

```powershell
docker compose stop sensor
```

---

## **16. Cloud Deployment**

### **Kurze Beschreibung**

Mit Cloud Deployment ist das Projekt online erreichbar. Andere Personen können das Dashboard ohne lokale Installation testen.

### **Verwendete Cloud-Dienste**

```text
Railway Backend
Railway Frontend
HiveMQ Cloud MQTT Broker
```

### **Wichtige Schritte**

1. Backend auf Railway deployen.
2. Frontend auf Railway deployen.
3. HiveMQ Cloud Broker einrichten.
4. Railway Variables setzen.
5. ESP32 auf HiveMQ konfigurieren.
6. Dashboard online testen.

### **Wichtiges Problem**

Backend lief online, aber empfing zuerst keine Daten.

### **Ursachen**

* falsche MQTT Credentials
* falsches MQTT Topic
* fehlender Timestamp
* Daten wurden nicht gespeichert

### **Lösung**

Schrittweise prüfen:

```text
MQTT connected?
MQTT subscribed to sensors/#?
MQTT message received?
/sensordaten zeigt Daten?
Dashboard zeigt Daten?
```

---

## **17. Machine-Learning-Vorhersage**

### **Kurze Beschreibung**

Die Machine-Learning-Funktion verwendet historische Sensordaten, um zukünftige Werte zu schätzen.

### **Beispiel**

```text
In 30 Minuten: 34 °C
```

### **Wichtige Schritte**

1. Historische Sensordaten sammeln.
2. Temperaturdaten vorbereiten.
3. Zeitwerte korrekt formatieren.
4. ML-Modell trainieren oder einfache Vorhersage berechnen.
5. Vorhersage im Dashboard anzeigen.
6. Optional E-Mail bei kritischer Vorhersage senden.

### **Nutzen**

* zukünftige Temperaturentwicklung abschätzen
* kritische Werte früher erkennen
* Projekt mit Datenanalyse erweitern

### **Wichtiges Problem**

Für ML braucht man genügend historische Daten.

### **Lösung**

Vorhersage erst sinnvoll anzeigen, wenn genug gespeicherte Messwerte vorhanden sind.

---

## **18. Deutsche echte Datum- und Zeitdarstellung**

### **Kurze Beschreibung**

Die Daten sollen nicht in Greenwich-Zeit angezeigt werden, sondern in deutscher lokaler Zeit.

### **Wichtige Schritte**

1. Backend speichert UTC-Zeit.
2. Frontend wandelt UTC in deutsche Zeit um.
3. Tabellen und Diagramme verwenden dieselbe Zeitlogik.
4. Historische Analyse zeigt keine zukünftigen Zeiten.

### **Beispiel**

```text
03.07.2026, 01:27:49
```

### **Wichtiges Problem**

Dashboard zeigte teilweise Greenwich-Zeit oder falsche Zeit im Verlauf.

### **Lösung**

Zeit im Frontend konsistent nach Deutschland/Berlin umwandeln.

---

## **19. BME280 Temperatur-Kalibrierung**

### **Kurze Beschreibung**

Der BME280 misst die Temperatur direkt am Sensor-Chip. Er zeigt nicht automatisch dieselbe Temperatur wie Handy, Laptop oder Wetter-App.

### **Mögliche Wärmequellen**

```text
ESP32
MQ-2 Sensor
Laptop
USB-Port
Finger/Hand
Breadboard
schlechte Belüftung
```

### **Wichtige Schritte**

1. BME280 30–50 cm weg vom ESP32 legen.
2. BME280 30–50 cm weg vom MQ-2 legen.
3. Sensor nicht berühren.
4. 10–15 Minuten warten.
5. Mit Referenztemperatur vergleichen.
6. Optional Offset setzen.

### **Offset-Beispiel**

```text
BME280 zeigt:      18 °C
Echte Temperatur:  15 °C
Offset:            15 - 18 = -3
```

### **Code-Beispiel**

```python
BME280_TEMP_OFFSETS = {
    "bme280_1": -3.0,
    "bme280_2": -3.0,
}
```

---

## **20. MQ-2 Test und Sicherheit**

### **Kurze Beschreibung**

Der MQ-2 erkennt Rauch und brennbare Gase. Er ist ein Warnsensor, aber kein exakt kalibrierter Messsensor.

### **Sicherer Test**

```text
1. MQ-2 5–10 Minuten aufwärmen lassen
2. Desinfektionsmittel oder Alkohol auf ein Tuch geben
3. Tuch 2–5 cm vor den MQ-2 halten
4. gas_value beobachten
```

### **Wichtiges Problem**

Ein Test mit offenem Feuer ist riskant.

### **Lösung**

Kein offenes Feuer verwenden. Alkohol-/Desinfektionsmittel-Dampf reicht für einen sicheren Funktionstest.

---

## **21. Finaler Testablauf**

### **Schritt 1: ESP32 Serial Monitor prüfen**

Erwartung:

```text
Gesendet an sensors/bme280_1
Gesendet an sensors/bme280_2
Gesendet an sensors/mq2_1
ESP32 läuft...
```

### **Schritt 2: Railway Backend Logs prüfen**

Erwartung:

```text
MQTT connected successfully
MQTT subscribed to sensors/#
MQTT message received: topic=sensors/bme280_1
MQTT message received: topic=sensors/bme280_2
MQTT message received: topic=sensors/mq2_1
```

### **Schritt 3: Backend API prüfen**

Öffnen:

```text
https://backend-production-4878.up.railway.app/sensordaten
```

Erwartung:

```text
JSON-Daten mit echten Sensorwerten werden angezeigt.
```

### **Schritt 4: Online Dashboard prüfen**

Öffnen:

```text
https://iot-dashboard-production-da48.up.railway.app
```

Erwartung:

```text
Dashboard zeigt aktuelle echte ESP32-Werte, Diagramme, historische Analyse und Warnungen.
```

---

## **22. Wichtigste Probleme und Lösungen**

| Problem                           | Kurze Ursache                   | Lösung                                 |
| --------------------------------- | ------------------------------- | -------------------------------------- |
| Simulator sendet Fake-Daten       | Docker-Sensor lief noch         | `docker compose stop sensor`           |
| ESP32 erreicht lokalen MQTT nicht | Netzwerk/Firewall/Hotspot       | Cloud-MQTT mit HiveMQ verwenden        |
| MQTT `Not authorized`             | falsche Credentials             | `Railway_backend` im Backend setzen    |
| Backend empfängt nichts           | falsches Topic                  | `client.subscribe("sensors/#")`        |
| Timestamp fehlt                   | ESP32 sendet keinen Timestamp   | Timestamp im Backend ergänzen          |
| `/sensordaten` ist leer           | Daten nicht gespeichert         | `sensor_data_list.append(...)`         |
| Dashboard leer                    | falsche `BACKEND_URL`           | Railway Frontend Variable korrigieren  |
| Zeit falsch                       | UTC/Greenwich statt Deutschland | Zeit im Frontend nach Berlin umwandeln |
| BME280 zeigt zu warm              | Sensor nahe Wärmequelle         | Sensor weglegen oder Offset setzen     |
| MQ-2 Warnung kommt nicht          | Grenzwert zu hoch               | Grenzwert für Demo reduzieren          |
| E-Mail kommt nicht                | SMTP/Cloud blockiert            | Resend API verwenden                   |

---

## **23. Finaler Projektstatus**

Am Ende unterstützt das Projekt:

```text
echte ESP32-Sensordaten
mehrere Sensoren
MQTT-Kommunikation
MQTT Authentication
REST API
Online Dashboard
Auto Refresh
historische Analyse
Diagramme
Grenzwertwarnungen
E-Mail-Alerts
CSV/PDF Export
Docker Deployment
Cloud Deployment
Machine-Learning-Vorhersage
Benutzer-Login im Dashboard
```

### **Kurze Zusammenfassung**

Das Projekt ist ein vollständiges verteiltes IoT-System. Es verbindet echte Hardware mit Cloud-MQTT, Backend, REST API und Online-Dashboard. Zusätzlich bietet es Sicherheitsfunktionen, Warnungen, Datenexport, historische Analyse und Machine-Learning-Vorhersage.

---

## **24. Projektstruktur**

```text
/backend        # FastAPI Backend, MQTT Subscriber, REST API
/frontend       # Streamlit Dashboard
/sensors        # Sensor-Simulation
/database       # Datenbank und Modelle
/docs           # Projektdokumentation
```

---

## **25. Wichtige Befehle**

### **ESP32 Dateien hochladen**

```powershell
cd C:\Users\guedr\esp32-iot-hardware
py -m mpremote connect COM3 fs cp .\main.py :main.py
py -m mpremote connect COM3 fs cp .\config.py :config.py
py -m mpremote connect COM3 reset
```

### **Docker lokal starten**

```powershell
cd C:\Users\guedr\iot-dashboard
docker compose up -d mqtt backend frontend
docker compose stop sensor
docker compose ps
```

### **Backend testen**

```powershell
Invoke-RestMethod https://backend-production-4878.up.railway.app/sensordaten | Select-Object -Last 10
```

