# 选择项目文档位置

语言：[English](README.md) | **中文**

`choose-project-doc-location` 用于在创建或修改项目文档前，判断内容应放在仓库 README、受版本控制的仓库文档，还是 GitHub Wiki 中。

## 如何使用

说明需要记录的信息以及期望的存放位置。该 Skill 会先检查仓库已有的文档约定，建议合适的载体，再指导后续的文档修改。

例如：

```text
为新贡献者记录部署流程。
这段项目概览应该写进 README 还是 Wiki？
整理新集成相关的仓库文档。
```

完整的位置选择规则和编辑指南见 [SKILL.md](SKILL.md)。

在 OpenAI Codex 中也可以显式用 `$choose-project-doc-location` 调用本 Skill。

## 何时触发

当需要创建、更新、改写或整理项目文档时使用，包括 README 内容、仓库文档、项目工作流、上手说明，或尚未确定最终位置的 Wiki 材料。

## 何时不触发

普通代码修改、非文档资源变更，以及管理或同步 Agent Skill 副本时，不使用此 Skill。
