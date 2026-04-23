name: "Step 8: Harness Gap — Bug to Test Case"
description: "将一个缺陷转化为永久的 pytest 测试用例，确保同样的问题不再出现"
labels: ["harness-gap"]
body:
  - type: markdown
    attributes:
      value: |
        ## Harness Gap: 缺陷 → 测试用例

        填写以下信息后，AI Agent 会自动生成对应的 pytest 测试并创建 PR。

  - type: input
    id: affected_file
    attributes:
      label: "受影响的文件"
      description: "存在缺陷的源文件路径（如 src/email_utils.py）"
      placeholder: "src/email_utils.py"
    validations:
      required: true

  - type: textarea
    id: bug_description
    attributes:
      label: "缺陷描述"
      description: "描述 bug 的具体表现"
      placeholder: "parse_email_list 函数无法处理空格分隔的邮箱列表"
    validations:
      required: true

  - type: textarea
    id: reproduction_steps
    attributes:
      label: "复现步骤"
      description: "如何复现这个 bug"
      placeholder: |
        1. 调用 parse_email_list("a@b.com c@d.com")
        2. 返回 ["a@b.com"]（丢失了第二个邮箱）
        3. 预期应该返回 ["a@b.com", "c@d.com"]
    validations:
      required: true

  - type: textarea
    id: expected_behavior
    attributes:
      label: "期望行为"
      description: "修复后应该是什么样的"
      placeholder: "parse_email_list 应该正确分割并返回所有有效邮箱地址"
