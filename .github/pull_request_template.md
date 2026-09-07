## Summary

Describe the intended change and its scope.

## Validation

- [ ] I ran `bash tests/pr-review-gate.sh origin/main` from a clean, committed worktree.
- [ ] I reviewed deletions, renames, executable-bit changes, and generated files in the full PR diff.
- [ ] I added negative and state-sequence tests for changed behavior where applicable.
- [ ] I traced every destructive or persistent entry point from validation to its first mutation and tested direct invocation without relying on a prior `--check`.
- [ ] I exercised applicable path-identity, nesting, recursive reserved-name, and missing-executable cases from `docs/pr-review-playbook.md`.
- [ ] I confirmed rejected operations leave source data, unselected state, existing outputs, and snapshots unchanged.
- [ ] I verified external product claims against current authoritative documentation or versioned product configuration.

## Evidence

Paste the reviewed head SHA, gate result, adversarial cases exercised, and any untested or intentionally deferred case with its residual risk.
