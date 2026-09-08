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

## 退出码与恢复

`link`、`link-location`、`convert`、`sync`、`rollback`、`rename` 和 `repair-agent-install` 返回退出码 **2** 时，表示变更已成功、报告刷新失败（`report_status: stale`）。此时只运行返回的 `report_retry_command`；不要因为 shell 显示非零退出码就重复变更。退出码 0 表示命令与报告刷新均已完成。

对于只读的 `relationships --strict`，退出码 **2** 表示新报告中存在问题或未关联副本。健康的 `project-only` 和 `synced` 均可通过；不加 `--strict` 时，发现的问题只记录在 JSON 中，不因此返回非零退出码。校验或执行错误会另行失败并给出错误信息。

使用 `rollback <sync-id> --snapshot <repair-snapshot-id> --roles local` 恢复安装修复快照，也支持只通过 location 登记的安装。它只恢复对应安装；对相同内容重复回滚不会创建新快照。若安装恢复失败，请保留错误中列出的 staging 目录和快照路径以便恢复。

随 Skill 分发的[契约校验器](scripts/validate_skill_relationship_report.py)是报告运行时契约的权威实现，仅依赖 Python 标准库。[JSON Schema](references/skill-relationships.schema.json)用于互操作文档；运行时只读取其中共享的状态词汇，不执行 Draft 2020-12 约束。校验器和 schema 均包含在 Skill 内，安装产物生成报告无需依赖仓库 CLI。
