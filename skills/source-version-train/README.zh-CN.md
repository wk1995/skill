# 源码版本列车

语言：[English](README.md) | **中文**

`source-version-train` 把需求分支送入 `dev/<version>` 和可见的 `publish_<version>` PR，再 rebase 成不可见的发布候选，然后调用打包和发布，通过后才打 Tag。没有打包实现时打包直接通过，有 `build-pipeline-engineering` 时由它打包。没有配置发布目的地时，发布发送到 GitHub Actions Artifacts。本 Skill 不实现签名、校验和、产物保留或某个目的地的上传。

## 如何使用

请尽可能提供仓库、需求或分支名称、版本号和目标代码阶段：

```text
使用 source-version-train 为这个需求创建功能分支。
将 feature/login 和 feature/report 选入 dev/1.4.0。
列出已经满足代码集成条件的需求 PR。
将通过评审的代码提升到 publish_1.4.0，并完成源码 Tag。
```

该 Skill 会解析默认分支，在版本确定前保留独立需求分支，检查 PR 就绪状态，并更新仓库内的版本元数据。PR 中可见的发布分支只由 `publish_template` 决定，默认是受保护的 `publish_<version>`，版本必须是 `x.x.x`，例如 `publish_5.1.3`。仓库可以替换这个模板，但不会再叠加前缀；修改只能经评审的 PR 进入，不能直接推送。`dev/<version>` 合入该分支后，先保留这次合并，再将结果 rebase 到默认分支，生成一条不可见的 release 候选分支。允许的构建号调整只发生在这条候选上，位于 rebase 之后、打包之前，并且必须重新通过检查。随后调用打包接口：没有实现即通过；存在 `build-pipeline-engineering` 时由它打包。发布接口在没有配置目的地时默认发送到 GitHub Actions Artifacts。配置了 FIR、GitHub Actions Artifacts 或 `wk1998.io` 时，一个成功即通过。重试同一个提交时跳过已成功的目的地，只补发失败的目的地。无论发布成功或失败，这条不可见分支都会删除。只有通过时才打 Tag，并合并回默认分支。Tag 已创建但合入失败时，保留 Tag 和所有分支，从已有 Tag 继续，不重新打。`dev/<version>` 要保留到 Tag 校验通过且合入默认分支成功之后；发布失败时它仍然在，用来修复。完整约束见 [SKILL.md](SKILL.md)。

新建版本集成分支时，按仓库自身的版本规则初始化全部版本值；已有分支经过校验后复用，不重复递增。有项目流程脚本时使用统一入口，没有脚本时通过 Git 和版本文件操作完成同样的初始化。不要求特定脚本、版本编码公式、语言或分支命名。发布保留已初始化的目标版本；提前创建的发布分支从记录的默认分支基准提交创建。

## 何时触发

适用于需求分支、版本范围选择、`dev/<version>` 集成、PR 中可见的受保护 `publish_<version>` 分支、不可见 release 候选、代码门禁、源码版本元数据或源码 Tag。

## 何时不触发

不要用于实现签名、打包、校验和生成、构建输出保留或单个发布目的地。打包实现使用 `build-pipeline-engineering`。普通代码修改如果不涉及版本列车，也不触发本 Skill。
