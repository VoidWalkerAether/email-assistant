# Harness Engineering 实践日志

> 📅 开始日期：2026-04-07  
> **官方文档**：https://docs.github.com/zh/actions/get-started/quickstart  
> **仓库**：https://github.com/VoidWalkerAether/email-assistant  
> **本地路径**：`/Users/caiwei/workbench/claude-agent-sdk-demos/githubactions/email-assistant`

---

## 📊 当前进度总览

### Harness Engineering 8 步 Control-Plane Pattern

| 步骤 | 功能 | 状态 | 完成日期 |
|------|------|------|---------|
| 1. Risk Contract | 定义规则，消除歧义 | ✅ 完成 | 2026-04-07 |
| 2. Preflight Gate | 先拦再跑，省 CI 成本 | ✅ 完成 | 2026-04-08 |
| 3. SHA Discipline | 只信当前 HEAD 的证据 | ✅ 完成 | 2026-04-21 |
| 4. Rerun Dedupe | 一个 canonical writer，不重复 | ✅ 完成 | 2026-04-21 |
| 5. Remediation Loop | Agent 自己修，不绕过 gate | ✅ 完成 | 2026-04-21 |
| 6. Bot Thread Auto Resolve | 自动清理 bot thread，不碰人的 | ✅ 完成 | 2026-04-22 |
| 7. Browser Evidence | UI 证据是 CI artifact | ❌ 未开始 | - |
| 8. Harness Gap Loop | 事故转 test case | ❌ 未开始 | - |

**当前状态**：✅ 6/8 步完成 — Control-Plane 核心闭环已建立 + Bot Thread 自动清理  
**下一步**：实现 Browser Evidence（Step 7）或 Harness Gap Loop（Step 8）

---

## 📦 项目文件清单

```
email-assistant/
├── .github/workflows/
│   ├── github-actions-demo.yml    # 官方文档：基础 CI 演示
│   ├── risk-policy-gate.yml       # Harness 扩展：风险门控 + SHA 验证
│   ├── qwen-review.yml            # AI Review：Claude 代码审查 + ReviewDog
│   ├── ai-remediation.yml         # AI 自动修复：读取 review 评论 → 生成修复 → push
│   └── auto-resolve-threads.yml   # Bot Thread 自动解析
├── harness/
│   └── risk-contract.json         # 风险合同：定义 high/medium/low 规则和 merge policy
├── scripts/
│   ├── qwen-review.py             # AI 审查脚本：并发扫描 + RDJSON 输出
│   └── auto-fix.py                # AI 修复脚本：读取评论 → 生成修复 → 写文件
├── src/
│   ├── __init__.py
│   └── sender.py                  # 邮件发送模块（High Risk 文件）
├── tests/
│   └── test_sender.py             # sender 模块单元测试
├── requirements.txt
├── README.md
└── LOG.md                         # 本日志
```

---

## 2026-04-07 - Day 1: 基础搭建 ✅

### 参考文档
- **GitHub Actions Quickstart**: https://docs.github.com/zh/actions/get-started/quickstart
- **官方流程**：Creating your first workflow

### 完成内容

| 步骤 | 任务 | 状态 | 说明 |
|------|------|------|------|
| Step 1 | 创建 GitHub 仓库 | ✅ | https://github.com/VoidWalkerAether/email-assistant |
| Step 2 | 创建第一个 Workflow | ✅ | `github-actions-demo.yml`（按官方文档） |
| Step 3 | 学习 GitHub Actions | ✅ | 官方文档 + 入门教程 |
| Step 4 | Harness 核心配置 | ✅ | `risk-contract.json` + `risk-policy-gate.yml` |

### 按官方文档创建的文件

**官方文档步骤**：
1. 创建 `.github/workflows/` 目录
2. 创建 `github-actions-demo.yml`
3. Commit changes
4. 触发 push 事件
5. 查看 workflow runs

