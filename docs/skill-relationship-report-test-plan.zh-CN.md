# Skill 关系报告测试计划

## 1. 目标与当前可执行范围

本计划验证 [Skill 关系报告 PRD](skill-relationship-report-prd.zh-CN.md) 和[技术设计](skill-relationship-report-technical-design.zh-CN.md)。测试分两类：

- 已落地的契约测试：固定 report v1 的 JSON 结构、动态 Builder、身份派生链、状态语义、绝对路径、canonical 顺序和派生 summary。
- 已落地的行为测试：adapter resolver、只读扫描、registry 兼容、Markdown 渲染、安全写入、命令接入、stale 语义和 Agent 安装修复；矩阵中标为“部分落地”或“实现阶段”的扩展对抗组合继续作为回归建设项。

仓库现已实现 `relationships`、`link-location` 和 `repair-agent-install`。契约测试与端到端行为测试都进入 CI；没有 skip、expected-failure 或永远失败的占位用例。

当前可直接运行：

```bash
bash tests/skill-relationship-report-contract.sh
bash tests/skill-relationships.sh
```

这些脚本由 `tests/pr-review-gate.sh` 的 `tests/*.sh` 自动发现，无需维护第二份测试列表。实现和测试只使用 Python 标准库，不要求安装 `jsonschema`。

## 2. 测试分层

1. **契约层**：解析 Schema 与固定 fixture，调用语义校验器；验证跨记录不变量和稳定顺序。
2. **单元层**：分别测试 adapter、resolver、registry view、inventory、manifest、graph、renderer 和 writer。
3. **组件层**：在临时 state/project/local roots 中运行一次完整只读报告生成，不接触用户真实目录。
4. **命令集成层**：通过真实 CLI 多次调用，覆盖旧状态、损坏状态、刷新失败和 `--strict`。
5. **变更入口层**：从每个会修改数据的入口追踪 `entry point -> mandatory validation -> first mutation`，验证报告刷新不会削弱原有安全边界。
6. **跨平台与依赖降级层**：macOS/Linux、大小写敏感/不敏感替身、软链接、受控 `PATH` 和缺失 Git。

所有会覆盖、移动、同步、生成或持久化数据的测试都使用 `tempfile`/`mktemp` 创建明确临时根，不使用真实 `~/.codex/skills`、`~/.agents/skills`、用户项目或仓库 `.skill-sync/`。

## 3. 契约测试说明

已提交文件：

- `schemas/skill-relationships.schema.json`：report v1 的机器可读结构契约。
- `scripts/validate_skill_relationship_report.py`：结构与跨记录语义的标准库参考校验器。
- `tests/fixtures/skill-relationships/valid.json`：同时覆盖完整、部分、全部缺失、跨 Builder 版本分歧、本机身份缺失、安装分歧、相关项目和未关联本机 Skill。
- `tests/skill-relationship-report-contract.sh`：正例、动态扩展和 mutation-style 负例。

当前测试明确证明：

- `agent_builds` 是开放的动态 key map，不存在 Codex/WorkBuddy 固定枚举；加入 `zcode` Builder 的数据后不改校验器仍通过。
- 每个 Logical Skill 必须恰好包含全部声明 Builder，Builder ID 不得重复。
- build key、`agent_id`、`build_id` 和 `sync_id` 必须一致。
- local install 只能 `derived_from` 同 Agent 的有效 build。
- 本机安装缺少 `sync_id` 时，install 与 Logical Skill 都有 `missing-sync-id`，不能标为 `synced`。
- 部分构建与跨 Builder core 版本差异必须产生对应状态。
- 不同 Agent 的合法输出 digest 不会被误报为 portable 内容分歧。
- 相对路径、不稳定排序和伪造 summary 会被拒绝。

## 4. 完整测试矩阵

本计划只维护下面一张主矩阵；编号同时用于测试函数/fixture 名称，避免另建重复的验收映射表。

