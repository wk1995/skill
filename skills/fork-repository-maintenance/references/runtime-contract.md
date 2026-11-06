# Runtime contract — 0.0.1

The executable interface is `python3 scripts/fork_maintenance.py --help`. Python
3.11+, Git 2.45+ and macOS/Linux are required, including for offline inspection.
GitHub.com uses gh authentication and API version 2026-03-10. Enterprise hosts and
other platforms are not implemented. The explicit local provider operates on
real local bare repositories and is also used for isolated tests.

## Commands

All commands emit JSON. `--state-dir <external-root>` is a global option before
the subcommand; default is XDG_STATE_HOME/fork-repository-maintenance (or
~/.local/state/fork-repository-maintenance). It must be owned and not writable by
other users/groups. For writes, reject links, case aliases and containment with
source/target trees. Root-owned macOS /tmp and /var aliases are canonicalized;
arbitrary symlink aliases are rejected. Path checks are conservatively case folded.

| Command | Planning inputs | Applying |
| --- | --- | --- |
| fork | provider github/local, source, destination, scope, repeated branch, default-name, optional default-base, checkout | --plan and matching --approve-plan |
| plan-sync | profile, scope, repeated branch, new-branches existing-only/include-new | Produces plan only |
| sync | No direct write inputs | Apply saved sync plan |
| integrate | profile, source-name, optional source-oid, target, result-branch, strategy merge/rebase/cherry-pick, base-oid for rebase, repeated pick, repeated validation JSON argv | Apply saved integrate plan; review/commit candidate, then resume |
| preserve | profile, snapshot-scope a/b/both, optional include-tags, archive-root | Apply saved preserve plan |
| restore | snapshot directory, destination-path (must not exist) | Apply saved restore plan; network is not used |
| inspect | profile; optional offline | Read-only; online failures are not success |
| resume / abort | operation ID and matching approve-plan | Resume original plan; abort only cancels an isolated integration |

Direct fork/integrate/preserve/restore inputs require --dry-run. An explicit
--refresh performs local object preparation before returning a plan; it never
updates B. --save-plan writes a new plan file only, after input and output-path
validation. Without refresh, missing objects block planning. An apply cannot be
combined with new repository/scope/path/strategy arguments or refresh. Resume
likewise cannot replace the original plan inputs.

Plan JSON rejects duplicate/unknown keys and invalid types. Digest uses canonical
UTF-8 JSON excluding the digest field. Plans expire after 24 hours; input drift
or expiry requires a new plan. Authorization is the caller's responsibility:
approve-plan binds explicit inputs and is not cryptographic authentication.

## State schema v1

```text
<state>/
  profiles/<profile-id>.json
  operations/<operation-id>.json
  locks/<profile-id>.json
  cache/<profile-id>/                 owned bare object repository
  candidates/<operation-id>/          isolated integration checkout
  snapshots/.fm-archive.json
  snapshots/<snapshot-id>/manifest.json
  snapshots/<snapshot-id>/history.bundle
```

An explicit archive-root replaces only snapshots, not state/profile/log storage.
An existing nonempty archive directory must carry the owned archive marker.
Profiles are keyed by canonical destination address; immutable repository IDs
are revalidated before online writes. Renames or reconstruction at the same
address require explicit migration, not automatic reidentification. Local IDs
also bind device/inode. Future schema migration must be explicit.

An operation journal contains its original plan, stage, send intents, per-ref
verified receipts, created-fork identity, original/proposed profiles, candidate
and recovery paths. Source baseline changes only after remote readback. After
uncertain send or failed state persistence, reconcile the remote first. Journals
and pinned Git anchors remain available; no automatic history or snapshot cleanup.

## Results and limitations

Exit 0 carries a status that must still be read: planned, candidate-review,
unverified and verification-failed do not mean a remote update completed.
completed with remote_verified=true confirms the specific fork/sync/integration.
Snapshots and offline restores use remote_verified=false by design.

Exit 2 is invalid input/state; 3 is blocked; 4 is partial publication; 5 is an
uncertain outcome; 6 is an execution/recovery error. Failure JSON includes the
operation ID and retained recovery paths when an operation exists. An interrupted
process may have no final JSON: use the journal, never assume no writes occurred.

GitHub API fixtures are tested; real fork creation/default-setting/protection
interactions remain unverified. Initializing a reused repository is deliberately
limited to an explicitly selected compatible head set without extra branches.
An unknown asynchronous creation outcome is never resolved by another create
request. Inspect the named destination and retain the original operation.

Only linear personal histories can be rebased automatically. Published rebase
results require a new personal result branch. Merge/cherry-pick require a normal
reviewed commit in the returned candidate before resume; the script does not
invent author attribution or bypass repository commit-message checks. Approved
validation commands run as argv arrays in that candidate and must not alter HEAD
or leave tracked/untracked files behind. Git filters are disabled in generated
checkouts to avoid unrequested downloads or filter execution.

Snapshots are self-contained for their declared Git refs. LFS payloads,
submodule repositories, working-tree edits and platform metadata are not included;
project_complete is false. Offline B restoration needs B's personal default in
the manifest and verifies refs in a fresh object database. Restored remote
configuration contains no credentials, and the remote default remains unverified.
