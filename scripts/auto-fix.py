#!/usr/bin/env python3
"""
AI Auto-Fix - 自动修复 AI Review 发现的问题
触发方式：在 PR 评论中 @github-actions 或手动触发 workflow
"""

import json
import os
import sys
import subprocess
import asyncio
from claude_agent_sdk import query, ClaudeAgentOptions, AssistantMessage, TextBlock


def get_pr_info():
    """从 GitHub Actions 环境变量获取 PR 信息"""
    owner = os.environ.get("GITHUB_REPOSITORY_OWNER")
    repo_full = os.environ.get("GITHUB_REPOSITORY", "")
    pr_number = os.environ.get("PR_NUMBER") or os.environ.get("GITHUB_EVENT_NUMBER")
    
    if not owner:
        raise ValueError("GITHUB_REPOSITORY_OWNER is not set")
    if not repo_full:
        raise ValueError("GITHUB_REPOSITORY is not set")
    if not pr_number:
        raise ValueError("PR_NUMBER or GITHUB_EVENT_NUMBER is not set")
    
    repo = repo_full.split("/")[1]
    if not repo:
        raise ValueError("Invalid GITHUB_REPOSITORY format")
    
    return {
        "owner": owner,
        "repo": repo,
        "pr_number": pr_number,
        "sha": os.environ.get("GITHUB_SHA", "HEAD"),
    }


def get_changed_files():
    """获取 PR 修改的文件列表"""
    base_sha = os.environ.get("GITHUB_BASE_SHA", "HEAD~1")
    head_sha = os.environ.get("GITHUB_SHA", "HEAD")
    
    result = subprocess.run(
        ["git", "diff", "--name-only", base_sha, head_sha],
        capture_output=True, text=True
    )
    
    if result.returncode != 0:
        print(f"[ERROR] git diff failed: {result.stderr}", file=sys.stderr)
        return []
    
    files = result.stdout.strip().split("\n")
    return [f for f in files if f and os.path.exists(f)]


def read_file_content(filepath):
    """读取文件内容"""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        print(f"[ERROR] Reading {filepath}: {e}", file=sys.stderr)
        return ""


def get_review_comments():
    """
    从 GitHub API 获取 AI Review 评论
    通过环境变量传入评论内容（由 workflow 传递）
    """
    comments_json = os.environ.get("REVIEW_COMMENTS", "[]")
    try:
        comments = json.loads(comments_json)
        print(f"[INFO] Found {len(comments)} review comments", file=sys.stderr)
        print(f"[DEBUG] Comments: {comments_json[:200]}...", file=sys.stderr)
        return comments
    except json.JSONDecodeError as e:
        print(f"[ERROR] Failed to parse REVIEW_COMMENTS: {e}", file=sys.stderr)
        return []


def group_issues_by_file(comments):
    """按文件分组问题"""
    issues_by_file = {}
    
    for comment in comments:
        filepath = comment.get("location", {}).get("path", "")
        if not filepath:
            continue
        
        if filepath not in issues_by_file:
            issues_by_file[filepath] = []
        
        issues_by_file[filepath].append({
            "line": comment.get("location", {}).get("range", {}).get("start", {}).get("line", 1),
            "message": comment.get("message", "Unknown issue"),
            "severity": comment.get("severity", "warning")
        })
    
    return issues_by_file


