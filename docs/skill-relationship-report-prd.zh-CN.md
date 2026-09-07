# Sync Skills 本机关系文档 PRD

## 1. 文档信息

| 项目 | 内容 |
| --- | --- |
| 状态 | Draft，待需求确认 |
| 日期 | 2026-09-07 |
| 目标版本 | `sync-skills` 后续版本 |
| PRD 属性 | 本文档提交到项目仓库并随实现接受评审 |
| 生成报告属性 | `skill-relationships.md/json` 仅保存在本机，不进入 Git 仓库 |
| 关联背景 | `sync-skills` 外置状态目录与跨项目 Skill 管理 |

## 2. 背景与问题

`sync-skills` 当前能通过 `sync_id` 管理同一个 Skill 在 `repo`、`local`、`project`、`external` 等位置的副本，但同步完成后缺少一份适合人直接阅读的全局关系文档。

用户需要快速回答以下问题：

1. 本机安装了哪些 Skill？
2. 当前项目中的每个 Skill 对应哪个本机 Skill？
3. 当前项目的 Skill 还与哪些其他项目关联？
4. 各副本是否同步，版本和内容摘要是否一致？
5. 哪些本机 Skill 尚未与当前项目建立关系？
6. 哪些已登记关系已经失效、冲突或存在安全问题？

## 3. 产品目标

### 3.1 必须实现

- 每次成功执行 `sync` 后，自动刷新一份本机 Markdown 关系文档。
- 提供独立命令，允许不执行同步也能重新扫描并生成关系文档。
- 展示配置范围内的全部本机 Skill，包括尚未关联当前项目的 Skill。
- 展示当前项目的全部 Skill，包括没有本机副本的 Skill。
- 展示当前项目 Skill 与多个其他项目 Skill 的关联。
- 使用不可变 `metadata.sync_id` 作为正式匹配依据。
- 展示名称、版本、内容摘要、路径、项目、角色、更新时间和同步状态。
- 报告失效路径、重复 `sync_id`、名称相同但 ID 不同、版本分歧和内容分歧。
- 文档及其中间数据只写入仓库外的本机状态目录。
- 文档写入必须原子化；失败时保留上一份完整文档，不留下半份文件。

### 3.2 本期不实现

- 不扫描整块磁盘寻找 Skill。
- 不自动把“名称相同”的 Skill 建立为正式关系。
- 不因生成报告而自动覆盖或同步任何 Skill。
- 不把本机绝对路径、用户名或项目关系提交到 Git。
- 不提供云端关系中心、多人共享或 Web UI。
- 不在本需求中清理 Git 历史里已有的机器路径。

## 4. 核心概念

| 概念 | 定义 |
| --- | --- |
| Logical Skill | 由不可变 `sync_id` 标识的逻辑 Skill。 |
| Skill Copy | Logical Skill 在一个具体路径中的物理副本。 |
| Local Copy | 本机 Agent Skill 根目录中的副本，例如 Codex 或其他 Agent 的用户级 Skill。 |
| Current Project Copy | 当前执行目录所属项目中的 Skill 副本。 |
| Related Project Copy | 显式登记的其他项目中的 Skill 副本。 |
| Relationship | 多个 Skill Copy 因具有同一 `sync_id` 而属于同一个 Logical Skill。 |
| Inventory Root | 用户允许扫描的本机 Skill 或项目 Skill 根目录。 |

关系是多点连接，不是一对一映射：

