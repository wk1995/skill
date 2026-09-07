# Sync Skills 本机关系与 Agent 构建覆盖报告 PRD

## 1. 文档信息

| 项目 | 内容 |
| --- | --- |
| 状态 | 需求已确认，待实现 |
| 日期 | 2026-09-07 |
| 目标版本 | `sync-skills` 后续版本 |
| PRD 属性 | 本文档提交到项目仓库并随实现接受评审 |
| 生成报告属性 | `skill-relationships.md/json` 仅保存在本机，不进入 Git 仓库 |
| 关联背景 | `sync-skills` 外置状态目录与跨项目 Skill 管理 |
| 技术设计 | [Skill 关系报告技术设计](skill-relationship-report-technical-design.zh-CN.md) |
| 测试计划 | [Skill 关系报告测试计划](skill-relationship-report-test-plan.zh-CN.md) |
| 数据契约 | [Skill 关系报告 JSON Schema](../schemas/skill-relationships.schema.json) |

## 2. 背景与问题

`sync-skills` 当前能通过 `sync_id` 管理同一个 Skill 在 `repo`、`local`、`project`、`external` 等位置的副本，但同步完成后缺少一份适合人直接阅读的全局关系文档。

用户需要快速回答以下问题：

1. 本机安装了哪些 Skill？
2. 当前项目中的每个 Skill 对应哪个本机 Skill？
3. 当前项目的 Skill 还与哪些其他项目关联？
4. 各副本是否同步，版本和内容摘要是否一致？
5. 哪些本机 Skill 尚未与当前项目建立关系？
6. 哪些已登记关系已经失效、冲突或存在安全问题？
7. 当前项目为哪些 AI Agent 生成了各个 Skill，例如 Codex、WorkBuddy？
8. 一个 Skill 是两个 Agent 都有、仅其中一个有，还是两个 Agent 都缺失？
9. 同一个 Skill 在不同 Agent 构建中的 core 版本是否一致？

## 3. 产品目标

### 3.1 必须实现

- 每次成功执行 `sync` 后，自动刷新一份本机 Markdown 关系文档。
- 提供独立命令，允许不执行同步也能重新扫描并生成关系文档。
- 展示配置范围内的全部本机 Skill，包括尚未关联当前项目的 Skill。
- 本机 Skill 扫描范围由当前项目支持的 AI Agent Builders 各自声明的本机 Skill 目录自动组成。
- 展示当前项目的全部 Skill，包括没有本机副本的 Skill。
- 展示当前项目 Skill 与多个其他项目 Skill 的关联。
- 按当前项目动态发现的 Agent adapter，展示每个 Skill 的 Agent 构建覆盖矩阵。
- 区分“全部 Agent 都有”“仅部分 Agent 有”“全部缺失”和“不同 Agent 构建使用不同 core 版本”。
- 分别展示 Skill core 版本、adapter 版本和构建产物版本，避免把三类版本混为一谈。
- 使用不可变 `metadata.sync_id` 作为正式匹配依据。
- 展示名称、版本、内容摘要、路径、项目、角色、更新时间和同步状态。
- 报告失效路径、重复 `sync_id`、名称相同但 ID 不同、版本分歧和内容分歧。
- 文档及其中间数据只写入仓库外的本机状态目录。
- 文档写入必须原子化；失败时保留上一份完整文档，不留下半份文件。

### 3.2 本期不实现

- 不扫描整块磁盘寻找 Skill。
- 不扫描项目父目录批量发现关联项目；其他项目必须逐个显式登记。
- 不自动把“名称相同”的 Skill 建立为正式关系。
- 不因生成报告而自动覆盖或同步任何 Skill。
- 不把本机绝对路径、用户名或项目关系提交到 Git。
- 不提供报告分享或路径脱敏模式；本机报告直接展示完整绝对路径。
- 不提供云端关系中心、多人共享或 Web UI。
- 不在本需求中清理 Git 历史里已有的机器路径。

## 4. 核心概念

