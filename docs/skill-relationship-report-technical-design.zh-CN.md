# Skill 关系报告技术设计

## 1. 文档信息

- 状态：首版已实现。
- 日期：2026-09-07。
- 对应需求：[Skill 关系报告 PRD](skill-relationship-report-prd.zh-CN.md)。
- 数据契约：[Skill 关系报告 JSON Schema](../schemas/skill-relationships.schema.json)。
- 测试策略：[Skill 关系报告测试计划](skill-relationship-report-test-plan.zh-CN.md)。
- 范围：`sync-skills` 的只读盘点、报告生成、同步后刷新，以及 Agent 安装副本安全修复所需的数据链路。

本文同时描述首版实现边界。当前 `skill_sync.py` 已提供 `relationships`、`link-location` 和 `repair-agent-install`；JSON Schema、独立契约校验器、扫描/渲染模块及端到端测试均已落地。

## 2. 设计原则

1. `metadata.sync_id` 是 Logical Skill 的唯一稳定身份；名称、目录名、URL 和 digest 都不能单独建立正式关系。
2. 当前项目支持的 AI Agent Builders 只从 `platforms/*/adapter.json` 动态发现。Codex、WorkBuddy 以及后续 Builder 在关系代码中没有固定分支或固定列。
3. 正确的可追溯链为 `portable source -> agent build -> local install`。本机安装副本只与同 Agent 的 build 比较，不能直接与 portable 目录比较 digest。
4. registry、adapter、build manifest 和磁盘扫描结果是输入；JSON/Markdown 报告是可删除、可重建的本机派生产物，不成为第二份事实来源。
5. 生成报告是只读盘点。它不构建、不安装、不补 metadata、不修改 registry，也不扫描未显式登记的项目父目录。
6. 所有写入均先验证目标和完整内容，再进行同目录原子替换。刷新失败不能回滚已经成功的同步或构建。
7. JSON 先生成并通过结构与语义校验，Markdown 再从同一个内存模型渲染，避免两份报告口径分裂。

## 3. 组件与数据流

关系报告实现已拆出 `skill_sync.py`，避免继续扩大命令入口文件：

```text
skill_sync.py / agent_build.py
        |
        v
skill_relationships.py           Builder/registry/inventory/build/graph/render/writer
        |
        `-- validate_skill_relationship_report.py  独立结构与语义契约校验
```

实现只依赖 Python 标准库。入口脚本继续可被直接执行；共享模块不依赖调用者先执行单独的 `--check`。首版保持一个内聚模块，后续只有在各子域继续增长时再按上述责任拆包。

一次生成过程固定为：

```text
解析 CLI 与外置状态目录
  -> 验证项目根、输出目录和显式输入
  -> 读取 registry 快照
  -> 动态发现 adapters 和本机根目录
  -> 扫描 portable / local / 显式项目副本
  -> 读取 build manifests
  -> 规范化路径并建立 Logical Skill 图
  -> 计算构建覆盖、安装派生和问题状态
  -> 生成 canonical JSON 内存对象
  -> 契约校验
  -> 渲染 Markdown
  -> 分别原子替换 JSON 与 Markdown
