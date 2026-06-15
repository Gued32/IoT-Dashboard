#!/usr/bin/env python3
import base64
import streamlit as st
from streamlit_autorefresh import st_autorefresh
import numpy as np
import pandas as pd
import plotly.express as px
import json
import os
import requests
import time
from io import BytesIO
from pathlib import Path
from statistics import mean
from urllib.error import HTTPError, URLError
from urllib.request import urlopen
from reportlab.lib.pagesizes import A4, landscape
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from sklearn.linear_model import LinearRegression


default_backend_url = os.getenv("BACKEND_URL", "http://localhost:8000")
PREDICTION_MINUTES = 60
TEMP_LIMIT = 30
HUMIDITY_LIMIT = 70
PRESSURE_LIMIT = 1030
GAS_LIMIT = 1800
ML_EMAIL_COOLDOWN_SECONDS = 3600
SENSOR_NAMES = {
    "bme280_1": "BME280_1 - Temperatur/Luftfeuchtigkeit/Luftdruck-Sensor",
    "bme280_2": "BME280_2 - Temperatur/Luftfeuchtigkeit/Luftdruck-Sensor",
    "mq2_1": "MQ2_1 - Gas-/Rauchüberwachung-Sensor",
}


def image_to_base64(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode()


def show_email_success_message():
    email_icon_path = Path("frontend/assets/email_red_white.png")

    if not email_icon_path.exists():
        email_icon_path = Path("assets/email_red_white.png")

    if not email_icon_path.exists():
        email_icon_path = Path(__file__).resolve().parent / "assets" / "email_red_white.png"

    email_icon_base64 = image_to_base64(email_icon_path)

    st.markdown(
        f"""
        <div style="
            background-color: #e8f5e9;
            padding: 16px 20px;
            border-radius: 8px;
            color: #1b5e20;
            font-size: 18px;
            display: flex;
            align-items: center;
            gap: 14px;
            margin-top: 10px;
            margin-bottom: 10px;
        ">
            <img src="data:image/png;base64,{email_icon_base64}"
                 style="width: 34px; height: 34px; object-fit: contain;">
            <span>Warnung erkannt – E-Mail-Warnung wurde erfolgreich gesendet.</span>
        </div>
        """,
        unsafe_allow_html=True,
    )


def fetch_json(url: str):
    try:
        with urlopen(url, timeout=5) as response:
            return json.loads(response.read().decode("utf-8")), None
    except HTTPError as exc:
        return None, f"HTTP {exc.code}: {exc.reason}"
    except URLError as exc:
        return None, f"Verbindungsfehler: {exc.reason}"
    except TimeoutError:
        return None, "Zeitüberschreitung bei der Anfrage."
    except json.JSONDecodeError:
        return None, "Ungültige JSON-Antwort vom Backend."


def send_ml_alert_email(
    backend_url,
    sensor_id,
    prediction_minutes,
    warnings,
    current_values,
    predicted_values,
):
    try:
        payload = {
            "sensor_id": sensor_id,
            "prediction_minutes": prediction_minutes,
            "warnings": warnings,
            "current_values": current_values,
            "predicted_values": predicted_values,
        }

        response = requests.post(
            f"{backend_url}/ml-alert-email",
            json=payload,
            timeout=15,
        )

        if response.status_code == 200:
            return response.json().get("email_sent", False)

        print(f"ML email request failed: {response.status_code} - {response.text}")
        return False

    except Exception as e:
        print(f"ML alert email request exception: {e}")
        return False


def format_sensor_name(sensor_id):
    return SENSOR_NAMES.get(
        sensor_id,
        sensor_id.upper().replace("_", " ")
    )


def predict_future_value(df, value_column, minutes_ahead=30):
    """
    Erstellt eine einfache ML-Vorhersage für einen Sensorwert.
    Beispiel: Temperatur in 30 Minuten.
    """

    if df is None or df.empty:
        return None

    data = df.copy()

    if "timestamp" not in data.columns:
        return None

    if value_column not in data.columns:
        return None

    if "timestamp_dt" in data.columns:
        data["prediction_timestamp_dt"] = pd.to_datetime(
            data["timestamp_dt"],
            errors="coerce",
            utc=True,
        )
    else:
        data["prediction_timestamp_dt"] = pd.to_datetime(
            data["timestamp"],
            errors="coerce",
            format="mixed",
            utc=True,
        )
    data[value_column] = pd.to_numeric(data[value_column], errors="coerce")

    data = data.dropna(subset=["prediction_timestamp_dt", value_column])

    if len(data) < 5:
        return None

    data = data.sort_values("prediction_timestamp_dt")
    start_time = data["prediction_timestamp_dt"].min()

    data["minutes_from_start"] = (
        data["prediction_timestamp_dt"] - start_time
    ).dt.total_seconds() / 60

    X = data[["minutes_from_start"]].to_numpy()
    y = data[value_column].to_numpy()

    if not np.isfinite(X).all() or not np.isfinite(y).all():
        return None

    model = LinearRegression()
    model.fit(X, y)

    last_minute = data["minutes_from_start"].max()
    future_minute = last_minute + minutes_ahead

    prediction = model.predict(np.array([[future_minute]]))[0]

    return round(float(prediction), 2)


def create_pdf_report(export_df, selected_sensor):
    buffer = BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(A4),
        rightMargin=20,
        leftMargin=20,
        topMargin=20,
        bottomMargin=20,
    )

    styles = getSampleStyleSheet()
    elements = []

    title = Paragraph(
        f"IoT Sensor Dashboard - Export für {format_sensor_name(selected_sensor)}",
        styles["Title"],
    )
    elements.append(title)
    elements.append(Spacer(1, 12))

    pdf_df = export_df.copy().fillna("-")
    pdf_df.index.name = "Nr."
    pdf_df = pdf_df.reset_index()

    data = [pdf_df.columns.tolist()] + pdf_df.astype(str).values.tolist()

    table = Table(data, repeatRows=1)

    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 7),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 6),
            ]
        )
    )

    elements.append(table)

    doc.build(elements)

    buffer.seek(0)
    return buffer


