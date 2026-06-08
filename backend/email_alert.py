import os
import time
import smtplib
from email.message import EmailMessage


SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 465

EMAIL_SENDER = os.getenv("EMAIL_SENDER")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
EMAIL_RECEIVER = os.getenv("EMAIL_RECEIVER")

EMAIL_COOLDOWN_SECONDS = 300  # 5 Minuten
last_email_time = 0


def send_email_alert(subject: str, body: str) -> None:
    global last_email_time

    current_time = time.time()

    if current_time - last_email_time < EMAIL_COOLDOWN_SECONDS:
        print("Email skipped: cooldown active.")
        return

    if not EMAIL_SENDER or not EMAIL_PASSWORD or not EMAIL_RECEIVER:
        print("Email skipped: missing EMAIL environment variables.")
        return

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = EMAIL_SENDER
    msg["To"] = EMAIL_RECEIVER
    msg.set_content(body)

    try:
        with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT) as smtp:
            smtp.login(EMAIL_SENDER, EMAIL_PASSWORD)
            smtp.send_message(msg)

        last_email_time = current_time
        print("Email alert sent successfully.")

    except Exception as e:
        print(f"Email error: {e}")
