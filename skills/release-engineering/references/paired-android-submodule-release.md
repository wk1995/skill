# Paired Android Submodule Release Flow

Use this reference for Android SDK/library repos where a parent repo publishes the AAR and a child repo or git submodule produces SO files or another lower-level artifact. The parent commit must pin the exact child commit that was built.

## Applicability

- Parent repo contains a child repo as a git submodule or otherwise records an exact child commit.
- Parent release branches use `*/dev_V` for development and `publish_V` for publish integration. `V` is a release identifier, not necessarily a semantic version; it may be a date, version string, or other agreed token.
- Child release branches are paired with parent branches by repository-specific configuration, scripts, or workflow inputs. Do not hard-code a generic prefix. Some repos use the same branch names in both repos; others use prefixes, suffixes, or different main branch names.
- Base branch is repository-specific, often `svm-main` in this family of repos.
- `publish_V` branches are automation-owned. Ordinary users generally should not create or push them directly unless the repository policy explicitly allows it.

## Source Contract

- The parent source is the reviewed parent commit on `publish_V`, including version files, build scripts, workflows, and the submodule pointer.
- The child source is the exact child commit recorded by the parent, not a moving child branch head.
- Validate that the recorded child commit is contained in the expected paired child `dev` or `publish` branch before release.
- After child repo commits, the parent repo must commit the updated submodule pointer. Local hooks can help, but CI must still validate the pointer.

## Bootstrap and Local Sync

For new machines, prefer a repository bootstrap script that performs both submodule setup and hook installation:

```bash
./scripts/bootstrap.sh
```

For Windows, provide `.cmd` or PowerShell entry points, for example:

```bat
scripts\bootstrap.cmd
```

```powershell
powershell -ExecutionPolicy Bypass -File scripts\bootstrap.ps1
```

Bootstrap should run `git submodule update --init --recursive` and install any local hooks used by the repo. Common hooks are:

- Parent `post-checkout`: when the parent switches branches, update the child worktree to the child commit recorded by the parent, then switch or create the paired child branch according to repository mapping.
- Child `post-commit`: stage the parent submodule pointer after a child commit. Auto-committing the parent pointer is optional and must be an explicit repo policy.

Hooks are local developer convenience only. Release workflows must not rely on hooks being installed.

## Branch Sync Flow

When a parent `*/dev_V` branch is created or pushed:

For GitHub Actions implementations, configure both creation and push triggers when the intended behavior is "create or update `publish_V` whenever `dev_V` or `*/dev_V` is pushed":

```yaml
on:
  create:
  push:
    branches:
      - 'dev_*'
      - '**/dev_*'
```

`create` only covers new branch creation. It does not run for later pushes to an existing `dev_V` branch. A `push` event can run a workflow from the pushed branch itself, including workflows that have not yet been merged to the default branch. Default-branch presence is still relevant for Actions UI registration and for events that GitHub defines as default-branch-only, but it is not a requirement for normal branch `push` workflows.

1. Derive `V` from the parent branch and derive paired child branch names from repo-owned mapping config or scripts.
2. If parent `publish_V` does not exist, create it from the parent base branch. If it exists, rebase it onto the parent base branch and push with `--force-with-lease`.
3. Ensure the paired child `dev` and `publish` branches exist or are synced according to the same release identifier and repo mapping. Existing child publish branches should be rebased onto the child base branch and pushed with `--force-with-lease`.
4. Allow bot operations explicitly, including creating publish branches, force-with-lease pushes, tags, PRs, and branch cleanup.
5. Reject or flag manual publish branch creation unless the repository explicitly allows it.

## PR Gate Flow

For a parent PR from `*/dev_V` to `publish_V`:

- Validate source and target branch names use the same `V`.
- Check merge conflicts in the parent repo. Also check conflicts in the paired child repo if child branches are part of the release.
- Validate component versions independently. Most component versions are `major.minor.patch`; if dev is lower than publish, fail. If dev equals publish, the bot may bump the patch version unless the repo says otherwise. If dev is higher than publish, keep the dev version.
- Reject the release PR if any other open PR has the current `*/dev_V` branch as its base.
- Verify the parent submodule pointer references a child commit contained in the expected paired child branch.
- If the workflow mutates versions, commit the change as the release bot and rerun the gate.

## Cross-Repo Build Flow

The parent and child can use separate workflows. This is preferred when the child artifact must appear in the child repo's GitHub Artifacts, because Actions artifacts belong to the repository that ran the workflow.

1. A push to parent `publish_V` starts the parent release workflow after the `*/dev_V -> publish_V` PR is merged.
2. The parent reads the pinned child commit from the submodule pointer.
3. The parent triggers the child workflow with `workflow_dispatch` or the GitHub API, passing the release identifier, expected paired child branch, child commit SHA, and any version metadata.
4. The child workflow checks out the exact child commit SHA, builds SO files, verifies expected outputs, and uploads a child artifact plus a manifest/checksum file.
5. If the child workflow fails or the SO artifact is missing, the parent release fails and must not tag, publish, or clean branches.
6. The parent downloads the child artifact, builds the AAR, and runs the repo's local PublishPlugin publish step.
7. The current success point is: local PublishPlugin publish succeeds and the AAR package is uploaded to GitHub Artifacts. The child SO artifact is a required prerequisite.

If one workflow must build both repos, the SO artifact will normally live under the parent workflow run. Use a child-repo workflow when the SO artifact must be visible in the child repo's Artifacts.

## Tags, Main Sync, and Cleanup

After the success point:

1. Create tags for every released component. Use the repository-declared tag format; `dependencyName-version` is a safe default. Do not use raw Maven coordinates with characters that are invalid in git refs unless the repo has already validated that format.
2. Tag parent components at the parent `publish_V` commit.
3. Tag child components at the exact child commit that produced the SO artifact.
4. Create a parent `publish_V -> base` PR, for example `publish_V -> svm-main`, and enable auto-merge.
5. Create or update the paired child publish-to-base PR if the child repo participates in the release, and enable auto-merge.
6. Delete parent and child `dev` and `publish` branches only after the corresponding base PRs are merged and repository policy allows cleanup.

Tags, base-branch PRs, auto-merge, and cleanup are aftercare unless the repo declares a stricter success point. If aftercare fails after artifacts are uploaded, preserve branches and tags and report the repair path.

## Required Configuration

- Release bot token with access to both repositories and permissions for contents write, pull requests write, Actions read/write, workflow dispatch, tags, and branch deletion.
- Main/base branch per repo.
- Parent-to-child branch mapping source.
- Version source files and component list.
- Child SO build command and artifact patterns.
- Parent AAR build command, local PublishPlugin command, and artifact patterns.
- Tag format.
- Branch protection or ruleset exceptions that allow the release bot to perform the required operations.

## Validation Checklist

Use repo scripts when present. Otherwise validate these points explicitly:

```bash
git submodule update --init --recursive
git submodule status --recursive
```

```bash
git -C <child-repo> merge-base --is-ancestor <child-sha> <expected-child-branch>
```

```bash
git check-ref-format "refs/tags/<candidate-tag>"
```

- Parent worktree records the intended child SHA.
- Child workflow checked out the exact SHA from the parent pointer.
- SO artifact and manifest exist before the parent AAR build.
- Local PublishPlugin publish produced the expected Maven local files or equivalent local publish output.
- AAR artifact uploaded successfully.
- No cleanup runs before publish success.
