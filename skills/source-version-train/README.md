# Source Version Train

Language: **English** | [中文](README.zh-CN.md)

`source-version-train` governs the source lifecycle of any repository, from a requirement branch through a visible publication PR and a hidden release candidate to a reviewed source commit and immutable tag. It calls packaging and publication interfaces but does not implement them.

## How To Use It

Provide the repository, requirement or branch names, version, and desired source stage when known:

```text
Use source-version-train to create a feature branch for this requirement.
Select feature/login and feature/report for dev/1.4.0.
Show which requirement PRs are ready for code integration.
Promote the approved code to publish/1.4.0 and finalize its source tag.
```

The Skill resolves the default branch, holds requirement branches until a version is selected, checks PR readiness, and updates repository-owned version metadata. The visible publication branch defaults to protected `publish/<version>`; a template may select another visible name. Changes enter it through a reviewed pull request, not a direct push. When its PR from `dev/<version>` merges, the Skill rebases that result onto the default branch and creates a hidden release candidate. It then calls the packaging interface: no implementation passes, while available `build-pipeline-engineering` performs the packaging. The publish interface works the same way and defaults to FIR, GitHub Actions Artifacts, and `wk1998.io`, with one success enough. The hidden candidate is deleted after both success and failure. Only a passing attempt is tagged and merged into the default branch. See [SKILL.md](SKILL.md) for the operational contract.

New integration trains initialize every repository-owned version value from the selected target under the repository's own version policy. Existing trains are validated and reused without another increment. The Skill discovers and uses project lifecycle tooling when available; otherwise it performs equivalent Git and version-file operations. No project script, fixed version formula, language, or particular branch naming convention is required. Publication preserves that initialized target; an early publication branch starts at the recorded default-branch baseline.

## When It Triggers

Use this Skill for requirement branches, version scope selection, `dev/<version>` integration, a visible protected publication branch, the hidden release candidate, code gates, source version metadata, or source tags.

## When It Does Not Trigger

Do not use this Skill to implement signing, packaging, checksum generation, output retention, or a single publish destination. Use `build-pipeline-engineering` for the packaging implementation. It also does not trigger for ordinary code editing without the version-train lifecycle.
