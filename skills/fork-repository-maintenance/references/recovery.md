# Recovery

Use `inspect --profile ... --offline` to read registered roles without contacting
the host. State still requires Git for reference validation. Never delete the
state root to make an error disappear: it contains role ownership and recovery
evidence.

## Uncertain or partial source writes

Keep the operation ID and original plan/digest. `resume --operation <id>
--approve-plan <digest>` repeats validation, reads current A/B identities and
refs, then reconciles send intents. If the remote already equals the desired SHA,
it records verification instead of resending. A third SHA, source advancement,
changed personal branch or default setting stops the operation for a new plan.
Previously verified branches are not reset to undo partial success.

If the plan has expired or upstream has advanced while recovery is pending,
inspect the journal and actual remote before preparing another plan. Do not edit
operation files to fabricate success. Source baselines changed externally require
an explicit audited migration; that migration is not automated in this release.

## Fork initialization

A creation request and default setting are separate effects. Resume an operation
whose created repository ID was recorded. If a request timed out before its ID
could be recorded, the tool refuses to repeat POST or claim ownership of an
existing same-name repository. Reconcile ownership first. It does not delete the
remote fork or bootstrap branches of reused repositories.

A failed clone or exclusive directory publication retains its staging path.
Inspect and preserve it; the tool refuses to overwrite a staging directory or a
new destination that appeared concurrently. Resume can recognize a completed
published checkout by the operation marker. Retained incomplete staging is not
silently discarded or automatically reused.

## Integration candidate

Only edit the returned owned candidate. Report conflicting files and intended
personal behavior. Resolve Git conflicts, continue Git's operation where needed,
then use normal commit policy (including any required agent commit-message
preflight) to commit merge/cherry-pick results. Resume runs the approved validation
before publishing. Missing or failed validation leaves the original target intact.

`abort --operation ... --approve-plan ...` aborts an active Git integration in the
candidate. After Git integration has completed, abort marks the candidate
abandoned and retains it; it does not issue reset on the personal original or
pretend merge --abort is still available. An aborted operation needs a new plan.

## Preservation and restoration

A failed snapshot or restore leaves existing snapshots and user worktrees intact
and reports retained staging. Verify manifest and bundle, including every later
record, before deciding whether to keep or remove staging. No automatic deletion
is provided. Restore into a nonexistent directory from a verified snapshot;
authentication and online default-setting verification are separate later steps.