| ID | 层级 / 阶段 | 场景与关键断言 | PRD 验收 |
| --- | --- | --- | --- |
| C01 | 契约 / 已落地 | 固定合法 fixture 通过 Schema 参考校验；报告版本、时间、digest、类型和必填字段有效。 | 2, 3, 4, 9 |
| C02 | 契约 / 已落地 | 动态加入第三个 `zcode` Builder 并为每个 Skill 增加单元格；不修改 Agent 枚举仍通过。重复 Builder 和未声明 Builder 引用失败。 | 13, 16, 18 |
| C03 | 契约 / 已落地 | build 的 map key、Agent、Logical Skill 身份或 local `derived_from` 任一不一致均失败。 | 15, 23 |
| C04 | 契约 / 已落地 | registry 已关联的 local install 缺少 `sync_id` 可以展示，但必须是 `registered-incomplete`，两层都含 `missing-sync-id`，且不能 `synced`。 | 24, 25 |
| C05 | 契约 / 已落地 | 多 Builder core 版本不同而缺少 `agent-version-diverged` 失败；build core 不等于 portable 而缺少 stale 状态失败。 | 14, 15 |
| C06 | 契约 / 已落地 | 仅部分 Builder 有 build 而未标 `agent-build-partial` 失败；所有 Builder 缺失时必须标 missing。 | 13 |
| C07 | 契约 / 已落地 | 所有已解析 path 必须为规范化绝对路径；Skill/Builder/status/source 顺序稳定；summary 必须由明细推导。 | 9, 20 |
| A01 | 单元 / 已落地 | 从临时 `platforms/*/adapter.json` 发现 Codex、WorkBuddy 和第三方 Builder；`dist/` 不能反向声明支持。adapter ID 重复、目录不匹配、manifest 损坏分别报错。 | 13, 16, 17 |
| A02 | 单元 / 已落地 | `home-relative`、可选/必需 `env` resolver；缺失根为 `missing-root`，不可解析为 `unresolved-root`。`--local-root` 可覆盖/补充但不写 adapter。 | 18, 19 |
| A03 | 单元 / 部分落地 | 多 Builder 声明同一根和重复路径时只扫描一次，同时保留所有 Builder 归属；嵌套根和软链接别名组合继续扩充。 | 18, 19 |
| B01 | 单元 / 已落地 | build manifest 的 sync ID、portable digest、core/adapter/artifact 版本、output digest 和相对产物路径全部核对；platform 错配、路径逃逸、重复 Skill 无效。 | 13, 15, 17, 23 |
| B02 | 单元 / 已落地 | v1 manifest 被报告为身份不完整的无效 build，不能作为安装修复可信源；重新 build 生成 v2 后才可用。 | 23, 24, 25 |
| I01 | 单元 / 已落地 | 扫描当前项目全部 portable Skill、本机 roots 全部直接子 Skill、两个逐个登记的项目；未登记父目录中的项目永不进入结果。 | 2, 3, 22 |
| I02 | 单元 / 部分落地 | 缺失 `SKILL.md`、frontmatter 损坏和缺失路径成为 issue/状态且其他 Skill 仍正常生成；扫描中变化的确定性故障注入继续扩充。 | 5, 10 |
| I03 | 单元 / 已落地 | 旧 `roles` registry 在内存映射为等价 locations；只生成报告不改变 registry 字节，多次调用不隐式迁移。 | 8, 12 |
| G01 | 单元 / 部分落地 | 相同 `sync_id` 连接本机、当前项目和两个其他项目；同名不同 ID、同 digest 无 ID、同 URL 不同 ID 的组合继续扩充。 | 3, 6 |
| G02 | 单元 / 部分落地 | 版本相同 digest 不同、版本不同、缺失 copy 和重复 ID 得到状态；同物理目录多 ID及更多不安全路径组合继续扩充。 | 4, 5 |
| G03 | 单元 / 已落地 | `portable -> build -> local` 两段分别比较；跨 Agent digest 不比较；local 与同 Agent build 不同才产生 install divergence。 | 15, 23 |
| R01 | 单元 / 已落地 | Markdown 只有一张常规主表，Builder 动态列顺序与 JSON 一致；列表展示跨项目、未关联本机、问题、扫描来源和完整绝对路径。 | 2, 3, 4, 13, 14, 20 |
| R02 | 单元 / 部分落地 | canonical 顺序与 input fingerprint 已由契约覆盖；固定时间下连续两次 JSON/Markdown 字节对比继续扩充。 | 9 |
| W01 | 单元 / 已落地 | 新建 reports 权限 `0700`、文件 `0600`；临时文件写完、fsync、校验后替换。报告不进入 registry、snapshot 或任何 Skill。 | 7, 8 |
| W02 | 单元 / 部分落地 | 已有报告后注入第二文件 replace 失败，首文件恢复且旧报告完整；JSON staging、fsync 和扫描阶段的独立故障点继续扩充。 | 10 |
| W03 | 对抗 / 部分落地 | 仓库内部 output、软链接 output、FIFO target 和并发 writer 在首次替换前失败；snapshot/registry 交叠、反向包含和 case-only alias 继续扩充。 | 7, 10, 20 |
| CLI01 | 组件 / 已落地 | 命令生成 JSON/Markdown 并输出绝对路径；`--project`、`--output-dir`、`--strict` 生效，底层组件覆盖 `--format` 和 `--local-root`。 | 1, 2, 3, 7, 19 |
| CLI02 | 组件 / 已落地 | 普通报告含诊断仍为 0；`--strict` 生成报告后为 2；运行失败为 1。报告过程不调用 build，不改变 `dist/`。 | 8, 17 |
| CLI03 | 状态化 / 部分落地 | 覆盖首次状态、已有合法报告、旧 registry 和并发刷新失败；已有损坏报告、malformed registry 的连续 CLI 组合继续扩充。 | 9, 10, 12 |
| M01 | 集成 / 部分落地 | 所有 mutation 入口已接入统一刷新，现有命令回归验证其可运行；逐入口的“成功恰好刷新一次、失败不刷新”注入断言继续扩充。 | 1, 8 |
| M02 | 集成 / 已落地 | 先完成一次真实同步，再注入报告刷新失败；Skill 与 registry 保留新状态，旧报告保留，返回 2 并输出 `report_status: stale`、旧路径和重试命令。 | 21 |
| M03 | 集成 / 已落地 | Agent build 成功后输出显式刷新命令；报告自身绝不隐式 build 或覆盖 `dist/`。 | 17, 21 |
| F01 | 安装修复 / 已落地 | 已登记 local 缺身份：没有可信同 Agent manifest v2 时失败关闭，不创建安装结果；只手工补字段仍因 digest/adapter 文件不完整而不算成功。 | 24, 25, 27 |
| F02 | 安装修复 / 已落地 | 有可信 build 时，先验证快照，再 staging 安装和原子替换；最终 sync ID、core 版本、digest、registry 派生来源及报告全部一致。 | 24, 25, 27 |
| F03 | 安装修复 / 已落地 | local 有额外修改时不覆盖，保留现场并提示导出或明确重装；快照/源均可复核。 | 25, 27 |
| F04 | 安装修复 / 已落地 | 修复成功后原参数第二次执行：不产生内容变化、不新增快照，报告仍一致。 | 27 |
| F05 | 安装修复 / 已落地 | 普通 `sync --source repo` 指向或解析到 Agent install 目录时，在 snapshot、清空、复制前失败并提示 build/install 流程。 | 26 |
| X01 | 跨平台 / 实现阶段 | macOS 与 Linux 运行核心测试；在大小写不敏感卷测试 case-only alias。当前卷无法表示时使用受控 identity comparator 替身并在结果中声明限制。 | 11 |
| X02 | 依赖降级 / 实现阶段 | 使用只含 Python/必要系统命令的受控 `PATH` 隐藏 Git；报告仍用 filesystem 时间或明确失败，安全检查不能静默消失。 | 11 |

