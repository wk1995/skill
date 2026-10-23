# GitHub Issues data and evidence plan

Status: optional integration plan, not a GitHub-backed store implemented by the bundled webpage. The current template still uses IndexedDB and JSON archive export. Apply this plan when the project requests an Issues adapter; do not silently migrate its existing data.

## Data ownership and deferred work

An Issues-backed project may use one Issue per case definition, one Issue per round with frozen definitions/source/build/environments, and structured comments for start/result/retest events and observations. Attach evidence to the corresponding record and retain its returned URL with case/round/environment identity. Keep definitions separate from execution evidence; Issue closure does not mean passed. JSON exports can remain backup/migration tools rather than a second manually maintained source of truth. Attachments need not be committed into Git.

**Deferred, 2026-10-23:** multi-user concurrent writes and strict remote history/audit protection are out of the initial integration scope. Start with a single operator writing sequentially. Distributed locking/atomic conflict handling and tamper-resistant remote history/recovery are future work, not a prerequisite for documenting or prototyping this single-operator flow. Do not claim multi-user consistency or immutable GitHub comments. This deferral does not remove the existing local revision checks, state-machine guards, frozen snapshots or append-only observation behavior.

## GitHub CLI version gate for media attachments

`gh --attach` on issue/PR create, edit and comment requires **GitHub CLI 2.99.0 or later**. This is the minimum for that optional media-upload step, not a universal minimum for CI packaging, read-only operations or plain-text comments. The feature was introduced in the [2.99.0 release](https://github.com/cli/cli/releases/tag/v2.99.0) and [official announcement](https://github.blog/changelog/2026-09-01-github-cli-media-in-issues-pull-requests-and-comments/).

Before an authorized attachment write:

1. Resolve the active executable and run `gh --version`. Compare numeric major/minor/patch components, not strings: 2.88.0 is too old; 2.99.0 and 2.103.0 satisfy the version gate.
2. Run the exact target command's help, for example `gh issue comment --help`, and confirm `--attach` is present. A version string alone cannot detect another stale binary, shim or unsupported build in PATH.
3. Verify the intended CLI account, repository and target Issue/PR. Check the target host, credential type and write/push access against the current [attachment documentation](https://docs.github.com/en/github-cli/github-cli/attaching-files-with-github-cli). A newer CLI alone does not grant access; do not assume GitHub Enterprise Server support from the version number.
4. Select supported image/video files and actual test evidence, then perform only the requested write. Verify the resulting comment/body and returned attachment URLs before reporting success. If a write's outcome is uncertain, inspect the target before retrying to avoid duplicate comments/uploads.

| Situation | Required handling |
| --- | --- |
| `gh` absent, older than 2.99.0, or target help lacks `--attach` | Do not invoke an unsupported media flag. Upgrade through the existing installation channel when within the authorized scope, then repeat version/help/account checks. |
| Upgrade unavailable, unsuccessful or outside requested scope | Continue supported requested steps; upload evidence through the GitHub browser UI and record returned URLs, or report just the attachment step as pending. Preserve records and pending local files. |
| Version/help pass but host, credentials or access do not support upload | Resolve the actual missing requirement or use browser upload with the user's available access. Do not misdiagnose it as an old CLI or repeatedly upgrade. |
| `.log`, `.txt`, `.zip` or another non-media evidence file | Use GitHub's browser attachment flow or a separately verified project upload adapter, even on a newer CLI. `--body-file` supplies comment text; it does not upload that file as an attachment. |

For an existing Homebrew installation, the targeted upgrade is:

```bash
brew upgrade gh
gh --version
gh issue comment --help
gh auth status
```

For another installation channel, follow the [official installation/upgrade guidance](https://github.com/cli/cli#installation) for that channel; do not overlay an unrelated binary or change credentials to work around a version mismatch. If the old version still resolves, inspect PATH and rerun these checks in a fresh shell.

Once the preflight succeeds and the specific comment is authorized, an illustrative media command is:

```bash
gh issue comment 123 --repo OWNER/REPO --body-file test-result.md --attach ./screenshot.png
```

Replace the repository, Issue, body and file with the actual confirmed targets. Attaching media is itself an external write; neither the command example nor the integration plan authorizes posting to an arbitrary Issue. Log files must follow the non-media route above.

## Scope and verification

The official CLI attachment feature uploads **images and videos**, with access/type/size limits described in [CLI attachments](https://docs.github.com/en/github-cli/github-cli/attaching-files-with-github-cli) and [browser attachments](https://docs.github.com/en/get-started/writing-on-github/working-with-advanced-formatting/attaching-files). Browser attachment support for logs/archive files must not be confused with CLI media support or an ordinary comment REST call accepting binary files.

Compatibility checked on 2026-10-23 with gh 2.103.0: issue/PR create, edit and comment help all expose `--attach`. This is a local capability check, not a completed upload or proof of repository permission. No live Issue or attachment was created for this check.
