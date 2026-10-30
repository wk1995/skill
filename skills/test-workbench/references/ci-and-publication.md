# CI packaging and explicit publication

## Resolve configuration before dispatch

Read repository instructions and the requested ref's workflow definitions, reusable workflows, local actions, and scripts. Discover the actual target, channel, build mode, toolchain versions, signing requirements, artifact names, and retention. A workflow step called “Upload package” may mean GitHub artifact storage; inspect the action and destination.

Resolve defaults from the user's explicit selection, then applicable project instructions, then the documented test-package mode; use Release only as the supported fallback. Discover test targets and platform destinations from actual configuration. A package-only run does not establish test execution. For App/firmware/schema/service combinations, apply [execution-quality.md](execution-quality.md#3-freeze-the-complete-tested-combination) to each participating component and verify installed/runtime identity before accepting integration results; the workflow checkout SHA identifies only the source it actually built.

Before a remote write, verify `gh auth status`, `gh api user --jq '.login'`, and the intended repository. Do not print tokens or signing material. Inspect workflow inputs, environments and ref restrictions. Manual dispatch requires a dispatch-enabled workflow registered on the default branch; do not silently merge or modify branches to make it runnable. The selected workflow ref and any separate checkout/source input must both be understood.

Typical discovery commands (fill in verified values):

```bash
gh workflow list --repo "$REPO"
gh workflow view "$BUILD_WORKFLOW" --repo "$REPO" --ref "$SOURCE_REF" --yaml
```

Only dispatch a workflow whose downstream paths stay within the requested stage. Ordinary packaging must not call external publishing, load distribution credentials, or chain a release workflow. Signing or provenance credentials may still be required by the package contract. If no package-only path exists, explain the blocker and prepare a scoped change when authorized; never fall back to the publishing path.

## Bind the run and package to source

Record the resolved source SHA immediately before dispatch. Use the workflow's verified input names. A workflow with no required inputs can be dispatched as follows:

```bash
gh workflow run "$BUILD_WORKFLOW" --repo "$REPO" --ref "$SOURCE_REF"
```

Supply any required target/variant inputs only after inspecting the YAML. Capture the returned run URL if available. Otherwise identify the new run using workflow, event, actor, ref/SHA, inputs and dispatch time; if multiple candidates remain, resolve ambiguity before using outputs. Never take the latest unrelated successful run. Inspect `gh run view` and, for custom checkouts, the build manifest/logged checkout SHA. A branch moving between resolution and checkout must be surfaced; a mismatched package is not accepted for the original SHA.

Wait for the exact job's successful completion, inspecting failures instead of treating a queued dispatch as success. Use bounded status checks and useful progress updates. Do not automatically rerun a workflow whose side effects are uncertain.

Download from the selected run into a fresh run-specific directory:

```bash
gh run download "$RUN_ID" --repo "$REPO" --name "$PACKAGE_ARTIFACT" --dir "$ARTIFACT_DIR"
```

For reruns, also record the run attempt and artifact identity; verify that downloaded outputs belong to the selected attempt/source. Select the unambiguous output set for the target, excluding test-helper packages unless requested. Fetch required companion files by their own artifact names. Check:

- package/application identity, version, expected target/channel and build mode;
- signature/provenance validity and expected publisher identity when applicable, using repository or target tooling;
- SHA-256 and agreement with the build manifest when supplied;
- required metadata, source maps, symbols or manifests and target-specific checks;
- artifact availability, actual retention, and source/run/attempt association.

A checksum calculated after download identifies those bytes; without a trusted expected digest it is not independent proof of provenance. Missing required verification tooling, metadata or artifact must be reported explicitly, and required verification blocks acceptance. An expired artifact requires an authorized rebuild; do not substitute a different package silently.

## Publish only the verified artifact

External publication requires an explicit publication request or an authorized release flow. A build-only CI request stops at artifact handoff. Describe the target before the remote write, then proceed within authorization without adding another confirmation round.

Inspect the dedicated publisher. It must validate the source run's repository, workflow, successful result, source ref/SHA, artifact identity and checksum before upload, and consume the same verified bytes without rebuilding. If the publisher pins itself to the current branch tip and the branch advanced, stop and resolve the mismatch; do not disable its checks. Keep distribution credentials inside the publishing environment. Honor an existing explicit choice such as `confirm_publish=publish` only for the authorized publish stage.

On upload failure or uncertain completion, inspect the publisher and remote version before retrying; do not blindly dispatch duplicate uploads. Never use a historical short URL as proof that this build was published. Confirm the current published package identity/version and upload evidence; compare the remote digest if available. Report which checks were possible and any uncertainty.

## Verified references and example scope

Checked on 2026-10-22:

- [GitHub manual workflow dispatch](https://docs.github.com/en/actions/how-tos/manage-workflow-runs/manually-run-a-workflow): dispatch prerequisites.
- [GitHub CLI workflow run](https://cli.github.com/manual/gh_workflow_run): ref selection, raw inputs, and returned run URL when available.
- [GitHub CLI run download](https://cli.github.com/manual/gh_run_download): run-specific named artifact retrieval.

The originating Flowtime conversation used `package-distribution.yml` with `package_type=fir`, a separate `publish-fir.yml` with `source_run_id` and `confirm_publish`, and three-day CI retention. These are historical examples, not portable defaults or a claim about the current remote configuration. Reinspect the target repository. This Skill assumes no vendor-specific publishing API schema.
