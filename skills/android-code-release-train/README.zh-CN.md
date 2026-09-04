# Android 代码发布列车

语言：[English](README.md) | **中文**

`android-code-release-train` 约束 Android 需求从功能分支、版本集成和发布提升，到形成已评审源码提交及不可变 Tag 的完整代码链路。它不构建、签名、打包或上传发布产物。

## 如何使用

请尽可能提供仓库、需求或分支名称、版本号和目标代码阶段：

```text
使用 $android-code-release-train 为这个 Android 需求创建功能分支。
将 feature/login 和 feature/report 选入 dev/1.4.0。
列出已经满足代码集成条件的需求 PR。
将通过评审的代码提升到 release/1.4.0，并完成源码 Tag。
```

该 Skill 会解析默认分支，在版本确定前保留独立需求分支，检查 PR 就绪状态，提升已评审代码，更新仓库内的版本元数据，同步默认分支并创建不可变源码 Tag。完整约束见 [SKILL.md](SKILL.md)。

## 何时触发

适用于 Android 需求分支、版本范围选择、`dev/<version>` 与 `release/<version>` 集成、代码门禁、源码版本元数据、默认分支同步或源码 Tag。

## 何时不触发

不要用于配置或执行签名、APK/AAB/AAR 打包、校验和生成、构建输出保留、GitHub Actions Artifacts 上传、应用商店交付或 Maven/插件发布；这些请求使用 `build-pipeline-engineering`。普通代码修改如果不涉及版本列车，也不触发本 Skill。
