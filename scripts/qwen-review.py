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
    model = os.environ.get('ANTHROPIC_MODEL', 'claude-sonnet-4-20250514')
    small_model = os.environ.get('ANTHROPIC_SMALL_FAST_MODEL', 'claude-3-haiku-20240307')
    
    if not auth_token:
        print("Error: ANTHROPIC_AUTH_TOKEN not set", file=sys.stderr)
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
{code_content[:5000]}

请以 JSON 格式返回审查结果，格式如下：
{{
  "issues": [
    {{
      "line": 行号（整数）,
      "column": 列号（可选，整数）,
      "message": "问题描述（中文）",
      "severity": "error|warning|info"
    }}
  ]
}}

如果没有问题，返回 {{"issues": []}}。
只返回 JSON，不要其他内容。"""

    options = ClaudeAgentOptions(
        system_prompt="你是一个专业的代码审查助手，擅长发现代码中的问题和改进建议。请用中文回复。",
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

        # 提取 JSON（处理可能的 markdown 格式）
        json_match = re.search(r'\{.*\}', full_response, re.DOTALL)
        if json_match:
            result = json.loads(json_match.group())
            return result.get('issues', [])
        else:
            print(f"Failed to parse JSON from response: {full_response}", file=sys.stderr)
            return []
    except Exception as e:
        print(f"Error calling Claude API: {e}", file=sys.stderr)
        return []


def call_claude_api(code_content, filename):
    """调用 Claude API 进行代码审核（包装异步函数）"""
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
            continue
        
        print(f"📝 Reviewing {filepath}...", file=sys.stderr)
        issues = call_claude_api(content, filepath)
        print(f"   Found {len(issues)} issues", file=sys.stderr)
        
        for issue in issues:
            diagnostic = {
                "message": {
                    "text": issue.get('message', 'Unknown issue')
                },
                "location": {
                    "path": filepath,
                    "range": {
                        "start": {
                            "line": issue.get('line', 1),
                            "column": issue.get('column', 1)
                        }
                    }
                },
                "severity": issue.get('severity', 'warning'),
                "source": {
                    "name": "qwen-review"
                }
            }
            all_diagnostics.append(diagnostic)
    
    # 只输出纯 JSON 到 stdout（ReviewDog 需要）
    print(json.dumps({"diagnostics": all_diagnostics}, indent=2))


if __name__ == "__main__":
    main()
