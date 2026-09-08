# Pull Request Review Playbook

This playbook defines the evidence required for a complete review in this
repository. It supplements the automated gate; it is not replaced by a green
gate or CI result.

## 0. Define Invariants And Plan Coverage

Before implementation, state the properties that must remain true across all
affected commands. Inventory both new entry points and existing consumers of
changed state, helpers, adapters, or formats. For work already implemented,
reconstruct this inventory before reviewing it.

Typical invariants in this repository include:

- changing one Skill must not modify an unselected Skill or registered location;
- conflicting identities must be rejected before a mutating operation writes;
- a failed replacement or recovery must retain a recoverable copy and identify it;
- inventory may write reports and locks only outside protected input trees;
- builder, reporter, repair, and rollback must agree on content and relevant modes;
- distributed Skills must run with their declared dependencies outside the checkout.

Use independently reviewable changes where practical: state migration, read-only
inventory, repair/rollback, and integration with existing commands are different
behavior boundaries. If they must ship together, explain why and test their
interactions. Line count alone does not determine the split.

Prepare the coverage ledger in section 6 before the first review. For a
documentation-only change, identify the affected rules, links, and consistency
checks; mark runtime matrices inapplicable with a reason. Do not invent runtime
tests merely to fill the ledger.

## 1. Establish The Exact Review Scope

- Fetch the PR base and head and record both exact commit SHAs reviewed.
- Inspect existing review threads, but verify each claim independently against
  the current head. Group repeated confirmations by root cause and trigger,
  retain links to the original finding, and distinguish new findings from
  independent reproductions. Do not infer review rounds from comment counts.
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
`--check`, lint, or CI step is not a runtime safety boundary. Include unchanged
callers of changed helpers and consumers of new registry records. Check early
returns such as `already-current`: they may still persist registration state.
Include lock creation, mkdir, chmod, staging, and snapshot writes when identifying
the first mutation, not just the final output replacement.

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
| ownership | same Skill, different registered Skill, unselected role or location |
| representation | legacy roles, local installs, external copies, related projects |

Use filesystem identity checks such as `samefile` where path strings are not
sufficient. On a case-sensitive runner, add a controlled substitute for the
case-insensitive identity behavior; when available, also exercise the native
case-insensitive filesystem.

Apply the matrix to each affected entry point. One tested command does not prove
that its siblings invoke the same validation. Select applicable combinations
from the actual call graph and state model; cover cross-group and cross-command
interactions explicitly. Record exclusions and untested combinations rather than
claiming that a few path probes cover the entire matrix.

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

### Distributed Artifacts And Shared Semantics

- Build each affected adapter and run the changed public commands from a copy
  of the artifact outside the source checkout. Use isolated project/state roots
  and a controlled environment so repository imports or optional tools cannot
  accidentally supply missing runtime dependencies.
- Exercise the actual built files. For executable scripts, check relevant modes
  and direct execution, including permission-only divergence and repair.
- Check producer/consumer agreement across builder, reporter, validator, repair,
  and rollback: identity, digest exclusions, status derivation, snapshot format,
  and relevant file modes. Prefer shared definitions and parameterized contract
  tests to independent copies of the same rule.
- Distinguish read-only diagnostic degradation from mutation safety. An invalid
  adapter or manifest may produce a report issue, but must not silently remove a
  protection or supply partially validated records to a mutating command.

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
- Exercise applicable sequences through public entry points: register → change
  identity → repair/rollback; repair → rollback → repeat; build → remove source
  or corrupt a later manifest record → report/repair; register a nested location
  → invoke an older sync command. Include positive controls for valid sequences.
- Inject failures during staging, replacement, post-install verification, and
  recovery, including failure of recovery itself. Verify preserved data and
  recovery diagnostics, not only the exit code. Use disposable fixtures, never
  production installs, for destructive probes.

## 5. Fix The Invariant Across Sibling Paths

For each confirmed finding:

