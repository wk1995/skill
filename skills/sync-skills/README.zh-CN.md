# 同步 Skills

语言：[English](README.md) | **中文**

`sync-skills` 用于管理同一个 Agent Skill 在本仓库、项目目录、本机 Codex/ZCode Skill 目录和明确指定的外部路径中的等价副本。它支持链接、转换、比较、同步、版本记录、快照、审计和回滚。

## 如何使用

请提供逻辑 Skill 名称、涉及的路径或位置角色，以及希望执行的操作。常见请求包括：

```text
使用 $sync-skills 比较 my-skill 的仓库副本和本机副本。
将此 Skill 的仓库副本链接到 ~/.codex/skills/my-skill。
以仓库版本为来源同步项目和外部副本。
```

需要确定性变更时使用随附脚本：

```bash
python skills/sync-skills/scripts/skill_sync.py status my-skill
python skills/sync-skills/scripts/skill_sync.py sync my-skill --source repo
```

从其他运行时导入 Skill 之前或之后，都可以校验它是否兼容 ZCode —— 支持已链接的角色组、单个 Skill 目录，也支持整个 Skill 文件夹；`link`、`convert` 和 `sync` 在所链接或来源副本不兼容时也会打印同样的警告：

```bash
python skills/sync-skills/scripts/skill_sync.py check --path ~/.codex/skills
```

每个位置使用一个固定角色：`repo`、`local`、`project` 或 `external`。流程会校验 `SKILL.md`，在覆盖前为已有副本创建快照；多份副本发生冲突时会报告而不会自行选择来源，并记录版本、摘要、来源和差异。完整命令及信任规则见 [SKILL.md](SKILL.md)。

ZCode 副本遵循同样的角色模型：可以链接或同步到 `~/.zcode/skills/`（用户级）或 `~/.agents/skills/`（跨工具共享），必需文件只有 `SKILL.md` —— `agents/openai.yaml` 和 `extensions.yaml` 为 Codex 专用，ZCode 会忽略。

## 何时触发

在以下情况使用此 Skill：

- 需要链接、转换、同步、记录版本、审计、比较或回滚 Skill 副本；
- 涉及同一个 Skill 的仓库、项目、本机 Codex/ZCode/用户目录或外部副本；
- 需要处理 Skill 的来源 URL、版本历史、内容摘要、快照或差异报告。

## 何时不触发

在以下情况不要使用此 Skill：

- 只是使用某个 Skill 的业务工作流，并不管理它的副本；
- 只是普通代码修改，且不涉及 Skill 同步、转换、审计或回滚。
