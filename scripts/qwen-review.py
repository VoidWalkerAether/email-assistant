#!/usr/bin/env python3
"""
Claude Code Review - 使用 Claude 模型进行代码审核
输出格式：ReviewDog RDJSON (https://github.com/reviewdog/reviewdog/blob/master/proto/rdf/)
"""

import json
import logging
import os
import sys
import subprocess
import re
import asyncio
import traceback
from typing import Optional, Dict, Any, List, Tuple
from claude_agent_sdk import query, ClaudeAgentOptions, AssistantMessage, TextBlock


DEFAULT_TIMEOUT = int(os.environ.get('REVIEW_TIMEOUT', '120'))
DEFAULT_MAX_CONCURRENT = int(os.environ.get('REVIEW_MAX_CONCURRENT', '3'))
MAX_FILE_SIZE = 1024 * 1024  # 1MB 最大文件大小限制
MAX_JSON_DEPTH = 50  # JSON 解析最大深度
MAX_CONCURRENT_LIMIT = 10  # 最大并发数限制
MIN_CONCURRENT = 1  # 最小并发数


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


def get_changed_files() -> List[str]:
    """从 GitHub Actions 环境变量获取 PR 改动的文件"""
    base_sha = os.environ.get('GITHUB_BASE_SHA', 'HEAD~1')
    head_sha = os.environ.get('GITHUB_SHA', 'HEAD')
    
    try:
        result = subprocess.run(
            ['git', 'diff', '--name-only', base_sha, head_sha],
            capture_output=True, text=True, check=True
        )
        files = result.stdout.strip().split('\n')
        return [f for f in files if f and os.path.exists(f)]
    except subprocess.CalledProcessError as e:
        logger.error(f"Git diff failed: {e}")
        return []
    except Exception as e:
        logger.error(f"Unexpected error getting changed files: {e}")
        return []


