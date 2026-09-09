# 同步 Skills

语言：[English](README.md) | **中文**

`sync-skills` 用于管理同一个 Agent Skill 在本仓库、其他项目、本机 Agent 安装目录、生成的 Agent 构建产物和明确指定的外部位置中的等价副本。它会记录稳定身份、来源、版本、摘要、快照与审计时间；比较或同步副本；盘点 Builder 关系；并从可信构建修复已登记的 Agent 安装。

## 如何使用

在 Skill 管理仓库中运行随附 CLI：

```bash
python3 skills/sync-skills/scripts/skill_sync.py --help
```

请使用 `SKILL.md` 中不可变的 `metadata.sync_id` 标识 Skill，不要使用目录名或展示名称作为身份。一个同步组可以包含以下位置角色：

| 角色 | 含义 |
| --- | --- |
| `repo` | 本 Skill 仓库中的便携源码，通常位于 `skills/<skill-name>` |
| `local` | 明确路径中的机器级用户副本或 Agent 安装 |
| `project` | 另一个项目工作区拥有的副本 |
| `external` | 其他明确副本，例如插件 checkout 或 staging 目录 |

仓库外的位置请使用绝对路径。不要登记符号链接、重复登记同一物理目录，也不要登记互相嵌套的路径。

### 创建或扩展同步组

登记便携仓库副本和等价的物理副本：

```bash
python3 skills/sync-skills/scripts/skill_sync.py link my-skill-id \
  --name my-skill \
  --repo skills/my-skill \
  --local /absolute/path/to/my-skill \
  --skill-url https://github.com/example/my-skill \
  --repo-url https://github.com/example/skills
```

当一个同步组需要额外的命名项目、本机 Agent 安装或外部位置时，使用 `link-location`：

```bash
python3 skills/sync-skills/scripts/skill_sync.py link-location my-skill-id \
  --location-id project:app-a \
  --kind project \
  --project-id app-a \
  --path /projects/app-a/skills/my-skill
```

`link` 和 `link-location` 只登记关系，不会让存在差异的副本自动变成一致。选择同步来源前，请先运行 `status`。

### 转换现有副本

使用 `convert` 将经过校验的来源物化到新位置，并同时登记两处位置：

```bash
python3 skills/sync-skills/scripts/skill_sync.py convert my-skill-id \
  --source-path /absolute/path/to/my-skill \
  --source-role local \
  --target-path skills/my-skill \
  --target-role repo
```

来源必须包含有效的 `SKILL.md`。已有目标 Skill 会在替换前创建快照；非 Skill 目标、重叠路径、符号链接、特殊文件或身份冲突都会被拒绝。

### 检查状态、历史与差异

```bash
python3 skills/sync-skills/scripts/skill_sync.py status my-skill-id
python3 skills/sync-skills/scripts/skill_sync.py versions my-skill-id
python3 skills/sync-skills/scripts/skill_sync.py snapshots my-skill-id
python3 skills/sync-skills/scripts/skill_sync.py diff my-skill-id \
  --role local \
  --from-snapshot 20260720T120000Z \
  --to-current
```

- `status` 显示已登记位置、版本、摘要与分歧状态。
- `versions` 显示曾观察到的版本及其创建/更新时间。
- `snapshots` 列出变更前创建的恢复点。
- `diff` 比较快照、当前角色或明确路径，并报告新增、删除、修改的文本及二进制文件。

### 同步与回滚

副本存在差异时，建议明确指定来源：

```bash
python3 skills/sync-skills/scripts/skill_sync.py sync my-skill-id --source repo
```

覆盖前会为所有现有已链接副本创建快照。如果多份副本都发生过变化且未指定来源，同步会停止并报告冲突。在仓库默认分支上，版本不一致时会选择较高的 `metadata.version`；在其他分支上，只有版本不一致并不足以授权同步。

从快照恢复所有已登记角色，或只恢复指定角色：

```bash
python3 skills/sync-skills/scripts/skill_sync.py rollback my-skill-id \
  --snapshot 20260720T120000Z

python3 skills/sync-skills/scripts/skill_sync.py rollback my-skill-id \
  --snapshot 20260720T120000Z \
  --roles local project
```

回滚不会删除选中的快照，并会在替换当前内容前创建新的回滚前快照。

### 重命名但不改变身份

为旧版名称键控 registry 分配第一个稳定 sync ID：

```bash
python3 skills/sync-skills/scripts/skill_sync.py rename old-skill-name \
  --to my-skill-id \
  --name new-skill-name
```

