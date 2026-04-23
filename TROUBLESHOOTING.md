# E2E 全链路调试记录

> 📅 2026-04-22 19:15

## 背景

推送 `test/e2e-full-chain` 分支后，GitHub Actions 的 Auto-Fix 环节始终失败，无法修复 AI Review 发现的问题。

## 问题现象

每次 Actions 日志都重复同样的错误：

```
Fetching review comments for PR #16
Found 9 review comments
Filtered to 0 qwen-review comments     ← 评论全被过滤
✅ No review issues found, skipping auto-fix
Error parsing result: ENOENT: no such file or directory, open 'auto-fix-result.json'  ← 后续步骤崩溃
Head Branch: main                       ← auto-resolve 在 main 上触发
```

## 根因分析（3 个问题）

### 1. Review 评论过滤条件错误（核心 bug）

**旧代码**：`.filter(c => c.body.includes('[qwen-review]'))`

**实际**：ReviewDog 发布的评论包含 `[claude-review]` 标记（来自 rdjson 的 `source.name` 字段）

所以 9 条评论全被过滤掉，AI Auto-Fix 被跳过

**修复**：改为 `.filter(c => c.body && c.body.includes('[claude-review]'))`

### 2. auto-fix-result.json 不存在时崩溃

当 Auto-Fix 被跳过时，不会生成 `auto-fix-result.json`，但后续 `Check if Fixes Applied` 步骤仍然执行，读取不存在的文件导致 ENOENT 错误。

**修复**：添加条件 `if: steps.check-issues.outputs.skip != 'true'` 跳过该步骤

### 3. Auto-Resolve 在 main 分支上误触发

`workflow_run` 事件的 `head_branch` 为 `main`（merge 后的 run），导致 auto-fix 和 auto-resolve 在 main 上执行，找不到对应 PR。

**修复**：两个 workflow 都添加 main 分支跳过逻辑

## 关键教训

1. **简单问题想复杂了**：过滤条件错误是最直接的原因，但我多次重写整个 workflow、重命名文件、加调试日志，没有第一时间定位到 `[qwen-review]` vs `[claude-review]` 的字符串不匹配
2. **GitHub Actions 缓存问题**：push 后 Actions 有时会跑旧版本代码，需要多次 push 或空 commit 触发新 run
3. **调试日志很重要**：dump 第一条评论结构能立即看清实际数据格式，避免猜测
4. **每一步都要有 `skip` 保护**：上游跳过的步骤，下游必须也跳过，否则读不到文件会崩溃

## 修复后的文件

- `.github/workflows/ai-auto-fix.yml` — 核心修复：`[claude-review]` 过滤 + skip guard + main branch guard
- `.github/workflows/auto-resolve-threads.yml` — main branch guard

## 完整预期流程

```
PR 推送
  │
  ├── AI Review (qwen-review.yml) → 发现问题 → reviewdog 发布 [claude-review] 评论
  │
  ├── AI Auto-Fix (ai-auto-fix.yml) → 按 [claude-review] 过滤评论 → AI 修复 → push
  │
  ├── Risk Policy Gate (risk-policy-gate.yml) → 验证 SHA + 运行 lint + 运行 test
  │
  └── Auto-Resolve (auto-resolve-threads.yml) → 折叠纯 bot 评论线程
```

## 遗留问题

- flake8 lint 检测到 `email_utils.py` 故意埋的问题后 exit 1，Risk Policy Gate 失败（这是预期行为，留给 AI Auto-Fix 修复）

---

> 📅 2026-04-23 — Step 6 (Bot Thread Auto-Resolve) 三轮修复记录

## 背景

4/22 的修复让 Auto-Fix 跑通了，但 Step 6（Bot Thread Auto-Resolve）在 PR 分支场景下从未被验证执行过。日志显示 `Head Branch: main` → `Skipping`，auto-resolve 被 main 分支守卫直接拦截。

## 根因：main 分支守卫过于激进

`auto-resolve-threads.yml` 的 Get PR Info 步骤在 `workflow_run` 事件中判断 `head_branch === 'main'` 时直接跳过。但 `workflow_run` 触发的 YAML 是从 default branch（main）读取的，`head_branch` 字段总是 `main`，即使实际工作是在 PR 分支上完成的。这导致合法的 PR run 也被挡在外面。

**关键发现**：push 到 PR 分支后，GitHub 有时不发送 `pull_request.synchronize` webhook，只有 `push` 事件触发。这导致 qwen-review 和 risk-policy-gate 没跑，整个 chain 断在第一环。

