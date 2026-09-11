# Version Upgrade Policy

Language: **English** | [中文](README.zh-CN.md)

`version-upgrade-policy` helps teams define and review version changes for custom version formats. It keeps the meaning of each component explicit without assuming three numeric SemVer parts.

## How To Use It

Provide the current and proposed versions, the change, and any project format rules:

```text
Use version-upgrade-policy to decide whether 2026.09.1 -> 2026.10.0 is a feature release.
Define CI rules for A.B.C where A is compatibility, B is capability, and C is maintenance.
Review whether 1-rc-7 -> 1-rc-8 is a valid maintenance upgrade.
```

The Skill records the grammar, component meanings, successor rules, compatibility evidence, changelog requirements, and validation cases. See [SKILL.md](SKILL.md) for the operational guidance.

## When It Triggers

Use it for versioning policies, release bump decisions, custom version formats, changelog release evidence, or CI checks that enforce those rules.

## When It Does Not Trigger

Do not use it for ordinary dependency version resolution, package selection, or implementation of an already-defined checker when no policy decision is needed.
