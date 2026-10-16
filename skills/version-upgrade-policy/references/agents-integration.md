# Add Version Rules To AGENTS.md

Read this reference when asked to install or update a project's persistent version-upgrade instructions. This is an instruction-editing workflow; it does not itself authorize a release, tag, publication, or deployment.

## Resolve Scope And Existing Rules

1. Resolve the target project from the user's request or the active workspace. If multiple projects remain plausible, ask which one before writing. Read the instructions that govern that project and the applicable AGENTS.md files, including nested scopes relevant to the requested components. Edit only the requested scope; do not write machine-wide instructions or unrelated repositories.
2. Read the project's version policy, authoritative version files, changelog convention, release process, and available validation commands. Record component ownership, existing grammar, initial version rules, and when a release version is finalized. Two-part, four-part, alphabetic and mixed formats remain valid when the project defines them. A calendar or enum successor is not automatically numeric +1.
3. Locate an existing version-policy section by its meaning, not only by its heading or markers. Extend that section instead of adding a competing one. Preserve unrelated instructions and project-specific rules. If existing sections conflict, resolve them from the authoritative project policy and explicit user intent; ask only for a decision that cannot be established from those sources. Do not silently replace established rules with the generic defaults below.
4. Prepare a concise section in the target document's language. Include verified project-relative paths to its version policy and authoritative version fields when available; mention validation commands only after verifying they exist. Do not copy machine-specific Skill installation paths, repository-specific scripts from the Skill authoring repository, or unresolved placeholders into the target project. If an empty project has no established versioning scheme, state the provisional default and record what still needs definition; do not invent release metadata files or scripts.

## Reusable Section

Adapt this block to the resolved project. Its instructions remain useful even when the Skill is unavailable. Keep existing release timing or changeset conventions when they provide an equivalent record to `[Unreleased]`.

```markdown
## Version Impact And Release Rules

After completing a feature, bug fix, optimization, interface or behavior change, proactively assess the impact on the affected component's next release, even when the user has not asked to increase the version. Documentation or configuration changes that alter a public contract require the same assessment. Assess dependency/tool changes when they affect the project's own supported behavior or compatibility; third-party version numbers alone do not determine this project's release level.

Use version-upgrade-policy when available. If unavailable, apply the rules in this section and the project's existing version policy directly, and disclose that the Skill was unavailable; do not skip the assessment.

- Identify the affected component, its authoritative version field, previous release, relevant changes, and compatibility boundary. Treat components with independent release histories independently. Use authoritative release records; a missing local version file does not prove this is an initial release.
- Classify the change as a compatible fix/optimization, compatible capability, breaking change, or no release impact. State the reason and supporting checks in the completion or PR summary. A small compatible fix must not advance a component reserved for breaking compatibility. Documentation-only edits that preserve behavior may conclude no bump.
- Follow the project's declared component count, token grammar, meanings, ordering, successor and reset rules. Do not impose three numeric parts on an established custom format. For an initial release, use an explicit or project-required value; otherwise default to numeric 0.0.1. Resolve any conflict with an explicitly chosen format before writing it, and never reset an existing release to this default.
- During development, record pending release-relevant changes in the owning changelog's [Unreleased] section or the project's established changeset mechanism. Assess impact after changes without incrementing the version for every commit or repeatedly incrementing an already-selected release version during review.
- At the project's established release-finalization step, aggregate changes since the same component's previous release. Advance the highest required level once by its declared successor, retain more significant components, and reset lower components according to the project policy. Validate an explicitly requested version against the same rules. If the target release already incorporates that decision, update its pending evidence without advancing it again. Never rewrite a published version to distribute new content.
- When assigning a release version, update its authoritative fields and owning release record together. Record previous/new values, selected impact, compatibility evidence, and the date. Breaking changes require a concrete old/new behavior example, affected consumers, and migration guidance.
- Run the project's existing version and release-evidence checks after edits. Report missing checks explicitly rather than claiming CI verifies them; a passing syntax/increment check does not establish the truth of compatibility claims.

This assessment requirement does not grant additional authority to create tags, publish, deploy, or synchronize copies. Perform those actions only within the user's task and established project workflow.
```

## Apply And Verify

- Show or write the prepared section according to the user's requested action. A request to add the rules authorizes the scoped AGENTS.md edit. If that file does not exist, create it at the resolved scope; if it exists, update only the relevant section. Do not replace the whole file or modify sibling projects to make the rule global.
- Read the result and inspect its diff. Confirm unrelated instructions are preserved, version rules are not duplicated, project-relative references resolve, and newly added commands are real. Review nested overrides that could prevent the intended rule from applying; report conflicts outside the requested scope instead of silently expanding the edit.
- Re-evaluate a normal "add a feature" and "fix a bug" task against the resulting instructions: each now requires a version-impact assessment without an explicit bump request. A neutral documentation edit can still result in no bump. Pending development should produce release notes or changesets, while release finalization should select the version once.
- Check a repeat application against the resulting file. Equivalent instructions require no further edit; later policy changes update the existing section without appending a duplicate. Report the target file, changed section, configured rules, missing information/checks, and whether a repeated application would be a no-op. Do not claim a general automated installer or independent routing test when only the instructions were edited.
