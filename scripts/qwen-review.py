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


def extract_json_object(text):
    """从文本中提取 JSON 对象，支持嵌套结构"""
    text = text.strip()
    
    # 尝试直接解析
    try:
        result = json.loads(text)
        return result
    except json.JSONDecodeError:
        pass
    
    # 尝试提取 markdown 代码块
    code_block_match = re.search(r'```(?:json)?\s*({.*?})\s*```', text, re.DOTALL)
    if code_block_match:
        try:
            return json.loads(code_block_match.group(1))
        except json.JSONDecodeError:
            pass
    
    # 使用栈匹配大括号来处理嵌套结构
    start_idx = text.find('{')
    if start_idx == -1:
        return None
    
    stack = []
    in_string = False
    escape_next = False
    
    for i, char in enumerate(text[start_idx:], start_idx):
        if escape_next:
            escape_next = False
            continue
        
        if char == '\\' and in_string:
            escape_next = True
            continue
        
        if char == '"' and not escape_next:
            in_string = not in_string
            continue
        
        if in_string:
            continue
        
        if char == '{':
            stack.append(i)
        elif char == '}':
            if len(stack) == 1:
                json_str = text[start_idx:i+1]
                try:
                    return json.loads(json_str)
                except json.JSONDecodeError:
                    pass
                stack.pop()
            elif stack:
                stack.pop()
    
    return None


async def call_claude_async(code_content, filename, timeout=120):
    """使用 Claude 进行代码审核（通过阿里云代理）"""

    auth_token = os.environ.get('ANTHROPIC_AUTH_TOKEN')
    base_url = os.environ.get('ANTHROPIC_BASE_URL', 'https://coding.dashscope.aliyuncs.com/apps/anthropic')
    model = os.environ.get('CODING_MODEL', 'qwen3-coder-plus')

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

    try:
        full_response = ""
        turn_count = 0
        message_count = 0

        logger.debug("Starting query loop...")
        async with asyncio.timeout(timeout):
            async for message in query(prompt=prompt, options=ClaudeAgentOptions(
                system_prompt="你是一个专业的代码审查助手，请用中文返回 JSON 格式的审查结果。",
                max_turns=1,
                model=model
            )):
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

        logger.debug("Attempting to extract and parse JSON")
        result = extract_json_object(full_response)
        
        if result and isinstance(result, dict):
            issues = result.get('issues', [])
            logger.debug(f"JSON parse successful, found {len(issues)} issues")
            return issues
        
        logger.error("Failed to parse JSON from response")
        logger.error(f"Raw response (first 1000 chars): {full_response[:1000]}")
        return []
    except asyncio.TimeoutError:
        logger.error(f"Request timed out after {timeout} seconds")
        return []
    except Exception as e:
        import traceback
        logger.error(f"Exception in call_claude_async: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return []


def call_claude_api(code_content, filename, timeout=120):
    """调用 Claude API 进行代码审核（包装异步函数）"""
    try:
        loop = asyncio.get_running_loop()
        logger.debug("call_claude_api: running in existing event loop")
        return asyncio.wait_for(
            call_claude_async(code_content, filename, timeout),
            timeout=timeout
        )
    except RuntimeError:
        logger.debug("call_claude_api: creating new event loop")
        return asyncio.run(call_claude_async(code_content, filename, timeout))


def validate_severity(severity):
    """校验 severity 字段，确保为合法值"""
    valid_severities = {'error', 'warning', 'info'}
    if severity and severity.lower() in valid_severities:
        return severity.lower()
    return 'warning'


async def review_file_async(filepath, content, semaphore):
    """异步审查单个文件"""
    async with semaphore:
        issues = await call_claude_async(content, filepath)
        return filepath, issues


async def review_all_files_async(py_files, max_concurrent=3):
    """并发审查所有文件，限制并发数量"""
    semaphore = asyncio.Semaphore(max_concurrent)
    tasks = []
    
    for filepath in py_files:
        content = read_file_content(filepath)
        if content:
            tasks.append(review_file_async(filepath, content, semaphore))
        else:
            logger.warning(f"Skipping {filepath}: empty or unreadable")
    
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    file_results = {}
    for result in results:
        if isinstance(result, Exception):
            logger.error(f"Review task failed: {result}")
        else:
            filepath, issues = result
            file_results[filepath] = issues
    
    return file_results


def main():
    """主函数 - 输出 RDJSON 格式（纯 JSON 到 stdout，日志到 stderr）"""
    changed_files = get_changed_files()
    
    if not changed_files:
        logger.warning("No changed files found")
        print(json.dumps({"diagnostics": []}, ensure_ascii=False))
        return

    logger.info(f"Found {len(changed_files)} changed files")

    py_files = [f for f in changed_files if f.endswith('.py')]
    logger.info(f"Found {len(py_files)} Python files to review")

    if not py_files:
        logger.warning("No Python files to review")
        print(json.dumps({"diagnostics": []}, ensure_ascii=False))
        return

    # 使用异步方式并发审查所有文件
    all_diagnostics = []
    file_results = asyncio.run(review_all_files_async(py_files))

    for filepath, issues in file_results.items():
        logger.info(f"Reviewing {filepath}...")
        logger.info(f"  Found {len(issues)} issues in {filepath}")

        for i, issue in enumerate(issues):
            logger.info(f"[ISSUE #{i+1}] Line {issue.get('line', '?')}: {issue.get('message', '?')} ({issue.get('severity', '?')})")

        for issue in issues:
            line = issue.get('line', 1)
            column = issue.get('column') or 1
            diagnostic = {
                "message": issue.get('message', 'Unknown issue'),
                "location": {
                    "path": filepath,
                    "range": {
                        "start": {
                            "line": line,
                            "column": column
                        },
                        "end": {
                            "line": line,
                            "column": column
                        }
                    }
                },
                "severity": validate_severity(issue.get('severity')),
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