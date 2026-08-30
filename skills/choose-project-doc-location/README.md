# Choose Project Doc Location

Language: **English** | [中文](README.zh-CN.md)

`choose-project-doc-location` helps decide whether project documentation belongs in the repository README, versioned repository docs, or a GitHub Wiki before the document is created or changed.

## How To Use It

Describe the information that needs documenting and any requested destination. The skill checks the repository's existing documentation conventions, recommends the appropriate surface, and then guides the documentation change.

For example:

```text
Document the deployment workflow for new contributors.
Should this project overview be added to the README or the Wiki?
Organize the repository documentation for the new integration.
```

See [SKILL.md](SKILL.md) for the full placement rules and editing guidance.

In OpenAI Codex you can also invoke the skill explicitly with `$choose-project-doc-location`.

## When It Triggers

Use this skill when creating, updating, rewriting, or organizing project documentation, including README content, repository docs, project workflows, onboarding notes, or Wiki material where the final location is not yet settled.

## When It Does Not Trigger

Do not use this skill for ordinary code changes, non-documentation assets, or managing and synchronizing copies of Agent Skills.