| 概念 | 定义 |
| --- | --- |
| Logical Skill | 由不可变 `sync_id` 标识的逻辑 Skill。 |
| Skill Copy | Logical Skill 在一个具体路径中的物理副本。 |
| Portable Source Copy | 当前项目 `skills/<skill>/` 中的跨 Agent 源目录。 |
| Local Installed Copy | 本机 Agent Skill 根目录中的已安装副本，例如 Codex 或其他 Agent 的用户级 Skill；它通常由对应 Agent Build Copy 生成，不是 Portable Source Copy 的原样复制。 |
| Current Project Copy | 当前执行目录所属项目中的 Skill 副本。 |
| Related Project Copy | 显式登记的其他项目中的 Skill 副本。 |
| Relationship | 多个 Skill Copy 因具有同一 `sync_id` 而属于同一个 Logical Skill。 |
| Inventory Root | 由受支持 Agent Builder 声明或由用户显式补充的本机 Skill / 项目 Skill 根目录。 |
| Agent Target | 由 `platforms/<agent>/adapter.json` 声明的构建目标，例如 `codex`、`workbuddy`。 |
| Agent Build Copy | 某个 Logical Skill 针对一个 Agent Target 生成的产物，以 `.agent-build.json` 为清单依据。 |
| Core Version | portable `SKILL.md` 中的 `metadata.version`，描述跨 Agent 的 Skill 行为版本。 |
| Adapter Version | `platforms/<agent>/adapter.json` 的 `version`，描述该 Agent 的适配规则版本。 |
| Artifact Version | adapter 的 `artifact_version`，描述该 Agent 可安装包的发布版本。 |

关系是多点连接，不是一对一映射：

```text
Logical Skill: demo
├─ Portable source: ./skills/demo
│  ├─ Codex build: dist/codex/skills/demo
│  │  └─ Codex local install: ~/.codex/skills/demo
│  └─ WorkBuddy build: dist/workbuddy/demo
│     └─ WorkBuddy local install: <adapter-resolved-root>/demo
├─ Project A: /projects/app-a/.agents/skills/demo
└─ Project B: /projects/app-b/skills/demo
```

## 5. 用户故事

### 5.1 同步后查看关系

作为 Skill 维护者，我执行 `sync demo --source repo` 后，希望命令输出关系文档路径，并能立即看到 `demo` 在本机、当前项目和其他项目中的版本与同步状态。

### 5.2 查看完整本机清单

作为本机用户，我希望关系文档列出配置根目录下的全部 Skill，即使某个 Skill 尚未登记到当前项目，也应出现在“未关联本机 Skill”章节。

### 5.3 发现跨项目分歧

作为多个项目的维护者，我希望看到同一个 `sync_id` 在 Project A 与 Project B 中版本相同但内容摘要不同，并获得可执行的 `status` 或 `diff` 建议，而不是被自动覆盖。

### 5.4 修复失效关系

作为使用者，我希望文档明确指出已登记但路径不存在、`SKILL.md` 缺失或 `sync_id` 冲突的关系，并且报告生成过程不修改任何 Skill。

### 5.5 查看 Agent 构建覆盖与版本差异

作为项目维护者，我希望按 Skill 查看当前项目支持的所有 AI Agent Builders 的构建覆盖。对于任意 Skill，可能全部受支持的 Builder 都有构建、仅部分 Builder 有构建或全部没有构建；如果多个 Builder 都有构建但使用的 Skill core 版本不同，报告必须突出显示版本分歧，而不能只显示“已构建”。Codex 和 WorkBuddy 只是当前项目的示例；新增 Agent adapter 后，该 Builder 应自动成为矩阵中的新列，不需要修改关系报告代码中的固定列表。

### 5.6 修复本机安装副本身份缺失

作为使用者，当 registry 已关联某个本机 Agent Skill，但本机 `SKILL.md` 缺少 `metadata.sync_id` 时，我希望报告说明它属于旧版或不完整的 Agent 安装产物，展示对应的可信构建来源，并给出“备份、重新构建、重新安装、验证”的修复建议，而不是让我手工只补一个字段或用 portable 源目录直接覆盖 Agent 安装目录。

## 6. 功能需求

### 6.1 关系发现范围

系统从四类来源构建关系图：

