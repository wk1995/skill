# Changelog

All notable changes to this Skill are documented here.

## [Unreleased]

- Make commenting opt-in. The loop writes findings to a pull request only when a comment policy enables it for that repository, so a machine-wide install no longer comments on every repository it is pointed at. The policy resolves from the user's statement for this review, a project-scope `.pr-review-loop.yml`, or an install-scope `pr-review-loop.yml` that lists repositories by git remote; a repository that has a project-scope file is decided by that file and the install scope is not read for it, only the running install is read, and the two file names are distinct. A remote must equal the pull request's own `host/owner/repo`, so a fork's remote never matches. The policy is read from outside the pull request's own changes, and every posted comment carries the `[<platform>][<model>]` attribution marker.
- Add loop limits to the same policy file: at most ten completed rounds that produced confirmed findings (`max_rounds`), checked before a round starts, after which the loop stops editing, names any fix that is pushed but no longer re-reviewed, reports why it needed that many rounds, and escalates instead of looping; and up to three further attempts after a review attempt fails to run (`review_retries`), which consume no round, post no comment, and never turn a review that did not run into a passing round.
- Clarify the contract. A request that forbids changing, committing, or pushing stops at the trigger gate, and the comment decision can never pull it back into the loop; the trigger metadata, both READMEs, and the example policy now say so. The round outcomes are aligned with the stop conditions, and the loop limits state that a limit omitted by the more specific policy file is inherited rather than owned by that scope.

## [0.1.0] - 2026-09-17

- Change-Type: initial
- Summary: Add `pr-review-loop`, a portable workflow Skill that reviews a pull request, posts each round's confirmed findings to the pull request under a `[<platform>][<model>]` marker, fixes and pushes them, and repeats until a round produces no confirmed findings. It defines the loop — trigger gate, attribution, round ordering, stop conditions, boundaries, and the round report — and intentionally defines no review criteria; each round resolves its method from the repository review standard, project documentation, user-stated criteria, or the host's general review capability.
- Compatibility: New component, so there is no earlier contract to preserve. The Skill adds no dependency, installs nothing, and changes no existing Skill, adapter, or artifact. It runs only when a single pull request is identified and write access exists, so requests without a pull request, read-only review requests, and pull-request administration keep their current behavior and remain outside this Skill.
