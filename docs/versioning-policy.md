# Versioning Policy

Language: English | [简体中文](versioning-policy.zh-CN.md)

This is the repository's required policy for choosing version increments. It
applies to new releases; it does not renumber existing releases. The policy is
enforced through CI, contribution, and review rules. CI checks version syntax,
increments, and release declarations; reviewers determine whether compatibility
claims accurately describe the implementation.

## Format And Ownership

Use `MAJOR.MINOR.PATCH` (`x.x.x`), matching
`^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$`.
Each part is a non-negative decimal integer, not a single digit: `1.2.10` is valid.
Leading zeroes, a `v` prefix, prerelease suffixes, and build metadata are not
allowed in stored release versions. The `v` in a tag such as
`skill/example/v1.2.3` belongs to the tag naming convention, not the version value.

Apply the rules independently to:

| Version owner | Compatibility boundary | Release record |
| --- | --- | --- |
| Skill `SKILL.md` → `metadata.version` | Portable workflows, triggers, inputs, outputs, safety behavior, and supported prerequisites | `skills/<skill>/CHANGELOG.md` |
| Adapter `adapter.json` → `version` | Agent adaptation, discovery, and builder configuration contract | `platforms/<agent>/CHANGELOG.md`, identify the adapter version |
| Adapter `adapter.json` → `artifact_version` | Installable bundle contents and its consumer contract | `platforms/<agent>/CHANGELOG.md`, identify the artifact version separately |

Do not copy a component's bump level into another component automatically. A
packaging-only change does not bump the portable Skill. Evaluate a released
bundle against its own previous release, including changes in bundled Skills.
See [Agent Build Architecture](agent-build-architecture.md) for ownership details.
Integer `schema_version` fields and versions in external user projects are
outside this policy. Reading legacy or external version strings is not the same
as authoring a repository release; this policy does not narrow sync parsers.

## Select The Increment

Choose the lowest level that fully describes the compatibility impact of all
changes since the same component's last release.

| Level | Required condition | Examples | From `1.2.3` |
| --- | --- | --- | --- |
| PATCH: third number | Preserve the documented contract; fix incorrect behavior or improve its implementation | Small bug fix, faster execution with equivalent results, internal refactor, restore a documented safety check | `1.2.4` |
| MINOR: second number | Add a capability while existing supported usage remains valid | Optional command or parameter, additional supported workflow, new compatible output capability | `1.3.0` |
| MAJOR: first number | Break the supported contract; existing valid usage or consumers must change | Remove a command, require a formerly optional input, incompatible output or state format without compatible handling, drop a supported environment | `2.0.0` |
| No bump | No behavior or contract change in a versioned component | Fix a README typo, clarify existing instructions, add tests, maintain repository contribution rules | Keep `1.2.3` |

For Skills, the public contract includes documented trigger and non-trigger
cases, procedure, outputs, and safety guarantees. Narrowing a supported trigger
or changing a workflow incompatibly can be MAJOR even when only Markdown changes.
Adding a trigger is MINOR only when existing routing and exclusions remain valid.
Restoring documented behavior is PATCH; introducing a new incompatible safety
requirement must be evaluated as a contract change even if motivated by a bug.
Adding output fields is MINOR only if supported consumers accept the extension.

The number of changed files, lines, commits, hours spent, or fixes does not
determine the level. A severe bug can still be PATCH; a one-line contract break
can be MAJOR. If compatibility is unclear, investigate the affected callers and
document the result before choosing a level. Do not default to MAJOR to be safe.

## Increment Mechanics And Early Versions

- Increment the selected part by exactly one and set every lower part to zero:
  PATCH `1.2.3 -> 1.2.4`, MINOR `1.2.3 -> 1.3.0`, MAJOR `1.2.3 -> 2.0.0`.
- Numbers have no decimal carry: `1.2.9 -> 1.2.10` for a fix, and
  `1.9.7 -> 1.10.0` for a compatible feature.
- For one release, aggregate pending changes and use the highest required level
  once. Three fixes plus one compatible feature mean `1.2.3 -> 1.3.0`.
  Do not bump once per commit or skip version numbers without a release reason.
- A new experimental component starts at `0.1.0`; a component with an explicitly
  established stable contract may start at `1.0.0`.
- This repository also protects documented compatibility during `0.x.x`:
  a fix is `0.2.3 -> 0.2.4`, a compatible feature is `0.2.3 -> 0.3.0`, and an
  incompatible change increments MAJOR to `1.0.0`. This is a stricter local rule
  than treating all `0.x` contracts as unstable.
