"""Tests for sender module"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from sender import send_email, validate_email


def test_validate_email_valid():
    """Test valid email addresses"""
    assert validate_email("test@example.com") == True
    assert validate_email("user@domain.org") == True
    assert validate_email("name.subname@company.co.uk") == True


def test_validate_email_invalid():
    """Test invalid email addresses"""
    assert validate_email("invalid") == False
    assert validate_email("no@domain") == False
    assert validate_email("@example.com") == False
    assert validate_email("user@") == False


def test_send_email():
    """Test send_email function"""
    result = send_email("test@example.com", "Test Subject", "Test Body")
    assert result == True


def test_send_email_empty_body():
    """Test send_email with empty body"""
    result = send_email("test@example.com", "", "")
    assert result == True
