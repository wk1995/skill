# Personal Skills

语言：[English](README.md) | **中文**

Personal Skills 是一个用于集中管理个人 Agent Skills 的 monorepo。每个 Skill 独立维护自己的内容和版本；仓库计划统一提供 Skill 管理、CLI、MCP Server 和运行时适配能力，并允许单个 Skill 按需贡献自己的 CLI 命令和 MCP tools。

## 当前状态

- 已完成：仓库定位、通用 Skill 约定、声明式 Codex/WorkBuddy 适配器、确定性 Agent 构建和 PR 校验。
- 规划中：共享管理包、CLI、MCP Server、安装、registry 发布和自动化发布流程。
- 尚未提供：项目级可执行命令。本文中的命令均描述目标接口。

当前适配层和版本边界见 [Agent Build 架构](docs/agent-build-architecture.md)；[最初的仓库设计](docs/superpowers/specs/2026-07-10-skill-management-architecture-design.md)保留为历史背景。

## 设计原则

- **通用核心**：基础 Skill 遵循 [Agent Skills Specification](https://agentskills.io/specification)，不绑定单一 Agent 产品。
- **开放适配器**：从 `platforms/*/adapter.json` 自动发现 Agent；新增默认适配器不需要修改每个 Skill 或中央分支逻辑。
- **独立版本**：通用 Skill、适配器与生成产物分别维护版本生命周期。
- **渐进扩展**：满足仓库管理文件契约后，仅在确有需要时增加脚本、资料、资产、CLI 命令或 MCP tools。
- **一套核心，两种入口**：CLI 和 MCP Server 复用相同的发现、校验、安装、版本和发布逻辑。
- **显式信任**：远程 Skill 的可执行扩展默认禁用，获得明确确认后才能加载。

## 目标目录

以下为规划目录，不代表所有文件和目录均已实现。

```text
skill/
|-- README.md
|-- README.zh-CN.md
|-- skills/
|   `-- <skill-name>/
|       |-- SKILL.md              # 必需：面向 Agent 的通用入口、版本和触发规则
|       |-- README.md             # 必需：英文使用说明
|       |-- README.zh-CN.md       # 必需：中文使用说明
|       |-- CHANGELOG.md          # 必需：通用 Skill 变更
|       |-- agent-builds/         # 必需边界；各 Agent 覆盖按需添加
|       |   `-- codex/
|       |       `-- agents/openai.yaml
|       |-- extensions.yaml       # 可选：CLI/MCP 扩展声明
|       |-- src/                  # 可选：扩展实现
|       |   |-- core.ts
|       |   |-- cli.ts
|       |   `-- mcp.ts
|       |-- scripts/              # 可选：确定性脚本
|       |-- references/           # 可选：按需加载的资料
|       |-- assets/               # 可选：模板与静态资产
|       `-- tests/                # 可选：行为、脚本和扩展测试
|-- platforms/
|   |-- codex/
|   |   |-- adapter.json          # 适配器/产物版本与输出布局
|   |   |-- SKILL.append.md       # Codex 通用生成说明
|   |   `-- root/.codex-plugin/plugin.json
|   `-- workbuddy/
|       |-- adapter.json
|       `-- SKILL.append.md
|-- scripts/
|   `-- agent_build.py            # 自动发现并构建全部平台适配器
|-- packages/                     # 规划中的共享管理运行时
|   |-- core/                     # Skill 发现、校验、安装和版本管理
|   |-- sdk/                      # Skill CLI/MCP 扩展 API
|   |-- cli/                      # 项目级 CLI
|   `-- mcp-server/               # 项目级 MCP Server
|-- schemas/                      # JSON 契约；关系报告已实现，其余仍为规划项
|   |-- skill.schema.json
|   |-- skillset.schema.json
|   |-- extensions.schema.json
|   `-- skill-relationships.schema.json # 已实现的本机报告契约
|-- tests/
|   |-- contract/
|   `-- integration/
|-- .changes/                     # Skill 独立版本变更记录
|-- package.json
|-- pnpm-workspace.yaml
|-- tsconfig.base.json
`-- dist/                         # 构建产物，不提交
```

Agent Skills 规范只要求 `SKILL.md`，但本仓库额外要求双语使用说明、changelog 和 `agent-builds/` 边界；详见 [AGENTS.md](AGENTS.md)。该边界下的平台目录仅在 Skill 需要覆盖时创建。

## Skills

每个 Skill 都有配套 README，说明使用方法、触发条件和不触发条件。此表由 `python scripts/skill_catalog.py --write` 生成，请勿手动编辑表格行。

<!-- skills-catalog:start -->
| Skill | 用途 | 文档 |
| --- | --- | --- |
| `android-code-release-train` | `android-code-release-train` 约束 Android 需求从功能分支、版本集成和发布提升，到形成已评审源码提交及不可变 Tag 的完整代码链路。它不构建、签名、打包或上传发布产物。 | [README](skills/android-code-release-train/README.zh-CN.md) |
| `build-pipeline-engineering` | `build-pipeline-engineering` 用于配置和执行 Android、Windows、Linux 及插件的可复现可分发构建流水线：从一个确定源码引用完成 build variant 选择、安装包格式选择、环境配置、签名、运行依赖处理、安装校验与输出上传。对于支持 variant 的目标，未指定时默认使用 `release`；在 GitHub Actions 中，构建输出默认上传到 GitHub Actions Artifacts。 | [README](skills/build-pipeline-engineering/README.zh-CN.md) |
| `choose-project-doc-location` | `choose-project-doc-location` 为项目文档选择路径，并整理指定文件夹或项目下的文档位置。适用于 PRD、技术文档和机器可读状态机规格文件，不管理它们的业务关联或内容 Schema。 | [README](skills/choose-project-doc-location/README.zh-CN.md) |
| `sync-skills` | `sync-skills` 用于管理同一个 Agent Skill 在本仓库、其他项目、本机 Agent 安装目录、生成的 Agent 构建产物和明确指定的外部位置中的等价副本。它会记录稳定身份、来源、版本、摘要、快照与审计时间；比较或同步副本；盘点 Builder 关系；并从可信构建修复已登记的 Agent 安装。 | [README](skills/sync-skills/README.zh-CN.md) |
<!-- skills-catalog:end -->

本机 Skill 清单与跨项目映射见 [Skill 关系报告 PRD](docs/skill-relationship-report-prd.zh-CN.md)、随仓库维护的[技术设计](docs/skill-relationship-report-technical-design.zh-CN.md)和[测试计划](docs/skill-relationship-report-test-plan.zh-CN.md)。实际生成的关系报告仍只保存在本机；当前机器可读契约见 [skill-relationships.schema.json](schemas/skill-relationships.schema.json)。 报告运行时契约以随 Skill 分发的[校验器](skills/sync-skills/scripts/validate_skill_relationship_report.py)为权威。JSON Schema 用作互操作文档；运行时只使用其共享状态词汇，不执行 Draft 2020-12 引擎。

## Pull Request 审查门禁

在宣布 PR 可以合并前，应从干净且已提交的工作区运行 `bash tests/pr-review-gate.sh origin/main`，并执行 [PR 审查手册](docs/pr-review-playbook.md)规定的独立对抗性检查。GitHub Actions 的 required check `skill-catalog` 会调用同一门禁：检查完整 PR diff 与模拟合并结果、在[协同迁移](docs/skill-sync-state-migration.md)完成前保护旧版 `.skill-sync/` 状态、拒绝预期范围外的已跟踪忽略文件、解析 Python 源码，并运行仓库全部校验测试。新的同步状态默认保存到仓库外的 XDG state 目录。门禁全绿是必要条件，但不能替代路径身份、直接入口、递归规则、依赖降级和失败后状态检查。内部 PR 在配置 `SKILL_CATALOG_TOKEN` 后仍可自动提交生成目录；fork PR 必须自行提交两份根 README。

## Skill 结构与版本

最小受管理 Skill：

```text
skills/example-skill/
|-- SKILL.md
|-- README.md
|-- README.zh-CN.md
|-- CHANGELOG.md
`-- agent-builds/
    `-- .gitkeep
```

`SKILL.md` 同时保存通用元数据、独立版本和可选触发规则：

```yaml
---
name: example-skill
description: Use when the user asks for a concrete example Skill workflow.
metadata:
  sync_id: "example-skill"
  version: "1.0.0"
  triggering:
    include:
      - 用户明确要求创建、编辑、校验或发布 example-skill。
      - 当前任务需要复用 example-skill 中定义的流程。
    exclude:
      - 用户只是询问 Skill 仓库总体架构。
      - 当前任务只需要普通代码实现，不涉及 example-skill。
---
```

其中 `name`、`description`、`metadata.sync_id` 和 `metadata.version` 是基础约定。`metadata.sync_id` 是 `sync-skills` 使用的逻辑 Skill 不可变标识；创建 Skill 时确定，后续即使触发名称或目录变化也不得修改。`description` 继续承担兼容 Agent Skills 发现的自然语言触发说明；`metadata.triggering` 是本仓库额外的结构化补充。`include` 表示明确触发时机，`exclude` 表示明确不触发时机。未配置 `metadata.triggering` 时等价于 `include: []` 和 `exclude: []`。`exclude` 优先于 `include`，避免关键词命中导致误触发。

Agent 专属的调用语法、安装路径、UI 元数据和 manifest 不写入通用 `SKILL.md`。平台默认规则放在 `platforms/<agent>/`，单个 Skill 的例外文件放在 `agent-builds/<agent>/`。

带可执行扩展的 Skill 可以增加：

```text
skills/example-skill/
|-- SKILL.md
|-- extensions.yaml
|-- src/
|   |-- core.ts
|   |-- cli.ts
|   `-- mcp.ts
`-- tests/
```

`src/core.ts` 保存 CLI/MCP 共用业务逻辑；`cli.ts` 与 `mcp.ts` 只负责注册和协议适配。

## CLI（规划）

项目级 CLI 计划负责完整的 Skill 生命周期：

```text
skills create <name>
skills list
skills info <name>
skills search <query>
skills validate [name|--all]
skills test [name|--all]
skills link <name> --adapter codex
skills install <source>
skills update <name>
skills uninstall <name>
skills version <name> <major|minor|patch|version>
skills build [--adapter codex]
skills pack <name>
skills publish <name>
skills mcp serve
```

Skill 自定义命令统一使用独立命名空间：

```text
skills run <skill-name> <command> [args]
```

这样可以避免不同 Skill 之间，以及 Skill 命令与项目管理命令之间发生冲突。

## MCP Server（规划）

MCP Server 与 CLI 共享 `packages/core`，计划提供：

- Resources：Skill 目录、元数据、版本和只读说明。
- Prompts：创建、校验和升级 Skill 的可复用提示模板。
- Management tools：搜索、校验、安装、升级和构建 Skill。
- Skill tools：由受信任 Skill 通过 `extensions.yaml` 注册的自定义能力。

管理 tools 使用 `skills__<action>` 命名；Skill tools 使用 `<skill-name>__<tool-name>` 命名。首版使用本地 stdio transport；远程 Streamable HTTP 应在加入认证和来源限制后再启用。

## Agent Build 适配器

现在可以通过通用构建器使用适配器：

```bash
python3 scripts/agent_build.py --list
python3 scripts/agent_build.py --check
python3 scripts/agent_build.py codex
python3 scripts/agent_build.py workbuddy
```

构建器扫描 `platforms/`，不硬编码 Agent 清单。新增具有仓库级默认行为的 Agent 时，只需新增 `platforms/<agent>/`；仅在某个 Skill 存在例外时，才新增对应的 `agent-builds/<agent>/`。

## Codex 适配器

Codex 适配器把通用源码构建成标准插件产物：

```text
dist/codex/
|-- .codex-plugin/
|   `-- plugin.json
|-- .agent-build.json
|-- skills/
|   `-- <skill-name>/
|       |-- SKILL.md
|       |-- agents/openai.yaml
|       |-- scripts/
|       |-- references/
|       `-- assets/
```

Codex 插件产物和 Codex 适配器分别拥有自己的版本；二者都不会替代或自动提升通用 Skill 的版本。插件结构依据 [OpenAI 官方插件打包文档](https://developers.openai.com/plugins/build/plugins)。

## 版本与发布（规划）

- Skill 版本的单一事实源是 `SKILL.md` 中的 `metadata.version`。
- `.changes/` 记录受影响 Skill、升级级别和变更摘要。
- Skill 发布标签格式为 `skill/<skill-name>/v<version>`。
- 生成的 registry 记录版本、来源和 SHA-256 内容摘要。
- 每个 `platforms/<agent>/adapter.json` 分别维护适配器版本和生成产物版本。
- 新增或修改 Agent 支持不会提升 `metadata.version`，除非通用 Skill 行为也发生变化。
- 发布产物按 `<skill-name>/<version>` 保存为不可变副本，源目录不复制历史版本。

## 安全与信任

- 说明型 Skill 不自动获得代码执行权限。
- 远程可执行扩展默认禁用。
- 启用扩展前展示来源、版本、摘要、入口和权限。
- MCP 中会修改状态的 tools 默认要求用户审批。
- 安装和升级完成 schema、路径与摘要校验后再原子替换。
- 密钥不写入 Skill、registry 或构建产物。

## 路线图

1. 完成仓库说明、架构设计和实施计划。
2. 定义 `SKILL.md` frontmatter、`skillset.yaml`、`extensions.yaml` 与 registry schema。
3. 实现 `packages/core` 和 Skill 校验流程。
4. 实现项目级 CLI 与 Skill 自定义命令 SDK。
5. 实现本地 MCP Server 与 Skill tools 注册。
6. 在声明式 Agent 构建之上补充安装和 registry 发布能力。
7. 实现独立版本、打包与发布流程。

## 参考规范

- [Agent Skills Specification](https://agentskills.io/specification)
- [OpenAI plugin packaging](https://developers.openai.com/plugins/build/plugins)
- [Model Context Protocol SDKs](https://modelcontextprotocol.io/docs/sdk)
