# Changelog

## [Unreleased]

## [0.1.0] - 2026-11-21

- Change-Type: initial
- Summary: Introduce a read-only-by-default audit for multi-device and team Git clones, branch classification for behind, ahead, diverged, rewritten, upstream-gone, unpublished, and foreign-upstream states, squash-merge detection through `git merge-tree --write-tree`, fast-forward sync with explicit rebase and rewrite reset paths, archive-first local and remote pruning, lease-checked remote deletion, open-pull-request blocking, and archive listing and restore.
- Compatibility: First release on the default branch, which previously had no git-repo-sync Skill. No migration is required. The default invocation of `sync` and `prune` is non-destructive; their mutations require `--apply`, while `restore` is an explicit branch-creation command. The tool never pushes commits, never force-pushes history, and refuses bare repositories, shallow-clone cleanup without `--allow-shallow`, unmerged deletion without explicit `--branch` names and `--allow-unmerged`, and operations in progress. Requires Python 3.10+ and Git 2.38+ for squash-merge detection; older Git falls back to ancestor-only detection and treats squash-merged branches as unmerged.