**我们创建的文件**：
```
email-assistant/
├── .github/workflows/
│   ├── github-actions-demo.yml    # 官方文档 Step 2
│   └── risk-policy-gate.yml       # Harness 扩展
├── harness/
│   └── risk-contract.json         # Harness 配置
├── src/
│   └── __init__.py
├── requirements.txt
└── README.md
```

### 官方 Workflow 内容（按文档复制）

```yaml
name: GitHub Actions Demo
run-name: ${{ github.actor }} is testing out GitHub Actions 🚀
on: [push]

jobs:
  Explore-GitHub-Actions:
    runs-on: ubuntu-latest
    steps:
      - run: echo "🎉 Hello from email-assistant!"
      - name: Check out repository code
        uses: actions/checkout@v5
      - run: echo "💡 Repository is ready!"
      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: python --version
```

### 验证结果

| 检查项 | 预期 | 实际 | 状态 |
|--------|------|------|------|
| Workflow 文件创建 | `.github/workflows/github-actions-demo.yml` | ✅ 已创建 | ✅ |
| Push 触发 | 自动运行 workflow | ✅ 触发 | ✅ |
| Workflow 运行 | 显示在 Actions 面板 | ✅ 成功 | ✅ |
| 输出日志 | 显示 "Hello from email-assistant!" | ✅ 显示 | ✅ |

---

## 2026-04-08 - Day 2: PR 流程验证 ✅

### 参考文档
- **GitHub Actions Quickstart**: https://docs.github.com/zh/actions/get-started/quickstart
- **Harness Engineering**: `memory/lessons/harness-engineering.md`

### 完成内容

| 步骤 | 任务 | 状态 | 说明 |
|------|------|------|------|
| Step 5 | 创建测试分支 | ✅ | `feature/add-sender` |
| Step 5 | 编写 sender.py | ✅ | High Risk 文件（邮件发送逻辑） |
| Step 5 | 编写测试用例 | ✅ | `tests/test_sender.py` |
| Step 5 | 开 PR 验证 | ✅ | Risk Gate 正确识别 High Risk |
| Step 6 | 添加 Enforce 步骤 | ✅ | High Risk 正确阻止 Merge |

### 验证结果

| 测试场景 | 修改文件 | 预期风险 | 实际结果 | 状态 |
|---------|---------|---------|---------|------|
| Test 1 | `src/sender.py` + tests | High | ✅ Risk Tier: high, 阻止 Merge | ✅ 成功 |
| Test 2 | `.github/workflows/` | Low | ✅ Risk Tier: low, 快速通过 | ✅ 成功 |

### 核心洞察

1. **GitHub Actions 触发机制**：
   - `on: [push]` → 任何 push 触发
   - `on: pull_request` → PR 创建/更新时触发

2. **Risk Contract 工作原理**：
   - 读取 JSON 规则文件
   - 分析 PR 修改的文件列表
   - 匹配路径模式 → 判断风险等级
   - 输出警告 + 可选阻止 Merge

3. **Harness 核心价值**：
   - 不是让 AI 替你思考
   - 是把你的思考变成 AI 能执行的规则
   - 用确定性的工具，框住不确定性的 AI

### 遇到的问题

1. **Git Push 网络问题**：多次超时（HTTP2 framing error）
2. **PR 不会自动创建**：Git Push 后需要在 GitHub 网页手动创建 PR
3. **路径匹配逻辑**：初始版本不完整，已改进支持通配符

---

## 2026-04-21 - Day 14: AI Review + Auto-Fix + SHA Discipline ✅

### 参考文档
- **Harness Engineering 完整拆解**: `~/myobsidian/03-Resources/素材/收藏/Harness Engineering 完整拆解.md`
- **Control-Plane Pattern**: Ryan Carson 的 8 步确定性流程

### 完成内容

