# Source Version Train

Language: **English** | [中文](README.zh-CN.md)

`source-version-train` carries a requirement branch through `dev_<version>`, a visible `publish_<version>` pull request, and a hidden release candidate, then calls packaging and publication before tagging the result. Packaging passes when no implementation is available and otherwise runs through `build-pipeline-engineering`. Publication sends the candidate to GitHub Actions Artifacts by default. The Skill does not name other publish channels or implement signing, checksums, retention, or a destination's upload.

## How To Use It

Provide the repository, requirement or branch names, version, and desired source stage when known:

```text
Use source-version-train to create a feature branch for this requirement.
Select feature/login and feature/report for dev_1.4.0.
Show which requirement PRs are ready for code integration.
Promote the approved code to publish_1.4.0 and finalize its source tag.
```

The Skill resolves the default branch, holds requirement branches until a version is selected, checks PR readiness, and updates repository-owned version metadata. The integration branch is resolved only from `integration_template`, which defaults to `dev_<version>`, such as `dev_5.1.3`. The visible publication branch is resolved only from `publish_template`, which defaults to protected `publish_<version>` with a `major.minor.patch` version, such as `publish_5.1.3`. A repository may replace either template; no separate prefix is applied. Changes enter the publication branch through a reviewed pull request, not a direct push. When its PR from `dev_<version>` merges, the Skill rebases that result onto the default branch and creates a hidden release candidate. Any permitted build-number adjustment happens on that candidate, after the rebase and before packaging, and must pass the candidate gates again. It then calls the packaging interface: no implementation passes, while available `build-pipeline-engineering` performs the packaging. The publish interface sends the candidate to GitHub Actions Artifacts by default and does not name other channels. Retrying the same commit skips destinations already recorded as successful and sends it only to destinations that failed. The hidden candidate is deleted after both success and failure. Only a passing attempt is tagged and merged into the default branch. If that merge fails after the tag exists, keep the tag and every branch and continue from the existing tag; do not recreate it. `dev_<version>` stays until the tag is verified and the default-branch merge succeeds, including when publication fails. See [SKILL.md](SKILL.md) for the operational contract.

New integration trains initialize every repository-owned version value from the selected target under the repository's own version policy. Existing trains are validated and reused without another increment. The Skill discovers and uses project lifecycle tooling when available; otherwise it performs equivalent Git and version-file operations. No project script, fixed version formula, language, or particular branch naming convention is required. Publication preserves that initialized target; an early publication branch starts at the recorded default-branch baseline.

## When It Triggers

Use this Skill for requirement branches, version scope selection, `dev_<version>` integration, a visible protected `publish_<version>` branch, the hidden release candidate, code gates, source version metadata, or source tags.

## When It Does Not Trigger

Do not use this Skill to implement signing, packaging, checksum generation, output retention, or a single publish destination. Use `build-pipeline-engineering` for the packaging implementation. It also does not trigger for ordinary code editing without the version-train lifecycle.
