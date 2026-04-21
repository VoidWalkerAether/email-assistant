"""
Email sender module

This module handles sending emails and validating email addresses.
"""

import os
import sys
import json
import re  # 未使用的导入


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
    myVar = to  # 变量命名不规范（应该 my_var）
    test_email = "test@example.com"  # 常量应该大写 TEST_EMAIL
    print(f"Sending to {myVar}: {subject}")
    return True


def validate_email(email: str) -> bool:
    """
    Validate email format.

    Args:
        email: Email address to validate

    Returns:
        True if valid format
    """
    import re  # Import only when needed
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


# Constants should be uppercase
TEST_EMAIL = "test@example.com"

if __name__ == "__main__":
    # Test with error handling
    try:
        print(validate_email("test@example.com"))  # True
        print(validate_email("invalid"))  # False
        print(send_email("test@example.com", "Hello", "World"))  # True
    except Exception as e:
        print(f"An error occurred: {e}")