1. **现有 registry**：读取已经登记的角色、路径、URL、版本历史与最近同步状态。
2. **本机 Inventory Roots**：读取当前项目支持的每个 AI Agent Builder 所声明的本机 Skill 目录并扫描其并集；例如 Codex adapter 可声明 Codex 的用户级 Skill 目录。用户显式传入的目录只作为补充或覆盖。
3. **项目 Inventory Roots**：扫描当前项目的 `skills/`，以及用户逐个显式登记的其他项目 Skill 根目录。不得配置父目录批量发现项目，也不得把父目录下的仓库自动纳入关系图。
4. **Agent adapter 与构建清单**：动态扫描当前项目 `platforms/*/adapter.json`，并读取已配置构建输出中的 `.agent-build.json`；不得把 `codex`、`workbuddy` 写死为唯一支持列表。关联项目如显式登记了 adapter root，也使用同一规则扫描；未登记时显示为 `unknown`，不得根据目录名猜测。

“全部本机 Skill”定义为：当前项目全部受支持 Agent Builders 所声明的本机 Skill 目录，加上用户显式补充的 Inventory Roots，其中能够识别的全部 Skill；不是整个文件系统中的所有目录。

扫描规则：

- 默认只检查根目录的直接子目录；扩展布局必须由适配器声明。
- 每个自动发现的本机根目录必须保留 `agent_id`，使报告能够区分 Skill 安装于哪个 Agent Builder；同一路径由多个 Builder 声明时按文件系统身份去重，但保留全部 Builder 归属。
- adapter 声明的目录无法解析或不存在时，记录 `unresolved-root` 或 `missing-root`，不得静默忽略对应 Builder。
- 不递归跟随目录软链接；软链接作为单独 Copy 记录，并解析真实路径用于去重和安全检查。
- 每个候选目录必须包含可读取的 `SKILL.md`。
- 缺少 `metadata.sync_id` 的 Skill 可以展示，但状态必须是 `missing-sync-id`，不能自动关联。
- 路径比较同时使用规范化路径和文件系统身份，处理软链接及大小写别名。

### 6.2 匹配优先级

正式关系只按以下顺序确定：

1. 相同且合法的 `metadata.sync_id`。
2. 已有 registry 中显式登记的同一 Logical Skill。

以下情况只生成提示，不自动建立关系：

- 名称相同但 `sync_id` 不同；
- 目录名相同但缺少 `sync_id`；
- URL 相同但 `sync_id` 不同；
- 内容摘要相同但没有稳定 ID。

### 6.3 多项目关系模型

当前单一 `project` 角色不足以表达多个项目。后续 registry 需要允许一个 Logical Skill 拥有多个带唯一 ID 的位置，例如：

```json
{
  "locations": {
    "local:codex": {
      "kind": "local",
      "path": "/Users/example/.codex/skills/demo"
    },
    "repo:current": {
      "kind": "project",
      "project_id": "personal-skills",
      "path": "/projects/skill/skills/demo"
    },
    "project:app-a": {
      "kind": "project",
      "project_id": "app-a",
      "path": "/projects/app-a/.agents/skills/demo"
    }
  }
}
```

兼容要求：旧 registry 的 `roles` 继续可读，并在内存中转换成 location 视图；只有发生明确的 registry 更新操作时才持久化新结构。

Agent 构建不是普通同步 Copy：同一个 Agent Build Copy 仍归属于对应的 Logical Skill，但其 identity 由 `sync_id + agent_id` 确定；名称只用于展示和诊断。建议派生报告结构如下：

```json
{
  "sync_id": "sync-skills",
  "core_version": "0.1.0",
  "agent_builds": {
    "codex": {
      "present": true,
      "core_version": "0.1.0",
      "adapter_version": "1.0.1",
      "artifact_version": "0.1.0",
      "digest": "3866fe4c"
    },
    "workbuddy": {
      "present": false
    }
  }
}
```

### 6.4 Agent 构建覆盖与版本判定

