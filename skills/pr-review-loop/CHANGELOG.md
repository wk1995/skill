# Changelog

All notable changes to this Skill are documented here.

## [Unreleased]

- No unreleased changes.

## [0.1.0] - 2026-09-17

- Change-Type: initial
- Summary: Add `pr-review-loop`, a portable workflow Skill that reviews a pull request, fixes the confirmed findings, commits and pushes them, and repeats until a round produces no confirmed findings. It defines the loop — trigger gate, comment policy, loop limits, attribution, round ordering, stop conditions, boundaries, and the round report — and intentionally defines no review criteria; each round resolves its method from the repository review standard, project documentation, user-stated criteria, or the host's general review capability. Commenting on the pull request is off unless the comment policy enables it for that repository: the policy resolves from a per-review statement, a project-scope `.pr-review-loop.yml`, or an install-scope `pr-review-loop.yml` that lists repositories by git remote, and every posted comment carries a `[<platform>][<model>]` marker naming the platform and model that produced it. The same file sets the loop limits: at most ten rounds that produced confirmed findings (`max_rounds`), after which the loop stops editing, reports why it needed that many rounds, and escalates instead of looping, and up to three further attempts after a review attempt fails to run (`review_retries`), which consume no round, post no comment, and never turn a review that did not run into a passing round.
- Compatibility: New component, so there is no earlier contract to preserve. The Skill adds no dependency, installs nothing, and changes no existing Skill, adapter, or artifact. It runs only when a single pull request is identified, and it writes to the pull request only when the resolved comment policy enables commenting, so requests without a pull request, read-only review requests, and pull-request administration keep their current behavior and remain outside this Skill. Both limits default to a finite value, so the loop cannot run indefinitely, and a review that could not be performed is reported as a failed attempt rather than as a clean or passing round.
