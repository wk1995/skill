# Changelog

## [Unreleased]

- Development validation uses isolated local bare repositories and controlled GitHub adapter fixtures. A live GitHub fork/default-setting workflow remains unverified; no production test repositories are created implicitly.

## [0.0.1] - 2026-11-06

- Change-Type: initial
- Summary: Introduce selected-branch Fork initialization with an independent personal default, immutable authorized plans, manual same-name fast-forward synchronization, separately reviewed personal integration, and self-contained Git bundle preservation and offline restoration.
- Compatibility: Initial experimental contract; no previous Skill or state schema is migrated. Requires Python 3.11+, Git 2.45+ and macOS/Linux for writes. GitHub.com operations additionally require gh with the correct account and permissions. Local-provider fixtures exercise real Git; live GitHub mutation and native Windows behavior are not certified. Merge/cherry-pick candidates require review and a policy-compliant commit before resume; rebase of merge histories is rejected instead of silently flattening it.