- The sole non-breaking MAJOR exception is an explicit first-stable release
  (`0.x.x -> 1.0.0`). Document the supported contract and readiness evidence.
  A small fix or optimization alone is not evidence of stable-release readiness.

## Required Release Evidence

Before changing a version, record the following in the PR or change description:

1. Component and version field; previous release and proposed version.
2. Selected level (or no bump), user-visible changes, and compatibility reasoning.
3. For MAJOR, a concrete previously supported example, its new behavior, affected
   consumers, and migration steps. For a first-stable release, supply the stable
   contract and readiness evidence instead; explain whether migration is needed.
4. Tests or consistency checks supporting the claim and known limitations.

Keep unshipped changes in the owning changelog's `[Unreleased]` section. When
assigning the release version, add its version heading, UTC date, and summary of
trigger, safety, and compatibility impact in the same change. Multiple pending
commits produce one release entry. Do not change an existing released entry to
publish different contents under the same version or downgrade a release to
undo it; publish a new corrective release instead.

Repository-only documentation changes need no Skill release. If changed
documentation is deliberately distributed in a new artifact, evaluate a PATCH
artifact release while leaving unchanged Skill and adapter behavior versions
alone. The future `.changes/` workflow mentioned in the root README is not a
prerequisite: the change description and owning changelog carry this evidence.

## CI Validation

Run `python3 scripts/version_guard.py --base origin/main` after committing the
change. The required `skill-catalog` check runs this validator before generating
or committing catalogs, and `tests/pr-review-gate.sh <base>` runs it again. CI
passes the exact PR base SHA. The optional `--head <commit>` defaults to `HEAD`;
uncommitted working-tree changes are not inputs.

The validator reads committed Git blobs and compares the base's recorded versions
with the simulated merge result. An unrelated base advance does not count as a
PR downgrade; conflicting changes fail until resolved. It may create temporary
Git merge objects but does not change the checkout, index, refs, or version files.
Missing Git, missing refs, malformed metadata, ambiguous identities, or unreadable
release records fail the check. Component directories and metadata cannot be
symlinks or submodules. Skill metadata uses a block-style YAML `metadata` mapping
with direct scalar `sync_id` and `version` keys; adapter manifests use JSON.

CI checks the format of all current Skill, adapter, and artifact versions. For
each added component or changed version, it requires a new, uniquely headed entry
in its owning changelog, a valid non-future UTC date, and these non-empty fields:

```markdown
## [1.2.4] - 2026-09-10

- Change-Type: fix
- Summary: Correct handling of an already supported input.
- Compatibility: Existing inputs and outputs remain supported.
```

Use `## [<version>] - YYYY-MM-DD` for Skill and adapter releases. Use
`## [artifact <version>] - YYYY-MM-DD` for artifact releases so the adapter and
artifact cannot accidentally share evidence when their numbers match. The fields
are literal, single-line Markdown bullets inside that release section; their
names and enum values remain English in all changelogs.

| `Change-Type` | Permitted version change | Additional required fields |
| --- | --- | --- |
| `fix` | PATCH + 1; includes compatible optimization, refactoring, or artifact documentation maintenance | None |
| `feature` | MINOR + 1, PATCH = 0 | None |
| `breaking` | MAJOR + 1, MINOR = PATCH = 0, including `0.x.x -> 1.0.0` | `Breaking-Change` (old/new behavior and affected consumers), `Migration` (steps) |
| `stable` | Only `0.x.x -> 1.0.0` | `Stable-Contract`, `Readiness` |
| `initial` | New component at `0.1.0` or `1.0.0` | For `1.0.0`: `Stable-Contract`, `Readiness` |

A release declared as `fix` cannot change `1.2.3` to `2.0.0`. Downgrades, skipped
numbers, missing resets, duplicate or reused release headings, and missing
declarations fail. Skill versions are matched by immutable `metadata.sync_id`,
so renaming a directory does not reset its version history. Adapter and artifact
histories are checked independently by adapter ID.

Unchanged versions and existing historical entries do not need these new fields;
pending changes can continue to use `[Unreleased]`. The comparison baseline is
the recorded version on the PR base, not remote release tags. CI does not infer
whether an implementation change needs a release or whether a claimed breaking
change is real, and it does not enforce immutability of all historical content.
Those decisions remain review requirements. Legacy/external sync parsing and
standalone build parsing retain their compatibility; the strict release-format
boundary introduced here is the repository CI validator.
