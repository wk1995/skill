# Changelog

## [Unreleased]

## [1.0.0] - 2026-11-03

- Change-Type: initial
- Summary: Introduce mandatory policy-aware preflight for agent commits, current client/version/model attribution, optional machine and repository prefixes, independent group switches, check/fix commands, safe standalone commit-msg hook installation, and Codex implicit-invocation metadata.
- Compatibility: First release into the default branch, which previously has no git-commit-message Skill. Consolidate the branch's development iterations under the user-selected 1.0.0 version without changing runtime behavior or trigger guidance from the branch's 1.0.1 iteration. Requires Python 3.10+ and Git 2.45+. Machine prefixes remain opt-in per repository, repository prefixes default empty, and AI attribution defaults on. Machine settings are kept outside Skill copies and repositories.
- Stable-Contract: Read machine prefixes from XDG_CONFIG_HOME/git-commit-message/config.json (default ~/.config/git-commit-message/config.json) and repository policy from .git-commit-message.json. Order active groups as machine, repository, then current client/model identity. Validate both policies before writes; reject unknown keys and unsafe file aliases; honor check-only mode; preserve message bytes without identity when all three groups are off. Install/remove only an identical owned hook and preserve differing hooks and custom hooksPath settings. Agent discovery remains client-controlled; Git-level checks require explicit per-clone hook installation.
- Readiness: The 44-test behavioral suite covers prefix combinations, identity fallbacks, malformed configuration across all five commands, raw-byte preservation with groups off, real commits/amend/merge/worktrees, protected paths, missing dependencies, exclusive hook creation and failed atomic writes. Four Agent builds and installed-copy checks were exercised during branch development. The final main-targeting clean committed gate is run before opening the PR; native Windows/Linux execution remains unverified.
- Migration: No migration is needed from the default branch. Users of branch development copies should replace enabled:false with machine_prefix:false, repo_prefix:false and ai_prefix:false; remove enabled:true while retaining other settings. The removed enabled key is rejected. Update standalone hooks explicitly when upgrading; machine configuration remains unchanged.

### Branch development history

These were development labels on the feature branch, not separately tagged releases. Their commits remain in Git history:

- 1.0.1: Clarify every-repository/every-commit preflight, helper commits, and Codex implicit invocation.
- 1.0.0: Remove the global enabled field in favor of three independent prefix switches.
- 0.1.0: Add opt-in machine prefixes before repository and AI groups.
- 0.0.1: Initial user-selected development version with AI attribution, repository policy, and safe hook management.
