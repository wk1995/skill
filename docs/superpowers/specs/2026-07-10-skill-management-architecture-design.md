# Skill 管理仓库架构设计

日期：2026-07-10

## 1. 背景

本仓库用于长期管理个人使用的多个 Agent Skill。每个 Skill 必须能够独立演进和独立版本化；仓库同时提供统一 CLI 与 MCP Server，并允许单个 Skill 按需贡献自己的 CLI 命令和 MCP tools。

仓库以 Agent Skills 通用规范为核心，首个运行时适配器面向 Codex。通用 Skill 内容不能依赖 Codex 私有目录；Codex 展示信息、插件清单和 MCP 配置由适配层提供。

本次任务只更新仓库 README，记录目标架构和规划状态，不实现 CLI、MCP Server、适配器或示例 Skill，也不创建尚未使用的空目录。

## 2. 目标与非目标

### 2.1 目标

- 在一个 monorepo 中管理大量 Skill。
- 使用 SemVer 为每个 Skill 维护独立版本。
- 保持基础 Skill 符合 Agent Skills 通用目录与 `SKILL.md` 规范。
- 提供统一的发现、创建、校验、测试、安装、升级、构建和发布能力。
- 让 CLI 与 MCP Server 复用同一套核心服务，保证行为一致。
- 允许 Skill 可选贡献 CLI 命令与 MCP tools。
- 通过 Codex 适配器生成标准 Codex 插件结构。
- 对可执行扩展建立显式信任、摘要校验和写操作审批边界。

### 2.2 非目标

- 不在首版同时实现多个 Agent 运行时适配器。
- 不为纯说明型 Skill 强制创建 TypeScript 包或扩展文件。
- 不把 Codex 专有字段写进所有运行时都需要读取的通用配置。
- 不让源代码目录按版本重复保存同一 Skill；版本化副本只存在于发布产物。
- 不在 README 中把尚未实现的命令描述为已经可用。

## 3. 已选方案

采用“独立 Skill 包 + 共享运行时”的 TypeScript monorepo。

与扁平目录加中央版本表相比，该方案让版本、说明和资源留在 Skill 自身目录中，减少中央清单冲突。与“每个 Skill 一个 Codex 插件”相比，它避免重复维护 CLI、MCP Server、插件清单和发布流程。

技术选择：

- Node.js 22 或更高版本。
- TypeScript。
- pnpm workspace。
- 稳定版 MCP TypeScript SDK；MCP SDK 封装在 `packages/mcp-server` 中，避免协议或 SDK 升级渗透到核心领域层。
- YAML 用于人类维护的仓库和扩展配置，JSON Schema 用于校验。

## 4. 仓库目录

```text
skill/
├── README.md
├── skillset.yaml
├── skills/
│   └── <skill-name>/
│       ├── SKILL.md
│       ├── agents/
│       │   └── openai.yaml
│       ├── extensions.yaml
│       ├── src/
│       │   ├── core.ts
│       │   ├── cli.ts
│       │   └── mcp.ts
│       ├── scripts/
│       ├── references/
│       ├── assets/
│       └── tests/
├── packages/
│   ├── core/
│   ├── sdk/
│   ├── cli/
│   ├── mcp-server/
│   └── adapter-codex/
├── schemas/
│   ├── skillset.schema.json
│   └── extensions.schema.json
├── tests/
│   ├── contract/
│   └── integration/
├── .changes/
├── package.json
├── pnpm-workspace.yaml
├── tsconfig.base.json
└── dist/
```

除 `SKILL.md` 外，单个 Skill 下的目录均按需创建：

- `agents/openai.yaml`：Codex 展示元数据，可选。
- `extensions.yaml` 与 `src/`：仅在 Skill 贡献 CLI/MCP 可执行能力时创建。
- `scripts/`：供 Agent 直接执行的确定性脚本。
- `references/`：按需加载的详细资料。
- `assets/`：模板、图片或其他输出资源。
- `tests/`：Skill 行为、脚本和扩展的测试。

`dist/` 是生成目录，不提交到 Git。

### 4.1 仓库配置

`skillset.yaml` 只保存仓库级设置，不保存单个 Skill 的版本：

```yaml
schemaVersion: 1
name: personal-skills
skillsDir: ./skills
outputDir: ./dist
adapters:
  - codex
execution:
  localExtensions: allow
  remoteExtensions: prompt
```

`localExtensions: allow` 只适用于当前受信任仓库中的扩展。`remoteExtensions: prompt` 表示远程扩展安装后仍保持禁用，必须在展示来源、版本、摘要和权限后获得明确确认才能执行。

## 5. Skill 包约定

### 5.1 通用入口与版本

`SKILL.md` 是唯一必需入口。Skill 名称和版本以其 YAML frontmatter 为单一事实源：