- 当前项目支持的 AI Agent Builder 种类以 `platforms/<agent>/adapter.json` 为唯一事实来源。不要再维护第二份手写 Builder 列表，也不要把已生成的 `dist/` 当成“项目支持”的声明。
- 每个有效 adapter 清单至少记录 `id`、`version`、`artifact_version`、`skills_path`，并通过 `local_skill_roots` 或等价的 adapter resolver 声明该 Builder 的本机 Skill 安装目录；目录名必须与 `id` 相同，`id` 在项目内唯一。
- adapter 中的本机目录声明必须使用用户主目录、环境变量或产品配置解析规则，不得把某台机器的用户名或绝对路径提交到仓库；解析后的绝对路径只写入本机派生报告。
- 本机 Inventory Roots 默认等于所有受支持 Builder 的 `local_skill_roots` 并集。`--local-root AGENT=PATH` 只用于覆盖无法自动解析的安装位置或补充非标准安装，不取代 adapter 驱动的默认发现。
- 关系报告把这些清单派生为项目级 `agent_builders` 列表；例如当前项目会得到 `codex`、`workbuddy`。将来新增 `platforms/claude/adapter.json` 后，下一次生成报告会自动出现 `claude`，不需要修改关系报告代码或注册中心。
- `.agent-build.json` 只记录“实际上构建了什么”，不能反向声明“项目支持什么”。因此即使 `dist/workbuddy` 不存在，WorkBuddy 仍是已支持但尚未生成产物的 Builder。
- 关联项目可以在本机外置 registry 中显式登记 `adapter_root`。能读取时展示其 Builder 列表；无法读取或未登记时标记 `unknown`，不影响当前项目报告生成。
- 已生成产物必须通过对应输出根目录的 `.agent-build.json` 识别；目录存在但清单缺失或损坏时，不得当作有效构建。
- 每个 Skill × Agent 单元格至少记录：是否存在、core 版本、adapter 版本、artifact 版本、构建 digest 和产物路径。
- `agent-build-complete`：所有已发现 Agent Target 都有该 Skill 的有效构建，且各构建的 core 版本与当前项目 portable core 版本一致。
- `agent-build-partial`：至少一个 Agent 有有效构建，至少一个 Agent 缺失。
- `agent-build-missing`：所有已发现 Agent 均没有该 Skill 的有效构建。
- `agent-version-diverged`：两个或更多 Agent 构建都有该 Skill，但它们记录的 core 版本不同；同时列出各 Agent 的版本。
- `agent-build-stale`：Agent 构建的 core 版本与当前项目 portable core 版本不同，即使各 Agent 构建之间版本一致也必须提示。
- `agent-build-invalid`：清单损坏、清单 platform 与目录不一致、Skill 重复或产物路径不安全。
- 不直接比较不同 Agent 的构建 digest 来判定内容分歧，因为 adapter overlay 天然会让 Codex 与 WorkBuddy 产物不同。digest 只在同一 Agent 的两次构建、已安装副本与对应构建产物之间比较。
- 关系报告是只读盘点；发现缺失或分歧时提供对应 `agent_build.py` 命令，但不得为了生成报告而隐式构建或覆盖 `dist/`。
- Markdown 默认只使用一张 Skill 主表。每个已发现 Builder 生成一个动态列，其他摘要、异常详情与扫描来源使用紧凑列表，避免重复维护“关系表”和“构建覆盖表”。

项目级派生记录示例：

```json
{
  "project_id": "personal-skills",
  "agent_builders": [
    {
      "id": "codex",
      "adapter_version": "1.0.1",
      "artifact_version": "0.1.0",
      "local_skill_roots": ["/Users/example/.codex/skills"],
      "source": "platforms/codex/adapter.json"
    },
    {
      "id": "workbuddy",
      "adapter_version": "1.0.1",
      "artifact_version": "0.1.0",
      "local_skill_roots": ["/configured/workbuddy/skills"],
      "source": "platforms/workbuddy/adapter.json"
    }
  ]
}
```

### 6.5 Portable、构建产物与本机安装副本的分层比对

同一个 Logical Skill 的正确派生链为：

```text
Portable Source Copy
  -> Agent Build Copy（应用 adapter 与 per-Skill overlay）
    -> Local Installed Copy（安装到该 Agent 的本机 Skill 目录）
```

比对与修复规则：

