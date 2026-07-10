# README Architecture Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the placeholder README with an accurate Chinese project guide that documents the approved multi-Skill architecture without presenting planned CLI, MCP, or Codex adapter capabilities as implemented.

**Architecture:** The README describes an Agent Skills-compatible monorepo in which each Skill owns its `SKILL.md` and SemVer, while shared TypeScript packages provide management CLI, MCP, SDK, and Codex adaptation. It distinguishes the current documentation-only repository state from the target directory and roadmap.

**Tech Stack:** Markdown, Agent Skills specification, planned Node.js 22+/TypeScript/pnpm workspace, planned MCP TypeScript SDK, planned Codex plugin adapter.

## Global Constraints

- This implementation modifies only `README.md` and this plan document; it does not scaffold the target directories or implement CLI/MCP code.
- The README must be written primarily in Chinese.
- Each Skill version lives only in `SKILL.md` at `metadata.version` and follows SemVer.
- The portable core follows Agent Skills; Codex-specific files stay in the Codex adapter or optional `agents/openai.yaml`.
- Both project-level management operations and optional per-Skill CLI/MCP contributions must be documented.
- All unimplemented commands and components must be labeled as planned.
- The target runtime stack is Node.js 22 or later, TypeScript, and pnpm workspace.
- Do not create empty target directories merely to match the documented tree.

---

### Task 1: Replace the placeholder README with the approved architecture guide

**Files:**
- Modify: `README.md`
- Reference: `docs/superpowers/specs/2026-07-10-skill-management-architecture-design.md`
- Test: shell content-contract checks against `README.md`

**Interfaces:**
- Consumes: the approved architecture decisions in `docs/superpowers/specs/2026-07-10-skill-management-architecture-design.md`.
- Produces: a single repository entry document that clearly separates current state, target architecture, Skill package rules, planned CLI/MCP surfaces, Codex adaptation, security, and roadmap.

- [ ] **Step 1: Run the README content contract and verify the placeholder fails it**

Run:

```bash
rg -q '^# Personal Skills$' README.md \
  && rg -q '^## 当前状态$' README.md \
  && rg -q '^## 目标目录$' README.md \
  && rg -q '^## CLI（规划）$' README.md \
  && rg -q '^## MCP Server（规划）$' README.md \
  && rg -q '^## Codex 适配器（首个适配器，规划）$' README.md
```

Expected: non-zero exit because the current file contains only `# skill`.

- [ ] **Step 2: Replace `README.md` with the complete project guide**

Write exactly:

````markdown
# Personal Skills

用于集中管理个人 Agent Skills 的 monorepo。每个 Skill 独立维护内容与版本；仓库统一提供 Skill 管理 CLI、MCP Server 和运行时适配器，并允许单个 Skill 按需贡献自己的 CLI 命令和 MCP tools。

## 当前状态

- 已完成：仓库定位、目标架构和目录规范设计。
- 规划中：Skill schema、核心管理库、CLI、MCP Server、Codex 适配器与发布流程。
- 当前仓库尚未提供可执行命令；本文中的命令均为目标接口。

详细设计见 [Skill 管理仓库架构设计](docs/superpowers/specs/2026-07-10-skill-management-architecture-design.md)。

## 设计原则

