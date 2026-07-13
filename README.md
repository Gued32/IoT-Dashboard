# IoT-Sensor-Dashboard 

## 📌 Projektübersicht

Dieses Projekt implementiert ein verteiltes IoT-System zur Erfassung, Verarbeitung, Speicherung und Visualisierung von Sensordaten in Echtzeit. Ziel ist es, eine skalierbare Architektur zu entwickeln, bei der mehrere unabhängige Komponenten über Netzwerkprotokolle miteinander kommunizieren.

Das System unterstützt sowohl simulierte Sensordaten als auch echte Hardware-Sensoren mit einem ESP32 DevKit. Die Sensordaten werden per MQTT übertragen, im Backend verarbeitet und anschließend über ein Web-Dashboard visualisiert.

---

## 🎯 Zielsetzung

Das Projekt demonstriert zentrale Konzepte verteilter Systeme, insbesondere:

* Kommunikation zwischen verteilten Komponenten
* Verarbeitung von Sensordaten in Echtzeit
* Publish/Subscribe-Kommunikation mit MQTT
* REST API für Datenzugriff
* Visualisierung von Echtzeit- und historischen Messdaten
* Cloud Deployment für öffentlichen Zugriff
* Containerisierung mit Docker
* Sichere MQTT-Kommunikation mit Authentication

---

## 🏗️ Systemarchitektur

Die Anwendung besteht aus mehreren logisch getrennten Komponenten:

* **ESP32 mit echten Sensoren:** Erfasst reale Temperatur-, Luftfeuchtigkeits-, Luftdruck- und Gas-/Rauchdaten
* **Sensor-Simulatoren:** Können alternativ künstliche Sensordaten für Tests erzeugen
* **MQTT-Broker:** Vermittelt Nachrichten zwischen Sensoren und Backend
* **Backend:** Empfängt, validiert, verarbeitet und speichert Sensordaten
* **REST API:** Stellt Sensordaten für das Frontend bereit
* **Web-Dashboard:** Visualisiert aktuelle und historische Sensordaten
* **Cloud Deployment:** Macht das Projekt online erreichbar
* **Docker Deployment:** Verpackt die Anwendung, damit sie auf verschiedenen Systemen gleich läuft

Finale Datenkette:

```text
ESP32 Sensoren → HiveMQ Cloud MQTT Broker → Railway Backend → Railway Frontend Dashboard
```

---

## 🔄 Systemablauf

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

---

## ⚙️ Verwendete Technologien

* **Python** – Backend, Sensorlogik und Datenverarbeitung
* **MicroPython** – Programmierung des ESP32
* **FastAPI** – REST API und Backend-Server
* **Streamlit** – Web-Dashboard
* **MQTT** – Publish/Subscribe-Kommunikation
* **HiveMQ Cloud** – Cloud MQTT Broker
* **Mosquitto** – Lokaler MQTT Broker für Tests
* **Docker** – Containerisierung der Anwendung
* **Railway** – Cloud Deployment von Backend und Frontend
* **SQLite / Backend-Speicherung** – Speicherung historischer Sensordaten
* **CSV/PDF Export** – Export von Messwerten
* **Machine Learning** – Vorhersage zukünftiger Sensorwerte

---

## 🚀 Funktionalitäten

### 1. Echtzeit-Erfassung von Sensordaten

Das System empfängt regelmäßig neue Messdaten vom ESP32. Die Werte werden über MQTT an das Backend gesendet und im Dashboard angezeigt.

Erfasste Werte:

* Temperatur
* Luftfeuchtigkeit
* Luftdruck
* Gas-/Rauchwert
* Rauchwarnung
* Zeitstempel

---

### 2. Mehrere Sensoren

Das Projekt unterstützt mehrere Sensoren gleichzeitig.

Verwendete Sensoren:

```text
BME280_1 → Temperatur, Luftfeuchtigkeit, Luftdruck
BME280_2 → Temperatur, Luftfeuchtigkeit, Luftdruck
MQ2_1    → Gas-/Rauchüberwachung
```

Die Sensoren senden an verschiedene MQTT-Topics:

```text
sensors/bme280_1
sensors/bme280_2
sensors/mq2_1
```

Das Backend abonniert alle Sensor-Topics über:

```text
sensors/#
```

---

### 3. Grafische Darstellung mit Diagrammen

Das Dashboard zeigt Messwerte grafisch an. Dadurch können Temperatur, Luftfeuchtigkeit, Luftdruck und Gaswerte besser analysiert werden.

Die Diagramme helfen dabei:

* Trends zu erkennen
* Messwerte über Zeit zu vergleichen
* plötzliche Änderungen sichtbar zu machen
* Sensorverhalten besser zu verstehen

---

### 4. Grenzwertbasierte Warnungen

Das System prüft Sensorwerte gegen definierte Grenzwerte.

