import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from email_utils import parse_email_list


def test_parse_email_list_handles_space_separated_emails():
    """测试 parse_email_list 能够正确处理空格分隔的邮箱列表"""
    result = parse_email_list("a@b.com c@d.com")
    assert result == ["a@b.com", "c@d.com"]
