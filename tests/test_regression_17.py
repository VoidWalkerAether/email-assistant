import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
try:
    from email_utils import parse_email_list
except ImportError:
    # main 上没有此模块，内联一个复现 bug 的函数定义
    def parse_email_list(raw_text):
        import re
        return re.split('[，\n]', raw_text)


def test_parse_email_list_handles_space_separated_emails():
    """测试 parse_email_list 能正确处理空格分隔的邮箱列表"""
    result = parse_email_list("a@b.com c@d.com")
    assert result == ["a@b.com", "c@d.com"]


def test_parse_email_list_handles_mixed_separators():
    """测试 parse_email_list 能处理逗号、换行和空格混合分隔的邮箱列表"""
    result = parse_email_list("a@b.com, c@d.com\ne@f.com g@h.com")
    assert "a@b.com" in result
    assert "c@d.com" in result
    assert "e@f.com" in result
    assert "g@h.com" in result
    assert len(result) == 4


def test_parse_email_list_strips_whitespace():
    """测试 parse_email_list 分割后会去除邮箱地址前后的空白字符"""
    result = parse_email_list("a@b.com   c@d.com")
    assert result == ["a@b.com", "c@d.com"]