Beispiele:

* Temperatur zu hoch > 30°C
* Temperaturwarnung aktiv
* Luftfeuchtigkeit zu hoch  > 70%
* Luftfeuchtigkeitwarnung aktiv
* Luftdruck zu hoch > 1030 hPa
* Luftdruckwarnung aktiv
* Gaswert zu hoch > 3000
* Rauchwarnung aktiv

Beim MQ-2 Sensor wird ein Gas-Grenzwert verwendet:

```python
GAS_WARNING_LIMIT = 3000
```

Wenn der Gaswert über dem Grenzwert liegt, wird eine Rauchwarnung aktiviert:

```text
gas_value > GAS_WARNING_LIMIT → smoke_warning = true
```

---

### 5. Historische Datenanalyse

Das Dashboard berechnet Statistiken aus gespeicherten Messwerten.

Beispiele:

* Durchschnittliche Temperatur
* Minimale Temperatur
* Maximale Temperatur
* Durchschnittliche Luftfeuchtigkeit
* Minimale Luftfeuchtigkeit
* Maximale Luftfeuchtigkeit

Beispiel aus der historischen Analyse:

```text
Ø Temperatur:        24.87 °C
Min Temperatur:      15.06 °C
Max Temperatur:      36.57 °C

Ø Luftfeuchtigkeit:  41.76 %
Min Luftfeuchtigkeit: 28.02 %
Max Luftfeuchtigkeit: 58.29 %
```

---

### 6. Benutzer-Login

Das Dashboard enthält einen Benutzer-Login. Dadurch ist der Zugriff auf die Visualisierung geschützt.

Vorteile:

* Nicht jeder Benutzer kann sofort auf das Dashboard zugreifen
* Die Oberfläche ist besser für Präsentation und Projektabgabe geeignet
* Sensordaten werden nicht ohne Anmeldung angezeigt

---

### 7. Email Alerts

Das System kann E-Mail-Benachrichtigungen senden, wenn kritische Grenzwerte überschritten werden.

Beispiele:

* Temperatur überschreitet Grenzwert
* Gaswert überschreitet Grenzwert
* Rauchwarnung wird aktiviert

Dadurch wird der Benutzer automatisch informiert, ohne dauerhaft das Dashboard beobachten zu müssen.

---

### 8. Echtzeit Auto Refresh

Das Dashboard aktualisiert die Daten automatisch in festen Zeitintervallen.

Vorteile:

* Keine manuelle Aktualisierung nötig
* Neue Sensordaten erscheinen automatisch
* Das Dashboard wirkt wie ein Live-Monitoring-System

Beispiel:

```text
Auto Refresh: alle 5 Sekunden
```

---

### 9. Deutsche Datums- und Zeitformatierung

Die Messwerte werden mit deutscher Datums- und Zeitdarstellung angezeigt.

Beispiel:

```text
03.07.2026, 01:27:49
```

Dadurch sind die Zeitstempel im Dashboard besser lesbar und für deutsche Benutzer verständlicher.

---

### 10. Docker Deployment

Docker verpackt die komplette Anwendung in Container. Dadurch läuft das Projekt auf verschiedenen Systemen gleich.

Vorteile:

* Einfacher Start der Services
* Gleiche Umgebung auf jedem Rechner
* Backend, Frontend und MQTT können getrennt laufen
* Gute Grundlage für Deployment und Tests

Lokaler Start:

```powershell
docker compose up -d mqtt backend frontend
docker compose stop sensor
```

Wichtig:

```text
Der Sensor-Simulator muss gestoppt werden, wenn echte ESP32-Sensordaten verwendet werden.
```

---

### 11. Export als CSV/PDF Datei

Das Dashboard unterstützt den Export von Sensordaten.

Mögliche Exportformate:

* CSV-Datei
* PDF-Datei

Nutzen:

* Messwerte können gespeichert werden
* Daten können für Dokumentation verwendet werden
* Analyse außerhalb des Dashboards ist möglich
* Ergebnisse können in Projektberichten verwendet werden

---

### 12. Gas-/Rauchüberwachung mit MQ-2

Der MQ-2 Sensor wird zur Überwachung von Rauch und brennbaren Gasen verwendet.

Warum MQ-2?

* günstig
* einfach mit ESP32 verwendbar
* geeignet für Rauch- und Gasdetektion
* analoger Ausgang kann über ADC gelesen werden

Der MQ-2 liefert einen Gaswert:

```json
{
  "sensor_id": "mq2_1",
  "sensor_type": "MQ2",
  "gas_value": 315,
  "smoke_warning": false
}
```

Wichtig:

```text
Der MQ-2 ist ein Warnsensor und kein exakt kalibrierter Messsensor.
Er eignet sich gut zur Erkennung von steigenden Gas- oder Rauchwerten.
```