def read_file_content(filepath: str) -> str:
    """读取文件内容，限制最大文件大小"""
    try:
        file_size = os.path.getsize(filepath)
        if file_size > MAX_FILE_SIZE:
            logger.warning(f"File {filepath} too large ({file_size} bytes), skipping")
            return ""
        
        with open(filepath, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError as e:
        logger.error(f"File not found {filepath}: {e}")
        return ""
    except UnicodeDecodeError as e:
        logger.error(f"Encoding error reading {filepath}: {e}")
        return ""
    except PermissionError as e:
        logger.error(f"Permission denied reading {filepath}: {e}")
        return ""
    except Exception as e:
        logger.error(f"Error reading {filepath}: {e}")
        return ""


def extract_json_object(text: str) -> Optional[Dict[str, Any]]:
    """从文本中提取 JSON 对象，支持嵌套结构"""
    text = text.strip()
    
    if not text:
        return None
    
    # 尝试直接解析
    try:
        result = json.loads(text)
        if isinstance(result, dict):
            return result
    except json.JSONDecodeError:
        pass
    
    # 尝试提取 markdown 代码块 - 使用原始字符串避免转义问题
    code_block_patterns = [
        r'```json\s*({.*?})\s*```',
        r'```\s*({.*?})\s*```',
        r'```json\n({.*?})\n```',
        r'```\n({.*?})\n```',
    ]
    
    for pattern in code_block_patterns:
        code_block_match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
        if code_block_match:
            try:
                result = json.loads(code_block_match.group(1))
                if isinstance(result, dict):
                    return result
            except json.JSONDecodeError:
                pass
    
    # 尝试查找第一个 { 和最后一个 } 之间的内容
    start_idx = text.find('{')
    end_idx = text.rfind('}')
    
    if start_idx != -1 and end_idx > start_idx:
        json_str = text[start_idx:end_idx + 1]
        try:
            result = json.loads(json_str)
            if isinstance(result, dict):
                return result
        except json.JSONDecodeError:
            pass
    
    # 使用栈匹配大括号来处理嵌套结构，添加最大深度限制
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
            # 检查最大深度限制
            if len(stack) > MAX_JSON_DEPTH:
                logger.warning(f"JSON nesting depth exceeded maximum of {MAX_JSON_DEPTH}")
                return None
        elif char == '}':
            if len(stack) == 1:
                json_str = text[start_idx:i+1]
                try:
                    result = json.loads(json_str)
                    if isinstance(result, dict):
                        return result
                except json.JSONDecodeError:
                    pass
                stack.pop()
            elif stack:
                stack.pop()
    
    return None


async def call_claude_async(
    code_content: str,
    filename: str,
    timeout: int = DEFAULT_TIMEOUT
) -> List[Dict[str, Any]]:
    """使用 Claude 进行代码审核"""

    auth_token = os.environ.get('ANTHROPIC_AUTH_TOKEN')
    base_url = os.environ.get('ANTHROPIC_BASE_URL', 'https://coding.dashscope.aliyuncs.com/apps/anthropic')
    model = os.environ.get('ANTHROPIC_MODEL') or os.environ.get('CODING_MODEL', 'qwen3-coder-plus')

    logger.debug(f"Config: model={model}, base_url={base_url}, token_set={bool(auth_token)}, timeout={timeout}")

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

如果没有问题，返回 {{"issues": []}}。
只返回 JSON，不要其他内容，不要用 markdown 包裹。"""

    try:
        full_response = ""
        turn_count = 0
        message_count = 0

        logger.debug("Starting query loop...")
        async with asyncio.timeout(timeout):
            async for message in query(
                prompt=prompt,
                options=ClaudeAgentOptions(
                    system_prompt="你是一个专业的代码审查助手。请直接返回纯 JSON 格式的审查结果，不要使用 markdown 包裹，不要添加任何额外说明。JSON 格式必须严格符合：{\"issues\": [{\"line\": 行号，\"message\": \"描述\", \"severity\": \"error|warning|info\"}]}",
                    max_turns=1,
                    model=model
                )
            ):
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
            if isinstance(issues, list):
                logger.debug(f"JSON parse successful, found {len(issues)} issues")
                return issues
            else:
                logger.error(f"'issues' field is not a list: {type(issues)}")
                return []
        
        logger.error("Failed to parse JSON from response")
        logger.error(f"Raw response (first 1000 chars): {full_response[:1000]}")
        return []
    except asyncio.TimeoutError:
        logger.error(f"Request timed out after {timeout} seconds")
        return []
    except asyncio.CancelledError:
        logger.error("Request was cancelled")
        return []
    except Exception as e:
        logger.error(f"Exception in call_claude_async: {type(e).__name__}: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return []


def call_claude_api(
    code_content: str,
    filename: str,
    timeout: int = DEFAULT_TIMEOUT
) -> List[Dict[str, Any]]:
    """调用 Claude API 进行代码审核（包装异步函数）"""
    try:
        asyncio.get_running_loop()
        logger.debug("call_claude_api: running in existing event loop")
        return asyncio.run(call_claude_async(code_content, filename, timeout))
    except RuntimeError:
        logger.debug("call_claude_api: creating new event loop")
        return asyncio.run(call_claude_async(code_content, filename, timeout))


def validate_severity(severity: Optional[str]) -> str:
    """校验 severity 字段，确保为合法值"""
    valid_severities = {'error', 'warning', 'info'}
    if severity and severity.lower() in valid_severities:
        return severity.lower()
    return 'warning'


def determine_column(message: str, line_content: Optional[str] = None) -> int:
    """根据问题描述确定列号"""
    if not line_content:
        return 1
    
    # 尝试从消息中提取关键词位置
    keywords = ['import', 'def ', 'class ', 'return', 'if ', 'for ', 'while ', 'with ', 'try:', 'except']
    for keyword in keywords:
        if keyword in message.lower():
            idx = line_content.find(keyword)
            if idx != -1:
                return idx + 1
    
    # 默认返回 1
    return 1


def validate_issue(issue: Dict[str, Any], filepath: str, line_count: int) -> Optional[Dict[str, Any]]:
    """验证 AI 返回的诊断信息"""
    if not isinstance(issue, dict):
        logger.warning(f"Invalid issue format: not a dict")
        return None
    
    # 验证 line 字段
    line = issue.get('line')
    if not isinstance(line, int) or line < 1 or line > line_count:
        logger.warning(f"Invalid line number: {line} for {filepath}")
        return None
    
    # 验证 message 字段
    message = issue.get('message')
    if not message or not isinstance(message, str):
        logger.warning(f"Invalid or missing message for {filepath}")
        return None
    
    # 验证 severity 字段
    severity = issue.get('severity', 'warning')
    if severity and severity.lower() not in {'error', 'warning', 'info'}:
        logger.warning(f"Invalid severity: {severity}, defaulting to warning")
        severity = 'warning'
    
    # 验证 column 字段
    column = issue.get('column')
    if column is not None:
        if not isinstance(column, int) or column < 1:
            logger.warning(f"Invalid column: {column}, defaulting to 1")
            column = 1
    
    return {
        'line': line,
        'column': column if column else 1,
        'message': message,
        'severity': severity.lower()
    }


async def review_file_async(
    filepath: str,
    content: str,
    semaphore: asyncio.Semaphore
) -> Tuple[str, List[Dict[str, Any]]]:
    """异步审查单个文件"""
    async with semaphore:
        issues = await call_claude_async(content, filepath)
        return filepath, issues


async def review_all_files_async(
    py_files: List[str],
    max_concurrent: int = DEFAULT_MAX_CONCURRENT
) -> Dict[str, List[Dict[str, Any]]]:
    """并发审查所有文件，限制并发数量"""
    # 验证并发数量范围
    max_concurrent = max(MIN_CONCURRENT, min(max_concurrent, MAX_CONCURRENT_LIMIT))
    if max_concurrent != DEFAULT_MAX_CONCURRENT:
        logger.info(f"Adjusted max_concurrent to {max_concurrent} (within range {MIN_CONCURRENT}-{MAX_CONCURRENT_LIMIT})")
    
    semaphore = asyncio.Semaphore(max_concurrent)
    tasks = []
    
    for filepath in py_files:
        content = read_file_content(filepath)
        if content:
            tasks.append(review_file_async(filepath, content, semaphore))
        else:
            logger.warning(f"Skipping {filepath}: empty or unreadable (file may not exist, encoding issue, or permission denied)")
    
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    file_results: Dict[str, List[Dict[str, Any]]] = {}
    for result in results:
        if isinstance(result, Exception):
            logger.error(f"Review task failed: {type(result).__name__}: {result}")
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

    # 验证并发数量范围
    max_concurrent = max(MIN_CONCURRENT, min(DEFAULT_MAX_CONCURRENT, MAX_CONCURRENT_LIMIT))
    timeout = DEFAULT_TIMEOUT
    
    file_results = asyncio.run(review_all_files_async(py_files, max_concurrent=max_concurrent))

    # 收集所有诊断信息并进行验证
    all_diagnostics = []
    valid_severities = {'error', 'warning', 'info'}

    for filepath, issues in file_results.items():
        logger.info(f"Reviewing {filepath}...")
        
        # 读取文件内容以获取行数用于验证
        content = read_file_content(filepath)
        line_count = len(content.splitlines()) if content else 1
        
        logger.info(f"  Found {len(issues)} issues in {filepath}")

        for i, issue in enumerate(issues):
            logger.info(f"[ISSUE #{i+1}] Line {issue.get('line', '?')}: {issue.get('message', '?')} ({issue.get('severity', '?')})")

        for issue in issues:
            # 验证 issue 数据
            validated_issue = validate_issue(issue, filepath, line_count)
            if not validated_issue:
                logger.warning(f"Skipping invalid issue for {filepath}: {issue}")
                continue
            
            line = validated_issue['line']
            column = validated_issue['column']
            severity = validated_issue['severity']
            message = validated_issue['message']
            
            # 额外验证 severity
            if severity not in valid_severities:
                severity = 'warning'
            
            diagnostic = {
                "message": message,
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
                "severity": severity,
                "source": {
                    "name": "claude-review"
                }
            }
            all_diagnostics.append(diagnostic)

    if not all_diagnostics:
        logger.warning("No issues found by AI review")

    print(json.dumps({"diagnostics": all_diagnostics}, ensure_ascii=False))


if __name__ == "__main__":
    main()