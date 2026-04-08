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

### 下一步（Day 2）

- [ ] 创建测试分支，开 PR 验证 Harness
- [ ] 编写实际的 sender.py 代码
- [ ] 添加测试用例（tests/）
- [ ] 配置 AI Code Review（可选）

---

*Last updated: 2026-04-07 18:40*
