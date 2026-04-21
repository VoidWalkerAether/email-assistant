#!/usr/bin/env python3
"""
Claude Code Review - 使用阿里云代理的 Claude 模型进行代码审核
输出格式：ReviewDog RDJSON (https://github.com/reviewdog/reviewdog/blob/master/proto/rdf/)
"""

import json
import os
import sys
import subprocess
import re
import asyncio
from claude_agent_sdk import query, ClaudeAgentOptions, AssistantMessage, TextBlock


def get_changed_files():
    """从 GitHub Actions 环境变量获取 PR 改动的文件"""
    base_sha = os.environ.get('GITHUB_BASE_SHA', 'HEAD~1')
    head_sha = os.environ.get('GITHUB_SHA', 'HEAD')
    
    result = subprocess.run(
        ['git', 'diff', '--name-only', base_sha, head_sha],
        capture_output=True, text=True
    )
    
    files = result.stdout.strip().split('\n')
    return [f for f in files if f and os.path.exists(f)]


def read_file_content(filepath):
    """读取文件内容"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        print(f"Error reading {filepath}: {e}", file=sys.stderr)
        return ""


async def call_claude_async(code_content, filename):
    """使用 Claude 进行代码审核（通过阿里云代理）"""

    # 环境变量配置
    auth_token = os.environ.get('ANTHROPIC_AUTH_TOKEN')
    base_url = os.environ.get('ANTHROPIC_BASE_URL', 'https://coding.dashscope.aliyuncs.com/apps/anthropic')
    model = os.environ.get('ANTHROPIC_MODEL', 'qwen3-coder-plus')
    small_model = os.environ.get('ANTHROPIC_SMALL_FAST_MODEL', 'qwen3-coder-plus')

    # [DEBUG] 打印配置信息
    print(f"[DEBUG] Config: model={model}, base_url={base_url}, token_set={bool(auth_token)}", file=sys.stderr)

    if not auth_token:
        print("[ERROR] ANTHROPIC_AUTH_TOKEN not set", file=sys.stderr)
        return []

    # 构建提示词
    prompt = f"""请审查以下代码，找出潜在问题：
- 代码风格和最佳实践
- 潜在 bug 和安全问题
- 性能问题
- 可改进的地方

文件名：{filename}

代码内容：
```python
{code_content}
```

请以 JSON 格式返回审查结果，格式如下：
```json
{{
  "issues": [
    {{
      "line": 行号（整数，从 1 开始）,
      "column": 列号（整数，从 1 开始，如果无法确定可以省略）,
      "message": "问题描述（中文）",
      "severity": "error|warning|info"
    }}
  ]
}}
```

