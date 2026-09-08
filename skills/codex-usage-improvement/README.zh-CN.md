# Codex 使用复盘与改进

语言：[English](README.md) | **中文**

`codex-usage-improvement` 将本地 Codex 会话元数据和经用户确认的经验整理成注重隐私的复盘。它帮助发现重复阻碍、保留有效做法，并通过小范围实验改进工作流，不会静默修改 Codex 配置或项目指令。

## 如何使用

可以指定一个时间范围进行复盘，也可以只分析某个项目；完成证据检查后，还可以要求保存或重新评估某条经验。

```text
复盘我最近七天的 Codex 使用，并建议两项改进。
分析这个仓库最近的 Codex 会话，找出重复出现的阻碍。
把这条结论记录为项目经验，然后列出当前已确认的经验。
```

随附脚本可以生成仅包含元数据的报告，也可以管理只追加、不覆写的经验日志：

```bash
python scripts/codex_usage_improvement.py review --days 7
python scripts/codex_usage_improvement.py review --days 30 --project-root /absolute/project/path
python scripts/codex_usage_improvement.py list --status confirmed
```

经验日志默认存放在仓库之外的 XDG 状态目录。证据、隐私和变更边界详见 [SKILL.md](SKILL.md)。

## 何时触发

在以下情况使用此 Skill：

- 复盘近期会话中使用 Codex 的方式；
- 查找反复出现的工具失败、上下文压力、任务拆分问题或有效习惯；
- 记录、确认、否定或替代一条有证据支持的经验；
- 设计一个小范围实验来改进后续 Codex 工作。

## 何时不触发

如果需求只是统计 token 或成本、进行普通代码审查或调试，或者要断言本地会话日志无法证明的 Codex 通用行为，则不使用此 Skill。它也不会静默修改项目指令、Skill、配置或自动化。
