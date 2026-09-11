---
name: version-upgrade-policy
description: Define, choose, validate, or apply a project's own release versions, including initial values, compatibility-based increments, custom formats, changelog evidence, and version-policy CI checks. Do not use for dependency/tool upgrades, ordinary code fixes, or build/publish execution alone.
metadata:
  sync_id: "version-upgrade-policy"
  version: "0.1.0"
  triggering:
    include:
      - Define or explain a project's own release-version format, component meanings, ordering, successor rules, resets, or initial value.
      - Decide whether released changes need a version bump and which level matches fixes, features, or breaking compatibility.
      - Validate or apply a requested release version in the project's authoritative source version fields using its existing policy.
      - Design, implement, review, or fix checks of the project's release-version grammar, increments, initial values, or required release evidence, including CI under an already-defined policy.
      - Prepare or review changelog declarations and compatibility or migration evidence needed to justify a release-version decision.
    exclude:
      - Only update dependencies, lockfiles, runtimes, SDKs, or tools, resolve package versions, or compare third-party versions under package-manager rules, without deciding the project's own release version.
      - Only compile, test, sign, package, create branches or tags, merge, publish, deploy, or roll back an already-selected release; a supplied version is only an execution input.
      - Only implement a feature, fix a bug, optimize code, or edit documentation, without a requested or project-required release-version decision.
      - Only format or translate existing release notes without assessing the version decision or its required evidence.
      - Only install, synchronize, inventory, or restore Skill copies without designing or reviewing their release-version policy.
---

# Version Upgrade Policy

Define the version contract before changing a version. A version is a sequence of ordered components chosen by the project; it is not automatically SemVer.

## Apply the trigger boundary

Select this Skill when the requested deliverable, or an explicit project requirement for the task, involves the project's own release-version contract, value, validation, or justification. A version string or the word "upgrade" alone is insufficient. The exclusions describe tasks that contain no such work; they take priority over broad keyword matches.

For a mixed request, apply this Skill only to its version-policy portion. For example, upgrading a dependency and deciding the application's next version includes a policy decision; upgrading that dependency alone does not. Building version `1.2.4` uses a selected version, while changing the source version to `1.2.4` requires validation and applies this Skill. An existing policy remains authoritative when implementing its checks; do not redesign it merely because this Skill was selected.

If "upgrade the version" does not identify whether the target is the project's release, a dependency, or a tool, inspect task context and the relevant version fields. Ask which target is intended if it remains unclear before changing versions. Selection does not authorize unrelated branches, tags, publication, deployment, or synchronization.

## Establish the format

Record, for the project:

- the separator and component count, or whether variable length is allowed;
- the allowed token grammar for each component (numeric, alphabetic, enumerated labels, dates, or mixed tokens);
- the ordering between components and any comparison rules;
- which component represents breaking compatibility, new compatible capability, maintenance, release channel, or another project-specific meaning;
- how a component is incremented when it is not numeric (for example an explicit ordered enum or a next-value table);
- whether leading zeroes, case changes, suffixes, and new components are meaningful.

Do not reject `A.B.C`, `2026.09.1`, `1-rc-7`, or a four-component version merely because it is not `x.x.x`. Reject it only when it violates the project's declared grammar.

## Choose an initial version

For a component with no previous release, use the initial value explicitly supplied by the user or required by the project's existing policy. If neither specifies a value, default to the numeric version `0.0.1`; do not silently choose `0.1.0`, `1.0.0`, or an alphabetic starting value.

Validate that initial value against the project's grammar before writing it. If the default `0.0.1` conflicts with an explicitly chosen format (for example four mandatory components or alphabetic-only tokens), ask for the initial value instead of coercing the format or inventing a token. If no format is established, use three dot-separated numeric components for this default, with compatibility, feature, and maintenance meanings respectively. An explicitly specified initial value can use the project's custom component count and tokens.

Apply this default only to a genuinely new component. A missing local version file or unavailable release history is not evidence that no release exists; inspect the project's authoritative release records. Keep existing releases on their established upgrade path and record the initial value and its source in the release evidence.

## Select one upgrade

Choose the smallest level that describes all released changes since the component's previous version. Change exactly the component assigned to that level. Reset or replace every less-significant component according to the project's contract. Leave more-significant components unchanged.

Typical compatibility mapping:

| Impact | Typical action |
| --- | --- |
| Behavior-preserving fix or optimization | Advance the maintenance component by one valid step |
| Backward-compatible capability | Advance the feature component and reset lower components |
| Breaking contract change | Advance the compatibility component and reset lower components; include migration guidance |
| No released behavior change | Keep the version unchanged |

These labels are examples, not universal positions. A date-based or channel-based scheme may assign different meanings. If a token is not numeric, use the declared successor (`alpha → beta`, an enum table, or a project-defined replacement); never invent arithmetic. If a change spans levels, advance only the highest required level once per release.

## Evidence and validation

For every bump, record the previous value, proposed value, selected impact, affected compatibility boundary, and evidence. Breaking changes require an old/new behavior example, affected consumers, and migration steps. A new component or format requires an explicit initial-release rule.

CI should validate the project grammar, parse the version into its declared components, compare old and new values, enforce the one-step rule and lower-component resets, and require a changelog entry. Keep parsing and comparison in one shared implementation used by release tooling, catalogs, builders, and sync clients. Validate before any generated-file or publishing mutation.

Tests should cover valid and invalid token forms, every component count supported by the project, numeric rollover, nonnumeric successor tables, separator and case rules, no-bump changes, each impact level, skipped or repeated increments, and failed validation preserving files and release state.

For repository-specific rules and examples, read the project's versioning policy and changelog instructions before editing files.