- Portable Source Copy 与 Agent Build Copy 通过 build manifest 中记录的 `sync_id`、core 版本、portable source digest、adapter ID、adapter 版本和 artifact 版本核对。
- Local Installed Copy 只与同一 `agent_id` 的 Agent Build Copy 比较版本和规范化内容 digest。不得把它的原始目录 digest 直接与 Portable Source Copy 比较，因为 Agent overlay、安装布局和 Agent 专属文件会产生合法差异。
- registry 中的本机位置必须记录 `agent_id` 和派生来源，例如 `derived_from: build:codex`；旧 registry 缺少该字段时，可根据已登记角色与受支持 Builder 的安装根目录生成待确认的内存映射，不静默持久化猜测结果。
- 本机副本缺少 `metadata.sync_id` 时标记 `missing-sync-id`。若 registry 已将该绝对路径登记到一个 Logical Skill，可继续展示为“已登记但身份不完整”，但不得仅凭名称为未登记路径建立新关系。
- 存在可信且有效的同 Agent 构建产物时，建议修复流程为：快照本机安装副本、重新构建、从该 Agent 构建产物原子安装、验证 `sync_id` / core 版本 / digest、刷新 registry 与关系报告。
- 不得只在本机 `SKILL.md` 中手工补 `sync_id` 后宣告修复完成；同一副本可能还缺少 triggering metadata、Agent adaptation 或其他新文件。
- 普通 `sync --source repo` 必须拒绝直接覆盖标记为 Agent 安装产物的本机目录，并提示使用对应 Agent build/install 流程。
- 本机安装副本相对对应构建产物存在额外修改时，标记 `agent-install-diverged`，保留本机副本并要求明确选择“导出本机修改”或“从可信构建重新安装”，不得自动覆盖。
- 任何重新安装都必须先创建可回滚快照；重复执行修复应幂等，第二次不得产生内容变化。

### 6.6 状态计算

每个 Logical Skill 生成一个汇总状态：

| 状态 | 条件 |
| --- | --- |
| `synced` | 所有存在的已关联 Copy 具有相同版本和内容摘要。 |
| `content-diverged` | 版本相同但内容摘要不同。 |
| `version-diverged` | 版本不同。 |
| `missing-copy` | registry 中存在路径，但磁盘副本不存在。 |
| `missing-sync-id` | `SKILL.md` 没有合法 `metadata.sync_id`。 |
| `identity-conflict` | 同一路径或同一物理目录被登记到多个 `sync_id`。 |
| `unsafe-path` | Copy 路径相同、互相嵌套或存在其他安全冲突。 |
| `unlinked-local` | 本机 Inventory 中存在，但未与当前项目关联。 |
| `project-only` | 当前项目存在，但没有已知本机副本。 |
| `agent-build-partial` | Skill 仅在部分已发现 Agent Target 中有有效构建。 |
| `agent-version-diverged` | 同一 Skill 在不同 Agent 构建中的 core 版本不同。 |
| `agent-build-stale` | Agent 构建的 core 版本落后或超前于当前项目 portable core。 |
| `agent-build-invalid` | Agent 构建清单或产物身份无效。 |
| `agent-install-diverged` | 本机 Agent 安装副本与同 Agent 的有效构建产物内容不同。 |

状态优先级为：安全/身份错误 > 构建无效 > 缺失身份 > 安装产物分歧 > core/Agent 版本分歧 > 构建覆盖不全 > portable 内容分歧 > 已同步。

### 6.7 生成时机

- `sync` 成功并保存 registry 后，自动刷新关系文档。
- `link`、`convert`、`rename`、`rollback` 成功后也应刷新，因为这些操作会改变关系或状态。
- 提供只读命令手动刷新：

```bash
python3 skills/sync-skills/scripts/skill_sync.py relationships
```

- 手动命令不得修改 Skill、registry 或 snapshot，只更新派生报告。
- Agent 构建成功后也应刷新关系文档；如果 builder 与关系报告解耦，至少应输出可直接执行的 `relationships` 刷新命令。
- 同步已完成但报告刷新失败时，不得伪装为整体成功：命令必须明确输出 `report_status: stale`、上一份报告路径和可重试命令；不得回滚已经完成的 Skill 同步。

### 6.8 本机存储与隐私

默认产物：

```text
<external-state-directory>/
├── registry.json
├── snapshots/
└── reports/
    ├── skill-relationships.json
    └── skill-relationships.md
```

- JSON 是机器可读的派生数据，Markdown 是面向用户的展示文档。
- 两者都不作为 registry 的第二份事实来源，可以随时重新生成。
- 文件默认权限为 `0600`，`reports/` 默认权限为 `0700`。
- 报告直接展示完整绝对路径，包括路径中的本机用户名；产物仅限本机用户读取，因此本期不提供 `--redact-paths`。
- 使用临时文件写完并校验后再原子替换正式文件。
- 报告不得进入 Skill snapshot，也不得被 `sync` 复制到任何角色目录。
- 输出路径必须拒绝指向仓库内部、Skill 目录内部、registry 或 snapshot 目录。

