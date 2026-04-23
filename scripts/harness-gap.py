#!/usr/bin/env python3
"""
Harness Gap — 将缺陷转化为永久测试用例

从 issue 中读取缺陷描述和复现步骤，使用 AI 生成 pytest 测试文件，
写入 tests/test_regression_*.py 并创建 PR。

所有日志输出到 stderr，只有 JSON 输出到 stdout。
"""

import json
import os
import sys
import asyncio
from claude_agent_sdk import query, ClaudeAgentOptions, AssistantMessage, TextBlock


def read_file_content(filepath):
    """读取文件内容"""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        print(f"[ERROR] Reading {filepath}: {e}", file=sys.stderr)
        return ""


async def call_ai_for_test(issue_info, source_code):
    """调用 AI 根据缺陷描述生成 pytest 测试"""

    auth_token = os.environ.get("ANTHROPIC_AUTH_TOKEN")
    model = os.environ.get("ANTHROPIC_MODEL", "qwen3-coder-plus")

    if not auth_token:
        print("[ERROR] ANTHROPIC_AUTH_TOKEN not set", file=sys.stderr)
        return None

    prompt = f"""你是一个测试工程师。根据以下缺陷描述和源代码，生成一个 pytest 测试用例。

受影响的文件：{issue_info['affected_file']}

缺陷描述：
{issue_info['bug_description']}

复现步骤：
{issue_info['reproduction_steps']}

期望行为：
{issue_info['expected_behavior']}

源代码：
```python
{source_code}
```

要求：
1. 生成一个 pytest 测试函数，放在 tests/test_regression_{issue_info['issue_number']}.py 中
2. 测试必须使用 assert 验证期望行为
3. import 模块时，受影响的文件路径如 src/email_utils.py，应去掉 src. 前缀，直接 import email_utils（已有 sys.path 配置）
   示例：from email_utils import parse_email_list
4. 测试函数名要有描述性，如 test_parse_email_list_handles_space_separated_emails
5. 只返回 Python 测试代码，不要解释
6. 代码中必须包含必要的 import（sys, os 用于设置 sys.path，以及测试目标模块的 import）
7. 不需要 main() 或 if __name__ 块，pytest 会自动发现测试

测试代码："""

    options = ClaudeAgentOptions(
        system_prompt="你是一个专业的测试工程师，擅长根据缺陷描述生成准确、简洁的 pytest 测试用例。只返回测试代码。",
        max_turns=1,
        model=model
    )

    try:
        full_response = ""

        async for message in query(prompt=prompt, options=options):
            if isinstance(message, AssistantMessage):
                for block in message.content:
                    if isinstance(block, TextBlock):
                        full_response += block.text

        if not full_response:
            print("[ERROR] Empty response from AI", file=sys.stderr)
            return None

        # 清理 markdown 包裹
        if full_response.startswith("```python"):
            full_response = full_response[9:]
        if full_response.startswith("```"):
            full_response = full_response[3:]
        if full_response.endswith("```"):
            full_response = full_response[:-3]

        return full_response.strip()

    except Exception as e:
        print(f"[ERROR] AI test generation failed: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc(file=sys.stderr)
        return None


async def main():
    """主函数"""
    print("[INFO] 🚀 Starting Harness Gap...", file=sys.stderr)

    # 从环境变量读取 issue 信息
    issue_info = {
        "issue_number": os.environ.get("ISSUE_NUMBER", "unknown"),
        "issue_title": os.environ.get("ISSUE_TITLE", ""),
        "issue_body": os.environ.get("ISSUE_BODY", ""),
        "affected_file": os.environ.get("AFFECTED_FILE", ""),
        "bug_description": os.environ.get("BUG_DESCRIPTION", ""),
        "reproduction_steps": os.environ.get("REPRODUCTION_STEPS", ""),
        "expected_behavior": os.environ.get("EXPECTED_BEHAVIOR", ""),
    }

    if not issue_info["bug_description"]:
        print("[ERROR] No bug description provided", file=sys.stderr)
        print(json.dumps({"success": False, "reason": "No bug description"}))
        return 1

    print(f"[INFO] Issue #{issue_info['issue_number']}: {issue_info['issue_title']}", file=sys.stderr)
    print(f"[INFO] Affected file: {issue_info['affected_file']}", file=sys.stderr)

    # 读取受影响的源文件
    source_file = issue_info["affected_file"]
    if not source_file or not os.path.exists(source_file):
        print(f"[WARN] Source file {source_file} not found, proceeding without source code", file=sys.stderr)
        source_code = ""
    else:
        source_code = read_file_content(source_file)
        print(f"[INFO] Read {len(source_code)} bytes from {source_file}", file=sys.stderr)

    # 生成测试代码
    test_code = await call_ai_for_test(issue_info, source_code)
    if not test_code:
        print("[ERROR] Failed to generate test code", file=sys.stderr)
        print(json.dumps({"success": False, "reason": "AI test generation failed"}))
        return 1

    # 确定测试文件名
    test_filename = f"tests/test_regression_{issue_info['issue_number']}.py"

    # 写入测试文件
    try:
        os.makedirs("tests", exist_ok=True)
        with open(test_filename, "w", encoding="utf-8") as f:
            f.write(test_code + "\n")
        print(f"[INFO] ✅ Wrote {test_filename}", file=sys.stderr)
    except Exception as e:
        print(f"[ERROR] Failed to write test file: {e}", file=sys.stderr)
        print(json.dumps({"success": False, "reason": str(e)}))
        return 1

    # 输出结果
    print("=" * 50, file=sys.stderr)
    print(f"Harness Gap Complete:", file=sys.stderr)
    print(f"  Issue: #{issue_info['issue_number']}", file=sys.stderr)
    print(f"  Test file: {test_filename}", file=sys.stderr)
    print("=" * 50, file=sys.stderr)

    result = {
        "success": True,
        "test_file": test_filename,
        "issue_number": issue_info["issue_number"]
    }
    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
