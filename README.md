# IoT-Dashboard – Projekt Verteilte Systeme (Projektbeschreibung)

## 📌 Projektübersicht

Dieses Projekt implementiert ein verteiltes IoT-System zur Erfassung, Verarbeitung und Visualisierung von Sensordaten in Echtzeit. Ziel ist es, eine skalierbare Architektur zu entwickeln, bei der mehrere unabhängige Komponenten über Netzwerkprotokolle miteinander kommunizieren.

---

## 🎯 Zielsetzung

Das Projekt demonstriert zentrale Konzepte verteilter Systeme, insbesondere:

* Kommunikation zwischen verteilten Komponenten
* Verarbeitung von Datenströmen in Echtzeit
* Integration verschiedener Technologien (MQTT, REST)

---

## 🏗️ Systemarchitektur

Die Anwendung besteht aus mehreren logisch getrennten Komponenten:

* **Sensor-Simulatoren (Python):** Generieren kontinuierlich Sensordaten (z. B. Temperatur, Luftfeuchtigkeit)
* **MQTT-Broker (Mosquitto):** Vermittelt Nachrichten zwischen Sendern und Empfängern
* **Backend (Flask oder FastAPI):** Empfängt, verarbeitet und speichert Daten
* **Datenbank (SQLite):** Persistente Speicherung der Sensordaten
* **Web-Dashboard (HTML/JavaScript/Flask oder Streamlit mit Python):** Visualisierung der Daten im Browser

---

## 🔄 Systemablauf

1. Sensor-Simulatoren erzeugen Messdaten
2. Daten werden über das MQTT-Protokoll veröffentlicht
3. Das Backend empfängt die Daten als Subscriber
4. Speicherung der Daten in der SQLite-Datenbank
5. Bereitstellung der Daten über eine REST API
6. Anzeige der Daten im Web-Dashboard in Echtzeit

---

## ⚙️ Verwendete Technologien

* **MQTT** – Publish/Subscribe-basierte Kommunikation
* **REST API (HTTP)** – Schnittstelle für Datenzugriff
* **Python** – Backend und Simulation
* **SQLite** – Leichtgewichtige Datenbanklösung
* **HTML, CSS, JavaScript, Flask oder Streamlit mit Python** – Frontend und Visualisierung

---

## 🚀 Funktionalitäten

### Basisfunktionen

* Echtzeit-Erfassung und Anzeige von Sensordaten
* Unterstützung mehrerer Sensoren
* Web-Oberfläche zur Visualisierung

### Erweiterungen (Optional)

* Grafische Darstellung (Diagramme)
* Grenzwertbasierte Warnungen
* Historische Datenanalyse

---

## 👥 Team

Dieses Projekt wird mit 1 Studierenden umgesetzt.

---

## ▶️ Ausführung

1. Starten des MQTT-Brokers (z. B. Mosquitto)
2. Ausführen der Sensor-Simulatoren
3. Starten des Backend-Servers
4. Öffnen des Dashboards im Webbrowser

---

## 📂 Projektstruktur

```
/backend        # Serverlogik und API
/sensors        # Sensor-Simulation
/frontend       # Web-Dashboard
/database       # Datenbank und Modelle
```

---

