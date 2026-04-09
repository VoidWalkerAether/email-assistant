# Harness Engineering 实践日志

> 📅 开始日期：2026-04-07  
> **官方文档**：https://docs.github.com/zh/actions/get-started/quickstart  
> **仓库**：https://github.com/VoidWalkerAether/email-assistant  
> **本地路径**：`/Users/caiwei/workbench/claude-agent-sdk-demos/others/email-assistant`

---

## 📊 当前进度总览

| 阶段 | 步骤 | 任务 | 状态 | 完成日期 |
|------|------|------|------|---------|
| **阶段 1** | Step 1 | 创建 GitHub 仓库 | ✅ 完成 | 2026-04-07 |
| **阶段 1** | Step 2 | 创建第一个 Workflow | ✅ 完成 | 2026-04-07 |
| **阶段 1** | Step 3 | 学习 GitHub Actions | ✅ 完成 | 2026-04-07 |
| **阶段 1** | Step 4 | Harness 核心配置 | ✅ 完成 | 2026-04-07 |
| **阶段 2** | Step 5 | PR 流程验证 | ✅ 完成 | 2026-04-08 |
| **阶段 2** | Step 6 | Enforce 步骤验证 | ✅ 完成 | 2026-04-09 |
| **阶段 3** | Step 7 | AI Review 集成 | ❌ 未开始 | - |
| **阶段 3** | Step 8 | Lint 检查启用 | ❌ 未开始 | - |

**当前状态**：✅ Harness 核心功能验证完成（High Risk 正确阻止）  
**下一步**：创建 PR 验证 High Risk 阻止 Merge

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
| Step 6 | 添加 Enforce 步骤 | ✅ | 代码完成，待验证 |
| Step 6 | 验证 Enforce | ⏳ | 待创建 PR 验证 |

### 新增文件

```
email-assistant/
├── src/sender.py                  # 邮件发送模块（High Risk）
├── tests/test_sender.py           # 单元测试
├── .github/workflows/
│   └── risk-policy-gate.yml       # 更新：添加 Enforce 步骤
└── LOG.md                         # 本日志
```

### 核心代码

#### sender.py（High Risk 文件）
```python
"""Email sender module - High Risk"""

def send_email(to: str, subject: str, body: str) -> bool:
    """Send an email."""
    print(f"Sending to {to}: {subject}")
    return True

def validate_email(email: str) -> bool:
    """Validate email format."""
    return "@" in email and "." in email
```

#### risk-policy-gate.yml（Enforce 步骤）
```yaml
- name: Enforce Risk Policy
  run: |
    RISK_TIER="${{ steps.risk.outputs.riskTier }}"
    
    if [ "$RISK_TIER" = "high" ]; then
      echo "❌ HIGH RISK: Changes require AI code review + manual approval"
      exit 1  # 失败，阻止 Merge
    fi
```

### 验证结果

| 测试场景 | 修改文件 | 预期风险 | 实际结果 | 状态 |
|---------|---------|---------|---------|------|
| Test 1 | `src/sender.py` + tests | High | ✅ Risk Tier: high, 警告输出 | ✅ 成功 |
| Test 2 | `.github/workflows/` | Low | ✅ Risk Tier: low | ✅ 成功 |
| Test 3 | `src/__init__.py` | High | ⏳ 待验证 | ⏳ Pending |

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

## 📅 下一步计划

### P0 - 必须完成（明天第一步）

| 任务 | 预计时间 | 说明 |
|------|---------|------|
| **创建 PR 验证 Test 3** | 10 分钟 | 确认 High Risk 阻止 Merge |
| **Low Risk 测试** | 10 分钟 | 修改 README，验证快速通过 |

### P1 - 核心功能

| 任务 | 预计时间 | 说明 |
|------|---------|------|
| 启用真实测试 | 15 分钟 | 取消 pytest 注释 |
| 启用 Lint 检查 | 15 分钟 | 取消 flake8 注释 |
| Medium Risk 测试 | 20 分钟 | 验证分层逻辑 |

### P2 - 进阶功能

| 任务 | 说明 |
|------|------|
| AI Code Review 集成 | CodeRabbit / Greptile |
| Browser Evidence | UI 测试验证 |
| 完整 Control-Plane | 8 步确定性流程 |

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
| 2026-04-08 | 更新进度总览，记录官方文档链接 | ✅ 完成 |

---

*Last updated: 2026-04-08 19:05*  
*Next session: 2026-04-09*  
*Status: Ready to continue - Step 6 待验证*
