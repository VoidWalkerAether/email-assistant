"""
Email sender module

This module handles sending emails and validating email addresses.
"""

import re
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional


# SMTP configuration - should be set via environment variables in production
SMTP_SERVER = "smtp.example.com"
SMTP_PORT = 587
SMTP_USER = ""
SMTP_PASSWORD = ""
SENDER_EMAIL = "noreply@example.com"


def send_email(
    to: str,
    subject: str,
    body: str,
    smtp_server: Optional[str] = None,
    smtp_port: Optional[int] = None,
    smtp_user: Optional[str] = None,
    smtp_password: Optional[str] = None,
    sender_email: Optional[str] = None
) -> bool:
    """
    Send an email.

    Args:
        to: Recipient email address
        subject: Email subject
        body: Email body content
        smtp_server: SMTP server address (optional, uses default if not provided)
        smtp_port: SMTP server port (optional, uses default if not provided)
        smtp_user: SMTP username (optional, uses default if not provided)
        smtp_password: SMTP password (optional, uses default if not provided)
        sender_email: Sender email address (optional, uses default if not provided)

    Returns:
        True if sent successfully, False otherwise
    """
    if not validate_email(to):
        return False

    smtp_server = smtp_server or SMTP_SERVER
    smtp_port = smtp_port or SMTP_PORT
    smtp_user = smtp_user or SMTP_USER
    smtp_password = smtp_password or SMTP_PASSWORD
    sender_email = sender_email or SENDER_EMAIL

    msg = MIMEMultipart()
    msg["From"] = sender_email
    msg["To"] = to
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    try:
        with smtplib.SMTP(smtp_server, smtp_port, timeout=10) as server:
            server.starttls()
            if smtp_user and smtp_password:
                server.login(smtp_user, smtp_password)
            server.send_message(msg)
        return True
    except (smtplib.SMTPException, ConnectionError, OSError):
        return False


def validate_email(email: str) -> bool:
    """
    Validate email format.

    Args:
        email: Email address to validate

    Returns:
        True if valid format
    """
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


TEST_EMAIL = "test@example.com"

if __name__ == "__main__":
    try:
        print(validate_email("test@example.com"))  # True
        print(validate_email("invalid"))  # False
        print(send_email("test@example.com", "Hello", "World"))  # False (no valid SMTP config)
    except Exception as e:
        print(f"An error occurred: {e}")