# Personal Skills

Language: **English** | [中文](README.zh-CN.md)

Personal Skills is a monorepo for managing personal Agent Skills. Each Skill owns its content and version, while the repository is intended to provide shared Skill management, CLI, MCP server, and runtime adapter capabilities. A Skill may also contribute its own CLI commands or MCP tools when needed.

## Current State

- Done: repository purpose, target architecture, directory conventions, and the first local Skill.
- Planned: Skill schemas, shared management packages, CLI, MCP server, Codex adapter, build, versioning, and publishing flows.
- Not yet available: project-level executable commands. Commands shown in this README describe the target interface.

See the detailed architecture notes in [Skill management repository architecture design](docs/superpowers/specs/2026-07-10-skill-management-architecture-design.md).

## Design Principles

- **Portable core:** Basic Skills follow the [Agent Skills Specification](https://agentskills.io/specification) and are not tied to a single agent product.
- **Codex first adapter:** The first adapter targets the standard Codex plugin shape: `skills/`, `.codex-plugin/plugin.json`, and `.mcp.json`.
- **Independent versions:** Each Skill keeps its SemVer value in its own `SKILL.md`.
- **Progressive extension:** Documentation-only Skills need only `SKILL.md`; scripts, references, assets, CLI commands, and MCP tools are added only when useful.
- **One core, two interfaces:** The CLI and MCP server should reuse the same discovery, validation, installation, versioning, and publishing logic.
- **Explicit trust:** Executable extensions from remote Skills are disabled by default and require clear user approval before they are loaded.

## Target Directory

The tree below is planned architecture. It does not mean every file or directory already exists.

```text
skill/
|-- README.md
|-- README.zh-CN.md
|-- skillset.yaml                 # Repository-level configuration, adapters, and trust policy
|-- skills/
|   `-- <skill-name>/
|       |-- SKILL.md              # Required: portable entrypoint, version, and optional trigger rules
|       |-- agents/
|       |   `-- openai.yaml       # Optional: Codex display metadata
|       |-- extensions.yaml       # Optional: CLI/MCP extension declaration
|       |-- src/                  # Optional: extension implementation
|       |   |-- core.ts
|       |   |-- cli.ts
|       |   `-- mcp.ts
|       |-- scripts/              # Optional: deterministic scripts
|       |-- references/           # Optional: lazily loaded reference material
|       |-- assets/               # Optional: templates and static assets
|       `-- tests/                # Optional: behavior, script, and extension tests
|-- packages/
|   |-- core/                     # Skill discovery, validation, installation, and versioning
|   |-- sdk/                      # Skill CLI/MCP extension API
|   |-- cli/                      # Project-level CLI
|   |-- mcp-server/               # Project-level MCP server
|   `-- adapter-codex/            # Codex plugin build and install adapter
|-- schemas/                      # Skill frontmatter, skillset, and extensions JSON Schema
|   |-- skill.schema.json
|   |-- skillset.schema.json
|   `-- extensions.schema.json
|-- tests/
|   |-- contract/
|   `-- integration/
|-- .changes/                     # Independent Skill version change records
|-- package.json
|-- pnpm-workspace.yaml
|-- tsconfig.base.json
`-- dist/                         # Build output, not committed
```

Only `SKILL.md` is required for an individual Skill. Other directories are created only when the Skill needs them.

## Skill Structure And Versioning

A minimal Skill:

```text
skills/example-skill/
`-- SKILL.md
```

`SKILL.md` keeps portable metadata, independent versioning, and optional trigger rules:

```yaml
---
name: example-skill
description: Use when the user asks for a concrete example Skill workflow.
metadata:
  version: "1.0.0"
  urls:
    - type: repository
      value: https://github.com/example/example-skill
    - type: documentation
      value: https://example.com/example-skill/docs
  triggering:
    include:
      - The user explicitly asks to create, edit, validate, or publish example-skill.
      - The current task needs to reuse workflow instructions from example-skill.
    exclude:
      - The user is only asking about the overall Skill repository architecture.
      - The current task only needs ordinary code changes and does not involve example-skill.
---
```

`name`, `description`, and `metadata.version` are the baseline contract. `description` remains the natural-language discovery text used by Agent Skills. `metadata.urls` is optional stable provenance information for the logical Skill, such as a source repository, documentation page, registry page, package page, or upstream project. `metadata.triggering` is this repository's structured supplement: `include` describes explicit trigger cases, and `exclude` describes explicit non-trigger cases. When `metadata.triggering` is not configured, it is equivalent to `include: []` and `exclude: []`. `exclude` takes priority over `include` to avoid accidental keyword-triggered activation.

A Skill with executable extensions may add:

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

`src/core.ts` should contain shared CLI/MCP business logic. `cli.ts` and `mcp.ts` should handle registration and protocol adaptation only.

## Shared Metadata And Audit Conventions

These conventions are shared across Skills and management tools. They should be reflected in schemas, registries, CLI output, and MCP resources as those pieces are implemented.

### Stable Skill information

Keep stable self-description in `SKILL.md`:

- `metadata.version`: the Skill's independent version.
- `metadata.urls`: canonical addresses for the logical Skill. Use typed entries such as `repository`, `documentation`, `registry`, `package`, or `source`.
- `metadata.triggering`: optional structured trigger rules.

Do not put machine-local paths, generated snapshots, local sync state, or per-copy timestamps in `SKILL.md`.

### Registry records

Generated registry records should capture environment-specific audit state:

- `skill_urls`: canonical URLs collected from `metadata.urls`, CLI arguments, registry data, or upstream sources.
- `role_urls`: role-specific URLs for physical copies, such as a local repository remote, project repository, external source page, or bundled plugin address.
- `roles`: absolute local paths for physical copies, such as `repo`, `local`, `project`, and `external`.
- `digest`: SHA-256 content digest for each copy or published artifact.
- `created_at` and `updated_at`: audit timestamps for groups, versions, digests, and operations.
- `version_history`: observed versions with their first and latest observed times, digests, roles, URLs, and content update times.
- `differences_by_role`: changed-file summaries for synchronization or upgrade operations.

If a role URL is not explicitly configured, infer it from `git remote get-url origin` when the Skill copy is inside a Git repository.

### Time inference

When a timestamp is missing, infer it in this order:

1. Existing registry or explicit metadata value.
2. Git commit history for the Skill path: first commit for `created_at`, latest commit for `updated_at`.
3. File modification time for non-ignored Skill files.
4. Current UTC time.

Always record how an inferred content timestamp was derived, for example `git`, `filesystem`, `manual`, or `registry`. Use timestamps for auditability only; use digests to decide whether two copies are identical.

### Version differences

When recording or reporting differences between Skill versions or linked copies, report:

- added files;
- removed files;
- modified text files, preferably with unified diffs when requested;
- modified binary files by path and digest only.

Prefer snapshot-to-snapshot comparisons for historical versions. Use snapshot-to-current comparisons when deciding whether an unsynchronized local copy should become the source.

## CLI (Planned)

The project-level CLI is planned to manage the complete Skill lifecycle:

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

Custom Skill commands use an isolated namespace:

```text
skills run <skill-name> <command> [args]
```

This avoids collisions between different Skills and between Skill commands and project management commands.

## MCP Server (Planned)

The MCP server shares `packages/core` with the CLI and is planned to provide:

- Resources: Skill directory, metadata, versions, and read-only instructions.
- Prompts: reusable prompts for creating, validating, and upgrading Skills.
- Management tools: search, validate, install, upgrade, and build Skills.
- Skill tools: custom capabilities registered by trusted Skills through `extensions.yaml`.

Management tools use the `skills__<action>` namespace. Skill tools use `<skill-name>__<tool-name>`. The first version should use local stdio transport. Remote Streamable HTTP should be enabled only after authentication and origin restrictions exist.

## Codex Adapter (Planned)

The Codex adapter builds portable source content into a standard plugin artifact:

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

The Codex plugin has its own aggregate package version. It does not replace the independent version of each Skill. The plugin shape follows the [Codex plugin documentation](https://developers.openai.com/codex/plugins/build).

## Versioning And Releases (Planned)

- The single source of truth for a Skill version is `metadata.version` in `SKILL.md`.
- `.changes/` records the affected Skill, bump level, and change summary.
- Skill release tags use `skill/<skill-name>/v<version>`.
- Generated registry records include version, source, and SHA-256 content digest.
- The root `package.json` maintains the shared CLI, MCP, and Codex bundle version.
- Published artifacts are stored as immutable copies under `<skill-name>/<version>`; source directories do not duplicate historical versions.

## Security And Trust

- Documentation-only Skills do not receive code execution permissions automatically.
- Remote executable extensions are disabled by default.
- Before enabling an extension, show its source, version, digest, entrypoints, and permissions.
- MCP tools that mutate state should require user approval by default.
- Installation and upgrade should validate schema, paths, and digests before atomic replacement.
- Secrets must not be written into Skills, registries, or build artifacts.

## Roadmap

1. Complete repository docs, architecture design, and implementation plan.
2. Define `SKILL.md` frontmatter, `skillset.yaml`, `extensions.yaml`, and registry schemas.
3. Implement `packages/core` and Skill validation.
4. Implement the project-level CLI and custom Skill command SDK.
5. Implement the local MCP server and Skill tool registration.
6. Implement Codex build, installation, and integration tests.
7. Implement independent versioning, packaging, and publishing.

## References

- [Agent Skills Specification](https://agentskills.io/specification)
- [Codex plugin structure](https://developers.openai.com/codex/plugins/build)
- [Model Context Protocol SDKs](https://modelcontextprotocol.io/docs/sdk)