## 7. 命令接口草案

### 7.1 生成关系文档

```bash
python3 skills/sync-skills/scripts/skill_sync.py relationships \
  --local-root codex=/Users/example/.codex/skills \
  --project app-a=/projects/app-a/.agents/skills
```

建议参数：

| 参数 | 说明 |
| --- | --- |
| `--local-root AGENT=PATH` | 覆盖或补充指定 Builder 由 adapter 声明的本机 Skill 根目录，可重复；默认无需传入。 |
| `--project NAME=PATH` | 增加一个关联项目 Skill 根目录，可重复。 |
| `--format markdown\|json\|both` | 默认 `both`。 |
| `--output-dir PATH` | 覆盖默认 reports 目录，但仍必须位于仓库外。 |
| `--strict` | 发现失效、冲突或不安全关系时返回非零退出码。 |

### 7.2 登记多个项目

建议新增显式位置命令，避免把任意名称塞入旧 `role` 字段：

```bash
python3 skills/sync-skills/scripts/skill_sync.py link-location demo \
  --location-id project:app-a \
  --kind project \
  --project-id app-a \
  --path /projects/app-a/.agents/skills/demo
```

## 8. 生成的关系文档示例

以下内容是未来 `skill-relationships.md` 的建议完整结构。

---

# 本机 Skill 关系表

- 生成时间：2026-09-07T08:30:00Z
- 当前项目：`personal-skills`
- 项目路径：`/projects/skill`
- 数据范围：2 个受支持 Builder 声明的本机根目录、当前项目、2 个关联项目
- 项目支持的 Agent Builders：`codex`（adapter `1.0.1`，artifact `0.1.0`）、`workbuddy`（adapter `1.0.1`，artifact `0.1.0`）
- 汇总：本机 Skill 12；当前项目 Skill 4；其他项目 2；构建完整 2；构建部分缺失 1；Builder 版本分歧 1；本机安装分歧 1；关系分歧或错误 2

## Skill 关系与 Agent 构建覆盖

| Sync ID | 当前项目 / 本机 / 其他项目 | Portable core | Codex | WorkBuddy | 汇总状态 |
| --- | --- | --- | --- | --- | --- |
| `sync-skills` | `skills/sync-skills` / `local:codex` / `app-a` | `0.1.0` | core `0.1.0` · adapter `1.0.1` · artifact `0.1.0` | core `0.1.0` · adapter `1.0.1` · artifact `0.1.0` | ✅ `synced` |
| `android-release-train` | `skills/android-release-train` / `local:codex` / `app-a`, `app-b` | `1.2.0` | core `1.2.0` | core `1.1.0` | ⚠️ `agent-version-diverged` |
| `build-pipeline-engineering` | `skills/build-pipeline-engineering` / — / — | `0.3.0` | core `0.3.0` | — | ⚠️ `agent-build-partial`, `project-only` |
| `choose-project-doc-location` | `skills/choose-project-doc-location` / `local:codex` / — | `0.0.1` | build `0.0.1` · local 缺少 `sync_id` | build `0.0.1` | ⚠️ `missing-sync-id`, `agent-install-diverged` |

说明：这是报告中唯一的常规表格，Builder 列由 adapter 动态生成。Codex 与 WorkBuddy 的 digest 不同是正常现象；只有 core 版本差异、同 Agent 新旧 digest 差异或无效清单才触发告警。

## 跨项目明细

### `android-release-train`

- Current project `personal-skills`：`/projects/skill/skills/android-release-train`，core `1.2.0`，digest `a1b2c3d4`，source。
- Local `codex`：`/Users/example/.codex/skills/android-release-train`，core `1.2.0`，digest `a1b2c3d4`，synced。
- Related project `app-a`：`/projects/app-a/.agents/skills/android-release-train`，core `1.2.0`，digest `a1b2c3d4`，synced。
- Related project `app-b`：`/projects/app-b/skills/android-release-train`，core `1.1.0`，digest `9f8e7d6c`，version-diverged。

建议操作：

```bash
python3 skills/sync-skills/scripts/skill_sync.py status android-release-train
python3 skills/sync-skills/scripts/skill_sync.py diff android-release-train --role project:app-b --to-current
```

