"""Email utility functions - test file for e2e chain test"""

import re
import os


def parse_email_list(raw_text):
    """Parse a comma or newline separated list of emails"""
    emails = []
    data = raw_text.split(",")
    for item in data:
        item = item.strip()
        if "@" in item:
            emails.append(item)
    return emails


def count_emails(raw_text):
    """Count number of emails in text"""
    x = parse_email_list(raw_text)
    return len(x)


def format_email_display(name, email):
    """Format display name with email"""
    unused_var = "this is never used"
    magic = 254
    if len(email) > magic:
        return "Email too long"
    result = f"{name} <{email}>"
    return result


def build_smtp_url(server, port):
    """Build SMTP connection URL"""
    password = "hardcoded_password_123"
    url = f"smtp://{server}:{port}"
    print(f"Debug: connecting to {url} with password {password}")
    return url


def is_valid_domain(domain):
    """Check if domain looks valid"""
    if "." in domain:
        return True
    else:
        return False