```yaml
---
name: example-skill
description: 描述该 Skill 的能力以及触发场景。
metadata:
  version: "1.0.0"
---
```

版本遵循 SemVer。CLI 解析 frontmatter，不再维护第二份中央版本字段。`name` 必须与父目录名一致。

### 5.2 可执行扩展

纯说明型 Skill 不需要 `extensions.yaml`。需要贡献命令或 tools 时，使用：

```yaml
schemaVersion: 1
contributes:
  cli:
    entry: ./src/cli.ts
    commands:
      - name: inspect
        description: Inspect this skill's local state
  mcp:
    entry: ./src/mcp.ts
    tools:
      - name: inspect
        description: Inspect this skill's local state
        mutating: false
execution:
  trust: required
```

声明中的命令和 tool 名称用于发现、冲突检测、帮助信息和审批分类；真实处理逻辑由对应入口通过共享 SDK 注册。

Skill 的 `src/core.ts` 保存 CLI/MCP 共用业务逻辑。`cli.ts` 与 `mcp.ts` 只负责协议适配，不复制业务实现。

## 6. 共享包职责

### 6.1 `packages/core`

负责：

- 扫描和解析 Skill。
- 校验目录名、frontmatter、版本与扩展清单。
- 构建内存 registry。
- 安装、链接、升级、卸载和发布编排。
- 版本解析、依赖检查、摘要计算和信任策略。
- 提供与 CLI、MCP、具体 Agent 适配器无关的服务接口。

### 6.2 `packages/sdk`

向 Skill 扩展提供稳定 API，包括 CLI 命令注册、MCP tool 注册、日志、结构化错误、工作目录、权限声明和核心服务访问。Skill 扩展不得直接依赖 CLI 或 MCP Server 的内部实现。

### 6.3 `packages/cli`

项目级命令规划：

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
skills run <skill-name> <command>
skills mcp serve
```

管理命令保留顶层命名空间。Skill 自定义命令统一通过 `skills run <skill> <command>` 调用，避免不同 Skill 之间以及与管理命令之间发生冲突。

所有命令支持人类可读输出；需要被脚本消费的命令支持 `--json`。成功退出码为 `0`，输入或校验失败为稳定的非零退出码。

### 6.4 `packages/mcp-server`

MCP Server 与 CLI 调用同一套 `packages/core` 服务，并提供：

- Resources：Skill 目录、Skill 元数据、版本和只读说明。
- Prompts：创建、校验、升级 Skill 的可复用提示模板。
- Tools：搜索、校验、安装、升级、构建等管理操作。
- Skill tools：从受信任 Skill 的 `extensions.yaml` 动态注册。

管理 tools 使用 `skills__<action>` 命名；Skill tools 使用 `<skill-name>__<tool-name>` 命名。启动时检测重复名称并拒绝不确定注册。

本地首版只启用 stdio transport。远程 Streamable HTTP 作为后续能力，启用时必须增加认证、来源限制和独立部署配置。

### 6.5 `packages/adapter-codex`

负责将通用源码转换为 Codex 插件产物：

```text
dist/codex/
├── .codex-plugin/
│   └── plugin.json
├── .mcp.json
├── skills/
│   └── <skill-name>/
│       ├── SKILL.md
│       ├── agents/openai.yaml
│       ├── scripts/
│       ├── references/
│       └── assets/
└── runtime/
    └── ...
```

Codex 插件版本是聚合包版本，与单个 Skill 版本分离。适配器根据根包版本生成 `plugin.json`，并生成指向共享 MCP Server 的 `.mcp.json`。

## 7. Registry 与构建产物

源仓库不手工维护 Skill 列表。`skills build` 扫描 `skills/` 并生成：

```text
dist/
├── registry.json
├── skills/
│   └── <skill-name>/
│       └── <version>/
│           └── ...
└── codex/
    └── ...