async def call_ai_for_fix(filepath, content, issues):
    """调用 AI 生成修复代码"""
    
    auth_token = os.environ.get("ANTHROPIC_AUTH_TOKEN")
    base_url = os.environ.get("ANTHROPIC_BASE_URL", "https://coding.dashscope.aliyuncs.com/apps/anthropic")
    model = os.environ.get("ANTHROPIC_MODEL", "qwen3-coder-plus")
    
    if not auth_token:
        print("[ERROR] ANTHROPIC_AUTH_TOKEN not set", file=sys.stderr)
        return None
    
    # 构建问题列表
    issues_text = "\n".join([
        f"  行 {issue['line']}: {issue['message']} (严重性：{issue['severity']})"
        for issue in issues
    ])
    
    prompt = f"""请修复以下 Python 代码中的问题。

文件名：{filepath}

原代码：
```python
{content}
```

需要修复的问题：
{issues_text}

要求：
1. 只返回修复后的完整代码，不要解释
2. 保持原有功能不变
3. 用标准 Python 最佳实践
4. 不要添加新的依赖库
5. 返回纯代码，不要用 markdown 包裹

修复后的代码："""
    
    options = ClaudeAgentOptions(
        system_prompt="你是一个专业的代码修复助手，擅长快速准确地修复代码问题。只返回修复后的代码，不要其他内容。",
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
            print(f"[ERROR] Empty response from AI for {filepath}", file=sys.stderr)
            return None
        
        # 清理 markdown 包裹（如果有）
        if full_response.startswith("```python"):
            full_response = full_response[9:]
        if full_response.startswith("```"):
            full_response = full_response[3:]
        if full_response.endswith("```"):
            full_response = full_response[:-3]
        
        return full_response.strip()
    
    except Exception as e:
        print(f"[ERROR] AI fix failed for {filepath}: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc(file=sys.stderr)
        return None


def apply_fix(filepath, fixed_content):
    """应用修复到文件"""
    try:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(fixed_content)
        print(f"[INFO] Applied fix to {filepath}", file=sys.stderr)
        return True
    except Exception as e:
        print(f"[ERROR] Failed to write {filepath}: {e}", file=sys.stderr)
        return False


async def process_file(filepath, issues):
    """异步处理单个文件的修复"""
    print(f"[INFO] Fixing {filepath} ({len(issues)} issues)...", file=sys.stderr)
    
    content = read_file_content(filepath)
    if not content:
        print(f"[WARN] Skipping {filepath}: empty or unreadable", file=sys.stderr)
        return None
    
    # 调用 AI 生成修复
    fixed_content = await call_ai_for_fix(filepath, content, issues)
    if not fixed_content:
        print(f"[WARN] AI failed to generate fix for {filepath}", file=sys.stderr)
        return None
    
    # 应用修复
    if apply_fix(filepath, fixed_content):
        print(f"[INFO] ✅ Fixed {filepath}", file=sys.stderr)
        return filepath
    
    return None


async def process_files_async(issues_by_file):
    """异步处理多个文件"""
    tasks = []
    for filepath, issues in issues_by_file.items():
        task = process_file(filepath, issues)
        tasks.append(task)
    
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    fixed_files = []
    for result in results:
        if isinstance(result, str):  # 成功修复的文件路径
            fixed_files.append(result)
        elif isinstance(result, Exception):
            print(f"[ERROR] Error processing file: {result}", file=sys.stderr)
    
    return fixed_files


def main():
    """主函数"""
    # 所有日志输出到 stderr，只有 JSON 输出到 stdout
    print("[INFO] 🚀 Starting AI Auto-Fix...", file=sys.stderr)
    
    try:
        # 获取 PR 信息
        pr_info = get_pr_info()
        print(f"[INFO] PR: #{pr_info['pr_number']} in {pr_info['owner']}/{pr_info['repo']}", file=sys.stderr)
    except ValueError as e:
        print(f"[ERROR] {e}", file=sys.stderr)
        result = {
            "fixed_files": [],
            "total_files": 0,
            "success": False,
            "reason": str(e)
        }
        print(json.dumps(result))
        return 1
    
    # 获取 Review 评论
    comments = get_review_comments()
    if not comments:
        print("[INFO] No review comments to fix, exiting.", file=sys.stderr)
        # 输出空 JSON（而不是直接退出）
        result = {
            "fixed_files": [],
            "total_files": 0,
            "success": False,
            "reason": "No review comments found"
        }
        print(json.dumps(result))
        return 0
    
    # 按文件分组问题
    issues_by_file = group_issues_by_file(comments)
    print(f"[INFO] Issues found in {len(issues_by_file)} file(s)", file=sys.stderr)
    
    # 限制最大修复文件数（避免过度修改）
    max_files = int(os.environ.get("MAX_FIX_FILES", "3"))
    if len(issues_by_file) > max_files:
        print(f"[WARN] Too many files ({len(issues_by_file)}), limiting to {max_files}", file=sys.stderr)
        issues_by_file = dict(list(issues_by_file.items())[:max_files])
    
    # 异步处理所有文件
    fixed_files = asyncio.run(process_files_async(issues_by_file))
    
    # 过滤掉 None 值（代表失败的修复）
    fixed_files = [f for f in fixed_files if f is not None]
    
    # 输出结果
    print("", file=sys.stderr)
    print("=" * 50, file=sys.stderr)
    print(f"AI Auto-Fix Summary:", file=sys.stderr)
    print(f"  Files processed: {len(issues_by_file)}", file=sys.stderr)
    print(f"  Files fixed: {len(fixed_files)}", file=sys.stderr)
    print(f"  Fixed files: {', '.join(fixed_files) if fixed_files else 'None'}", file=sys.stderr)
    print("=" * 50, file=sys.stderr)
    
    # 输出 JSON 供 workflow 使用
    result = {
        "fixed_files": fixed_files,
        "total_files": len(issues_by_file),
        "success": len(fixed_files) > 0
    }
    print(json.dumps(result))
    
    return 0 if result["success"] else 1


if __name__ == "__main__":
    sys.exit(main())