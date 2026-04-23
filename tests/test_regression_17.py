import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.email_utils import parse_email_list


def test_parse_email_list_handles_space_separated_emails():
    """Test that parse_email_list correctly handles space-separated email addresses."""
    result = parse_email_list("a@b.com c@d.com")
    assert result == ["a@b.com", "c@d.com"]