## 未关联的本机 Skill

- `hatch-pet`：sync_id `hatch-pet`，本机位置 `codex`，core `1.0.0`；如需纳入当前项目，执行 `link-location`。
- `home-assistant`：sync_id `home-assistant`，本机位置 `agents`，core `2.1.0`；当前无需操作。

## 问题与警告

- Error — `demo-a` / `demo-b`：两个 ID 指向同一物理目录；禁止同步，需先修复 identity conflict。
- Warning — `choose-project-doc-location`：registry 已关联 repo 与 `local:codex`，但本机 Codex 副本缺少 `sync_id`，且与 Codex build digest 不同；先快照本机副本，再从可信 Codex build 重新安装并验证。禁止用 portable repo 目录直接覆盖。

## 扫描来源

- Local `codex`：`/Users/example/.codex/skills`，10 个 Skill。
- Local `agents`：`/Users/example/.agents/skills`，2 个 Skill。
- Current project `personal-skills`：`/projects/skill/skills`，4 个 Skill。
- Related projects：`app-a` 2 个 Skill；`app-b` 1 个 Skill。
- Agent adapters：`codex@1.0.1`、`workbuddy@1.0.1`。
- Agent builds：`dist/codex` 4 个 Skill；`dist/workbuddy` 3 个 Skill。

---

## 9. 异常与边界情况

- 一个本机 Skill 同时服务多个项目：只展示一份 Local Copy，并连接到多个 Project Copy。
- 同一项目出现重复 `sync_id`：标记 `identity-conflict`，禁止自动选源。
- Skill 名称改变但 `sync_id` 不变：保持同一关系，并展示 alias。
- 路径不存在：保留 registry 关系，标记 `missing-copy`，不从报告中静默删除。
- `SKILL.md` 无法读取或 frontmatter 损坏：列入问题章节，不中断其他 Skill 的报告生成。
- 文件在扫描过程中变化：该 Copy 标记为 `scan-unstable`，不输出可能错误的 `synced`。
- 报告目标已存在且是软链接、目录或特殊文件：拒绝覆盖并保留旧报告。
- 两个扫描根目录互相嵌套：去重后扫描，禁止重复计数。
- 多个受支持 Builder 声明同一本机 Skill 根目录：只扫描一次，但每个 Skill 保留全部 Builder 归属。
- 受支持 Builder 的本机 Skill 根目录缺失或无法解析：在扫描来源中显示 `missing-root` 或 `unresolved-root`，不得把该 Builder 从统计中移除。
- 大小写不敏感文件系统中的路径别名：按文件系统身份去重。
- 仅 Codex 或仅 WorkBuddy 构建存在：标记 `agent-build-partial`，并明确缺失的 Agent，不视为普通同步失败。
- 两个 Agent 构建都存在但 core 版本不同：标记 `agent-version-diverged`，保留每个 Agent 的实际版本，不自动选择较高版本覆盖。
- 两个 Agent 构建版本相同但 digest 不同：默认合法，因为 adapter overlay 不同；仅与相同 Agent 的预期/历史 digest 比较。
- 新增第三个 adapter：下一次生成报告时自动新增矩阵列，并重新计算完整/部分覆盖，不要求修改固定枚举。
- 产物存在但 `.agent-build.json` 缺失或 platform 不匹配：标记 `agent-build-invalid`，不得通过目录结构猜测版本。
- registry 已关联本机路径但该副本缺少 `sync_id`：展示为“已登记但身份不完整”；只允许从同 Agent 的可信构建产物修复，不得靠名称重新关联。
- portable repo 与本机 Agent 安装副本 digest 不同：先检查中间 Agent build；只要 build 与 portable 来源记录一致且 local 与 build 一致，就不得误报为内容分歧。
- 本机安装副本包含未进入 Agent build 的修改：标记 `agent-install-diverged` 并保留现场，禁止自动重装覆盖。

## 10. 验收标准

