# Choose Project Doc Location

Language: **English** | [中文](README.zh-CN.md)

`choose-project-doc-location` helps decide whether project documentation belongs in the repository README, versioned repository docs, or a GitHub Wiki before the document is created or changed.

## How To Use It

Describe the information that needs documenting and any requested destination. The Skill checks the repository's existing documentation conventions, recommends the appropriate surface, and then guides the documentation change. A request that explicitly says “README” or “Wiki” still triggers this check: the named destination is treated as a preference until the content and repository conventions confirm it.

For example:

```text
Document the deployment workflow for new contributors.
Should this project overview be added to the README or the Wiki?
Organize the repository documentation for the new integration.
```

See [SKILL.md](SKILL.md) for the full placement rules and editing guidance.

## When It Triggers

Use this Skill when creating, updating, rewriting, or organizing project documentation, including README content, repository docs, project details, workflow documentation, architecture notes, onboarding guides, or Wiki material. It also triggers when the user names README or Wiki directly, because the final placement still needs to be checked against the content and repository conventions.

## When It Does Not Trigger

Do not use this skill for ordinary code changes, non-documentation assets, or managing and synchronizing copies of Agent Skills.
