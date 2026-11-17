# Skill Issue Labels

Every Skill in `skills/` owns exactly one issue label so that issues can be
routed to the Skill that has to change. The label set is derived from the
repository, not maintained by hand.

| Property | Value |
| --- | --- |
| Label name | The Skill directory name, which `scripts/skill_catalog.py` already requires to equal `SKILL.md`'s `name` |
| Description | `Issues related to the <name> Skill.` |
| Color | `1D76DB` |
| Owner | `scripts/skill_labels.py`, run by the `skill-labels` workflow |

## Lifecycle

| Repository event | Label effect |
| --- | --- |
| A Skill is added to `skills/` | The label is created after the merge to the default branch |
| A Skill keeps its directory name | No change |
| A Skill is renamed, `metadata.sync_id` unchanged | The label is **renamed**; every issue and pull request that carries it keeps it |
| A Skill is removed | The label becomes an orphan, is reported, and is left in place; deleting it is an explicit `--prune` decision |
| Color or description drifts from the contract | Reported as a note; rewriting it is an explicit `--normalize` decision |
| A label exists whose name is a Skill name but was never managed by the tool | Adopted, so a hand-created label is not duplicated |

## Why A Rename Instead Of A Delete And A Create

Deleting a label removes it from every issue and pull request that uses it, and
a later label with the same name starts empty. Renaming keeps the label object,
so the association survives. The difference was measured on this repository:

| Operation | Resulting labels on an issue that carried the label |
| --- | --- |
| `PATCH /labels/zz-probe-label {"new_name": "zz-probe-label-renamed"}` | `zz-probe-label-renamed` |
| `DELETE /labels/zz-probe-label-renamed` then `POST /labels` with the same name | none |

`metadata.sync_id` is what makes a rename detectable. `AGENTS.md` declares it
immutable, and `scripts/version_guard.py` rejects a changed `sync_id` for a Skill
that still exists. The tool reads the Skills at the push's previous commit and
compares `sync_id` values, so a name change is classified as a rename, while a
removal plus an unrelated addition stays a removal plus an addition.

```text
old push:  skills/old-name/SKILL.md   metadata.sync_id: stable-id
new push:  skills/new-name/SKILL.md   metadata.sync_id: stable-id
           -> PATCH /labels/old-name {"new_name": "new-name"}
```

## Running It

The workflow runs on every push to `main` that touches `skills/`, and it is
read-only on branches. It plans the complete set of changes before the first
mutation, so a rejected plan changes nothing.

```bash
# What would change against the live repository
python3 scripts/skill_labels.py --repository wk1995/skill --check

# Merge-time behaviour: reconcile, detect renames since the given commit
python3 scripts/skill_labels.py --base <previous-commit> --apply

# Manual repair
python3 scripts/skill_labels.py --apply --rename old-name=new-name
python3 scripts/skill_labels.py --apply --prune
python3 scripts/skill_labels.py --apply --normalize
```

`--apply` needs a token in `GITHUB_TOKEN` or `GH_TOKEN` with write access to
issues; reads work without one on a public repository.

## Recovery

- **A rename was missed** (the run failed, or the name changed outside a push):
  the new label is created and the old one is reported as an orphan. Repair it
  with `--rename old=new`, then optionally `--prune`. Do not delete the old label
  first, or its issues lose the association.
- **Two Skills exchange names**: the tool refuses, because GitHub cannot rename
  two labels onto each other's names in one pass. Rename one label by hand and
  rerun.
- **A Skill is retired**: rerun the workflow manually with `prune` enabled. The
  deleted label leaves the issue timeline intact but disappears from the issues
  themselves.
- **A hand-written label looks wrong**: `--normalize` rewrites the color and
  description of labels whose name matches a Skill.

## Limits

- GitHub rejects label names longer than 50 characters; the tool fails before
  contacting the API when a Skill name exceeds that limit.
- Label names are case-insensitive on GitHub, so a label that differs only by
  letter case is renamed to the Skill's name instead of being duplicated.
- Labels are matched by name, so an unrelated label that happens to share a
  Skill name is adopted rather than duplicated.
- The workflow is driven by the default branch. A Skill rename staged only on a
  branch does not touch labels until it merges.
- Concurrent runs are serialized by a workflow concurrency group; a failed run
  leaves partial changes that the next run reconciles.