st.set_page_config(page_title="IoT Dashboard", layout="wide")
st.markdown(
    """
    <style>
    .block-container {
        padding-top: 0rem !important;
        padding-bottom: 1rem !important;
    }

    h1 {
        margin-top: -0.5rem !important;
        padding-top: 0rem !important;
    }

    section[data-testid="stSidebar"] .block-container {
        padding-top: 0rem !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

VALID_USERNAME = "Ayoub"
VALID_PASSWORD = "1234"

if not st.session_state.logged_in:
    st.sidebar.title("Login")

    username = st.sidebar.text_input("Benutzername")
    password = st.sidebar.text_input("Passwort", type="password")

    st.sidebar.markdown("""
<style>
/* Einloggen Button komplett grün */
div.stButton > button {
    width: 100%;
    background-color: #28a745;
    color: white;
    border: none;
    border-radius: 8px;
    padding: 10px;
    font-weight: bold;
}

/* Hover Effekt */
div.stButton > button:hover {
    background-color: #1e7e34;
    color: white;
}
</style>
""", unsafe_allow_html=True)

    if st.sidebar.button("Einloggen"):
        if username.strip() == VALID_USERNAME and password.strip() == VALID_PASSWORD:
            st.session_state.logged_in = True
            st.rerun()
        else:
            st.sidebar.warning("Falscher Benutzername oder Passwort")

    st.stop()

st.sidebar.success("✅ Eingeloggt")

st.sidebar.markdown("""
<style>
/* Logout Button komplett rot */
div.stButton > button {
    width: 100%;
    background-color: #ff4b4b;
    color: white;
    border: none;
    border-radius: 8px;
    padding: 10px;
    font-weight: bold;
}

/* Hover Effekt */
div.stButton > button:hover {
    background-color: #cc0000;
    color: white;
}
</style>
""", unsafe_allow_html=True)

# Größere Schrift für Sensor-Auswahl
st.markdown("""
<style>
div[data-testid="stSelectbox"] label {
    font-size: 1.1rem;
    font-weight: 600;
}

div[data-testid="stSelectbox"] div[data-baseweb="select"] > div {
    font-size: 1.1rem;
}

div[data-testid="stSelectbox"] ul {
    font-size: 1.05rem;
}
</style>
""", unsafe_allow_html=True)

if st.sidebar.button("Ausloggen"):
    st.session_state.logged_in = False
    st.rerun()

# Auto Refresh erst nach Login anzeigen
refresh_seconds = st.sidebar.slider("Auto Refresh (Sekunden)", 2, 30, 5)
st_autorefresh(interval=refresh_seconds * 1000, key="auto_refresh")

st.title("IoT Sensor Dashboard")

backend_url = st.sidebar.text_input(
    "Backend URL",
    value=default_backend_url,
)
backend_url = backend_url.rstrip("/")
history_limit = st.sidebar.slider(
    "Anzahl Messwerte in Tabelle",
    min_value=10,
    max_value=1000,
    value=100,
    step=10,
)

health_data, health_error = fetch_json(f"{backend_url}/health")

backend_ok = (
    not health_error
    and isinstance(health_data, dict)
    and health_data.get("status") == "ok"
)

if backend_ok:
    st.sidebar.success("Backend-Status: ✅ ok")
    st.sidebar.caption("Das Backend läuft. Sensordaten können geladen und gespeichert werden.")
else:
    st.sidebar.error("Backend-Status: ❌ nicht erreichbar")
    st.sidebar.caption("Das Backend läuft nicht oder die Backend-URL ist falsch.")

    if health_error:
        st.error(f"Backend nicht erreichbar: {health_error}")
    else:
        backend_status = (
            health_data.get("status", "unknown")
            if isinstance(health_data, dict)
            else "unknown"
        )
        st.error(f"Backend nicht erreichbar: Status `{backend_status}`")
    st.stop()

history, history_error = fetch_json(f"{backend_url}/sensordaten")
has_valid_history = isinstance(history, list) and bool(history)
filtered_history = []
selected_sensor = "sensor"

if has_valid_history:
    df = pd.DataFrame(history)
    if "sensor_id" in df.columns:
        sensor_ids = sorted(df["sensor_id"].dropna().unique().tolist())

        if sensor_ids:
            if "selected_sensor" not in st.session_state:
                st.session_state.selected_sensor = sensor_ids[0] if sensor_ids else None

            if st.session_state.selected_sensor not in sensor_ids:
                st.session_state.selected_sensor = sensor_ids[0] if sensor_ids else None

            selected_sensor = st.selectbox(
                "Sensor auswählen",
                sensor_ids,
                index=sensor_ids.index(st.session_state.selected_sensor),
                format_func=format_sensor_name,
                key="selected_sensor",
            )
            filtered_history = [
                entry for entry in history if entry.get("sensor_id") == selected_sensor
            ]
        else:
            st.warning("Keine sensor_id in den Messwerten gefunden.")
            filtered_history = history
    else:
        st.warning("Keine sensor_id in den Messwerten gefunden.")
        filtered_history = history

df = pd.DataFrame(filtered_history)
sensor_df = df.copy()
chart_df = pd.DataFrame()
table_df = pd.DataFrame()
if not df.empty and "timestamp" in df.columns:
    timestamp_raw = df["timestamp"].astype("string")
    has_timezone = timestamp_raw.str.contains(r"(Z|[+-]\d{2}:\d{2})$", na=False)

    aware_dt = pd.to_datetime(
        timestamp_raw.where(has_timezone),
        errors="coerce",
        format="mixed",
        utc=True,
    ).dt.tz_convert("Europe/Berlin")
    naive_dt = pd.to_datetime(
        timestamp_raw.where(~has_timezone),
        errors="coerce",
        format="mixed",
    ).dt.tz_localize("Europe/Berlin", nonexistent="shift_forward", ambiguous="NaT")
    df["timestamp_dt"] = aware_dt.fillna(naive_dt)

    # Schöne Anzeige
    df["timestamp_display"] = df["timestamp_dt"].dt.strftime("%d.%m.%Y %H:%M:%S")
    df = df.dropna(subset=["timestamp_dt"]).copy()
    sensor_df = df.copy()

    # Gleiches Zeitfenster für Verlauf und Tabelle
    window_df = df.sort_values("timestamp_dt", ascending=False).head(history_limit).copy()

    # Für Diagramme: aufsteigend sortieren
    chart_df = window_df.sort_values("timestamp_dt", ascending=True)

    # Für Tabelle: absteigend sortieren
    table_df = window_df.sort_values("timestamp_dt", ascending=False)

latest = filtered_history[0] if filtered_history else None
latest_display = (
    table_df["timestamp_display"].iloc[0]
    if not table_df.empty and "timestamp_display" in table_df.columns
    else latest.get("timestamp", "unbekannt") if latest else "unbekannt"
)
sensor_type = None
if latest:
    sensor_type = latest.get("sensor_type")
    sensor_id = latest.get("sensor_id", "")
    if not sensor_type and isinstance(sensor_id, str):
        if sensor_id.lower().startswith("bme280"):
            sensor_type = "BME280"
        elif sensor_id.lower().startswith("mq2"):
            sensor_type = "MQ2"

st.subheader("Aktuelle Werte")

if history_error:
    col1, col2 = st.columns(2)
    col1.metric("Temperatur (°C)", "–")
    col2.metric("Luftfeuchtigkeit (%)", "–")
    st.warning(f"Keine Sensordaten verfügbar: {history_error}")
elif not isinstance(history, list):
    col1, col2 = st.columns(2)
    col1.metric("Temperatur (°C)", "–")
    col2.metric("Luftfeuchtigkeit (%)", "–")
    st.error("Ungültiges Datenformat vom Backend. Erwartet wurde eine Liste.")
elif latest is None:
    col1, col2 = st.columns(2)
    col1.metric("Temperatur (°C)", "–")
    col2.metric("Luftfeuchtigkeit (%)", "–")
    st.info("Noch keine Messwerte vorhanden.")
else:
    email_alert_warnings = []

    if sensor_type == "BME280":
        col1, col2, col3 = st.columns(3)

        col1.metric(
            "Temperatur (°C)",
            f"{latest['temperature_c']:.2f}"
            if latest["temperature_c"] is not None else "-"
        )

        col2.metric(
            "Luftfeuchtigkeit (%)",
            f"{latest['humidity_percent']:.2f}"
            if latest["humidity_percent"] is not None else "-"
        )

        col3.metric(
            "Luftdruck (hPa)",
            f"{latest['pressure_hpa']:.2f}"
            if latest["pressure_hpa"] is not None else "-"
        )

        if latest.get("temperature_c") is not None and latest["temperature_c"] > TEMP_LIMIT:
            warning_text = f"Warnung: Hohe Temperatur erkannt ({latest['temperature_c']:.2f} °C)."
            email_alert_warnings.append(warning_text)
            st.warning(warning_text)
        if latest.get("humidity_percent") is not None and latest["humidity_percent"] > HUMIDITY_LIMIT:
            warning_text = f"Warnung: Hohe Luftfeuchtigkeit erkannt ({latest['humidity_percent']:.2f} %)."
            email_alert_warnings.append(warning_text)
            st.warning(warning_text)
        if latest.get("pressure_hpa") is not None and latest["pressure_hpa"] < 980:
            warning_text = "Warnung: Niedriger Luftdruck erkannt"
            st.warning(warning_text)
        if latest.get("pressure_hpa") is not None and latest["pressure_hpa"] > PRESSURE_LIMIT:
            warning_text = f"Warnung: Hoher Luftdruck erkannt ({latest['pressure_hpa']:.2f} hPa)."
            email_alert_warnings.append(warning_text)
            st.warning(warning_text)

    elif sensor_type == "MQ2":
        col1, col2 = st.columns(2)

        col1.metric(
            "Gaswert (ADC)",
            latest["gas_value"] if latest["gas_value"] is not None else "-"
        )

        col2.markdown("Rauchwarnung")

        if latest["smoke_warning"] is True:
            col2.markdown(
                "<h1 style='color: red;'>Ja</h1>",
                unsafe_allow_html=True
            )
            warning_text = "Warnung: Rauchwarnung erkannt."
            email_alert_warnings.append(warning_text)
            st.warning(warning_text)
        else:
            col2.markdown(
                "<h1 style='color: green;'>Nein</h1>",
                unsafe_allow_html=True
            )

    else:
        st.warning("Unbekannter Sensortyp.")

    email_sent = latest.get("email_sent", False)
    email_sent_success = email_sent is True or str(email_sent).lower() == "true" or email_sent == 1

    if email_sent_success:
        show_email_success_message()
    elif email_alert_warnings:
        show_email_success_message()

    st.caption(f"Letztes Update: {latest_display}")

st.subheader("Historische Analyse")
if filtered_history:
    if sensor_type == "MQ2":
        gas_values = [
            entry.get("gas_value")
            for entry in filtered_history
            if entry.get("gas_value") is not None
        ]
        analysis_cols = st.columns(3)
        analysis_cols[0].metric(
            "Ø Gaswert (ADC)",
            f"{mean(gas_values):.2f}" if gas_values else "–",
        )
        analysis_cols[1].metric(
            "Min Gaswert (ADC)",
            f"{min(gas_values):.2f}" if gas_values else "–",
        )
        analysis_cols[2].metric(
            "Max Gaswert (ADC)",
            f"{max(gas_values):.2f}" if gas_values else "–",
        )
    else:
        temperatures = [
            entry.get("temperature_c")
            for entry in filtered_history
            if entry.get("temperature_c") is not None
        ]
        humidities = [
            entry.get("humidity_percent")
            for entry in filtered_history
            if entry.get("humidity_percent") is not None
        ]

        analysis_cols = st.columns(6)
        analysis_cols[0].metric(
            "Ø Temperatur (°C)",
            f"{mean(temperatures):.2f}" if temperatures else "–",
        )
        analysis_cols[1].metric(
            "Min Temperatur (°C)",
            f"{min(temperatures):.2f}" if temperatures else "–",
        )
        analysis_cols[2].metric(
            "Max Temperatur (°C)",
            f"{max(temperatures):.2f}" if temperatures else "–",
        )
        analysis_cols[3].metric(
            "Ø Luftfeuchtigkeit (%)",
            f"{mean(humidities):.2f}" if humidities else "–",
        )
        analysis_cols[4].metric(
            "Min Luftfeuchtigkeit (%)",
            f"{min(humidities):.2f}" if humidities else "–",
        )
        analysis_cols[5].metric(
            "Max Luftfeuchtigkeit (%)",
            f"{max(humidities):.2f}" if humidities else "–",
        )
else:
    st.info("Für die historische Analyse sind noch keine Messwerte vorhanden.")

st.subheader("Machine-Learning-Vorhersage")

prediction_minutes = PREDICTION_MINUTES
selected_sensor_id = selected_sensor or ""

if history_error:
    st.info("Vorhersage nicht verfügbar, weil keine Historie geladen werden konnte.")
elif sensor_df.empty:
    st.info("Noch nicht genug Messwerte für eine Vorhersage vorhanden.")
else:
    latest_sort_column = "timestamp_dt" if "timestamp_dt" in sensor_df.columns else "timestamp"
    latest_row = sensor_df.sort_values(latest_sort_column).iloc[-1].to_dict()
    current_values = {
        "temperature_c": latest_row.get("temperature_c"),
        "humidity_percent": latest_row.get("humidity_percent"),
        "pressure_hpa": latest_row.get("pressure_hpa"),
        "gas_value": latest_row.get("gas_value"),
    }
    ml_warnings = []
    ml_warning_codes = []
    predicted_values = {}

    if selected_sensor_id.lower().startswith("bme280"):
        predicted_temp = predict_future_value(
            sensor_df,
            "temperature_c",
            minutes_ahead=prediction_minutes,
        )
        predicted_humidity = predict_future_value(
            sensor_df,
            "humidity_percent",
            minutes_ahead=prediction_minutes,
        )
        predicted_pressure = predict_future_value(
            sensor_df,
            "pressure_hpa",
            minutes_ahead=prediction_minutes,
        )
        predicted_values = {
            "temperature_c": predicted_temp,
            "humidity_percent": predicted_humidity,
            "pressure_hpa": predicted_pressure,
            "gas_value": None,
        }

        col1, col2, col3 = st.columns(3)

        with col1:
            if predicted_temp is not None:
                st.metric(
                    f"Temperatur in {prediction_minutes} Min.",
                    f"{predicted_temp:.2f} °C",
                )
            else:
                st.info("Nicht genug Temperaturdaten für Vorhersage.")

        with col2:
            if predicted_humidity is not None:
                st.metric(
                    f"Luftfeuchtigkeit in {prediction_minutes} Min.",
                    f"{predicted_humidity:.2f} %",
                )
            else:
                st.info("Nicht genug Luftfeuchtigkeitsdaten für Vorhersage.")

        with col3:
            if predicted_pressure is not None:
                st.metric(
                    f"Luftdruck in {prediction_minutes} Min.",
                    f"{predicted_pressure:.2f} hPa",
                )
            else:
                st.info("Nicht genug Luftdruckdaten für Vorhersage.")

        if predicted_temp is not None and predicted_temp > TEMP_LIMIT:
            ml_warnings.append(
                f"Temperatur-Vorhersage zu hoch: {predicted_temp:.2f} °C in 1 Stunde"
            )
            ml_warning_codes.append("temperature")

        if predicted_humidity is not None and predicted_humidity > HUMIDITY_LIMIT:
            ml_warnings.append(
                f"Luftfeuchtigkeit-Vorhersage zu hoch: "
                f"{predicted_humidity:.2f} % in 1 Stunde"
            )
            ml_warning_codes.append("humidity")

        if predicted_pressure is not None and predicted_pressure > PRESSURE_LIMIT:
            ml_warnings.append(
                f"Luftdruck-Vorhersage zu hoch: "
                f"{predicted_pressure:.2f} hPa in 1 Stunde"
            )
            ml_warning_codes.append("pressure")

    elif selected_sensor_id.lower().startswith("mq2"):
        predicted_gas = predict_future_value(
            sensor_df,
            "gas_value",
            minutes_ahead=prediction_minutes,
        )
        predicted_values = {
            "temperature_c": None,
            "humidity_percent": None,
            "pressure_hpa": None,
            "gas_value": predicted_gas,
        }

        if predicted_gas is not None:
            st.metric(
                f"Gaswert in {prediction_minutes} Min.",
                f"{predicted_gas:.2f} ADC",
            )
            if predicted_gas > GAS_LIMIT:
                ml_warnings.append(
                    f"Gaswert-Vorhersage zu hoch: {predicted_gas:.2f} ADC in 1 Stunde"
                )
                ml_warning_codes.append("gas")
        else:
            st.info("Nicht genug Gaswerte für Vorhersage.")

    else:
        st.info("Für diesen Sensortyp ist keine Vorhersage verfügbar.")

    if "last_ml_alert_email_key" not in st.session_state:
        st.session_state.last_ml_alert_email_key = None

    if "last_ml_alert_email_time" not in st.session_state:
        st.session_state.last_ml_alert_email_time = 0

    if "ml_alert_email_sent_success" not in st.session_state:
        st.session_state.ml_alert_email_sent_success = False

    if "ml_alert_email_success_until" not in st.session_state:
        st.session_state.ml_alert_email_success_until = 0

    if ml_warnings:
        st.warning("ML-Warnung erkannt: " + " | ".join(ml_warnings))

        ml_email_key = (
            f"{selected_sensor_id}-"
            f"{PREDICTION_MINUTES}-"
            f"{'-'.join(ml_warning_codes)}"
        )
        current_time = time.time()
        should_send_ml_email = (
            st.session_state.last_ml_alert_email_key != ml_email_key
            or current_time - st.session_state.last_ml_alert_email_time
            > ML_EMAIL_COOLDOWN_SECONDS
        )

        if should_send_ml_email:
            email_sent = send_ml_alert_email(
                backend_url,
                selected_sensor_id,
                PREDICTION_MINUTES,
                ml_warnings,
                current_values,
                predicted_values,
            )

            if email_sent:
                st.session_state.ml_alert_email_sent_success = True
                st.session_state.ml_alert_email_success_until = time.time() + 60
                st.session_state.last_ml_alert_email_key = ml_email_key
                st.session_state.last_ml_alert_email_time = current_time
            else:
                st.session_state.ml_alert_email_sent_success = False

        if (
            st.session_state.get("ml_alert_email_sent_success", False)
            and time.time() < st.session_state.get("ml_alert_email_success_until", 0)
        ):
            show_email_success_message()

        if not should_send_ml_email:
            remaining_minutes = int(
                (
                    ML_EMAIL_COOLDOWN_SECONDS
                    - (current_time - st.session_state.last_ml_alert_email_time)
                )
                // 60
            ) + 1
            st.info(
                f"ML-E-Mail-Cooldown aktiv. Nächste E-Mail in ca. "
                f"{remaining_minutes} Min."
            )
    else:
        st.session_state.ml_alert_email_sent_success = False
        st.session_state.ml_alert_email_success_until = 0

st.subheader("Verlauf")
if history_error:
    st.error(f"Historie konnte nicht geladen werden: {history_error}")
elif not isinstance(history, list):
    st.error("Historie konnte nicht geladen werden: Ungültiges Datenformat.")
elif chart_df.empty:
    st.info("Noch keine Messwerte vorhanden.")
else:
    chart_data = chart_df.copy()

    if "timestamp_dt" in chart_data.columns:
        chart_data = chart_data.sort_values("timestamp_dt")

    if selected_sensor and selected_sensor.lower().startswith("mq2"):
        chart_data["gas_value"] = pd.to_numeric(chart_data["gas_value"], errors="coerce")
        chart_data["smoke_warning_num"] = (
            chart_data["smoke_warning"]
            .astype(str)
            .str.strip()
            .str.lower()
            .map(
                {
                    "true": 1,
                    "1": 1,
                    "ja": 1,
                    "yes": 1,
                    "false": 0,
                    "0": 0,
                    "nein": 0,
                    "no": 0,
                }
            )
            .fillna(0)
        )

        gas_chart_col, smoke_chart_col = st.columns(2)

        with gas_chart_col:
            fig_gas = px.line(
                chart_data,
                x="timestamp_display",
                y="gas_value",
                markers=True,
                title="Gaswert (ADC)-Verlauf",
            )
            fig_gas.update_layout(xaxis_title="Zeit", yaxis_title="Gaswert (ADC)")
            st.plotly_chart(fig_gas, use_container_width=True, key="mq2_gas_chart")

        with smoke_chart_col:
            fig_smoke = px.line(
                chart_data,
                x="timestamp_display",
                y="smoke_warning_num",
                markers=True,
                title="Rauchwarnung-Verlauf",
                line_shape="hv",
            )
            fig_smoke.update_layout(xaxis_title="Zeit", yaxis_title="Rauchwarnung")
            fig_smoke.update_yaxes(
                tickmode="array",
                tickvals=[0, 1],
                ticktext=["Nein", "Ja"],
                range=[-0.1, 1.1],
            )
            st.plotly_chart(fig_smoke, use_container_width=True, key="mq2_smoke_chart")
    else:
        chart_data["temperature_c"] = pd.to_numeric(
            chart_data["temperature_c"],
            errors="coerce",
        )
        chart_data["humidity_percent"] = pd.to_numeric(
            chart_data["humidity_percent"],
            errors="coerce",
        )

        temp_chart_col, humidity_chart_col = st.columns(2)

        with temp_chart_col:
            fig_temp = px.line(
                chart_data,
                x="timestamp_display",
                y="temperature_c",
                markers=True,
                title="Temperatur-Verlauf",
            )
            fig_temp.update_layout(
                xaxis_title="Zeit",
                yaxis_title="Temperatur (°C)",
            )
            st.plotly_chart(fig_temp, use_container_width=True, key="bme_temp_chart")

        with humidity_chart_col:
            fig_humidity = px.line(
                chart_data,
                x="timestamp_display",
                y="humidity_percent",
                markers=True,
                title="Luftfeuchtigkeit-Verlauf",
            )
            fig_humidity.update_layout(
                xaxis_title="Zeit",
                yaxis_title="Luftfeuchtigkeit (%)",
            )
            st.plotly_chart(
                fig_humidity,
                use_container_width=True,
                key="bme_humidity_chart",
            )

st.subheader("Messwert-Tabelle")
if history_error:
    st.error(f"Messwerte konnten nicht geladen werden: {history_error}")
elif not isinstance(history, list):
    st.error("Messwerte konnten nicht geladen werden: Ungültiges Datenformat.")
elif table_df.empty:
    st.info("Noch keine Messwerte vorhanden.")
else:
    table_limit = history_limit

    if selected_sensor.startswith("mq2"):
        table_df = sensor_df[
            [
                "sensor_id",
                "timestamp_display",
                "gas_value",
                "smoke_warning",
            ]
        ].copy()

        table_df = table_df.rename(
            columns={
                "sensor_id": "Sensor",
                "timestamp_display": "Zeit",
                "gas_value": "Gaswert (ADC)",
                "smoke_warning": "Rauchwarnung",
            }
        )

        table_df["Sensor"] = table_df["Sensor"].apply(format_sensor_name)

        table_df["Rauchwarnung"] = table_df["Rauchwarnung"].apply(
            lambda value: "Ja" if value is True or value == 1 else "Nein"
        )

    else:
        table_df = sensor_df[
            [
                "sensor_id",
                "timestamp_display",
                "temperature_c",
                "humidity_percent",
                "pressure_hpa",
            ]
        ].copy()

        table_df = table_df.rename(
            columns={
                "sensor_id": "Sensor",
                "timestamp_display": "Zeit",
                "temperature_c": "Temperatur (°C)",
                "humidity_percent": "Luftfeuchtigkeit (%)",
                "pressure_hpa": "Luftdruck (hPa)",
            }
        )

        table_df["Sensor"] = table_df["Sensor"].apply(format_sensor_name)

    table_df = table_df.reset_index(drop=True)

    visible_table_df = table_df.head(table_limit).copy()
    visible_table_df.index.name = "Nr."

    st.dataframe(
        visible_table_df,
        use_container_width=True,
    )

    st.markdown(
        """
        <style>
        div[data-testid="stDownloadButton"] button {
            color: white !important;
            border: none !important;
            font-weight: 600 !important;
        }

        div[data-testid="stHorizontalBlock"] > div:nth-child(1)
        div[data-testid="stDownloadButton"] button {
            background-color: orange !important;
        }

        div[data-testid="stHorizontalBlock"] > div:nth-child(2)
        div[data-testid="stDownloadButton"] button {
            background-color: #1f77ff !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.subheader("Export")

    export_df = visible_table_df.copy()
    export_df.index.name = "Nr."

    if not export_df.empty:
        sensor_file_name = str(selected_sensor).replace(" ", "_").lower()

        csv_data = export_df.to_csv(index=True).encode("utf-8-sig")
        pdf_buffer = create_pdf_report(export_df, selected_sensor)

        col_csv, col_pdf = st.columns(2)

        with col_csv:
            st.download_button(
                label="CSV herunterladen",
                data=csv_data,
                file_name=f"{sensor_file_name}_aktuelle_messwert_tabelle.csv",
                mime="text/csv",
                key=f"csv_download_{selected_sensor}",
            )

        with col_pdf:
            st.download_button(
                label="PDF herunterladen",
                data=pdf_buffer,
                file_name=f"{sensor_file_name}_aktuelle_messwert_tabelle.pdf",
                mime="application/pdf",
                key=f"pdf_download_{selected_sensor}",
            )
    else:
        st.info("Keine Daten zum Exportieren vorhanden.")