| 步骤 | 任务 | 状态 | 说明 |
|------|------|------|------|
| Step 3 | SHA Discipline | ✅ | PR gate 验证 review SHA 匹配 HEAD |
| Step 4 | Rerun Dedupe | ✅ | 删除旧评论 + 发布带 SHA marker 的新评论 |
| Step 5 | Remediation Loop | ✅ | AI 自动修复 review 问题并 push |
| Step 7 | AI Review 集成 | ✅ | `qwen-review.yml` + `scripts/qwen-review.py` |
| Step 8 | Lint 检查启用 | ✅ | risk-policy-gate 中集成 flake8 |

### 新增文件

```
.github/workflows/
├── qwen-review.yml            # AI Review 工作流
└── ai-remediation.yml         # AI 自动修复工作流
scripts/
├── qwen-review.py             # AI 代码审查脚本
└── auto-fix.py                # AI 自动修复脚本
```

### 核心架构

**Control-Plane 闭环**：
```
PR 开启
  │
  ├── Risk Contract → 判断风险等级
  ├── Preflight Gate → Tests + Lint
  ├── AI Review (qwen-review.yml) → 审查代码 + 评论
  ├── SHA Discipline → 验证 review 匹配 HEAD
  ├── Remediation Loop → Agent 自修 → 回到 Gate
  │
  └── Merge
```

### 技术要点

1. **AI Review**：
   - 并发审查多个 Python 文件
   - 输出 RDJSON 格式 → ReviewDog 集成到 PR
   - 通过阿里云代理访问 Claude 模型

2. **SHA Discipline**（文章说"这是最大的实战教训"）：
   - `risk-policy-gate.yml` 轮询 PR 评论
   - 验证 `<!-- review-status -->` 中的 SHA 与 HEAD 匹配
   - 3 分钟超时，未匹配则 fail

3. **Remediation Loop**：
   - `ai-remediation.yml` 由 review workflow 的 `workflow_run` 事件触发
   - 读取 review 评论 → 按文件分组问题 → AI 生成修复
   - 限制最多修复 3 个文件，修复后 push 到 PR 分支
   - push 自动触发完整的 preflight gate 重跑（SHA discipline 闭环）

4. **Rerun Dedupe**：
   - 先删除所有旧的 `<!-- review-status -->` 评论
   - 再发布带当前 SHA 的新评论
   - 避免同一 HEAD 的重复 rerun

---

## 2026-04-22 - Day 15: Bot Thread Auto Resolve (Step 6) ✅

### 参考文档
- **Harness Engineering 完整拆解**: Step 6 — Bot Thread 的自动 Resolve

### 完成内容

| 步骤 | 任务 | 状态 | 说明 |
|------|------|------|------|
| Step 6 | Bot Thread Auto Resolve | ✅ | `auto-resolve-threads.yml` |

### 新增文件

```
.github/workflows/
└── auto-resolve-threads.yml    # Bot Thread 自动解析工作流
```

### 核心逻辑

1. **触发时机**：AI Auto-Remediation 完成后自动触发（`workflow_run`）
2. **Thread 分组**：按 `in_reply_to_id` 将 review 评论分组为 thread
3. **人类参与检测**：检查 thread 中是否有非 `github-actions[bot]` 的评论
   - 有人类参与 → **跳过**（不代替人做决策）
   - 纯 bot thread → **自动 resolve**
4. **Resolve 方式**：使用 GitHub GraphQL `resolveReviewThread` mutation

---

## 📅 下一步计划

### P0 - 必须完成

| 任务 | 预计时间 | 说明 |
|------|---------|------|
| **PR 实测 Step 6** | 15 分钟 | 开 PR 验证 bot thread auto-resolve 是否正常工作 |

### P1 - 核心功能

| 任务 | 预计时间 | 说明 |
|------|---------|------|
| Medium Risk 测试 | 20 分钟 | 验证分层逻辑 |
| Remediation 收敛性 | 30 分钟 | 添加 max retry / circuit breaker 防无限 loop |

### P2 - 进阶功能

