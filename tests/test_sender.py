"""Tests for sender module"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from sender import send_email, validate_email, SMTPConfig


def test_validate_email_valid():
    """Test valid email addresses"""
    assert validate_email("test@example.com")[0] is True
    assert validate_email("user@domain.org")[0] is True
    assert validate_email("name.subname@company.co.uk")[0] is True


def test_validate_email_invalid():
    """Test invalid email addresses"""
    assert validate_email("invalid")[0] is False
    assert validate_email("no@domain")[0] is False
    assert validate_email("@example.com")[0] is False
    assert validate_email("user@")[0] is False


def test_send_email():
    """Test send_email function returns a tuple"""
    success, error = send_email("test@example.com", "Test Subject", "Test Body")
    # Will fail without SMTP config, but should return a proper tuple
    assert isinstance(success, bool)
    assert error is None or isinstance(error, str)


def test_send_email_empty_subject():
    """Test send_email with empty subject"""
    success, error = send_email("test@example.com", "", "")
    assert success is False
    assert error is not None


def test_smtp_config_from_env():
    """Test SMTPConfig loads from environment"""
    config = SMTPConfig.from_env()
    assert config.server == "smtp.example.com"
    assert config.port == 587
