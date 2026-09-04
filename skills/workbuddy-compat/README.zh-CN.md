# WorkBuddy 兼容性

语言：[English](README.md) | **中文**

`workbuddy-compat` 用于让本仓库中的每一个 Agent Skill 在 OpenAI Codex 和 WorkBuddy 中都能运行。配套脚本 `scripts/workbuddy_compat.py` 会检查并自动修复两类常见兼容问题：缺少 `## Platform Compatibility` 章节，以及 `SKILL.md` 或 README 使用示例中存在未注明 Codex 场景的 `$<skill>` 调用语法。WorkBuddy 的 Skill 安装目录由具体产品配置决定，并不存在适用于所有版本的单一路径。

## 如何使用

请说明 Skill 名称（或说“所有 Skill”）以及希望执行的操作。常见请求包括：

```text
检查每个 Skill 是否都兼容 WorkBuddy。
让这个新的 Codex Skill 也兼容 WorkBuddy。
修复 skills/my-skill 的兼容性缺口。
```

在 OpenAI Codex 中也可以显式用 `$workbuddy-compat` 调用本 Skill。

需要确定性输出时可直接运行脚本：

```bash
python3 scripts/workbuddy_compat.py --check
python3 scripts/workbuddy_compat.py --fix --skill skills/my-skill
```

具体规则、注入的章节内容、运行时兼容与市场发布规范的区别，以及 CI 卡点的运行方式见 [SKILL.md](SKILL.md)。

## 何时触发

在以下情况使用此 Skill：

- 新增一个为 OpenAI Codex 编写的 Skill，且需要同时能在 WorkBuddy 中运行；
- 要求检查或强制某个或所有 Skill 的 WorkBuddy 兼容性；
- 希望把一个 Codex Skill 的文档（Platform Compatibility 章节、README 示例）转换为 WorkBuddy 可用。

## 何时不触发

在以下情况不要使用此 Skill：

- 只是运行某个 Skill 的业务工作流，并不涉及它的跨工具兼容性；
- 只是与 Skill 可移植性无关的日常代码修改。
