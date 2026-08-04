# Personal Skills

语言：[English](README.md) | **中文**

Personal Skills 是一个用于集中管理个人 Agent Skills 的 monorepo。每个 Skill 独立维护自己的内容和版本；仓库计划统一提供 Skill 管理、CLI、MCP Server 和运行时适配能力，并允许单个 Skill 按需贡献自己的 CLI 命令和 MCP tools。

## 当前状态

- 已完成：仓库定位、目标架构、目录约定和第一个本地 Skill。
- 规划中：Skill schema、共享管理包、CLI、MCP Server、Codex 适配器、构建、版本和发布流程。
- 尚未提供：项目级可执行命令。本文中的命令均描述目标接口。

详细设计见 [Skill 管理仓库架构设计](docs/superpowers/specs/2026-07-10-skill-management-architecture-design.md)。

## 设计原则

- **通用核心**：基础 Skill 遵循 [Agent Skills Specification](https://agentskills.io/specification)，不绑定单一 Agent 产品。
- **Codex 优先适配**：首个适配器面向标准 Codex 插件结构：`skills/`、`.codex-plugin/plugin.json` 和 `.mcp.json`。
- **独立版本**：每个 Skill 在自己的 `SKILL.md` 中维护 SemVer。
- **渐进扩展**：说明型 Skill 只需要 `SKILL.md`；需要时再增加脚本、资料、资产、CLI 命令或 MCP tools。
- **一套核心，两种入口**：CLI 和 MCP Server 复用相同的发现、校验、安装、版本和发布逻辑。
- **显式信任**：远程 Skill 的可执行扩展默认禁用，获得明确确认后才能加载。

## 目标目录

以下为规划目录，不代表所有文件和目录均已实现。

```text
skill/
|-- README.md
|-- README.zh-CN.md
|-- skillset.yaml                 # 仓库级配置、适配器和信任策略
|-- skills/
|   `-- <skill-name>/
|       |-- SKILL.md              # 必需：面向 Agent 的通用入口、版本和触发规则
|       |-- README.md             # 必需：使用说明、触发条件和不触发条件
|       |-- agents/
|       |   `-- openai.yaml       # 可选：Codex 展示元数据
|       |-- extensions.yaml       # 可选：CLI/MCP 扩展声明
|       |-- src/                  # 可选：扩展实现
|       |   |-- core.ts
|       |   |-- cli.ts
|       |   `-- mcp.ts
|       |-- scripts/              # 可选：确定性脚本
|       |-- references/           # 可选：按需加载的资料
|       |-- assets/               # 可选：模板与静态资产
|       `-- tests/                # 可选：行为、脚本和扩展测试
|-- packages/
|   |-- core/                     # Skill 发现、校验、安装和版本管理
|   |-- sdk/                      # Skill CLI/MCP 扩展 API
|   |-- cli/                      # 项目级 CLI
|   |-- mcp-server/               # 项目级 MCP Server
|   `-- adapter-codex/            # Codex 插件构建与安装适配
|-- schemas/                      # Skill frontmatter、skillset 和 extensions JSON Schema
|   |-- skill.schema.json
|   |-- skillset.schema.json
|   `-- extensions.schema.json
|-- tests/
|   |-- contract/
|   `-- integration/
|-- .changes/                     # Skill 独立版本变更记录
|-- package.json
|-- pnpm-workspace.yaml
|-- tsconfig.base.json
`-- dist/                         # 构建产物，不提交
```

Agent Skills 规范只要求 `SKILL.md`，但本仓库额外要求每个受管理的 Skill 都提供面向使用者的 `README.md`；详见 [AGENTS.md](AGENTS.md)。其他目录按需创建。

## Skills

每个 Skill 都有配套 README，说明使用方法、触发条件和不触发条件。此表由 `python scripts/skill_catalog.py --write` 生成，请勿手动编辑表格行。

<!-- skills-catalog:start -->
| Skill | 用途 | 文档 |
| --- | --- | --- |
| `release-engineering` | `release-engineering` 用于规划、校验、自动化、记录和排查受控发布流程。它覆盖 Android 应用、Android 库与 SDK、Gradle 插件、构建产物、发布分支和标签、CI 门禁、发布、回滚计划及发布后处理。 | [README](skills/release-engineering/README.zh-CN.md) |
| `sync-skills` | `sync-skills` 用于管理同一个 Agent Skill 在本仓库、项目目录、本机 Codex Skill 目录和明确指定的外部路径中的等价副本。它支持链接、转换、比较、同步、版本记录、快照、审计和回滚。 | [README](skills/sync-skills/README.zh-CN.md) |
<!-- skills-catalog:end -->

## Pull Request 目录检查

`skill-catalog` GitHub Actions 检查会在 PR 合入 `main` 前校验所有 Skill 和两份目录。它会在 CI 日志中打印每一项校验失败原因，并为对应文件创建 GitHub Actions error 注释。若 PR 分支属于本仓库，且已配置具有仓库内容写权限的 `SKILL_CATALOG_TOKEN` secret，workflow 可以将生成后的根 README 目录提交回该 PR；对于 fork PR 或未配置该 secret 的情况，只要目录未同步，检查就会失败并提示贡献者运行生成器后提交两份根 README。

## Skill 结构与版本

基础 Skill：

```text
skills/example-skill/
`-- SKILL.md
```

`SKILL.md` 同时保存通用元数据、独立版本和可选触发规则：

```yaml
---
name: example-skill
description: Use when the user asks for a concrete example Skill workflow.
metadata:
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

其中 `name`、`description` 和 `metadata.version` 是基础约定。`description` 继续承担兼容 Agent Skills 发现的自然语言触发说明；`metadata.triggering` 是本仓库额外的结构化补充。`include` 表示明确触发时机，`exclude` 表示明确不触发时机。未配置 `metadata.triggering` 时等价于 `include: []` 和 `exclude: []`。`exclude` 优先于 `include`，避免关键词命中导致误触发。

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

## Codex 适配器（规划）

Codex 适配器把通用源码构建成标准插件产物：

```text
dist/codex/
|-- .codex-plugin/
|   `-- plugin.json
|-- .mcp.json
|-- skills/
|   `-- <skill-name>/
|       |-- SKILL.md
|       |-- agents/openai.yaml
|       |-- scripts/
|       |-- references/
|       `-- assets/
`-- runtime/
```

Codex 插件使用独立的聚合包版本；它不会替代每个 Skill 自己的版本。插件结构依据 [Codex 插件文档](https://developers.openai.com/codex/plugins/build)。

## 版本与发布（规划）

- Skill 版本的单一事实源是 `SKILL.md` 中的 `metadata.version`。
- `.changes/` 记录受影响 Skill、升级级别和变更摘要。
- Skill 发布标签格式为 `skill/<skill-name>/v<version>`。
- 生成的 registry 记录版本、来源和 SHA-256 内容摘要。
- 根 `package.json` 维护共享 CLI、MCP 与 Codex 聚合包版本。
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
6. 实现 Codex 构建、安装和集成测试。
7. 实现独立版本、打包与发布流程。

## 参考规范

- [Agent Skills Specification](https://agentskills.io/specification)
- [Codex plugin structure](https://developers.openai.com/codex/plugins/build)
- [Model Context Protocol SDKs](https://modelcontextprotocol.io/docs/sdk)
