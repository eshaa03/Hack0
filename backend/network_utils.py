import socket
import os
import smtplib
from email.message import EmailMessage
from dotenv import load_dotenv

load_dotenv()

def is_online(host="8.8.8.8", port=53, timeout=3):
    """Check if the system has active internet connection"""
    try:
        socket.setdefaulttimeout(timeout)
        socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect((host, port))
        return True
    except socket.error:
        return False

def send_real_email(recipient_email, otp_code):
    """Send real OTP via SMTP"""
    if not recipient_email or not is_online():
        return False
        
    sender = os.getenv("SMTP_EMAIL")
    password = os.getenv("SMTP_PASSWORD")
    
    if not sender or not password:
        print("NetworkUtils Warning: SMTP credentials missing in .env")
        return False

    try:
        msg = EmailMessage()
        msg.set_content(f"Your Hack0 authentication code is: {otp_code}")
        msg['Subject'] = 'Hack0 Real-Time Secure Code'
        msg['From'] = sender
        msg['To'] = recipient_email
        
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(sender, password)
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        print(f"NetworkUtils Error sending email: {e}")
        return False

def send_real_sms(recipient_phone, otp_code):
    """Send real OTP via Twilio SMS"""
    if not recipient_phone or not is_online():
        return False
        
    account_sid = os.getenv("TWILIO_ACCOUNT_SID")
    auth_token = os.getenv("TWILIO_AUTH_TOKEN")
    twilio_number = os.getenv("TWILIO_PHONE_NUMBER")
    
    if not account_sid or not auth_token or not twilio_number:
        print("NetworkUtils Warning: Twilio credentials missing in .env")
        return False
        
    try:
        from twilio.rest import Client
        client = Client(account_sid, auth_token)
        message = client.messages.create(
            body=f"Your Hack0 secure OTP is: {otp_code}",
            from_=twilio_number,
            to=recipient_phone
        )
        return True
    except Exception as e:
        print(f"NetworkUtils Error sending SMS: {e}")
        return False
