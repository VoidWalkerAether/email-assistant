#!/usr/bin/env python3
"""
Qwen Code Review - 使用阿里云 Qwen 模型进行代码审核
输出格式：ReviewDog RDJSON (https://github.com/reviewdog/reviewdog/blob/master/proto/rdf/)
"""

import json
import os
import sys
import subprocess
import re
from http.client import HTTPSConnection


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


def call_qwen_api(code_content, filename):
    """调用阿里云 Qwen API 进行代码审核"""
    api_key = os.environ.get('DASHSCOPE_API_KEY')
    base_url = os.environ.get('DASHSCOPE_BASE_URL', 'https://coding.dashscope.aliyuncs.com/v1')
    api_path = os.environ.get('DASHSCOPE_API_PATH', '/compatible-mode/v1/chat/completions')
    
    if not api_key:
        print("Error: DASHSCOPE_API_KEY not set", file=sys.stderr)
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

    # 调用 Qwen API（OpenAI 兼容格式）
    request_body = json.dumps({
        "model": "qwen-plus",
        "messages": [
            {
                "role": "system",
                "content": "你是一个专业的代码审查助手，擅长发现代码中的问题和改进建议。请用中文回复。"
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        "temperature": 0.3,
        "max_tokens": 2000
    })
    
    try:
        conn = HTTPSConnection(base_url, timeout=30)
        conn.request(
            "POST",
            api_path,
            body=request_body,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}"
            }
        )
        
        response = conn.getresponse()
        data = json.loads(response.read().decode())
        
        # 解析 Qwen 返回的结果
        content = data['choices'][0]['message']['content']
        
        # 提取 JSON（处理可能的 markdown 格式）
        json_match = re.search(r'\{.*\}', content, re.DOTALL)
        if json_match:
            result = json.loads(json_match.group())
            return result.get('issues', [])
        else:
            print(f"Failed to parse JSON from response: {content}", file=sys.stderr)
            return []
            
    except Exception as e:
        print(f"Error calling Qwen API: {e}", file=sys.stderr)
        return []


def main():
    """主函数 - 输出 RDJSON 格式"""
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
        issues = call_qwen_api(content, filepath)
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
    
    # 输出 RDJSON 格式
    print(json.dumps({"diagnostics": all_diagnostics}, indent=2))
    print(f"✅ Review complete. Total issues: {len(all_diagnostics)}", file=sys.stderr)


if __name__ == "__main__":
    main()