对于已经拥有稳定 ID 的同步组，`--to` 必须等于当前 ID。只使用 `--name` 修改展示/触发名称；现有稳定 sync ID 不可替换。

### 盘点 Builder 关系

生成本机 JSON 和 Markdown 报告：

```bash
python3 skills/sync-skills/scripts/skill_sync.py relationships
python3 skills/sync-skills/scripts/skill_sync.py relationships \
  --project app-a=/projects/app-a/skills \
  --strict
```

支持的 Builder 来自 `platforms/*/adapter.json`，报告不依赖硬编码 Agent 列表。报告遵循 `便携源码 -> 同 Agent 的 manifest-v2 构建 -> 本机安装` 推导链，包含显式登记的项目和多层本机位置，按物理路径去重，并报告构建缺失、身份不完整、内容分歧和冲突。

报告默认写入 checkout 专属的仓库外状态目录。如果使用 `--output-dir`，目标必须位于仓库和所有 Skill 输入树之外。使用 `--strict` 时，新报告只要含有问题或未关联副本就返回退出码 2；健康的 `synced` 与 `project-only` 项会通过。

### 修复已登记的 Agent 安装

先构建当前 adapter 产物，再从可信 manifest-v2 构建修复已登记安装：

```bash
python3 scripts/agent_build.py codex --force
python3 skills/sync-skills/scripts/skill_sync.py repair-agent-install my-skill-id \
  --agent codex
```

默认会保留存在分歧的安装。只有确实希望替换时才添加 `--discard-local-changes`，并且替换前仍会创建快照。修复会检查 Skill 身份、内容和文件执行权限；遇到不同的非空 sync ID 会拒绝操作；可信构建已经安装时可安全重复执行。普通 `sync` 只用于便携副本，绝不能用它把便携源码直接复制进 Agent 安装目录。

### 迁移旧版仓库状态

运行期 registry、快照、报告和锁应放在仓库外、按 checkout 隔离的 XDG 状态目录中。下面的命令会复制并校验旧版 `.skill-sync/` 状态，而不会删除来源：

```bash
python3 skills/sync-skills/scripts/skill_sync.py migrate-state
```

迁移会保留文件权限，拒绝不安全路径和不同的已有目标；对相同目标重复运行时不会产生额外变更。在所有协作者都已迁移或备份，并通过独立变更处理旧目录前，请保留 `.skill-sync/`。

完整操作和信任规则见 [SKILL.md](SKILL.md)；身份、冲突、快照、版本与 Agent 构建策略见[同步模型](references/sync-model.md)。

## 何时触发

在以下情况使用本 Skill：

- 链接、转换、同步、比较、审计或回滚 Skill 副本；
- 涉及同一个 Skill 的仓库、项目、机器级、Agent 构建或明确外部副本；
- 需要稳定身份、来源 URL、版本历史、摘要、快照、审计时间或文件差异；
- 盘点本机 Skills、支持的 Builders、生成构建、Agent 安装或关联项目；
- 修复不完整或存在分歧的已登记 Agent 安装；
- 将旧版仓库内 Skill 同步状态迁移到仓库外。

## 何时不触发

在以下情况不要使用本 Skill：

- 只是使用某个 Skill 的业务工作流，并不管理它的副本或安装；
- 只创建或修改一个 Skill 的行为，不涉及副本管理；
- 普通应用或仓库工作，与 Skill 同步、转换、盘点、修复或回滚无关。

## 退出码与恢复

`link`、`link-location`、`convert`、`sync`、`rollback`、`rename` 和 `repair-agent-install` 返回退出码 **2** 时，表示变更已成功，但报告刷新失败（`report_status: stale`）。此时只运行返回的 `report_retry_command`，不要重复执行变更。退出码 0 表示请求的操作和报告刷新都已完成。

对于只读的 `relationships --strict`，退出码 **2** 表示新生成的报告中存在问题或未关联副本。不加 `--strict` 时，问题仍会保留在报告中，但不改变命令退出状态。

修复快照可通过 `rollback <sync-id> --snapshot <snapshot-id> --roles local` 恢复。若安装恢复失败，请保留返回的 staging 目录和快照路径。随 Skill 分发的[关系报告校验器](scripts/validate_skill_relationship_report.py)是权威的可执行报告契约；[JSON Schema](references/skill-relationships.schema.json)是说明性的互操作文档。运行时校验只读取共享状态词汇，不执行 Draft 2020-12 约束。
