# Android Version Train

Language: **English** | [中文](README.zh-CN.md)

`android-release-train` orchestrates a protected Android delivery path from feature or bugfix branches through version integration, release promotion, a signed AAB, Play publication, and a verified release tag.

## How To Use It

State the version, branches, repository, and desired release stage when known. Typical prompts include:

```text
Use $android-release-train to list feature branches ready for version 1.4.0.
Create a feature branch for this Android requirement and open its PR.
Prepare the dev/1.4.0 integration train from feature/login and feature/report.
Promote release/1.4.0 after its checks pass, then publish the signed AAB to internal testing.
```

The skill resolves the repository's default branch rather than assuming `main` or `master`. It inventories branch readiness before selection, keeps version metadata changes in the protected release flow, and uses the same verified AAB for track promotion. Remote writes are stated in advance and require the relevant release gates and credentials. See [SKILL.md](SKILL.md) and its release-train contract for the detailed procedure.

## When It Triggers

Use this skill when the request:

- creates, assesses, integrates, promotes, publishes, or tags an Android version train;
- involves Android feature or bugfix branches, `dev/<version>` or `release/<version>` branches, AAB signing, Play-track promotion, or release tags; or
- needs Android release-train CI, release configuration, branch gates, or a readiness inventory.

## When It Does Not Trigger

Do not use this skill when the request:

- is a general Android build, test, or code-change task without version-train or release orchestration; or
- only manages copies or metadata of Skills; use `sync-skills` instead.
