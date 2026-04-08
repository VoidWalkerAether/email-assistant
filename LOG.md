# Harness Engineering 实践日志

## 2026-04-07 - Day 1: 基础搭建 ✅

### 完成内容

| 步骤 | 任务 | 状态 | 说明 |
|------|------|------|------|
| Step 1 | 创建 GitHub 仓库 | ✅ | https://github.com/VoidWalkerAether/email-assistant |
| Step 2 | 创建第一个 Workflow | ✅ | `github-actions-demo.yml`（Python 项目） |
| Step 3 | 学习 GitHub Actions | ✅ | 官方文档 + 入门教程 |
| Step 4 | Harness 核心配置 | ✅ | `risk-contract.json` + `risk-policy-gate.yml` |

### 创建的文件

```
email-assistant/
├── .github/workflows/
│   ├── github-actions-demo.yml    # 测试 Workflow
│   └── risk-policy-gate.yml       # Harness 核心
├── harness/
│   └── risk-contract.json         # 风险配置
├── src/
│   └── __init__.py
├── requirements.txt
└── README.md
```

### 关键配置

**risk-contract.json**：
- High Risk: `src/sender.py`, `src/harness/**`
- Medium Risk: `src/*.py`
- Low Risk: 其他文件

**High Risk 需要**：risk-policy-gate + test + lint  
**Low Risk 需要**：risk-policy-gate + test

### 遇到的问题

- Git push 时缺少 `workflow` 权限
- 解决：在 GitHub 网页上手动创建第一个 Workflow

---

## 2026-04-08 - Day 2: PR 流程验证 ✅

### 完成内容

| 步骤 | 任务 | 状态 | 说明 |
|------|------|------|------|
| Step 5 | 创建测试分支 | ✅ | `feature/add-sender` |
| Step 5 | 编写 sender.py | ✅ | High Risk 文件（邮件发送逻辑） |
| Step 5 | 编写测试用例 | ✅ | `tests/test_sender.py` |
| Step 5 | 开 PR 验证 | ✅ | Risk Gate 正确识别 High Risk |
| Step 6 | 添加 Enforce 步骤 | ✅ | High Risk 真正阻止 Merge |
| Step 6 | 验证 Enforce | ⏳ | 待确认（推送成功，待创建 PR） |

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

### 未完成事项

| 任务 | 状态 | 说明 |
|------|------|------|
| Test 3 验证 | ⏳ Pending | `src/__init__.py` 已推送，待创建 PR 验证 High Risk 阻止 Merge |
| AI Code Review 集成 | ❌ 未开始 | 进阶功能，可后续添加 |
| 启用实际测试 | ❌ 未开始 | pytest 目前被注释 |
| 启用 Lint 检查 | ❌ 未开始 | flake8 目前被注释 |

---

## 📅 明日计划（2026-04-09）

### P0 - 必须完成

| 任务 | 预计时间 | 说明 |
|------|---------|------|
| 完成 Test 3 验证 | 10 分钟 | 创建 PR，确认 High Risk 阻止 Merge |
| 总结 Harness 流程 | 20 分钟 | 输出完整文档/文章 |

### P1 - 可选继续

| 任务 | 预计时间 | 说明 |
|------|---------|------|
| 启用实际测试 | 15 分钟 | 取消 pytest 注释，运行真实测试 |
| 启用 Lint 检查 | 15 分钟 | 取消 flake8 注释 |
| 应用到外贸助理 | 60 分钟 | 将 Harness 应用到实际项目 |

### P2 - 长期目标

| 任务 | 说明 |
|------|------|
| AI Code Review 集成 | CodeRabbit / Greptile |
| Browser Evidence | UI 测试验证 |
| 完整 Control-Plane | 8 步确定性流程 |

---

## 🧠 知识沉淀

### GitHub Actions 核心概念

| 概念 | 说明 | 示例 |
|------|------|------|
| **Workflow** | 整个自动化流程 | `.yml` 文件 |
| **Event** | 触发条件 | `push`, `pull_request` |
| **Job** | 一组步骤 | `risk-check` |
| **Step** | 单个任务 | `run:`, `uses:` |
| **Runner** | 执行环境 | `ubuntu-latest` |

### Harness 风险分层

| 风险等级 | 检查要求 | 适用场景 |
|---------|---------|---------|
| **High** | AI Review + 人工审批 + 测试 + Lint | 核心代码、安全相关 |
| **Medium** | 测试 + Lint | 普通源码 |
| **Low** | 快速通过 | 文档、配置 |

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

**当前分支**：
- `main` - 主分支（受保护）
- `feature/add-sender` - 已合并 ✅
- `feature/add-enforce-step` - 待创建 PR ⏳

**GitHub 仓库**：https://github.com/VoidWalkerAether/email-assistant

**本地路径**：`/Users/caiwei/workbench/claude-agent-sdk-demos/others/email-assistant`

---

*Last updated: 2026-04-08 19:00*
*Next session: 2026-04-09*
*Status: Ready to continue*