- **通用核心**：基础 Skill 遵循 [Agent Skills Specification](https://agentskills.io/specification)，不绑定单一 Agent 产品。
- **Codex 优先**：首个适配器生成 Codex 插件所需的 `skills/`、`.codex-plugin/plugin.json` 和 `.mcp.json`。
- **独立版本**：每个 Skill 在自己的 `SKILL.md` 中维护 SemVer。
- **渐进扩展**：纯说明型 Skill 只需 `SKILL.md`；需要时再添加脚本、资料、CLI 或 MCP 能力。
- **一套核心，两种入口**：CLI 与 MCP Server 复用相同的发现、校验、安装、版本和发布逻辑。
- **显式信任**：远程 Skill 的可执行扩展默认禁用，获得明确确认后才能加载。

## 目标目录

以下是规划目录，不代表所有文件均已实现：

```text
skill/
├── README.md
├── skillset.yaml                 # 仓库级配置、适配器和信任策略
├── skills/
│   └── <skill-name>/
│       ├── SKILL.md              # 必需：通用入口与独立版本
│       ├── agents/
│       │   └── openai.yaml       # 可选：Codex 展示元数据
│       ├── extensions.yaml       # 可选：CLI/MCP 扩展声明
│       ├── src/                  # 可选：扩展实现
│       │   ├── core.ts
│       │   ├── cli.ts
│       │   └── mcp.ts
│       ├── scripts/              # 可选：确定性脚本
│       ├── references/           # 可选：按需加载的资料
│       ├── assets/               # 可选：模板与静态资源
│       └── tests/                # 可选：行为、脚本和扩展测试
├── packages/
│   ├── core/                     # Skill 发现、校验、安装和版本管理
│   ├── sdk/                      # Skill CLI/MCP 扩展 API
│   ├── cli/                      # 项目级 CLI
│   ├── mcp-server/               # 项目级 MCP Server
│   └── adapter-codex/            # Codex 插件构建与安装适配
├── schemas/                      # skillset/extensions JSON Schema
├── tests/
│   ├── contract/
│   └── integration/
├── .changes/                     # Skill 独立版本变更记录
├── package.json
├── pnpm-workspace.yaml
├── tsconfig.base.json
└── dist/                         # 构建产物，不提交
```

只有 `SKILL.md` 是单个 Skill 的必需文件，其余目录按需创建。

## Skill 结构与版本

基础 Skill：

```text
skills/example-skill/
└── SKILL.md
```

`SKILL.md` 同时保存通用元数据和独立版本：

```yaml
---
name: example-skill
description: 描述该 Skill 的能力以及何时使用。
metadata:
  version: "1.0.0"
---
```

带可执行扩展的 Skill 可以增加：

```text
skills/example-skill/
├── SKILL.md
├── extensions.yaml
├── src/
│   ├── core.ts
│   ├── cli.ts
│   └── mcp.ts
└── tests/
```

`src/core.ts` 保存 CLI/MCP 共用逻辑，`cli.ts` 与 `mcp.ts` 只负责注册和协议适配。

## CLI（规划）

项目级 CLI 负责完整的 Skill 生命周期：

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

这样可以避免不同 Skill 之间以及与项目管理命令之间发生冲突。

## MCP Server（规划）

MCP Server 与 CLI 共享 `packages/core`，计划提供：

- Resources：Skill 目录、元数据、版本和只读说明。
- Prompts：创建、校验和升级 Skill 的提示模板。
- Management tools：搜索、校验、安装、升级和构建 Skill。
- Skill tools：由受信任 Skill 通过 `extensions.yaml` 注册的自定义能力。

管理 tools 使用 `skills__<action>` 命名；Skill tools 使用 `<skill-name>__<tool-name>` 命名。首版使用本地 stdio transport，远程 Streamable HTTP 在加入认证和来源限制后再启用。

## Codex 适配器（首个适配器，规划）

Codex 适配器把通用源码构建成标准插件：

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
```

Codex 插件使用独立的聚合包版本；它不会替代每个 Skill 自己的版本。插件结构依据 [Codex 插件文档](https://developers.openai.com/codex/plugins/build)。

## 版本与发布（规划）

- Skill 版本的单一事实源是 `SKILL.md` 中的 `metadata.version`。
- `.changes/` 记录受影响 Skill、升级级别和变更摘要。
- Skill 发布标签格式为 `skill/<skill-name>/v<version>`。
- 生成的 registry 记录版本、来源和 SHA-256 内容摘要。
- 根 `package.json` 维护共享 CLI、MCP 与 Codex 聚合包版本。
- 发布产物按 `<skill-name>/<version>` 保存不可变副本，源目录不复制历史版本。

## 安全边界

- 说明型 Skill 不自动获得代码执行权限。
- 远程可执行扩展默认禁用。
- 启用扩展前展示来源、版本、摘要、入口和权限。
- MCP 写 tools 默认要求用户审批。
- 安装和升级完成 schema、路径与摘要校验后再原子替换。
- 密钥不写入 Skill、registry 或构建产物。

## 路线图

1. 完成仓库说明、架构设计和实施计划。
2. 定义 `skillset.yaml`、`extensions.yaml` 与 registry schema。
3. 实现 `packages/core` 和 Skill 校验流程。
4. 实现项目级 CLI 与 Skill 自定义命令 SDK。
5. 实现本地 MCP Server 与 Skill tools 注册。
6. 实现 Codex 构建、安装和集成测试。
7. 实现独立版本、打包与发布流程。

## 参考规范

- [Agent Skills Specification](https://agentskills.io/specification)
- [Codex plugin structure](https://developers.openai.com/codex/plugins/build)
- [Model Context Protocol SDKs](https://modelcontextprotocol.io/docs/sdk)
````

- [ ] **Step 3: Run the content and formatting checks**

Run:

```bash
set -e
rg -q '^# Personal Skills$' README.md
rg -q '^## 当前状态$' README.md
rg -q '^## 目标目录$' README.md
rg -q '^## Skill 结构与版本$' README.md
rg -q '^## CLI（规划）$' README.md
rg -q '^## MCP Server（规划）$' README.md
rg -q '^## Codex 适配器（首个适配器，规划）$' README.md
rg -q 'metadata:' README.md
rg -q 'version: "1.0.0"' README.md
rg -q 'skills run <skill-name> <command> \[args\]' README.md
rg -q 'skills__<action>' README.md
rg -q '<skill-name>__<tool-name>' README.md
rg -q '远程可执行扩展默认禁用' README.md
test -f docs/superpowers/specs/2026-07-10-skill-management-architecture-design.md
! rg -n 'TBD|TODO|FIXME|PLACEHOLDER' README.md
git diff --check
```

Expected: exit code `0` with no output from `git diff --check` or the placeholder scan.

- [ ] **Step 4: Review the rendered structure and scope**

Run:

```bash
rg -n '^#|^## ' README.md
git diff -- README.md
```

Expected headings, in order: title, current state, principles, target directory, Skill structure/version, planned CLI, planned MCP, planned Codex adapter, planned version/release, security, roadmap, references. The diff must modify only `README.md`; it must not create any target architecture directory.

- [ ] **Step 5: Commit the README update**

```bash
git add README.md
git diff --cached --check
git commit -m "[codex] docs: document skill repository architecture"
```

Expected: one commit containing only `README.md`.
