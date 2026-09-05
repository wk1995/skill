# Paired Android submodule build pipeline

Use this reference when a parent Android SDK/library build consumes SO files or another lower-level artifact from a child repository or submodule.

## Immutable source contract

- Resolve the parent input to an exact commit.
- Read the exact child commit recorded by the parent; never substitute a moving child branch head.
- Verify the child commit is available and, when repository policy requires it, is contained in the expected reviewed source line.
- Record both SHAs in every manifest and parent artifact's build evidence.
- Source branch creation, paired-branch synchronization, PRs, version commits, tags, and cleanup remain outside the artifact workflow.

## Cross-repository build flow

Separate workflows are preferred when the child output must appear in the child repository's GitHub Actions Artifacts:

1. The parent workflow resolves the pinned child SHA.
2. It dispatches the child workflow with child SHA, expected variant/ABI, parent SHA, and non-source build inputs.
3. The child checks out that exact SHA, builds the SO/native outputs, verifies them, and uploads an artifact plus manifest and checksums.
4. The parent waits for the child run, verifies its identity and checksums, and downloads the artifact.
5. The parent builds the AAR or SDK from the pinned child output, validates its contents and local publication, then uploads the verified parent artifact and combined manifest.

If one workflow builds both repositories, the child output normally belongs to the parent run's artifact set. Choose the split based on the required ownership and visibility of GitHub Actions Artifacts.

## Required configuration

- Exact parent/child source-ref mapping.
- Toolchains, child ABI/variant matrix, native build command, and expected output patterns.
- Parent module/publication, build command, expected AAR/JAR paths, and validation command.
- Workflow-dispatch and Actions read permissions across repositories when workflows are split.
- Artifact names, retention, manifest schema, and checksum algorithm.
- Protected signing or publishing credentials when required.

## Validation checklist

```bash
git submodule update --init --recursive
git submodule status --recursive
```

- Parent checkout equals the requested parent SHA.
- Parent source records the child SHA that was actually built.
- Child workflow checked out the exact child SHA.
- Native outputs match the required ABI/variant and checksums.
- Parent artifact contains the expected child payload.
- Local publication or package inspection succeeds.
- Required child and parent artifacts are visible in their intended workflow runs.

Missing or mismatched child evidence blocks the parent build. Retrying must preserve both source SHAs; if either source changes, treat it as a new build input rather than silently reusing evidence.