```

`registry.json` 至少包含名称、版本、描述、相对路径、是否含可执行扩展、支持的适配器、内容摘要和构建提交。生成物中的版本目录不可原地修改；新版本产生新的不可变目录。

## 8. 版本与发布

- 每个 Skill 在 `SKILL.md` 的 `metadata.version` 中维护独立 SemVer。
- `.changes/` 中的一次变更记录只声明受影响 Skill、升级级别和摘要。
- `skills version` 应用变更记录、更新 frontmatter 并生成 changelog 数据，但不在 Skill 目录创建额外 `CHANGELOG.md`。
- 发布标签使用 `skill/<skill-name>/v<version>`。
- registry 记录发布内容的 SHA-256 摘要。
- 根 `package.json` 维护 CLI/MCP/Codex 聚合包版本；任何共享运行时或 Codex bundle 变化都升级该版本。
- 构建时校验根包版本与生成的 Codex `plugin.json` 版本一致。

## 9. 安全与信任

- 说明型 Skill 只读取 Markdown 和资源，不获得代码执行权限。
- 本仓库本地 Skill 可被显式配置为可信；来自远程的可执行扩展默认禁用。
- 首次启用远程扩展时展示来源、版本、摘要、入口和权限，并要求明确确认。
- 安装和升级先写入临时目录，完成路径检查、摘要和 schema 校验后再原子替换。
- 禁止扩展入口逃逸 Skill 根目录；拒绝符号链接和 `..` 路径造成的越界访问。
- 密钥不写入 `SKILL.md`、`extensions.yaml`、registry 或构建产物。
- MCP 中标记为 `mutating: true` 的 tool 默认要求用户审批；远程 transport 不默认开放写 tools。
- 受信任的本地扩展可在进程内加载；未受信任扩展不加载，而不是尝试提供不完整的伪沙箱。

## 10. 关键流程

### 10.1 发现与校验

1. 扫描 `skills/*/SKILL.md`。
2. 解析 frontmatter 和可选 `extensions.yaml`。
3. 校验名称、版本、路径、入口、命令/tool 冲突和依赖。
4. 构建只读内存 registry。
5. CLI、MCP Server 和适配器消费同一 registry。

### 10.2 Skill 自定义调用

1. CLI 或 MCP 解析目标 Skill 和能力名称。
2. 核心层检查版本、摘要、信任状态和权限。
3. SDK 加载已声明入口。
4. 适配层调用处理器并转换结果。
5. 错误以统一错误码返回，日志不混入结构化输出。

### 10.3 Codex 构建

1. 校验全部 Skill 和共享包。
2. 复制通用 Skill 内容，排除源码测试和未构建入口。
3. 构建 CLI/MCP 运行时与 Skill 扩展。
4. 生成 `.codex-plugin/plugin.json` 和 `.mcp.json`。
5. 校验生成的插件目录。
6. 在临时 HOME 中执行安装和发现集成测试。

## 11. 错误处理

核心层使用稳定错误码，例如：

- `SKILL_NOT_FOUND`
- `INVALID_SKILL_NAME`
- `INVALID_SKILL_VERSION`
- `INVALID_FRONTMATTER`
- `INVALID_EXTENSION_MANIFEST`
- `COMMAND_CONFLICT`
- `MCP_TOOL_CONFLICT`
- `UNTRUSTED_EXTENSION`
- `CHECKSUM_MISMATCH`
- `ADAPTER_NOT_SUPPORTED`

CLI 将错误码映射为退出码和标准错误输出；`--json` 模式只在标准输出写入单个 JSON 结果。MCP 将同一错误映射为结构化 tool error。安装、升级和构建失败不得留下半成品或破坏当前可用版本。

## 12. 测试策略

- Schema 测试：覆盖合法和非法的 `SKILL.md`、`skillset.yaml`、`extensions.yaml`。
- Core 单元测试：发现、版本、registry、摘要、冲突和信任策略。
- CLI 契约测试：命令、退出码、stdout/stderr 和 `--json`。
- MCP 契约测试：resources、prompts、tools、命名空间和错误映射。
- Adapter 集成测试：在临时 HOME 中构建、安装并验证 Codex 可发现的目录。
- Golden 测试：固定 Codex 插件产物结构和生成清单。
- Skill 测试：脚本测试、扩展测试和针对 `SKILL.md` 行为的场景测试。
- 兼容性校验：使用 Agent Skills 官方 `skills-ref validate`，并使用 Codex 插件校验器检查适配产物。

测试不得写入真实的 `~/.codex/skills`、`~/.agents/skills` 或用户 marketplace。

## 13. README 更新范围

本次 README 应包含：

- 仓库定位与当前状态。
- 核心设计原则。
- 目标目录结构。
- 单个 Skill 的标准结构和独立版本约定。
- CLI 与 MCP 的规划职责和命名空间。
- Codex 首个适配器与构建产物结构。
- 安全与信任原则。
- 分阶段路线图。

README 必须明确区分“已存在”和“规划中”的能力。当前仓库只有 README 和本设计说明，因此所有 CLI、MCP、适配器和发布命令均标注为规划中。

## 14. 验收标准

- 新贡献者能从 README 理解仓库用途、目录和 Skill 版本位置。
- README 展示基础 Skill 与带 CLI/MCP 扩展 Skill 的差异。
- README 说明通用核心与 Codex 适配器的边界。
- README 不声称尚未实现的命令已经可运行。
- 目录、命名和示例与本设计一致。
- Markdown 链接有效，结构清晰，无占位符或未决问题。

## 15. 规范依据

- Agent Skills Specification: https://agentskills.io/specification
- Codex plugin structure: https://developers.openai.com/codex/plugins/build
- Model Context Protocol SDKs: https://modelcontextprotocol.io/docs/sdk
