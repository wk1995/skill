# Changelog

All notable changes to this Skill are documented here.

## [Unreleased]

## [1.0.0] - 2026-10-15

- Change-Type: breaking
- Summary: Add project policy beside the project Skill and one shared machine policy for every Agent platform. Upgrade a pre-existing Skill-adjacent machine policy into that shared file without changing its content. Exclude project policy from builds, sync copies, and digests.
- Compatibility: Existing root policies remain supported as a base-only fallback, and legacy machine-wide top-level settings and `comment_targets` continue to work. A new machine policy is no longer read from beside an installed Skill. On first use, identical legacy machine files are copied to `$XDG_STATE_HOME/skill/pr-review-loop.yml` (or `$HOME/.local/state/skill/pr-review-loop.yml`); an existing shared file is preserved, and differing legacy files are reported instead of merged.
- Breaking-Change: Previously, an installed adjacent machine policy took priority over an existing shared XDG file; now the shared file is authoritative. With adjacent `comment: false` and shared `comment: true` plus a matching legacy target, comments change from disabled to enabled even without a `projects` mapping. This changes existing authorization precedence for Codex, WorkBuddy, and WorkBuddy AI installations.
- Migration: Before the first review, compare every legacy adjacent policy with the shared file and explicitly select the intended settings in the shared file. Keep comments disabled there until the effective targets and limits are verified. If the shared file is absent, identical legacy files can be copied with `upgrade-machine-policy`; differing files require manual reconciliation. Legacy originals are retained.
- All Agent platforms resolve machine settings from the same state file. Do not create `pr-review-loop.yml` beside Codex, WorkBuddy, or WorkBuddy AI installations.
- Before resolving policy, copy one regular legacy `<agent-skill-root>/pr-review-loop/pr-review-loop.yml` to the shared path only when the shared file is absent and every such legacy file has identical bytes. Preserve file mode, refuse symlinks, and leave the legacy files in place.
- A project Skill without its own adjacent policy still does not inherit the shared machine policy.
- Check this review's user criteria first, then apply required repository and project standards; record sources and explain conflicts.
- Select the active project Skill by `metadata.sync_id` before a machine-wide copy. A project Skill without adjacent policy does not inherit the machine-wide policy, and only a machine-wide copy may use the XDG fallback. A PR cannot introduce the Skill or policy that governs its own review.
- Separate review eligibility, `max_rounds`, and PR commenting. Project policy or a project Skill covers its own project without `comment_targets`; a machine-wide Skill requires a matching target. An authenticated PR author may fix and push for the configured review cycles even when `comment` is false. Only `comment: true` or an explicit request for this review enables PR comments; a machine-wide boolean grant also requires a matching target.
- Count completed reviews, including a passing review, against `max_rounds`. Zero performs one read-only review; one permits one review and its fix without claiming the pushed head was re-reviewed. Reject invalid limits before a fix, and retry review attempts that could not run without counting them as reviews.
- Finish and verify feasible fixes before stopping for findings that cannot be fixed. Push only a verified change, never manufacture an empty commit, and report remaining findings. Reuse a passing result only when base, head, requested scope, standards, and evidence of completed checks are unchanged.

## [0.1.0] - 2026-09-17

- Change-Type: initial
- Summary: Add `pr-review-loop`, a portable workflow Skill that reviews a pull request, posts each round's confirmed findings to the pull request under a `[<platform>][<model>]` marker, fixes and pushes them, and repeats until a round produces no confirmed findings. It defines the loop — trigger gate, attribution, round ordering, stop conditions, boundaries, and the round report — and intentionally defines no review criteria; each round resolves its method from the repository review standard, project documentation, user-stated criteria, or the host's general review capability.
- Compatibility: New component, so there is no earlier contract to preserve. The Skill adds no dependency, installs nothing, and changes no existing Skill, adapter, or artifact. It runs only when a single pull request is identified and write access exists, so requests without a pull request, read-only review requests, and pull-request administration keep their current behavior and remain outside this Skill.
