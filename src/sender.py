"""Email sender module - High Risk"""

# 故意制造错误用于测试自动修复
import os
import sys
import re
import json


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
    myVar = to  # 变量命名不规范（应该用 my_var）
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
    
    # 多余空行测试
    return "@" in email and "." in email


# 常量应该全大写
test_email = "test@example.com"

if __name__ == "__main__":
    # Test
    print(validate_email("test@example.com"))  # True
    print(validate_email("invalid"))  # False
    print(send_email("test@example.com", "Hello", "World"))  # True

# High Risk Test - 2026-04-09
# 这行代码用于测试 High Risk 阻止功能