---

### 13. Echte Hardware

Neben Sensor-Simulatoren unterstützt das Projekt echte Hardware.

Verwendete echte Hardware:

* ESP32 DevKit
* BME280 Sensor 1
* BME280 Sensor 2
* MQ-2 Gas-/Rauchsensor

Warum BME280 statt DHT22?

* genauer
* stabiler
* schneller
* misst zusätzlich Luftdruck
* besser geeignet für zuverlässige Umgebungsdaten

Der ESP32 sendet echte Sensordaten im JSON-Format:

```json
{
  "sensor_id": "bme280_1",
  "sensor_type": "BME280",
  "temperature_c": 27.27,
  "humidity_percent": 40.70,
  "pressure_hpa": 1015.11,
  "gas_value": null,
  "smoke_warning": false
}
```

---

### 14. Cloud Deployment

Das Projekt ist online verfügbar. Dadurch kann das Dashboard von anderen Geräten getestet werden.

Cloud-Komponenten:

* Railway Backend
* Railway Frontend
* HiveMQ Cloud MQTT Broker

Vorteile:

* Projekt ist online erreichbar
* Keine lokale Installation für Tester nötig
* ESP32 kann Daten direkt in die Cloud senden
* Dashboard kann von Laptop, Handy oder anderen Geräten geöffnet werden

---

### 15. MQTT Authentication

MQTT Authentication schützt das System vor unautorisierten Geräten.

Es gibt getrennte MQTT-Benutzer:

```text
Sensor_user      → ESP32 sendet Sensordaten
Railway_backend  → Backend empfängt Sensordaten
```

Vorteile:

* Nur autorisierte Geräte dürfen Daten senden
* Fake-Sensordaten werden erschwert
* Backend und Sensor haben getrennte Rechte
* Mehr Sicherheit im MQTT-System

Beispiel:

```text
ESP32 darf publishen
Backend darf subscriben
```

---

### 16. Machine Learning Vorhersage

Das Dashboard enthält eine Machine-Learning-Vorhersage.

Ziel:

```text
Vorhersage zukünftiger Sensorwerte
```

Beispiel:

```text
In 30 Minuten: 34 °C
```

Die ML-Funktion kann historische Sensordaten verwenden, um zukünftige Temperaturwerte zu schätzen.

Vorteile:

* Frühzeitige Erkennung möglicher kritischer Werte
* Erweiterung über reine Echtzeit-Anzeige hinaus
* Demonstration von Datenanalyse im IoT-Kontext

---

## 🔐 Sicherheit

Das Projekt nutzt mehrere Sicherheitsmechanismen:

* Benutzer-Login im Dashboard
* MQTT Authentication
* getrennte MQTT-Benutzer für Sensor und Backend
* Cloud-Zugangsdaten über Umgebungsvariablen
* keine festen Passwörter im öffentlichen Code

Wichtige Umgebungsvariablen für das Backend:

```env
MQTT_BROKER=ec53cff1a655417a8246e130835c8427.s1.eu.hivemq.cloud
MQTT_PORT=8883
MQTT_USERNAME=Railway_backend
MQTT_PASSWORD=DEIN_PASSWORT
```

---

## ▶️ Ausführung

### Lokale Ausführung mit Docker

```powershell
cd C:\Users\guedr\iot-dashboard
docker compose up -d mqtt backend frontend
docker compose stop sensor
```

Dashboard lokal öffnen:

```text
http://localhost:8501
```

Backend lokal öffnen:

```text
http://localhost:8000
```

---

### Online-Ausführung

Online Dashboard:

```text
https://iot-dashboard-production-da48.up.railway.app
```

Backend API:

```text
https://backend-production-4878.up.railway.app
```

Sensordaten:

```text
https://backend-production-4878.up.railway.app/sensordaten
```

---

## 📂 Projektstruktur

```text
/backend        # FastAPI Backend, MQTT Subscriber, REST API
/frontend       # Streamlit Dashboard
/sensors        # Sensor-Simulation
/database       # Datenbank und Modelle
/docs           # Projektdokumentation
```

[Abschlussbericht als PDF](docs/IoT_Sensor_Dashboard_Abschlussbericht.pdf)

---

## ✅ Finaler Projektstatus

Das Projekt unterstützt:

* echte ESP32-Sensordaten
* mehrere Sensoren
* MQTT-Kommunikation
* MQTT Authentication
* REST API
* Online Dashboard
* Auto Refresh
* historische Analyse
* Diagramme
* Grenzwertwarnungen
* E-Mail-Alerts
* CSV/PDF Export
* Docker Deployment
* Cloud Deployment
* Machine-Learning-Vorhersage

Damit demonstriert das Projekt zentrale Konzepte verteilter Systeme in einer realistischen IoT-Anwendung.
