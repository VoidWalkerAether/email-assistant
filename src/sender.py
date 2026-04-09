"""Email sender module - High Risk"""


def send_email(to: str, subject: str, body: str) -> bool:
    """
    Send an email.
    
    Args:
        to: Recipient email address
        subject: Email subject
        body: Email body content
    
    Returns:
        True if sent successfully
    """
    # TODO: Implement actual email sending
    print(f"Sending to {to}: {subject}")
    return True


def validate_email(email: str) -> bool:
    """
    Validate email format.
    
    Args:
        email: Email address to validate
    
    Returns:
        True if valid format
    """
    return "@" in email and "." in email


if __name__ == "__main__":
    # Test
    print(validate_email("test@example.com"))  # True
    print(validate_email("invalid"))  # False
    print(send_email("test@example.com", "Hello", "World"))  # True

# High Risk Test - 2026-04-09
# 这行代码用于测试 High Risk 阻止功能