## 5. Fixture 设计

组件和集成测试统一用一个临时场景工厂，不复制大量目录模板。工厂参数包括：Builder 列表、每个 Builder 的 resolver/build manifest、portable Skill 列表、本机安装列表、显式项目、registry 版本和故障注入点。

基础场景至少包含四个当前项目 Skill：

- `alpha`：所有 Builder 有效 build，Codex local 与 Codex build 一致，两个 Agent 输出 digest 故意不同但整体可 `synced`。
- `beta`：仅一个 Builder 有 build，没有本机安装，得到 partial + project-only。
- `delta`：所有 Builder build 缺失，得到 build missing + project-only。
- `gamma`：多个 Builder build core 版本不同，Codex local 已在 registry 登记但缺少 `sync_id`，且 local digest 与 Codex build 不同。

另含一个已登记相关项目、一个未关联本机 Skill，以及一个位于未登记父目录下的诱饵项目。每个负例只改变一个变量；若故障会同时触发多个安全状态，断言必须检查主要错误及“首次 mutation 尚未发生”。

digest 必须由真实目录内容计算，除纯契约 fixture 外不写死伪摘要。涉及扫描稳定性的测试在 digest 前后替换文件并断言 `scan-unstable`，不依赖不稳定的时间竞态。

## 6. 状态化命令与故障注入

不能只测试全新临时目录的一次 happy path。每个有持久状态的命令至少连续执行：

1. 空状态首次运行。
2. 输入未变的第二次运行。
3. 已有合法 registry/report/snapshot 的运行。
4. 已有 malformed 或身份冲突状态的运行。
5. 在第一处可能写入前、staging 写入后、替换前和替换后分别注入失败。

故障注入优先 patch 文件系统包装函数，不通过真实磁盘耗尽、权限破坏或删除用户目录制造失败。测试结束检查：Skill 输入、registry、snapshot、build 和旧报告的 digest 是否符合该阶段承诺；不能只断言退出码或错误字符串。

## 7. 路径安全矩阵

每个会写入的入口都复用项目 PR review playbook 的身份与包含关系矩阵：完全相同、软链接别名、source 包含 target、target 包含 source、case-only alias、文件/目录/特殊文件、仓库内/外路径。检查必须直接调用真实入口，不能先运行 `--check` 再假设直接命令安全。

根目录扫描还需覆盖顶层和嵌套层级的保留名、ignore 规则、adapter overlay 和排除项。即使首版只扫描根的直接子目录，也要放置嵌套诱饵，证明扫描不会意外扩大范围或递归跟随软链接。

## 8. 验证命令与完成标准

开发过程中至少运行：

```bash
bash tests/skill-relationship-report-contract.sh
python3 scripts/validate_skill_relationship_report.py \
  tests/fixtures/skill-relationships/valid.json
python3 scripts/agent_build.py --check
python3 scripts/skill_catalog.py --check
git diff --check
```

实现进入 PR 完成阶段后，从干净、已提交的工作区运行：

```bash
bash tests/pr-review-gate.sh origin/main
```

“测试完成”必须同时满足：对应矩阵用例已成为可执行测试；所有确认缺陷有回归测试；状态化/对抗性用例实际运行；未覆盖场景及环境原因被明确报告。CI 绿色或 repository gate 绿色本身不是完整审查结论。
