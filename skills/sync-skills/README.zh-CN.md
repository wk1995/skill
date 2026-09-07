# 同步 Skills

语言：[English](README.md) | **中文**

`sync-skills` 用于管理同一个 Agent Skill 在仓库、项目、本机 Agent 安装目录、Agent 构建产物和明确指定的外部路径中的等价副本。它还会按项目支持的全部 AI Agent Builders 生成本机关系报告，并安全修复身份不完整的 Agent 安装副本。

## 如何使用

请使用每个 `SKILL.md` 中声明的不可变 `metadata.sync_id`，并提供涉及的路径或位置角色以及希望执行的操作。Skill 名称只是展示/触发名称，可以变化而不改变同步组。常见请求包括：

```text
比较 my-skill 的仓库副本和本机副本。
将此 Skill 的仓库副本链接到指定的本机 Skill 目录。
以仓库版本为来源同步项目和外部副本。
```

需要确定性变更时使用随附脚本：

```bash
python skills/sync-skills/scripts/skill_sync.py migrate-state
python skills/sync-skills/scripts/skill_sync.py status my-skill-id
python skills/sync-skills/scripts/skill_sync.py sync my-skill-id --source repo
python skills/sync-skills/scripts/skill_sync.py rename old-skill-name --to my-skill-id --name new-skill-name
python skills/sync-skills/scripts/skill_sync.py relationships
python skills/sync-skills/scripts/skill_sync.py repair-agent-install my-skill-id --agent codex --discard-local-changes
```

运行期 registry 和快照数据默认存放在仓库外、按 checkout 隔离的 XDG state 目录。对于仍有 `.skill-sync/` 旧状态的 checkout，应先运行一次 `migrate-state`；它会完整复制并校验数据、保留源目录，且可安全重复执行。在所有协作者都完成迁移或备份前，不要删除旧目录。

`--to` 仅用于迁移按名称作为键的旧 registry。对于已有稳定同步组，`--to` 必须保持为当前 ID；如需修改展示或触发名称，请使用 `--name`，稳定 ID 不可变。

每个位置使用角色或显式 Location ID。流程会校验 `SKILL.md` 及其稳定的 `metadata.sync_id`，在覆盖前为已有副本创建快照；多份副本发生冲突时会报告而不会自行选择来源，并记录版本、摘要、来源和差异。`relationships` 从 adapter 清单动态发现 Builder，生成的 JSON/Markdown 仅写入仓库外的本机状态目录。完整命令及信任规则见 [SKILL.md](SKILL.md)。

## 何时触发

在以下情况使用此 Skill：

- 需要链接、转换、同步、记录版本、审计、比较或回滚 Skill 副本；
- 涉及同一个 Skill 的仓库、项目、本机用户目录或外部副本；
- 需要处理 Skill 的来源 URL、版本历史、内容摘要、快照或差异报告；
- 需要把仓库内旧版 Skill 同步状态迁移到本机状态目录。
- 需要盘点本机 Skill、项目支持的 Builders、构建产物及显式登记的关联项目；
- 需要修复缺少稳定身份或构建文件不完整的 Agent 安装副本。

## 何时不触发

在以下情况不要使用此 Skill：

- 只是使用某个 Skill 的业务工作流，并不管理它的副本；
- 只是普通代码修改，且不涉及 Skill 同步、转换、审计或回滚。