```text
                         ┌─ Local: Codex ~/.codex/skills/demo
Logical Skill: demo ─────┼─ Current project: ./skills/demo
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

## 6. 功能需求

### 6.1 关系发现范围

系统从三类来源构建关系图：

1. **现有 registry**：读取已经登记的角色、路径、URL、版本历史与最近同步状态。
2. **本机 Inventory Roots**：扫描用户配置的 Agent Skill 根目录；默认候选可包括当前 Agent 的用户级 Skill 目录。
3. **项目 Inventory Roots**：扫描当前项目的 `skills/`，以及用户显式登记的其他项目 Skill 根目录。

“全部本机 Skill”定义为：全部已配置 Inventory Roots 中能够识别的 Skill，而不是整个文件系统中的所有目录。

扫描规则：

- 默认只检查根目录的直接子目录；扩展布局必须由适配器声明。
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

### 6.4 状态计算

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

状态优先级为：安全/身份错误 > 缺失 > 版本分歧 > 内容分歧 > 已同步。

### 6.5 生成时机

- `sync` 成功并保存 registry 后，自动刷新关系文档。
- `link`、`convert`、`rename`、`rollback` 成功后也应刷新，因为这些操作会改变关系或状态。
- 提供只读命令手动刷新：

```bash
python3 skills/sync-skills/scripts/skill_sync.py relationships
```

- 手动命令不得修改 Skill、registry 或 snapshot，只更新派生报告。
- 同步已完成但报告刷新失败时，不得伪装为整体成功：命令必须明确输出 `report_status: stale`、上一份报告路径和可重试命令；不得回滚已经完成的 Skill 同步。

### 6.6 本机存储与隐私

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
| `--local-root NAME=PATH` | 增加一个本机 Skill 根目录，可重复。 |
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
- 数据范围：2 个本机根目录、当前项目、2 个关联项目

## 汇总

| 指标 | 数量 |
| --- | ---: |
| 本机 Skill | 12 |
| 当前项目 Skill | 4 |
| 已关联 Logical Skill | 4 |
| 关联的其他项目 | 2 |
| 未关联本机 Skill | 8 |
| 分歧或错误 | 2 |

## 当前项目关系

| Sync ID | 当前项目 | 本机副本 | 其他项目 | 版本 | 状态 |
| --- | --- | --- | --- | --- | --- |
| `sync-skills` | `skills/sync-skills` | `codex:sync-skills` | `app-a` | `0.1.0` | ✅ `synced` |
| `android-release-train` | `skills/android-release-train` | `codex:android-release-train` | `app-a`, `app-b` | `1.2.0 / 1.1.0` | ⚠️ `version-diverged` |
| `build-pipeline-engineering` | `skills/build-pipeline-engineering` | — | — | `0.3.0` | ℹ️ `project-only` |
| `choose-project-doc-location` | `skills/choose-project-doc-location` | `codex:choose-project-doc-location` | — | `0.0.1` | ⚠️ `content-diverged` |

## 跨项目明细

### `android-release-train`

| 位置 | 项目/Agent | 路径 | 版本 | Digest | 状态 |
| --- | --- | --- | --- | --- | --- |
| Current project | `personal-skills` | `/projects/skill/skills/android-release-train` | `1.2.0` | `a1b2c3d4` | source |
| Local | `codex` | `/Users/example/.codex/skills/android-release-train` | `1.2.0` | `a1b2c3d4` | synced |
| Related project | `app-a` | `/projects/app-a/.agents/skills/android-release-train` | `1.2.0` | `a1b2c3d4` | synced |
| Related project | `app-b` | `/projects/app-b/skills/android-release-train` | `1.1.0` | `9f8e7d6c` | version-diverged |

建议操作：

```bash
python3 skills/sync-skills/scripts/skill_sync.py status android-release-train
python3 skills/sync-skills/scripts/skill_sync.py diff android-release-train --role project:app-b --to-current
```

## 未关联的本机 Skill

| Skill | Sync ID | 本机位置 | 版本 | 建议 |
| --- | --- | --- | --- | --- |
| `hatch-pet` | `hatch-pet` | `codex` | `1.0.0` | 如需纳入当前项目，执行 `link-location`。 |
| `home-assistant` | `home-assistant` | `agents` | `2.1.0` | 当前无需操作。 |

## 问题与警告

| 严重级别 | Sync ID | 问题 | 影响 |
| --- | --- | --- | --- |
| Error | `demo-a` / `demo-b` | 两个 ID 指向同一物理目录。 | 禁止同步，需先修复 identity conflict。 |
| Warning | `choose-project-doc-location` | 版本相同但 digest 不同。 | 需要选择可信来源后再同步。 |

## 扫描来源

| 类型 | 名称 | 根目录 | 结果 |
| --- | --- | --- | --- |
| Local | `codex` | `/Users/example/.codex/skills` | 10 个 Skill |
| Local | `agents` | `/Users/example/.agents/skills` | 2 个 Skill |
| Current project | `personal-skills` | `/projects/skill/skills` | 4 个 Skill |
| Related project | `app-a` | `/projects/app-a/.agents/skills` | 2 个 Skill |
| Related project | `app-b` | `/projects/app-b/skills` | 1 个 Skill |

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
- 大小写不敏感文件系统中的路径别名：按文件系统身份去重。

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

## 11. 建议实施顺序

1. 定义 `Project`、`Location` 和关系报告 JSON schema。
2. 实现 Inventory Root 配置与只读扫描器。
3. 将旧 `roles` 转换为兼容的内存 Location 视图。
4. 实现关系图、状态计算与冲突检测。
5. 实现稳定 JSON 输出和 Markdown renderer。
6. 实现安全、原子的本机报告写入。
7. 增加 `relationships` 与 `link-location` 命令。
8. 在 `sync`、`link`、`convert`、`rename`、`rollback` 成功后自动刷新。
9. 补齐状态化、路径安全、跨项目、多次调用和缺失依赖测试。

## 12. 待确认项

1. “全部本机 Skill”的默认扫描根目录是否只包含 `~/.codex/skills` 与 `~/.agents/skills`，还是还要自动读取已安装 Agent adapter 声明的目录？
2. 其他项目是否只展示显式登记的项目，还是允许配置一个父目录批量发现项目？本 PRD 建议只使用显式登记，避免扫描范围过大。
3. 关系文档是否需要隐藏绝对路径中的用户名？本 PRD 默认完整显示，因为文件仅本机可读；如需要分享，可增加 `--redact-paths`。
4. 同步成功但报告刷新失败时，是否接受“同步成功 + 报告 stale”的结果？本 PRD 建议接受并明确告警，避免为派生报告回滚已完成同步。