1. Record the trigger, violated invariant, affected head, and original discussion
   link. Qualify the observed impact: losing the working install is not the same
   as losing every recoverable copy.
2. Add a regression that fails on the affected version and passes with the fix.
   When running the old version is impractical, explain why and provide the
   reproduction evidence. For documentation-only defects, verify the corrected
   contract and its consumers instead of adding an artificial runtime test.
3. Search for sibling implementations and callers governed by the same rule.
   Record each affected entry point in the ledger, including older commands and
   alternative representations, even when its source lines did not change.
4. Fix the shared boundary where appropriate and run the applicable negative,
   successful, and idempotent cases across those entry points. A shared helper
   alone is not proof that every caller uses it.
5. Recheck interactions affected by the fix, update the ledger for the new head,
   and distinguish newly discovered omissions from demonstrated regressions
   introduced by the fix. Do not label an issue a new regression without evidence.

Use these expansion prompts when applicable; they are starting points, not an
exhaustive checklist:

| Finding family | Expand the investigation to |
| --- | --- |
| Identity conflict | local/external/project copies; registration, report, repair, rollback; changed persisted metadata |
| Path ownership or containment | all groups and legacy roles; old/new sync commands; output, lock, staging, snapshots; aliases and both nesting directions |
| Freshness or equality | producer and consumer definitions; top-level/nested exclusions; content-only and mode-only changes |
| Invalid input or missing discovery | malformed persisted state; later invalid manifest records; incomplete adapter roots; read-only and mutating behavior |
| Recovery or packaging | repeated repair/rollback; installation and recovery failure; real distributed runtime and retry command |

Reply to an existing finding for repeat verification when posting is authorized.
Keep a single finding-to-fix/test mapping rather than publishing duplicate issue
lists for each reviewer.

## 6. Coverage Ledger And Completion

Keep one ledger in the PR description or a linked repository review document;
use the PR template as its starting point. It is evidence for a specific code
version, not a permanent claim that an entry point is safe.

Record the exact base/head and validation environment above the table. Each row
must identify one invariant, entry point, and scenario (or an explicitly
enumerated parameterized set). Use stable test names or reproducible commands.
For mutations, include the validation-to-first-write trace and the observed
post-failure state. For documentation, record the relevant consistency check.

| Invariant / finding | Entry point and validation → first mutation | Scenario / sequence | Test or command | Result and observed state | Gap / reason / residual risk |
| --- | --- | --- | --- | --- | --- |
| Fill with the rule or original finding link | Name the actual caller and boundary; N/A for read-only or docs | Enumerate the cases exercised | Link or exact test ID | PASS, FAIL, NOT RUN, or N/A, with evidence | Explain every NOT RUN or N/A |

Checkmarks, test counts, and statements such as “path matrix passed” do not
replace these rows. Evidence from an older head may be carried forward only
with its original SHA and an explicit explanation that the relevant paths and
dependencies are unchanged. Rerun affected evidence after fixes; rerun the full
gate on the final head.

After the independent adversarial pass, run from a clean committed worktree:

```bash
bash tests/pr-review-gate.sh <base>
```

The review report must include:

- the exact reviewed base and head commits;
- the gate result;
- the coverage ledger, including same-invariant expansion for every fixed finding;
- confirmed findings and their fix commits and regression evidence;
- cases not exercised, with the reason and residual risk;
- authoritative sources and version scope for external product claims.

Review completion requires the scoped file inventory to be read, affected entry
points accounted for, and applicable evidence recorded. A review may conclude
that changes are required; a fix is complete only when the confirmed findings
are resolved and their affected cases pass. Missing evidence for an applicable
mutation safety invariant leaves the review incomplete. Platform limitations
must be explicit: report controlled substitutes and qualify the conclusion to
the tested scope. Repeated clean reviews are not an independent completion
criterion, and no number of reviews proves that all defects are absent.

Do not declare a review complete merely because CI is green, the gate passes,
or existing tests cover the happy path.
