# Agent Build Architecture

This document defines how portable Skill sources are adapted for Codex, WorkBuddy, and future Agent runtimes without spreading platform rules across every Skill.

## Responsibility Boundaries

The repository has three layers:

```text
skills/<skill>/                    portable source and core version
  SKILL.md
  README.md
  README.zh-CN.md
  CHANGELOG.md
  agent-builds/<agent>/            optional per-Skill overrides

platforms/<agent>/                 defaults for all Skills on one Agent
  adapter.json
  SKILL.append.md                  optional generated instruction suffix
  root/                            optional artifact-root overlay

dist/<agent>/                      generated artifact; never committed
```

`SKILL.md` contains only the workflow that remains true across Agents: purpose, routing, domain procedure, safety boundaries, and stable core metadata. It must not document an Agent's installation path, invocation prefix, UI manifest, or discovery implementation.

`platforms/<agent>/` owns the default packaging and runtime adaptation for every Skill. `skills/<skill>/agent-builds/<agent>/` is an overlay used only when one Skill needs extra platform files or instructions. Codex `agents/openai.yaml` metadata is therefore stored in the Codex override and materialized at the standard path only in `dist/codex`.

## Declarative Adapter Contract

Every adapter is discovered by scanning `platforms/*/adapter.json`; there is no central Agent list. The manifest fields are:

- `schema_version`: currently `1`.
- `id`: lowercase hyphenated Agent identifier matching the directory name.
- `version`: adapter implementation/configuration version.
- `artifact_version`: version of the generated distributable bundle.
- `skills_path`: relative directory in the artifact where Skills are written; `.` is allowed.
- `local_skill_roots`: non-empty list of declarative, side-effect-free local installation resolvers. `home-relative` resolves below the current user's home; optional or required `env` reads one named absolute-path environment variable.
- `root_overlay`: optional directory copied once to the artifact root.
- `skill_overlay`: optional directory copied into every generated Skill.
- `skill_append`: optional Markdown fragment appended to every generated `SKILL.md`.

Adapter fragments may use `{{skill_name}}`, `{{adapter_id}}`, `{{adapter_version}}`, and `{{artifact_version}}`. A Skill override may contain one top-level `SKILL.append.md` fragment and any files that should overlay the built Skill. The reserved fragment is appended rather than copied; nested files with that reserved name are rejected.

Build inputs must be regular files and directories. Symbolic links, undeclared Agent override directories, nested reserved append fragments, and parent-traversal paths are rejected by both `--check` and direct builds. Repository-local outputs must be children of `dist/`. With `--force`, the builder replaces only a directory whose regular `.agent-build.json` identifies it as an artifact for the selected platform; unrelated directories and files are preserved. The builder stages the complete artifact before replacing a validated existing output.

## Build Flow

Run:

```bash
python3 scripts/agent_build.py --list
python3 scripts/agent_build.py --check
python3 scripts/agent_build.py codex
python3 scripts/agent_build.py workbuddy --skill sync-skills
```

For each selected Skill, the builder:

1. copies the portable source while excluding `agent-builds/`;
2. applies the adapter-wide Skill overlay;
3. applies `agent-builds/<agent>/` for that Skill;
4. appends adapter-wide and per-Skill instruction fragments;
5. records stable sync IDs, core versions, portable source digests, output digests, and safe relative artifact paths in `.agent-build.json` schema v2.

The manifest-v2 identity chain allows relationship reporting to compare portable source to build and then compare a local installation only to the corresponding same-Agent build. A schema-v1 artifact may be inspected as legacy output but is not trusted for installation repair because it lacks stable identity and portable provenance.

Codex builds also copy `.codex-plugin/plugin.json` from the adapter root overlay. This follows the official OpenAI plugin package boundary: a plugin has a root manifest and can bundle Skills under `skills/`; a generated Skill may contain `agents/openai.yaml` for its own Codex interface metadata.

## Open/Closed Extension Rule

Adding a new Agent with common behavior requires only a new `platforms/<agent>/` directory containing `adapter.json` and any adapter-owned files. Existing Skills, the generic builder, and the central catalog remain unchanged. Add `skills/<skill>/agent-builds/<agent>/` only for genuine exceptions.

The `agent-builds/` directory is required on every managed Skill so the override boundary is explicit. An otherwise-empty directory may contain `.gitkeep`.

## Version Policy

Three versions have distinct meanings:

- `metadata.version` in `SKILL.md`: portable Skill behavior.
- `version` in `platforms/<agent>/adapter.json`: adapter rules and builder contract used by that Agent.
- `artifact_version` in the adapter manifest: installable bundle release.

Adding Agent support, moving UI metadata into an adapter override, or changing only packaging must not bump the portable Skill version. Change the adapter and/or artifact version and record it in that adapter's `CHANGELOG.md`. Bump a Skill core version only when its cross-Agent workflow, triggers, inputs, outputs, or safety behavior changes.

## Current Outputs

```text
dist/codex/
  .codex-plugin/plugin.json
  .agent-build.json
  skills/<skill>/
    SKILL.md
    agents/openai.yaml             when the Skill supplies a Codex override

dist/workbuddy/
  .agent-build.json
  <skill>/
    SKILL.md
```

Generated output is ignored by Git. Installation commands belong to their adapter documentation or packaging layer; portable Skill READMEs describe how to use the workflow, not how a specific Agent installs it.

After a successful build, the builder prints the machine-local `skill_sync.py relationships` refresh command. Report generation never invokes a build implicitly.
