# Enter Flowtime Android Release Flow

Use this reference for `/Users/chengpeng/project/wk/android/Enter-Flowtime-Android` and similar repos using `dev_*`, `publish_*`, and `scripts/release_flow.py`.

## Implemented Workflows

- `.github/workflows/sync-publish-branch.yml`: on push to `dev_*` or `**/dev_*`, create or reuse matching `publish_V`, then configure branch protection.
- `.github/workflows/sync-publish-pr.yml`: on PRs targeting `dev_*` or `**/dev_*`, create or update the matching `dev_V -> publish_V` PR and sync a marker comment.
- `.github/workflows/publish-pr-gate.yml`: on PRs targeting `publish_*`, reject invalid sources and run `scripts/release_flow.py pr-gate`.
- `.github/workflows/android-release-flow.yml`: on push to `publish_*`, reject manual publish branch creation or run packaging and aftercare.

## Branch Model

- Base branch: `master`.
- Development branch: `dev_5.1.0` or namespaced `team/dev_5.1.0`.
- Publish branch: `publish_5.1.0`.
- `publish_*` should not receive direct business pushes.
- `publish_*` code should enter through same-version `dev_*` or `*/dev_*` PRs.

## Version Model

- `versionName`: `major.minor.patch`.
- `versionCode`: `major * 1000000 + minor * 10000 + patch * 100 + buildNo`.
- Tag format: zero-padded `versionCode` plus `versionName`, for example `05010000(5.1.0)`.
- If `dev` and `publish` versions match, the next build uses `publishBuildNo + 1`.
- If `dev` version is newer than `publish`, keep the dev build number.
- If `dev` version is older than `publish`, fail.

## Operator Flow

```bash
git fetch enter
git switch -c team/dev_5.1.0 enter/master
git push enter team/dev_5.1.0
```

After push:

1. `Sync Publish Branch` creates/protects `publish_5.1.0`.
2. Feature PRs into the dev branch trigger `Sync Publish PR`.
3. The release PR `team/dev_5.1.0 -> publish_5.1.0` must pass `Publish PR Gate`.
4. After review/QA, merge the release PR.
5. Push to `publish_5.1.0` triggers `Android Release Flow`.

Local PR gate check:

```bash
python3 scripts/release_flow.py pr-gate \
  --base-ref publish_5.1.0 \
  --head-ref team/dev_5.1.0 \
  --remote enter \
  --base master
```

## Android Release Build

The current app release packages use the `ApiComFlowtime` variant:

```bash
./gradlew clean \
  :app:assembleApiComFlowtimeDebug \
  :app:assembleApiComFlowtimeRelease \
  :app:bundleApiComFlowtimeRelease
```

Expected archive contents include APKs, AAB, `output-metadata.json`, and release mapping.

## Aftercare Order

After Gradle packaging succeeds:

1. Create a release artifact zip and upload GitHub Artifact.
2. Upload Bugly mapping with `buglyqq-upload-symbol-v3.3.5/buglyqq-upload-symbol.jar`; failure is non-blocking.
3. Create annotated release tag after artifact upload succeeds.
4. Rebase `publish_V` onto latest `master` and push to `master` with `--force-with-lease`.
5. Delete `publish_V` and the full PR head dev branch.

Packaging success is the release success point. Artifact upload, tag, master sync, and cleanup are aftercare gates; when one aftercare gate fails, later aftercare steps stop.

## Required CI Configuration

- `RELEASE_PROTECTION_TOKEN`: token with repository Administration write permission for branch protection.
- `BUGLY_APP_KEY`: Bugly upload secret.
- Optional variables: `BUGLY_APP_ID`, `BUGLY_BUNDLE_ID`.

Do not add signing or Bugly secrets in plaintext.
