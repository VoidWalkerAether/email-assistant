"""Email utility functions - test file for e2e chain test"""

import re

# Constants
MAX_EMAIL_LENGTH = 254


def is_valid_email(email):
    """Validate email format using regex"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


def parse_email_list(raw_text):
    """Parse a comma or newline separated list of emails"""
    emails = []
    # Split by comma or newline
    data = re.split(r'[,\n]', raw_text)
    for item in data:
        item = item.strip()
        if item and is_valid_email(item):
            emails.append(item)
    return emails


def count_emails(raw_text):
    """Count number of emails in text"""
    email_list = parse_email_list(raw_text)
    return len(email_list)


def format_email_display(name, email):
    """Format display name with email"""
    if len(email) > MAX_EMAIL_LENGTH:
        return "Email too long"
    return f"{name} <{email}>"


def build_smtp_url(server, port):
    """Build SMTP connection URL"""
    return f"smtp://{server}:{port}"


def is_valid_domain(domain):
    """Check if domain looks valid"""
    if not domain or not isinstance(domain, str):
        return False
    
    # Check domain has at least one dot and valid structure
    parts = domain.split('.')
    if len(parts) < 2:
        return False
    
    # Check each part is non-empty and contains only valid characters
    for part in parts:
        if not part or not re.match(r'^[a-zA-Z0-9-]+$', part):
            return False
    
    # Check TLD is at least 2 characters
    if len(parts[-1]) < 2:
        return False
    
    return True