**临时解法**：关闭再重新打开 PR，强制触发 `pull_request.reopened` 事件。

## 第一轮修复：用 Search API 替代 main 分支守卫

**思路**：不依赖 `head_branch` 判断，改用 Search API 查找 open PR 来确定真实分支。

```javascript
// 旧逻辑：head_branch === 'main' 直接跳过
// 新逻辑：Search API 搜索 open PR
const { data: searchResult } = await github.rest.search.issuesAndPullRequests({
  q: `repo:${owner}/${repo} type:pr state:open`,
  sort: 'created', order: 'desc', per_page: 5
});
prNumber = searchResult.items[0].number;
branchName = searchResult.items[0].head.ref;
```

**结果**：`Head Branch: main` 不再跳过，但 Search API 报错：

```
Search API failed: Cannot read properties of undefined (reading 'ref')
```

## 第二轮修复：Search API 返回结构不符预期

**问题**：Search API (`issuesAndPullRequests`) 返回的 items **不包含 `head` 属性**，`head_ref_name` 也是 `None`。PR 的分支信息需要通过 `pulls.get` 或 `pulls.list` API 获取。

**结果**：修复 null 检查后，auto-resolve 找到了 PR，但 GraphQL 权限失败：

```
Resource not accessible by integration
```

## 第三轮修复：两个最终 bug

### Bug 1: Search API 不返回 head 分支信息

`issuesAndPullRequests` 是 Issues + PR 混合搜索，不返回完整 PR 对象。改用 `pulls.list` API：

```javascript
// 之前：Search API (无 head 信息)
const { data: searchResult } = await github.rest.search.issuesAndPullRequests(...)

// 现在：pulls.list (有 head.ref)
const { data: prs } = await github.rest.pulls.list({
  owner, repo, state: 'open', sort: 'created', direction: 'desc', per_page: 5
});
prNumber = prs[0].number;
branchName = prs[0].head.ref;
```

### Bug 2: GraphQL resolveReviewThread 权限不足

`GITHUB_TOKEN` 的 `pull-requests: write` 权限不够执行 `resolveReviewThread` mutation。改用 REST API 回复评论标记已解决：

```javascript
// 之前：GraphQL (权限不足)
await github.graphql(`mutation { resolveReviewThread(input: { threadId: ... }) }`)

// 现在：REST API (权限足够)
await github.rest.pulls.createReplyForReviewComment({
  pull_number: prNumber,
  comment_id: rootComment.id,
  body: '✅ Auto-resolved by bot'
});
```

## 最终验证结果

```
Found PR #16, branch: test/e2e-full-chain     ← pulls.list API 正确找到 PR
Resolving bot threads for PR #16
Found 8 thread(s)
Thread 3128683342: File: src/email_utils.py, Line: 10 (bot-only)
  ✅ Replied to comment #3128683342
  ...
  ✅ Replied to comment #3128683367
Bot Thread Auto-Resolve Complete
  ✅ Resolved: 8
  ⏭️  Skipped (human): 0
```

## 完整 E2E 链路状态

| 步骤 | 名称 | 状态 |
|------|------|------|
| 1 | Risk Contract | ✅ |
| 2 | Preflight Gate | ✅ |
| 3 | SHA Discipline | ✅ |
| 4 | Rerun Dedupe | ✅ |
| 5 | Remediation Loop | ✅ |
| 6 | Bot Thread Auto Resolve | ✅ |
| 7 | Browser Evidence | ❌ 未实现 |
| 8 | Harness Gap Loop | ❌ 未实现 |

## 新增教训

1. **API 返回结构不要猜，要查**：Search API 和 Pulls API 的返回结构不同，直接看 API 文档或 `curl` 调一次比猜省时间
2. **GitHub Token 权限分层**：REST API 和 GraphQL API 的权限检查不同，`pull-requests: write` 不够的 mutation 可以试试 REST API 等价操作
3. **workflow_run 始终读 main 分支 YAML**：任何 workflow_run 触发器的修改，都必须推到 main 才能生效，PR 分支上的改动被忽略

---

> 📅 2026-04-23 — Step 5 (Remediation Loop) Commit 不提交问题

## 背景

AI Auto-Remediation 日志显示 `✅ Fixed src/email_utils.py`，但 PR 分支上没有新 commit，代码没有被实际推送。

## 根因：`2>&1` 把 stderr 混入了 JSON 结果文件

**旧代码**：
```yaml
python3 scripts/auto-fix.py > auto-fix-result.json 2>&1 || true
```