1. 成功执行 `sync` 后，命令输出 Markdown 与 JSON 报告的绝对路径。
2. 报告同时包含：全部配置范围内的本机 Skill、当前项目 Skill、显式关联的其他项目 Skill。
3. 同一 `sync_id` 可展示一个本机副本、当前项目副本和至少两个其他项目副本。
4. 未关联本机 Skill 和仅存在于当前项目的 Skill 均有独立状态。
5. 相同版本不同 digest、不同版本、缺失路径、重复 ID 和不安全路径均可识别。
6. 名称相同但 `sync_id` 不同的 Skill 不会被自动关联。
7. 报告只写入仓库外状态目录，权限分别为目录 `0700`、文件 `0600`。
8. 报告生成不会修改 Skill、registry 或 snapshot。
9. 重复生成结果在输入未变化时内容稳定；仅 `generated_at` 等明确的运行元数据允许变化。
10. 写入失败、扫描中途失败或目标冲突时，上一份完整报告保持不变。
11. Linux、macOS 大小写敏感/不敏感路径行为，以及缺少 Git 可执行文件的场景均有测试。
12. 旧 `roles` registry 能生成等价关系文档，不要求用户先手动迁移 schema。
13. 报告按已发现 adapter 为每个当前项目 Skill 展示 Agent 构建矩阵，至少覆盖：Codex 与 WorkBuddy 都有、仅 Codex、仅 WorkBuddy、两者都缺失。
14. Codex 与 WorkBuddy 都有但 core 版本不同的场景标记为 `agent-version-diverged`，并逐 Agent 展示实际版本。
15. 报告分别展示 core、adapter、artifact 三类版本；不同 Agent 的 digest 不会被误判为 portable 内容分歧。
16. 新增 adapter 后，无需修改关系报告的 Agent 枚举即可自动出现在矩阵中。
17. 生成关系报告不会隐式执行 Agent build，也不会修改或覆盖现有 `dist/`。
18. 本机 Skill 默认扫描范围由所有受支持 Agent Builders 声明的本机 Skill 目录并集生成；新增 Builder 后，其目录自动进入扫描范围，无需修改固定目录列表。
19. `--local-root AGENT=PATH` 可以覆盖或补充非标准安装目录；重复、嵌套及软链接别名路径会安全去重并保留 Builder 归属。
20. Markdown 与 JSON 报告展示完整绝对路径且仅限本机用户读取；命令接口不包含路径脱敏选项。
21. Skill 同步成功但报告刷新失败时，保留同步结果并明确输出 `report_status: stale`、上一份报告路径和重试命令，不回滚已完成的同步。
22. 其他项目只有在逐个显式登记后才进入报告；父目录扫描不会自动发现或纳入任何项目。
23. 每个本机 Agent 安装副本按 `portable source -> agent build -> local install` 分层核对，不直接拿 portable 与安装目录的原始 digest 判定分歧。
24. registry 已关联但本机副本缺少 `sync_id` 时，报告显示“已登记但身份不完整”、对应 Agent 构建来源及安全修复建议。
25. 缺少 `sync_id` 的 Agent 安装副本必须通过快照后重新构建/安装来完整修复；仅手工补字段不能得到修复成功状态。
26. `sync --source repo` 直接指向 Agent 安装目录时在首次修改前失败关闭，并提示对应 build/install 命令。
27. Agent 安装修复测试覆盖：缺少身份的负例、快照后修复成功、保留本机修改的冲突路径和重复修复幂等。

## 11. 建议实施顺序

1. 定义 `Project`、`Location`、`AgentTarget`、`AgentBuildCopy` 和关系报告 JSON schema。
2. 扩展 adapter 的本机 Skill 目录声明/解析约定，实现受支持 Builder 驱动的 Inventory Root 发现。
3. 实现 Inventory Root 覆盖配置、路径去重与只读扫描器。
4. 实现 adapter 动态发现与 `.agent-build.json` 只读解析。
5. 实现 portable source、Agent build、本机安装副本的派生来源记录与分层 digest 比对。
6. 将旧 `roles` 转换为兼容的内存 Location 视图。
7. 实现关系图、Agent 构建矩阵、状态计算与冲突检测。
8. 实现稳定 JSON 输出和 Markdown renderer。
9. 实现安全、原子的本机报告写入。
10. 增加 `relationships` 与 `link-location` 命令，并让普通 sync 对 Agent 安装目标失败关闭。
11. 在 `sync`、`link`、`convert`、`rename`、`rollback` 成功后自动刷新，并为 Agent build/install 提供刷新衔接。
12. 补齐状态化、路径安全、跨项目、多 Agent、多次调用、安装修复幂等和缺失依赖测试。
