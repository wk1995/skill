# Changelog

All notable changes to this Skill are documented here.

## [Unreleased]

- No unreleased changes.

## [0.1.0] - 2026-09-17

- Change-Type: initial
- Summary: Add `pr-review-loop`, a portable workflow Skill that reviews a pull request, posts each round's confirmed findings to the pull request under a `[<platform>][<model>]` marker, fixes and pushes them, and repeats until a round produces no confirmed findings. It defines the loop — trigger gate, attribution, round ordering, stop conditions, boundaries, and the round report — and intentionally defines no review criteria; each round resolves its method from the repository review standard, project documentation, user-stated criteria, or the host's general review capability.
- Compatibility: New component, so there is no earlier contract to preserve. The Skill adds no dependency, installs nothing, and changes no existing Skill, adapter, or artifact. It runs only when a single pull request is identified and write access exists, so requests without a pull request, read-only review requests, and pull-request administration keep their current behavior and remain outside this Skill.
