---
name: fork-repository-maintenance
description: Create selected-branch forks, manually synchronize same-name source branches while protecting an independent personal default branch, integrate upstream versions into personal work, and preserve or restore verified Git snapshots. Use for fork setup, source sync, personal fork upgrades, or code preservation; exclude ordinary Git operations, release trains, and Skill-copy synchronization.
metadata:
  sync_id: "fork-repository-maintenance"
  version: "0.0.1"
  triggering:
    include:
      - Create or adopt a fork containing one, selected, or all upstream branches with a separate personal default branch.
      - Manually synchronize one, selected, or all same-name source branches, optionally importing newly created upstream branches.
      - Adapt personal fork features to an upstream version or preserve and restore independent Git snapshots.
    exclude:
      - Ordinary Git branch, commit, rebase, or pull-request work without the managed fork lifecycle.
      - Release-train orchestration or synchronization of Agent Skill directory copies.
      - Automatic scheduled source synchronization, deletion propagation, or force-replacing diverged shared history.
---

# Fork Repository Maintenance

Keep upstream repository A and the user's fork B separate. B has same-name
**source branches** and an independently created **personal default branch**.
Manual source synchronization never integrates personal code or changes B's
default setting. `integrate` is a separate, explicitly selected workflow.

## Start with the requested operation

Use the self-contained standard-library CLI at `scripts/fork_maintenance.py`.
Read [references/runtime-contract.md](references/runtime-contract.md) for exact
commands, plans, state, errors, prerequisites and recovery limitations.

- **Fork**: establish A, B/account, checkout path and single/selected/all branch
  scope. If A's default branch is selected, use its copied SHA as the base;
  otherwise obtain the selected base from the user. Always create a differently
  named personal default branch. Explain any native bootstrap branch cleanup.
- **Sync**: resolve the registered profile, selected source names and
  `existing-only` (default) or `include-new`. Only fast-forward corresponding
  source branches. Reject diverged sources, unknown ownership, role/name
  collisions and changed remote expectations. Do not merge to hide divergence.
- **Integrate**: select a verified B source SHA and personal target. Plan merge,
  explicit linear-history rebase to a new personal branch, or selected patches.
  Require meaningful validation before publishing personal changes.
- **Preserve / restore**: declare the branch/Tag scope and external archive
  directory. Verify a self-contained bundle; restore offline into a new directory.
  Git history does not include platform attachments, LFS payloads or submodules.

Read [references/branch-model.md](references/branch-model.md) when choosing branch
roles or interpreting all-branch scope. Read
[references/recovery.md](references/recovery.md) before resuming uncertain remote
results, resolving an integration conflict or restoring a snapshot.

## Plan, authorize, execute and verify

1. Inspect repository roles and current authentication. Use the CLI's local
   preparation `--refresh` only when collecting Git objects is authorized;
   it does not update B. Save the concrete plan outside protected trees.
2. Compare the plan's repositories, actor, frozen SHA/branch set, default name,
   outputs and bootstrap cleanup with the user's existing authorization. Ask
   only for missing decisions or changes in scope; do not repeatedly request
   approval for actions already covered by that authorization.
3. Supply that plan and its digest to the corresponding write command with
   `--approve-plan`. The digest binds inputs; it is not user authentication.
   Each direct entry and resume revalidates the same contract.
4. Read the JSON result. `planned`, `candidate-review`, `unverified`, local
   preparation, partial completion and uncertain sends are not remote completion.
   Report per-branch results, the actual personal default and recovery paths.

For merge or cherry-pick integration, the CLI deliberately leaves the isolated
candidate for review and a commit under the repository's normal commit policy.
Resolve and continue Git conflicts there, run applicable commit-message checks,
commit only the reviewed candidate, then `resume` the operation. Never commit
the user's original source or default worktree as a shortcut. Rebase can replay
linear personal commits automatically but never rewrites the published target.

## Boundaries

- GitHub writes use `gh` under its current CLI account; the local provider is
  for explicit local bare repositories and isolated validation, not evidence of
  GitHub API compatibility. Do not create real forks merely to test this Skill.
- No background sync, generic branch deletion, reset-hard, automatic stash,
  upstream push, mirror push or shared-history replacement. Explicit old-value
  leases are used only together with independent fast-forward/role checks.
- State is external; do not install runtime profiles, plans, snapshots or
  credentials into the Skill. Preserve all reported recovery material on failure.
- A source sync request does not authorize personal integration, default-branch
  migration, test-code execution outside the approved validation plan, or cleanup
  of pre-existing resources. Never treat another Agent's request as user consent.