```

扫描期间任何文件发生变化时，对应 Copy 标记 `scan-unstable`；不能使用前后不一致的数据输出 `synced`。实现至少记录每个输入文件扫描前后的 `stat` 身份、大小和纳秒级 mtime，并在 digest 后复核。

## 4. 数据模型

机器可读报告遵循 `schemas/skill-relationships.schema.json`。顶层包含：

- `schema_version`：报告契约版本，首版为 `1`。
- `generated_at`：本次成功生成的 UTC 时间。
- `input_fingerprint`：除 `generated_at` 外，规范化输入模型的 SHA-256；用于证明重复生成是否读取了相同输入。
- `project`：当前项目 ID、项目根与 portable Skill 根，均为规范化绝对路径。
- `agent_builders`：按 Builder ID 排序的动态 Builder 列定义。
- `summary`：从 `skills`、`unlinked_local_skills` 和 `issues` 派生的计数，不接受独立维护的计数。
- `skills`：按 `sync_id` 排序的 Logical Skill。
- `unlinked_local_skills`：未与当前项目建立关系的本机安装副本。
- `issues` 与 `scan_sources`：问题和实际扫描边界。

每个 Logical Skill 保存 portable 当前项目副本、显式登记的位置、每个 Builder 的 build 单元格、每个本机安装副本及汇总状态。portable 和 build 都显式记录 `present`；registry 已登记但路径已消失时保留预期绝对路径并使用 `present: false`，不得静默删掉整个 Logical Skill。`agent_builds` 是开放对象：其 key 集合必须与 `agent_builders[].id` 集合完全一致，包括 `present: false` 的单元格。这样新增 Builder 后矩阵会自动扩列，并可正确重算“完整、部分、全部缺失”。

所有实际路径必须是解析后的规范化绝对路径。无法解析的根目录不伪造路径：记录 resolver 描述和 `unresolved-root`，省略 `path`；一旦存在 `path`，它必须是完整绝对路径。本机报告不提供脱敏字段。

### 4.1 Canonical 顺序

为保证重复生成稳定，写 JSON 前使用以下顺序：

- Builder 按 `id`；Builder 本机根按解析路径或 resolver。
- Logical Skill 按 `sync_id`；alias 按字符串；location 按 `location_id`。
- `agent_builds` key 按 Builder ID；local install 按 `agent_id + path`。
- 未关联本机 Skill 按 `path + agent_ids`。
- issue 按 `severity(error, warning, info) + code + sync_id + agent_id + path`。
- scan source 按 `kind + id + path/resolver`。
- 状态数组去重后按状态代码排序。

序列化固定使用 UTF-8、`ensure_ascii=false`、两空格缩进、对象 key 排序并以换行结尾。`generated_at` 不参与 `input_fingerprint`。输入未变化时，两次报告除 `generated_at` 外必须字节稳定。

### 4.2 结构校验与语义校验

JSON Schema 负责字段、类型、枚举、格式和条件必填；`scripts/validate_skill_relationship_report.py` 负责 JSON Schema 难以表达的跨记录约束：

- Builder ID 唯一，且 Skill 的 `agent_builds` 恰好覆盖全部已声明 Builder。
- build map key、`agent_id`、`build_id` 与 Logical Skill `sync_id` 相互一致。
- build 的 adapter/artifact 版本与对应 Builder 声明一致，portable digest 与源副本一致。
- local install 的 `derived_from` 必须指向同 Agent 且实际存在的可信 build。
- 本机副本缺少 `sync_id` 时，install 和 Logical Skill 都必须包含 `missing-sync-id`，且不能汇总为 `synced`。
- 部分构建、全部缺失、build stale、跨 Builder core 版本分歧必须带正确状态。
- summary 只能由明细重新计算得到。

生成器必须调用同一语义校验逻辑，不能让 CI 校验器与生产写入器各自维护一套规则。当前独立脚本是契约参考实现；后续迁移到共享模块时，CLI 脚本只保留薄包装。

## 5. Adapter 与本机根目录发现

### 5.1 Builder 发现

扫描当前项目直属的 `platforms/*/adapter.json`，仅把通过 adapter 校验的目录加入 `agent_builders`。事实来源是 adapter，不是 `dist/`。因此一个 Builder 没有 build 产物时仍必须出现在矩阵中。

adapter 的目录名必须等于 `id`，ID 必须为小写连字符形式并在当前项目唯一。无效 adapter 产生 `agent-build-invalid` 问题；在普通模式下继续处理其他有效 Builder，在 `--strict` 下报告生成后返回 findings 退出码。

### 5.2 `local_skill_roots` 扩展

当前 adapter 已声明本机安装目录，关系扫描支持以下无副作用的 `local_skill_roots` resolver：

```json
{
  "local_skill_roots": [
    {"type": "home-relative", "path": ".codex/skills"},
    {"type": "env", "name": "WORKBUDDY_SKILLS_ROOT", "required": false}
  ]
}
```

- `home-relative` 相对当前用户主目录解析，`path` 不允许绝对路径或 `..`。
- `env` 读取命名环境变量；值必须解析为绝对路径。变量未设置且 `required: false` 时记录 `unresolved-root`；为必需项时 adapter 无效。
- 不从 adapter 执行 shell 命令，也不导入任意代码 resolver，避免只读报告成为代码执行入口。
- `--local-root AGENT=PATH` 在内存中覆盖或补充对应 Builder 的 resolver 结果；不写回 adapter 或 registry。

未来新增 resolver 类型时，通过 adapter schema 版本扩展统一解析器，不通过 Agent ID 分支实现。若某产品只能从配置文件发现路径，应新增受约束的 `config-file` resolver，明确允许读取的文件、字段格式和失败语义。

同一个物理根可能由多个 Builder 声明。扫描器按规范路径与文件系统身份去重，只读一次，但在每个发现副本上保留全部 `agent_ids`。

## 6. Registry v2 与旧数据兼容

目标 registry 使用 `locations` 替代一组固定 `roles`：

```json
{
  "schema_version": 2,
  "projects": {
    "app-a": {
      "root": "/projects/app-a",
      "skill_roots": ["/projects/app-a/.agents/skills"],
      "adapter_root": "/projects/app-a/platforms"
    }
  },
  "groups": {
    "demo": {
      "sync_id": "demo",
      "locations": {
        "repo:current": {
          "kind": "project",
          "project_id": "personal-skills",
          "path": "/projects/skill/skills/demo"
        },
        "local:codex": {
          "kind": "local",
          "agent_id": "codex",
          "derived_from": "build:codex",
          "path": "/Users/example/.codex/skills/demo"
        }
      }
    }
  }
}
```

其他项目只能由 `link-location` 或等价显式配置逐个写入 `projects`/`locations`；不接受父目录扫描配置。

读取旧 registry 时，在内存中转换：`repo` 映射为 `repo:current`，`project` 映射为一个待命名的显式项目位置，`external` 映射为 `external:<role>`。旧 `local` 若落在唯一 Builder 根目录内，可产生 `agent_id` 候选，但标记为待确认；多个 Builder 共享根或路径不在已声明根内时保持 `agent_id: unknown`。报告生成绝不把推测结果写回 registry。

只有 `link-location`、安装成功或其他明确的 registry 更新命令才持久化 v2。迁移写入前要保留现有字段、快照索引和审计时间；不得借关系报告功能删除仓库内受保护的旧 `.skill-sync/` 状态。

## 7. Build manifest 契约

`.agent-build.json` 已升级为 schema v2，每个 Skill 至少记录：

```json
{
  "name": "demo",
  "sync_id": "demo",
  "core_version": "1.0.0",
  "portable_digest": "<sha256>",
  "output_digest": "<sha256>",
  "path": "skills/demo"
}
```

manifest 顶层继续记录 `platform`、`adapter_version`、`artifact_version` 和 `schema_version`。`path` 必须位于构建输出和 adapter `skills_path` 内，不能通过 `..`、软链接或大小写别名逃逸。manifest platform 必须与输出所属 Builder 一致，Skill 名称与实际目录唯一。

v1 manifest 可用于展示历史 build，但因缺少稳定身份与 portable digest，应标记身份不完整，不能作为覆盖本机安装的“可信 build”。重新执行对应 Builder 后生成 v2 manifest，才可进入自动化修复链。

不同 Builder 的 `output_digest` 不互相比较。只有以下比较有效：

- portable 当前 digest 对 build manifest 的 `portable_digest`；
- 同一 Agent 的 build `output_digest` 对该 Agent local install 的规范化 digest；
- 同一 Agent 两次 build 的输出 digest，用于重现性检查。

## 8. 关系发现与身份判定

扫描只读取五类明确输入：当前 registry、当前项目 `skills/`、已解析的 Builder 本机根、逐个登记的其他项目根、当前项目及显式关联项目的 adapter/build 根。扫描根默认只看直接子目录，除非 adapter 声明另一种受约束布局。

每个候选 Copy 记录规范路径、`lstat/stat` 文件系统身份、Skill metadata、core 版本、digest 和扫描稳定性。软链接不递归跟随：保留链接本身作为发现记录，同时用真实身份去重和检查冲突。路径身份检测覆盖：

- 完全相同路径和软链接别名；
- source/target 任一方向的嵌套；
- 大小写不敏感文件系统上的 case-only alias；
- 文件、目录、软链接与特殊文件；
- 仓库内与仓库外边界。

正式关联顺序只有：合法且相同的 `sync_id`，随后是 registry 已显式登记的 Logical Skill。名称、目录名、URL 或 digest 相同只生成 issue。一个物理目录落入两个 Logical Skill 时是 `identity-conflict`，相关同步和安装入口必须在首次修改前失败关闭。

## 9. 状态计算

状态先在 Copy/Build 单元计算，再汇总到 Logical Skill。计算必须遍历动态 Builder 全集：

1. 无有效 build 为 `agent-build-missing`；部分 Builder 有效为 `agent-build-partial`。
2. 全部 Builder 有效且 core 版本都等于 portable，计入 build complete；无需为正常 Skill 强制额外显示 `agent-build-complete`。
3. 两个以上有效 build 的 core 版本不同，增加 `agent-version-diverged`。
4. 任意 build core 版本不等于 portable，增加 `agent-build-stale`。
5. manifest 损坏、身份不一致或路径越界，增加 `agent-build-invalid`；无效 build 不计入 present。
6. 本机 install 缺少 `sync_id`，在 install 和 Logical Skill 同时增加 `missing-sync-id`；registry 关联只允许继续展示，不能把状态提升为 `synced`。
7. 本机 install 与同 Agent 可信 build digest 不同，增加 `agent-install-diverged`。
8. portable 与显式项目 Copy 再计算 `missing-copy`、`version-diverged`、`content-diverged`、`project-only` 或 `unlinked-local`。

显示主状态时按 PRD 优先级选择：安全/身份错误、构建无效、缺失身份、安装分歧、core/Agent 版本分歧、构建覆盖不全、portable 内容分歧、已同步。JSON 保留全部适用状态；Markdown 主表的“汇总状态”按优先级展示，问题章节保留完整诊断。

## 10. Markdown 渲染

Markdown 只维护一张常规主表：每行一个 Logical Skill，固定列为 Sync ID、位置摘要、portable core 和汇总状态，中间按 `agent_builders` 动态插入 Builder 列。Builder 单元显示 build core/adapter/artifact 版本，以及对应 local install 的身份或 digest 状态。

跨项目明细、未关联本机 Skill、问题和扫描来源使用列表，不再建立重复矩阵。完整绝对路径只在本机报告展示。所有文字由结构化状态映射生成，不能重新解析已渲染 Markdown 得出结论。

## 11. 命令接入

在 `build_parser()` 新增：

- `relationships`：只读扫描后刷新报告，支持 PRD 中的 `--local-root`、`--project`、`--format`、`--output-dir`、`--strict`。
- `link-location`：显式登记一个项目/本机/外部位置；在修改 registry 前完成路径身份与包含关系校验。

`command_relationships()` 只调用 relationship service。`command_sync()`、`command_link()`、`command_convert()`、`command_rename()` 和 `command_rollback()` 在自身 mutation 与 `save_registry()` 成功后调用 `refresh_after_mutation()`。刷新不是 mutation 事务的一部分：

- mutation 失败：返回 `1`，不刷新。
- mutation 成功且报告刷新成功：返回 `0`，输出 `report_status: fresh` 和两个绝对路径。
- mutation 成功但报告刷新失败：保留 mutation，返回 `2`，输出 `report_status: stale`、上一份报告路径、失败原因和可直接重试的 `relationships` 命令。

独立 `relationships` 在成功时返回 `0`；运行失败且未替换旧报告时返回 `1`；`--strict` 生成完整报告但发现 error/配置的 warning 时返回 `2`。自动刷新不启用 `--strict`，否则一般诊断会把已成功 mutation 误报为刷新失败。

`agent_build.py` 成功替换构建目录后调用同一刷新入口。若外置状态尚未初始化，至少输出明确的 `relationships` 命令；若已有 registry/report，则必须尝试刷新。构建已成功但刷新失败时同样返回部分成功码 `2`，不删除新 build。

## 12. 报告写入安全

默认目录为 `<external-state-directory>/reports`。在创建目录或临时文件前，验证：

- 输出目录不在仓库、任何 Skill、registry 文件或 snapshots 目录内部；反向包含也拒绝。
- 目标 JSON/Markdown 不存在，或是同一用户拥有的普通文件；软链接、目录和特殊文件一律拒绝。
- 输出目录的每个既有父节点都不是意外软链接；使用解析路径和文件系统身份复核。
- JSON 与 Markdown 目标互不相同，大小写不敏感别名也视为相同。

创建 `reports/` 后设置 `0700`。在该目录分别创建不可预测名称的临时普通文件，写入完整内容、`flush + fsync`、设置 `0600`、重新读取并校验，再用 `os.replace` 替换目标，最后 fsync 目录。异常时只删除本次临时文件，保留上一份正式报告。

JSON 和 Markdown 是一对输出。先完成两份 staging 与校验，再依次替换；如果第一份替换后第二份失败，保留 input fingerprint 不一致诊断并返回 stale，下一次刷新重建两份。后续若需要严格的双文件原子可见性，可改为版本目录加单一 current 指针，但首版不引入该复杂度。

并发刷新使用外置状态目录内的独占锁。等待超时不强杀持锁进程；返回 stale/运行失败并保留旧文件。锁文件不是报告内容，也不进入 snapshot。

## 13. 本机安装身份修复

`missing-sync-id` 不是“补一行 frontmatter”问题。修复入口必须执行：

1. 确认 registry 已明确关联路径、Agent ID 和 Logical Skill；名称相同不足以确认。
2. 校验同 Agent 的 manifest v2 build，其 `sync_id`、portable digest、版本和路径全部可信。
3. 比较 local 与 build。若 local 有 build 外修改，标记 `agent-install-diverged`，只输出“导出本机修改”或“放弃修改后重装”的显式选择，不覆盖。
4. 在外置 snapshots 下创建包含本机完整副本、路径、版本、digest、权限和 build 来源的快照，并复核快照。
5. 将可信 build 安装到同父目录 staging，复核 `sync_id`、core 版本和 digest 后原子替换。
6. 更新 registry 的 `agent_id`、`derived_from` 与审计记录，再刷新报告。
7. 再次执行修复时检测 local 已与 build 一致，不新建快照、不产生内容变化，返回幂等成功。

普通 `sync --source repo` 在目标属于 Builder 本机根或 registry 标记为 Agent install 时，必须在 snapshot、清空或复制之前失败关闭，并提示对应 build/install 命令。portable 源不能直接覆盖 Agent 安装产物。

## 14. 可观测性与隐私

命令输出包含扫描数量、报告绝对路径、`report_status`、input fingerprint、问题计数和重试命令。日志不输出文件正文或环境变量值；本机报告按需求完整显示解析后的绝对路径。

报告不得加入 Git、Skill snapshots 或同步源树。建议在仓库 ignore 规则中只忽略仓库内误生成的同名文件，但 writer 仍必须主动拒绝仓库内输出，不能依赖 `.gitignore` 作为安全边界。

## 15. 实施拆分

1. 已完成：以 Schema、契约校验器和契约测试固定 report v1。
2. 已完成：扩展 adapter 校验并补 Codex/WorkBuddy 声明式本机根。
3. 已完成：将 Agent build manifest 升级为 v2；v1 可识别为旧产物，但不能作为安装修复可信源。
4. 已完成：registry 内存 Location 视图、显式项目登记与动态 Builder/inventory 扫描。
5. 已完成：关系图、状态计算、canonical JSON 和单主表 Markdown。
6. 已完成：安全 writer 与 `relationships` 命令。
7. 已完成：mutation 后刷新、Agent build 刷新提示和 stale 退出语义。
8. 已完成：Agent install 修复入口及其快照、冲突和幂等测试。

每一步合并前都按测试计划增加回归用例；涉及覆盖、移动、同步或安装的入口还必须执行项目 PR review playbook 的路径身份、首次修改前校验、缺失依赖和多次调用检查。

## PR #14 契约与恢复补充

报告运行时以 `skills/sync-skills/scripts/validate_skill_relationship_report.py` 为权威；`references/skill-relationships.schema.json` 是随 Skill 分发的互操作文档及共享状态词汇。根目录 validator CLI 和 schema 引用入口保留兼容。运行时不执行 Draft 2020-12 约束，也不需要第三方 Python 包。

`tests/skill-relationship-regressions.sh` 覆盖完整 manifest 拒绝、身份冲突、报告输出路径矩阵、真实构建产物脱离仓库运行、安装与恢复双故障、repair → rollback → 重复 rollback，以及退出码 2 的变更成功/报告过期语义。健康 `project-only` 不导致 strict 失败。
