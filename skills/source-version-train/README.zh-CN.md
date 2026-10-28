# 源码版本列车

语言：[English](README.md) | **中文**

`source-version-train` 把需求分支送入 `dev_<version>` 和可见的 `publish_<version>` PR，再 rebase 成不可见的发布候选，然后调用打包和发布，通过后才打 Tag。先识别仓库声明的各平台产物。声明过的产物缺失、失败或从未运行，都会拦住 Tag 和合入默认分支。仓库完全没有打包流程时可以合入，但不能打 Tag。存在声明产物时，由可用的 `build-pipeline-engineering` 打包。全部声明产物都存在后，发布才默认发送到 GitHub Actions Artifacts。本 Skill 不点名其他发布渠道，也不实现签名、校验和、产物保留或某个目的地的上传。

## 如何使用

请尽可能提供仓库、需求或分支名称、版本号和目标代码阶段：

```text
使用 source-version-train 为这个需求创建功能分支。
将 feature/login 和 feature/report 选入 dev_1.4.0。
列出已经满足代码集成条件的需求 PR。
将通过评审的代码提升到 publish_1.4.0，并完成源码 Tag。
```

该 Skill 会解析默认分支，在版本确定前保留独立需求分支，检查 PR 就绪状态，并更新仓库内的版本元数据。集成分支只由 `integration_template` 决定，默认是 `dev_<version>`，例如 `dev_5.1.3`。PR 中可见的发布分支只由 `publish_template` 决定，默认是受保护的 `publish_<version>`，版本必须是 `x.x.x`，例如 `publish_5.1.3`。仓库可以替换这两个模板，但不会再叠加前缀；发布分支的修改只能经评审的 PR 进入，不能直接推送。`dev_<version>` 合入该分支后，先保留这次合并，再将结果 rebase 到默认分支，生成一条不可见的 release 候选分支。允许的构建号调整只发生在这条候选上，位于 rebase 之后、打包之前，并且必须重新通过检查。随后调用打包接口。Android 产物是 `.apk` 或 `.aab`，Windows 是 `.exe`、`.msi`、`.msix` 或便携 `.zip`，macOS 是 `.dmg`、`.pkg` 或 `.app` 归档，iOS 是 `.ipa`。绿色任务如果没有对应产物文件，也算失败。存在声明产物时，由可用的 `build-pipeline-engineering` 产出。仓库没有打包流程时，候选可以合入且不打 Tag，并跳过发布。否则要等全部声明产物都存在，发布才默认发送到 GitHub Actions Artifacts，不在本 Skill 中点名其他渠道。重试同一个提交时跳过已成功的目的地，只补发失败的目的地。打 Tag 前的尝试失败时删除不可见候选分支；打 Tag 后则保留到最终校验通过，再清理。声明了产物时，两个接口都通过才打 Tag，再合并回默认分支。Tag 已创建但合入失败时，保留 Tag 和所有分支，从已有 Tag 继续，不重新打。`dev_<version>` 要保留到合入默认分支成功、且需要 Tag 时 Tag 已校验通过之后；打包或发布失败时它仍然在，用来修复。完整约束见 [SKILL.md](SKILL.md)。

最终合入必须使用保留原提交的 merge commit，或分支保护允许的真正快进。禁止用 squash、rebase-and-merge 或 cherry-pick 完成发布；如果合并策略只允许这些改写方式，在发布前停止。远端合入后，重新获取 Tag 和默认分支，确认 Tag 解析到打包、发布时记录的原提交，并用祖先关系校验确认该提交位于默认分支历史中。只有全部通过才算发布完成，才允许清理分支。合入或校验失败时保留 Tag 和所有相关分支，通过受保护流程修复；重试时即使 PR 已显示合入，也必须重新校验。具体步骤见[最终校验](references/code-train-contract.md#finalization-check)。

新建版本集成分支时，按仓库自身的版本规则初始化全部版本值；已有分支经过校验后复用，不重复递增。有项目流程脚本时使用统一入口，没有脚本时通过 Git 和版本文件操作完成同样的初始化。不要求特定脚本、版本编码公式、语言或分支命名。发布保留已初始化的目标版本；提前创建的发布分支从记录的默认分支基准提交创建。

## 何时触发

适用于需求分支、版本范围选择、`dev_<version>` 集成、PR 中可见的受保护 `publish_<version>` 分支、不可见 release 候选、代码门禁、源码版本元数据或源码 Tag。

## 何时不触发

不要用于实现签名、打包、校验和生成、构建输出保留或单个发布目的地。打包实现使用 `build-pipeline-engineering`。普通代码修改如果不涉及版本列车，也不触发本 Skill。
