import socket
import os
import smtplib
from email.message import EmailMessage
from dotenv import load_dotenv
from urllib.parse import quote

import requests

load_dotenv()

def is_online(host="8.8.8.8", port=53, timeout=3):
    try:
        socket.setdefaulttimeout(timeout)
        socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect((host, port))
        return True
    except socket.error:
        return False

def _get_smtp_credentials():
    sender = os.getenv("SMTP_EMAIL")
    password = os.getenv("SMTP_PASSWORD")
    return sender, password

def _send_via_smtp(recipient_email, subject, body, attachments=None):
    if not recipient_email or not is_online():
        return False

    sender, password = _get_smtp_credentials()
    if not sender or not password:
        print("NetworkUtils Warning: SMTP credentials missing in .env")
        return False

    try:
        import mimetypes

        msg = EmailMessage()
        msg.set_content(body)
        msg["Subject"] = subject
        msg["From"] = sender
        msg["To"] = recipient_email

        for file_path in attachments or []:
            if os.path.exists(file_path):
                ctype, encoding = mimetypes.guess_type(file_path)
                if ctype is None or encoding is not None:
                    ctype = "application/octet-stream"
                maintype, subtype = ctype.split("/", 1)
                with open(file_path, "rb") as fp:
                    msg.add_attachment(
                        fp.read(),
                        maintype=maintype,
                        subtype=subtype,
                        filename=os.path.basename(file_path),
                    )

        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(sender, password)
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        print(f"NetworkUtils Error sending email: {e}")
        return False

def send_real_email(recipient_email, otp_code):
    """Send real OTP via SMTP"""
    return _send_via_smtp(
        recipient_email,
        "Hack0 Real-Time Secure Code",
        f"Your Hack0 authentication code is: {otp_code}",
    )

def send_carrier_email(recipient_email, file_paths):
    """Send carrier files seamlessly to a recipient."""
    return _send_via_smtp(
        recipient_email,
        "Hack0 Secure Export",
        "Please find attached the exported Hack0 Secure Carrier and required Private Key (if mapped).\nUse Hack0 Recovery to decode.",
        attachments=file_paths,
    )

def send_real_sms(recipient_phone, otp_code):
    """SMS disabled - email only."""
    print("SMS disabled - use Email OTP.")
    return False