| 任务 | 说明 |
|------|------|
| Harness Gap Loop | 线上事故 → 转 test case → 加入 harness |
| Browser Evidence | UI 改动的 first-class CI artifact |

---

## 🧠 知识沉淀

### GitHub Actions 核心概念（来自官方文档）

| 概念 | 官方定义 | 我们的理解 |
|------|---------|-----------|
| **Workflow** | 自动化流程，由 YAML 文件定义 | 相当于"剧本"，定义要做什么 |
| **Event** | 触发 workflow 的事件 | GitHub 上的动作（push、PR 等） |
| **Job** | 一组步骤，在同一个 runner 上执行 | 相当于"场景" |
| **Step** | 单个任务，可以是 run 或 uses | 相当于"台词" |
| **Runner** | 执行 job 的服务器 | GitHub 提供的虚拟机 |

### Harness 风险分层

| 风险等级 | 检查要求 | 适用场景 | 类比 |
|---------|---------|---------|------|
| **High** | AI Review + 人工审批 + 测试 + Lint | 核心代码、安全相关 | 进小区装修 |
| **Medium** | 测试 + Lint | 普通源码 | 进小区维修 |
| **Low** | 快速通过 | 文档、配置 | 进小区送快递 |

### 关键命令

```bash
# 创建分支
git checkout -b feature/xxx

# 提交代码
git add .
git commit -m "feat: xxx"

# 推送分支
git push -u origin feature/xxx

# 查看分支状态
git branch -v
```

---

## 📊 仓库状态

### 本地分支
```
* feature/add-enforce-step  872e4af docs: update LOG.md
  feature/add-sender        03796d5 feat: add sender module
  main                      06d0970 Add Harness configuration
```

### 远程分支（GitHub）
- `main` - 主分支（受保护）
- `feature/add-sender` - 已合并 ✅
- `feature/add-enforce-step` - 待创建 PR ⏳

### 待创建 PR
- **分支**：`feature/add-enforce-step`
- **目的**：验证 High Risk 阻止 Merge
- **预期**：Risk Policy Gate 显示 🔴 Failed

---

## 📚 参考资源

### 官方文档
- **GitHub Actions Quickstart**: https://docs.github.com/zh/actions/get-started/quickstart
- **Understanding GitHub Actions**: https://docs.github.com/en/actions/learn-github-actions/understanding-github-actions
- **Workflow syntax**: https://docs.github.com/en/actions/writing-workflows/workflow-syntax-for-github-actions

### Harness 相关
- **Harness Engineering 方法论**: `memory/lessons/harness-engineering.md`
- **OpenAI 工程团队实践**: 100 万行代码，0 行人写
- **Ryan Carson Control-Plane**: 8 步确定性流程

---

## 🔄 迭代记录

| 日期 | 更新内容 | 状态 |
|------|----------|------|
| 2026-04-07 | 初始创建，基础搭建 | ✅ 完成 |
| 2026-04-08 | PR 流程验证，Enforce 步骤 | ✅ 完成 |
| 2026-04-21 | AI Review 集成、Remediation Loop、SHA Discipline | ✅ 完成 |
| 2026-04-22 | 更新 LOG.md 进度总览（8 步模式） | ✅ 完成 |
| 2026-04-22 | Bot Thread Auto Resolve (Step 6) | ✅ 完成 |

---

## 📊 与文章建议的"最小可行组合"对比

| 优先级 | 建议 | 状态 |
|--------|------|------|
| P0: Risk Contract + SHA 追踪 | 零成本，纯纪律 | ✅ 完成 |
| P0: Code Review Agent | CodeRabbit/Greptile 等价 | ✅ 完成（自建 qwen-review） |
| P1: Remediation Loop | Agent 自修 | ✅ 完成 |

---

*Last updated: 2026-04-22*  
*Next session: PR 实测 Step 6 (Bot Thread Auto Resolve)*  
*Status: 6/8 步完成*
