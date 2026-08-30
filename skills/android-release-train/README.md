# Android Version Train

Language: **English** | [中文](README.zh-CN.md)

`android-release-train` orchestrates a protected Android delivery path from feature or bugfix branches through version integration, release promotion, a signed Android artifact, configurable distribution, and a verified release tag.

## How To Use It

State the version, branches, repository, and desired release stage when known. Typical prompts include:

```text
Use $android-release-train to list feature branches ready for version 1.4.0.
Create a feature branch for this Android requirement; do not open a PR until I select its version.
Prepare the dev/1.4.0 integration train from feature/login and feature/report.
Promote release/1.4.0 after its checks pass, then distribute the signed APK to the enterprise MDM test group.
```

In OpenAI Codex you can invoke the skill explicitly with `$android-release-train`. In ZCode the same prompts trigger the skill automatically from its `description` and `when_to_use` metadata; run `scripts/link-zcode-skill.sh` once from this repository to link it into `~/.zcode/skills/`.

The skill resolves the repository's default branch rather than assuming `main` or `master`. A feature branch has no PR until it is explicitly selected for a version; the selection creates `dev/<version>` and feature-to-dev PRs. It inventories those PRs before merging, keeps version metadata changes in the protected release flow, and distributes the same verified AAB or APK to every configured destination. Google Play is optional: configure another store, enterprise MDM, direct delivery, or artifact-only delivery when appropriate. Remote writes are stated in advance and require the relevant release gates and credentials. See [SKILL.md](SKILL.md) and its release-train contract for the detailed procedure.

## When It Triggers

Use this skill when the request:

- creates, assesses, integrates, promotes, publishes, or tags an Android version train;
- involves Android feature or bugfix branches, `dev/<version>` or `release/<version>` branches, AAB/APK signing, distribution to a store, enterprise MDM, direct recipients, or an artifact archive, or release tags; or
- needs Android release-train CI, release configuration, branch gates, or a readiness inventory.

## When It Does Not Trigger

Do not use this skill when the request:

- is a general Android build, test, or code-change task without version-train or release orchestration; or
- only manages copies or metadata of Skills; use `sync-skills` instead.