如果没有问题，返回 {{"issues": []}}。
只返回 JSON，不要其他内容，不要用 markdown 包裹。"""

    options = ClaudeAgentOptions(
        system_prompt="你是一个专业的代码审查助手，擅长发现代码中的问题和改进建议。请用中文回复。",
        max_turns=1,
        model=model
    )

    try:
        full_response = ""
        turn_count = 0
        message_count = 0

        print("[DEBUG] Starting query loop...", file=sys.stderr)
        async for message in query(prompt=prompt, options=options):
            message_count += 1
            print(f"[DEBUG] Received message #{message_count}: {type(message).__name__}", file=sys.stderr)

            if isinstance(message, AssistantMessage):
                turn_count += 1
                print(f"[DEBUG] AssistantMessage turn {turn_count}, content blocks: {len(message.content)}", file=sys.stderr)
                for i, block in enumerate(message.content):
                    print(f"[DEBUG]   Block {i}: {type(block).__name__}", file=sys.stderr)
                    if isinstance(block, TextBlock):
                        full_response += block.text
                        print(f"[DEBUG]   Appended {len(block.text)} chars", file=sys.stderr)
            else:
                print(f"[DEBUG] Skipping unknown message type: {type(message).__name__}", file=sys.stderr)

        print(f"[DEBUG] Total messages: {message_count}, turns: {turn_count}", file=sys.stderr)
        print(f"[DEBUG] Full response length: {len(full_response)} chars", file=sys.stderr)

        if not full_response:
            print("[ERROR] Empty response from model", file=sys.stderr)
            return []

        # [DEBUG] 打印原始响应前 500 字符
        preview = full_response[:500] + "..." if len(full_response) > 500 else full_response
        print(f"[DEBUG] Response preview:\n{preview}", file=sys.stderr)

        # 提取 JSON（处理可能的 markdown 格式）
        # 先尝试直接解析
        print("[DEBUG] Attempting JSON parse method 1: direct parse", file=sys.stderr)
        try:
            result = json.loads(full_response.strip())
            print(f"[DEBUG] Direct parse successful, found {len(result.get('issues', []))} issues", file=sys.stderr)
            return result.get('issues', [])
        except json.JSONDecodeError as e:
            print(f"[DEBUG] Direct parse failed: {e}", file=sys.stderr)
            pass

        # 尝试提取 markdown 代码块中的 JSON
        print("[DEBUG] Attempting JSON parse method 2: markdown code block", file=sys.stderr)
        code_block_match = re.search(r'```(?:json)?\s*({.*?})\s*```', full_response, re.DOTALL)
        if code_block_match:
            print("[DEBUG] Found markdown code block", file=sys.stderr)
            try:
                result = json.loads(code_block_match.group(1))
                print(f"[DEBUG] Markdown block parse successful, found {len(result.get('issues', []))} issues", file=sys.stderr)
                return result.get('issues', [])
            except json.JSONDecodeError as e:
                print(f"[DEBUG] Markdown block parse failed: {e}", file=sys.stderr)
                pass
        else:
            print("[DEBUG] No markdown code block found", file=sys.stderr)

        # 最后尝试匹配大括号包裹的内容
        print("[DEBUG] Attempting JSON parse method 3: brace matching", file=sys.stderr)
        json_match = re.search(r'\{[^{}]*"issues"[^{}]*\}', full_response, re.DOTALL)
        if json_match:
            print("[DEBUG] Found brace pattern", file=sys.stderr)
            try:
                result = json.loads(json_match.group())
                print(f"[DEBUG] Brace match parse successful, found {len(result.get('issues', []))} issues", file=sys.stderr)
                return result.get('issues', [])
            except json.JSONDecodeError as e:
                print(f"[DEBUG] Brace match parse failed: {e}", file=sys.stderr)
                pass
        else:
            print("[DEBUG] No brace pattern found", file=sys.stderr)

        print(f"[ERROR] All JSON parse methods failed", file=sys.stderr)
        print(f"[ERROR] Raw response (first 1000 chars): {full_response[:1000]}", file=sys.stderr)
        return []
    except Exception as e:
        import traceback
        print(f"[ERROR] Exception in call_claude_async: {e}", file=sys.stderr)
        print(f"[ERROR] Traceback: {traceback.format_exc()}", file=sys.stderr)
        return []


def call_claude_api(code_content, filename):
    """调用 Claude API 进行代码审核（包装异步函数）"""
    try:
        # 检查是否已在事件循环中运行
        loop = asyncio.get_running_loop()
        print(f"[DEBUG] call_claude_api: running in existing event loop", file=sys.stderr)
        # 在已有循环中同步运行（使用嵌套事件循环）
        return loop.run_until_complete(call_claude_async(code_content, filename))
    except RuntimeError:
        # 没有事件循环，创建新的
        print(f"[DEBUG] call_claude_api: creating new event loop", file=sys.stderr)
        return asyncio.run(call_claude_async(code_content, filename))


def main():
    """主函数 - 输出 RDJSON 格式（纯 JSON 到 stdout，日志到 stderr）"""
    changed_files = get_changed_files()
    all_diagnostics = []

    print(f"🔍 Found {len(changed_files)} changed files", file=sys.stderr)

    # 只审查 Python 文件
    py_files = [f for f in changed_files if f.endswith('.py')]
    print(f"🐍 Found {len(py_files)} Python files to review", file=sys.stderr)

    for filepath in py_files:
        content = read_file_content(filepath)
        if not content:
            print(f"[WARN] Skipping {filepath}: empty or unreadable", file=sys.stderr)
            continue

        print(f"[INFO] Reviewing {filepath} ({len(content)} bytes)...", file=sys.stderr)
        issues = call_claude_api(content, filepath)
        print(f"[INFO]   Found {len(issues)} issues in {filepath}", file=sys.stderr)

        # 打印每个 issue 详情
        for i, issue in enumerate(issues):
            print(f"[ISSUE #{i+1}] Line {issue.get('line', '?')}: {issue.get('message', '?')} ({issue.get('severity', '?')})", file=sys.stderr)

        for issue in issues:
            diagnostic = {
                "message": issue.get('message', 'Unknown issue'),
                "location": {
                    "path": filepath,
                    "range": {
                        "start": {
                            "line": issue.get('line', 1),
                            "column": issue.get('column') or 1
                        }
                    }
                },
                "severity": issue.get('severity', 'warning'),
                "source": {
                    "name": "qwen-review"
                }
            }
            all_diagnostics.append(diagnostic)

    if not all_diagnostics:
        print("[WARN] No issues found by AI review", file=sys.stderr)

    # 只输出纯 JSON 到 stdout（ReviewDog 需要）
    # 不用 indent，输出单行 JSON
    print(json.dumps({"diagnostics": all_diagnostics}))


if __name__ == "__main__":
    main()