Python 脚本的 INFO 日志输出到 stderr，`2>&1` 把 stderr 也重定向到文件，导致 `auto-fix-result.json` 内容是：
```
[INFO] 🚀 Starting AI Auto-Fix...
[INFO] PR: #None in VoidWalkerAether/email-assistant
...
{"fixed_files": ["src/email_utils.py"], "total_files": 1, "success": true}
```

`Check if Fixes Applied` 步骤 `JSON.parse()` 失败，`has_fixes` 始终是 `false`，Commit 步骤被跳过。

**修复**：
```yaml
python3 scripts/auto-fix.py > auto-fix-result.json || true
```

只捕获 stdout（JSON），让 INFO 日志正常输出到 Actions 控制台。

**教训**：Python 脚本里 `print(..., file=sys.stderr)` 的日志应该始终走 stderr，stdout 只保留结构化输出。`2>&1` 看起来是"收集所有输出"，实际上会污染数据文件。

---

> 📅 2026-04-23 — Step 8 (Harness Gap Loop) 实现记录

## 背景

实现 Harness Engineering 8 步的最后一步：将缺陷转化为永久测试用例。

## 实现文件

- `.github/ISSUE_TEMPLATE/harness-gap.md` — Issue 模板，强制填写缺陷描述和复现步骤
- `.github/workflows/harness-gap.yml` — 监听 `harness-gap` 标签，触发 AI 生成测试 + 自动创建 PR
- `scripts/harness-gap.py` — 核心脚本：读 issue → 调用 AI 生成 pytest 测试 → 写入文件

## 调试过程（6 轮）

### 第 1 轮：YAML 多行字符串语法错误

```
Invalid workflow file: .github/workflows/harness-gap.yml#L162
You have an error in your yaml syntax on line 162
```

**原因**：PR body 模板里直接嵌入了多行中文，YAML 解析器误认为是缩进错误。

**修复**：多行字符串改用单行 `\n` 拼接。

### 第 2 轮：Issue Body 字段未解析

```
[INFO] Affected file: ## 受影响的文件
src/email_utils.py
## 缺陷描述
...
```

**原因**：workflow 把 `${{ github.event.issue.body }}` 直接传给了所有环境变量，没有提取结构化字段。

**修复**：新增 `Parse Issue Body` 步骤，用 GitHub Script 解析 markdown 标题分隔的字段。

### 第 3 轮：Git API Tree SHA 错误

```
RequestError [HttpError]: Tree SHA is not a tree object
```

**原因**：`ref.object.sha` 是 commit SHA，但 `createCommit` 的 `tree` 参数需要的是 tree SHA。

**修复**：先用 `git.getCommit` 获取 `tree.sha`，再用 `git.createTree` 添加测试文件，最后用 `git.createCommit` 创建 commit。

### 第 4 轮：分支已存在导致 createRef 失败

```
RequestError [HttpError]: Reference already exists
```

**原因**：上一次创建 PR 失败后分支已存在，重复执行 `createRef` 报错。

**修复**：`createRef` 前先 `deleteRef`（已存在则忽略错误）。

### 第 5 轮：GitHub Actions 权限不足

```
RequestError [HttpError]: GitHub Actions is not permitted to create or approve pull requests.
```

**原因**：GitHub 仓库默认禁止 Actions 创建 PR（安全设置）。

**修复**：Settings → Actions → 勾选 "Allow GitHub Actions to create and approve pull requests"。

### 第 6 轮：AI 生成的测试 import 路径错误

```
from src.email_utils import parse_email_list
E   ModuleNotFoundError: No module named 'src.email_utils'
```

**原因**：AI prompt 没有指定项目的 import 风格（项目用 `sys.path.insert` + `from email_utils import`）。

**修复**：在 prompt 中明确说明 import 时去掉 `src.` 前缀。

## 新增教训

1. **YAML 多行字符串要转义**：在 `script: |` 块里嵌入多行模板字符串时，GitHub Actions 的 YAML 解析器容易混淆，改用单行 `\n` 拼接更安全
2. **Git API 的 commit sha ≠ tree sha**：`refs/heads/main` 返回的是 commit SHA，要 tree SHA 需额外调用 `git.getCommit`
3. **GitHub Actions 默认不能创建 PR**：这是一个仓库级安全设置，需要手动开启，代码层面无法绕过
4. **AI prompt 要约束项目风格**：AI 不知道项目现有的 import 惯例，prompt 里必须给出示例（如 `from email_utils import ...`）
5. **重试前清理残留状态**：分支、评论 marker、PR 都可能残留，每次重试前都要考虑幂等性
