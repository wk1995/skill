# Version Upgrade Policy

Language: **English** | [中文](README.zh-CN.md)

`version-upgrade-policy` defines, chooses, validates, and applies a project's own release versions, including initial values, upgrade levels, custom formats, release evidence, version-policy CI checks, and persistent AGENTS.md instructions. Ordinary code changes trigger version assessment when required by project instructions; incidental version mentions and release execution alone do not.

## How To Use It

Provide the current and proposed versions, the change, and any project format rules:

```text
Use version-upgrade-policy to decide whether 2026.09.1 -> 2026.10.0 is a feature release.
Define CI rules for A.B.C where A is compatibility, B is capability, and C is maintenance.
Review whether 1-rc-7 -> 1-rc-8 is a valid maintenance upgrade.
Add version-upgrade rules to this project's AGENTS.md so future feature and fix tasks assess release impact automatically.
```

The Skill records the grammar, component meanings, successor rules, compatibility evidence, changelog requirements, and validation cases. See [SKILL.md](SKILL.md) for the operational guidance.

For an initial release, provide a starting value or use the project's required value. Otherwise the default is numeric `0.0.1`. If an explicit custom format cannot represent `0.0.1`, the Skill asks for a compatible initial value. Existing releases are never reset to this default; a missing version file alone does not make a component new.

To install persistent rules, specify the project or AGENTS.md scope. The Skill updates an existing version section or creates one if needed, preserves unrelated instructions, and avoids duplicate edits on repetition. It adopts the project's actual formats and release process. Future feature/fix tasks must assess version impact without a separate reminder; pending work uses `[Unreleased]` or existing changesets, and versions advance once at release finalization. If the Skill is unavailable later, the written rules still provide the essential guidance. See the [integration guide and reusable section](references/agents-integration.md).

## When It Triggers

Select this Skill when the deliverable, or an explicit project requirement for the task, concerns the project's **own release version**:

| Request | Work covered |
| --- | --- |
| "Add proactive version rules to AGENTS.md." | Install, update, or review scoped persistent project instructions |
| "Add a feature" where AGENTS.md requires version assessment | Proactively assess release impact even without a bump request |
| "Choose the first version for this project." | Explicit/project-required initial value, otherwise numeric `0.0.1` |
| "After this fix, should 1.2.3 become 1.2.4 or 2.0.0?" | Decide whether to bump and select the impact level |
| "Change our source version to 1.2.4." | Validate and apply the supplied version under existing rules |
| "Define four-component or alphabetic version rules." | Grammar, meanings, ordering, successor and reset rules |
| "Implement our existing one-step version rule in CI" or "Fix the version check that accepts skipped versions." | Implement, review, or correct version-policy validation; no new policy is required |
| "Does this changelog justify a breaking release?" | Check release declarations, compatibility and migration evidence |

## When It Does Not Trigger

Do not select it when the task only involves:

- Updating a dependency, lockfile, runtime, SDK, or tool; resolving or comparing third-party versions under package-manager rules.
- Compiling, testing, signing, packaging, creating branches/tags, merging, publishing, deploying, or rolling back an already-selected version, such as "Build and publish 1.2.4."
- Fixing a bug, adding a feature, optimizing code, or editing documentation without requested or project-required version-policy work or release-impact assessment.
- Formatting or translating existing release notes without evaluating the version or its evidence.
- Installing, synchronizing, inventorying, or restoring Skill copies without release-policy work.

These exclusions take priority over keyword matches. For "Upgrade a dependency and choose our next application version," use this Skill for the application's version decision only. If "upgrade the version" has no clear target, resolve it from context or ask before editing. Selecting this Skill grants no extra authority to publish, deploy, create tags, or synchronize copies.
