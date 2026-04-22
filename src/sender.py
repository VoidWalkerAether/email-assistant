import os
import re
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional, NamedTuple
from dataclasses import dataclass


@dataclass
class SMTPConfig:
    """SMTP configuration container."""
    server: str
    port: int
    user: str
    password: str
    sender_email: str

    @classmethod
    def from_env(cls) -> "SMTPConfig":
        """Load SMTP configuration from environment variables."""
        return cls(
            server=os.getenv("SMTP_SERVER", "smtp.example.com"),
            port=int(os.getenv("SMTP_PORT", "587")),
            user=os.getenv("SMTP_USER", ""),
            password=os.getenv("SMTP_PASSWORD", ""),
            sender_email=os.getenv("SENDER_EMAIL", "noreply@example.com"),
        )


def validate_email(email: str) -> tuple[bool, Optional[str]]:
    """
    Validate email format.

    Args:
        email: Email address to validate

    Returns:
        Tuple of (is_valid, error_message). error_message is None if valid.
    """
    if not email or not isinstance(email, str):
        return False, "Email address is required and must be a string"

    if not email.strip():
        return False, "Email address cannot be empty or whitespace"

    email = email.strip()

    if len(email) > 254:
        return False, "Email address is too long (max 254 characters)"

    pattern = (
        r"^(?P<local>[a-zA-Z0-9.!#$%&'*+/=?^_`{|}~-]+)"
        r"@"
        r"(?P<domain>[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?"
        r"(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*)$"
    )

    match = re.match(pattern, email)
    if not match:
        return False, "Invalid email format"

    local_part = match.group("local")
    if local_part.startswith(".") or local_part.endswith("."):
        return False, "Local part cannot start or end with a dot"

    if ".." in local_part:
        return False, "Local part cannot contain consecutive dots"

    domain_part = match.group("domain")
    if not domain_part or "." not in domain_part:
        return False, "Domain must contain at least one dot"

    tld = domain_part.split(".")[-1]
    if len(tld) < 2:
        return False, "TLD must be at least 2 characters"

    return True, None


def send_email(
    to: str,
    subject: str,
    body: str,
    config: Optional[SMTPConfig] = None,
) -> tuple[bool, Optional[str]]:
    """
    Send an email.

    Args:
        to: Recipient email address
        subject: Email subject
        body: Email body content
        config: SMTP configuration (optional, uses env vars if not provided)

    Returns:
        Tuple of (success, error_message). error_message is None if successful.
    """
    is_valid, error = validate_email(to)
    if not is_valid:
        return False, f"Invalid recipient email: {error}"

    if not subject or not isinstance(subject, str):
        return False, "Subject is required and must be a string"

    if not body or not isinstance(body, str):
        return False, "Body is required and must be a string"

    if config is None:
        config = SMTPConfig.from_env()

    if not config.server:
        return False, "SMTP server is not configured"

    if not config.sender_email:
        return False, "Sender email is not configured"

    msg = MIMEMultipart()
    msg["From"] = config.sender_email
    msg["To"] = to
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    try:
        with smtplib.SMTP(config.server, config.port, timeout=10) as server:
            server.starttls()
            if config.user and config.password:
                server.login(config.user, config.password)
            server.send_message(msg)
        return True, None
    except smtplib.SMTPAuthenticationError as e:
        return False, f"SMTP authentication failed: {e}"
    except smtplib.SMTPConnectError as e:
        return False, f"Failed to connect to SMTP server: {e}"
    except smtplib.SMTPHeloError as e:
        return False, f"SMTP HELO error: {e}"
    except smtplib.SMTPRecipientsRefused as e:
        return False, f"Recipient refused: {e}"
    except smtplib.SMTPSenderRefused as e:
        return False, f"Sender refused: {e}"
    except smtplib.SMTPDataError as e:
        return False, f"SMTP data error: {e}"
    except smtplib.SMTPException as e:
        return False, f"SMTP error: {e}"
    except ConnectionError as e:
        return False, f"Connection error: {e}"
    except OSError as e:
        return False, f"OS error: {e}"
    except TimeoutError as e:
        return False, f"Timeout error: {e}"


TEST_EMAIL = os.getenv("TEST_EMAIL", "test@example.com")


def run_tests() -> None:
    """Run module tests."""
    print("Testing email validation:")
    print(f"  'test@example.com': {validate_email('test@example.com')[0]}")
    print(f"  'invalid': {validate_email('invalid')[0]}")
    print(f"  '': {validate_email('')[0]}")
    print(f"  'test..test@example.com': {validate_email('test..test@example.com')[0]}")

    print("\nTesting send_email (expected to fail without valid SMTP config):")
    success, error = send_email(TEST_EMAIL, "Hello", "World")
    print(f"  Result: {success}, Error: {error}")


if __name__ == "__main__":
    run_tests()