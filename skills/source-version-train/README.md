# Source Version Train

Language: **English** | [中文](README.zh-CN.md)

`source-version-train` governs the source lifecycle of any repository, from a requirement branch through version integration and publication to a reviewed source commit and immutable tag. It does not build, sign, package, or upload release artifacts.

## How To Use It

Provide the repository, requirement or branch names, version, and desired source stage when known:

```text
Use source-version-train to create a feature branch for this requirement.
Select feature/login and feature/report for dev/1.4.0.
Show which requirement PRs are ready for code integration.
Promote the approved code to publish/1.4.0 and finalize its source tag.
```

The Skill resolves the default branch, holds requirement branches until a version is selected, checks PR readiness, promotes reviewed code, and updates repository-owned version metadata. Publication defaults to a protected `publish/<version>` branch; set a publication template to use another name, such as `release/<version>`. Changes enter that branch through a reviewed pull request, not a direct push. After those checks pass, the Skill rebases it onto the default branch, pushes that result, and reruns the checks. A repository with CI packaging then builds that commit through `build-pipeline-engineering`; without CI packaging, the passed checks are enough. The publish interface then runs its configured implementations, including FIR, GitHub Actions Artifacts, and `wk1998.io`. One success is enough by default. Only then does the Skill tag that commit and merge it into the default branch. See [SKILL.md](SKILL.md) for the operational contract.

New integration trains initialize every repository-owned version value from the selected target under the repository's own version policy. Existing trains are validated and reused without another increment. The Skill discovers and uses project lifecycle tooling when available; otherwise it performs equivalent Git and version-file operations. No project script, fixed version formula, language, or particular branch naming convention is required. Publication preserves that initialized target; an early publication branch starts at the recorded default-branch baseline.

## When It Triggers

Use this Skill for requirement branches, version scope selection, `dev/<version>` integration, a protected publication branch, code gates, source version metadata, rebasing a verified publication onto the default branch, or source tags.

## When It Does Not Trigger

Do not use this Skill to configure or run signing, packaging, checksum generation, output retention, artifact uploads, store delivery, or package publication. Use `build-pipeline-engineering` for those requests. It also does not trigger for ordinary code editing without the version-train lifecycle.
