---
name: version-upgrade-policy
description: Define, review, and apply a project's version upgrade rules when version components may use any count, separator, ordering, or character set. Use this to classify changes, choose the smallest valid increment, document compatibility, and design checks without assuming numeric x.x.x SemVer.
metadata:
  sync_id: "version-upgrade-policy"
  version: "0.1.0"
  triggering:
    include:
      - The user asks how a version should change after a fix, feature, breaking change, or compatibility change.
      - A project needs a versioning policy, upgrade matrix, changelog requirements, or CI validation for custom version strings.
      - A review must decide whether a proposed version bump matches the impact of a change.
    exclude:
      - The task requires implementing a repository-specific CI checker without first defining its version contract.
      - The task is only about dependency resolution, package selection, or comparing versions under an existing package manager rule.
---

# Version Upgrade Policy

Define the version contract before changing a version. A version is a sequence of ordered components chosen by the project; it is not automatically SemVer.

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
