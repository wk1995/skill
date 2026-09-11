# Version Upgrade Policy

Language: **English** | [中文](README.zh-CN.md)

`version-upgrade-policy` defines, chooses, validates, and applies a project's own release versions, including initial values, upgrade levels, custom formats, release evidence, and version-policy CI checks. Dependency/tool upgrades, code fixes, and build/publish execution alone do not trigger it.

## How To Use It

Provide the current and proposed versions, the change, and any project format rules:

```text
Use version-upgrade-policy to decide whether 2026.09.1 -> 2026.10.0 is a feature release.
Define CI rules for A.B.C where A is compatibility, B is capability, and C is maintenance.
Review whether 1-rc-7 -> 1-rc-8 is a valid maintenance upgrade.
```

The Skill records the grammar, component meanings, successor rules, compatibility evidence, changelog requirements, and validation cases. See [SKILL.md](SKILL.md) for the operational guidance.

For an initial release, provide a starting value or use the project's required value. Otherwise the default is numeric `0.0.1`. If an explicit custom format cannot represent `0.0.1`, the Skill asks for a compatible initial value. Existing releases are never reset to this default; a missing version file alone does not make a component new.

## When It Triggers

Select this Skill when the deliverable, or an explicit project requirement for the task, concerns the project's **own release version**:

| Request | Work covered |
| --- | --- |
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
- Fixing a bug, adding a feature, optimizing code, or editing documentation without a requested or project-required release-version decision.
- Formatting or translating existing release notes without evaluating the version or its evidence.
- Installing, synchronizing, inventorying, or restoring Skill copies without release-policy work.

These exclusions take priority over keyword matches. For "Upgrade a dependency and choose our next application version," use this Skill for the application's version decision only. If "upgrade the version" has no clear target, resolve it from context or ask before editing. Selecting this Skill grants no extra authority to publish, deploy, create tags, or synchronize copies.
