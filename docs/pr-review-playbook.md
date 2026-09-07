# Pull Request Review Playbook

This playbook defines the evidence required for a complete review in this
repository. It supplements the automated gate; it is not replaced by a green
gate or CI result.

## 1. Establish The Exact Review Scope

- Fetch the PR base and head and record the exact head commit reviewed.
- Inspect existing review threads, but verify each claim independently against
  the current head.
- Run `git diff --name-status --find-renames <base>...HEAD` and inspect the
  complete file list, summary, modes, generated files, and tracked ignored
  files.
- Read every changed implementation file completely. Reopen bounded ranges
  whenever combined command output is truncated.

## 2. Review In Separate Passes

Perform distinct passes so success in one area does not hide gaps in another:

1. tree shape, renames, modes, generated files, and protected state;
2. behavior and call graph;
3. destructive operations and persistence boundaries;
4. platform, filesystem, and missing-dependency behavior;
5. documentation, versioning, and external product claims.

For each public CLI command, script entry point, or callable build operation
that can mutate state, write down and verify:

```text
entry point -> mandatory validation -> first mutation -> failure-state invariant
```

Validation must be shared by or invoked from the mutating entry point. A prior
`--check`, lint, or CI step is not a runtime safety boundary.

## 3. Adversarial Matrices

### Paths And Filesystems

For copy, move, delete, synchronization, output, and rollback behavior, cover
every applicable case:

| Dimension | Cases |
| --- | --- |
| identity | same spelling, symlink alias, case-only alias to the same inode |
| containment | target inside source, source inside target, unrelated peers |
| target state | absent, empty directory, populated directory, regular file, symlink |
| location | allowed repository output, protected repository path, external path |
| persistence | fresh state, existing valid state, malformed or legacy state |

Use filesystem identity checks such as `samefile` where path strings are not
sufficient. On a case-sensitive runner, add a controlled substitute for the
case-insensitive identity behavior; when available, also exercise the native
case-insensitive filesystem.

### Recursive Rules

For reserved filenames, ignored paths, overlays, templates, and exclusions,
test both:

- the reserved item at the top level;
- the same item below one or more nested directories.

Verify the generated artifact contents, not only the source validation result.

### Executable Dependencies

Run command wrappers with a controlled `PATH` that removes each external helper
in turn. Required safety checks must either use a verified fallback or stop with
an explicit error. Absence must never turn a failed or skipped safety check into
success.

## 4. Stateful And Destructive Behavior

- Search changed code for deletion, replacement, copy, move, registry write,
  snapshot, rollback, and generated-output operations.
- Trace every caller to confirm validation happens before the first mutation.
- Exercise more than one invocation so persisted state from an earlier command
  participates in the next command.
- For every rejected operation, assert that source data, unselected roles,
  existing outputs, registries, and snapshot sets remain unchanged.
- For automatic fixes or replacement workflows, cover rejection, successful
  correction, and a second idempotent run.

## 5. Evidence And Completion

After the independent adversarial pass, run from a clean committed worktree:

```bash
bash tests/pr-review-gate.sh <base>
```

The review report must include:

- the exact reviewed head commit;
- the gate result;
- adversarial cases actually exercised;
- confirmed findings and their regression tests;
- cases not exercised, with the reason and residual risk;
- authoritative sources and version scope for external product claims.

Do not declare a review complete merely because CI is green, the gate passes,
or existing tests cover the happy path.
