#!/usr/bin/env python3
"""
Claude Code Review - 使用阿里云代理的 Claude 模型进行代码审核
输出格式：ReviewDog RDJSON (https://github.com/reviewdog/reviewdog/blob/master/proto/rdf/)
"""

import json
import logging
import os
import sys
import subprocess
import re
import asyncio
from claude_agent_sdk import query, ClaudeAgentOptions, AssistantMessage, TextBlock


def setup_logging():
    """配置日志级别"""
    log_level = os.environ.get('LOG_LEVEL', 'WARNING').upper()
    level = getattr(logging, log_level, logging.WARNING)
    logging.basicConfig(
        level=level,
        format='[%(levelname)s] %(message)s',
        stream=sys.stderr
    )
    return logging.getLogger(__name__)


logger = setup_logging()


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
        logger.error(f"Error reading {filepath}: {e}")
        return ""


async def call_claude_async(code_content, filename):
    """使用 Claude 进行代码审核（通过阿里云代理）"""

    auth_token = os.environ.get('ANTHROPIC_AUTH_TOKEN')
    base_url = os.environ.get('ANTHROPIC_BASE_URL', 'https://coding.dashscope.aliyuncs.com/apps/anthropic')
    model = os.environ.get('ANTHROPIC_MODEL', 'qwen3-coder-plus')
    small_model = os.environ.get('ANTHROPIC_SMALL_FAST_MODEL', 'qwen3-coder-plus')

    logger.debug(f"Config: model={model}, base_url={base_url}, token_set={bool(auth_token)}")

    if not auth_token:
        logger.error("ANTHROPIC_AUTH_TOKEN not set")
        return []

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

        logger.debug("Starting query loop...")
        async for message in query(prompt=prompt, options=options):
            message_count += 1
            logger.debug(f"Received message #{message_count}: {type(message).__name__}")

            if isinstance(message, AssistantMessage):
                turn_count += 1
                logger.debug(f"AssistantMessage turn {turn_count}, content blocks: {len(message.content)}")
                for i, block in enumerate(message.content):
                    logger.debug(f"  Block {i}: {type(block).__name__}")
                    if isinstance(block, TextBlock):
                        full_response += block.text
                        logger.debug(f"  Appended {len(block.text)} chars")
            else:
                logger.debug(f"Skipping unknown message type: {type(message).__name__}")

        logger.debug(f"Total messages: {message_count}, turns: {turn_count}")
        logger.debug(f"Full response length: {len(full_response)} chars")

        if not full_response:
            logger.error("Empty response from model")
            return []

        preview = full_response[:500] + "..." if len(full_response) > 500 else full_response
        logger.debug(f"Response preview:\n{preview}")

        logger.debug("Attempting JSON parse method 1: direct parse")
        try:
            result = json.loads(full_response.strip())
            logger.debug(f"Direct parse successful, found {len(result.get('issues', []))} issues")
            return result.get('issues', [])
        except json.JSONDecodeError as e:
            logger.debug(f"Direct parse failed: {e}")
            pass

        logger.debug("Attempting JSON parse method 2: markdown code block")
        code_block_match = re.search(r'```(?:json)?\s*({.*?})\s*```', full_response, re.DOTALL)
        if code_block_match:
            logger.debug("Found markdown code block")
            try:
                result = json.loads(code_block_match.group(1))
                logger.debug(f"Markdown block parse successful, found {len(result.get('issues', []))} issues")
                return result.get('issues', [])
            except json.JSONDecodeError as e:
                logger.debug(f"Markdown block parse failed: {e}")
                pass
        else:
            logger.debug("No markdown code block found")

        logger.debug("Attempting JSON parse method 3: brace matching")
        json_match = re.search(r'\{[^{}]*"issues"[^{}]*\}', full_response, re.DOTALL)
        if json_match:
            logger.debug("Found brace pattern")
            try:
                result = json.loads(json_match.group())
                logger.debug(f"Brace match parse successful, found {len(result.get('issues', []))} issues")
                return result.get('issues', [])
            except json.JSONDecodeError as e:
                logger.debug(f"Brace match parse failed: {e}")
                pass
        else:
            logger.debug("No brace pattern found")

        logger.error("All JSON parse methods failed")
        logger.error(f"Raw response (first 1000 chars): {full_response[:1000]}")
        return []
    except Exception as e:
        import traceback
        logger.error(f"Exception in call_claude_async: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return []


def call_claude_api(code_content, filename):
    """调用 Claude API 进行代码审核（包装异步函数）"""
    try:
        loop = asyncio.get_running_loop()
        logger.debug("call_claude_api: running in existing event loop")
        return loop.run_until_complete(call_claude_async(code_content, filename))
    except RuntimeError:
        logger.debug("call_claude_api: creating new event loop")
        return asyncio.run(call_claude_async(code_content, filename))


def main():
    """主函数 - 输出 RDJSON 格式（纯 JSON 到 stdout，日志到 stderr）"""
    changed_files = get_changed_files()
    all_diagnostics = []

    logger.info(f"Found {len(changed_files)} changed files")

    py_files = [f for f in changed_files if f.endswith('.py')]
    logger.info(f"Found {len(py_files)} Python files to review")

    for filepath in py_files:
        content = read_file_content(filepath)
        if not content:
            logger.warning(f"Skipping {filepath}: empty or unreadable")
            continue

        logger.info(f"Reviewing {filepath} ({len(content)} bytes)...")
        issues = call_claude_api(content, filepath)
        logger.info(f"  Found {len(issues)} issues in {filepath}")

        for i, issue in enumerate(issues):
            logger.info(f"[ISSUE #{i+1}] Line {issue.get('line', '?')}: {issue.get('message', '?')} ({issue.get('severity', '?')})")

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
        logger.warning("No issues found by AI review")

    print(json.dumps({"diagnostics": all_diagnostics}, ensure_ascii=False))


if __name__ == "__main__":
    main()