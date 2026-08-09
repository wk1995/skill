# Android 版本列车

语言：[English](README.md) | **中文**

`android-release-train` 用于编排受保护的 Android 交付路径：从功能或修复分支，经版本集成和发布提升，到签名 Android 产物、可配置分发及已验证的发布标签。

## 如何使用

请尽可能提供版本号、分支、仓库和期望的发布阶段。常见请求包括：

```text
使用 $android-release-train 列出可进入 1.4.0 版本的功能分支。
为这个 Android 需求创建功能分支；在确定其版本前不要创建 PR。
将 feature/login 和 feature/report 集成到 dev/1.4.0。
在检查通过后提升 release/1.4.0，并将签名 APK 分发到企业 MDM 测试组。
```

该 Skill 会解析仓库的默认分支，而不是假定为 `main` 或 `master`。功能分支在被明确选入版本前不创建 PR；选定版本后，流程会创建 `dev/<版本>` 及功能分支到该分支的 PR。它会在合并前盘点这些 PR 的就绪状态，将版本元数据修改限制在受保护的发布流程中，并将同一个已验证的 AAB 或 APK 分发到每个配置的目标。Google Play 只是可选项；也可配置其他应用商店、企业 MDM、直接交付或仅归档产物。远程写入会先明确说明，并要求满足相应发布门禁和凭据条件。详细流程参见 [SKILL.md](SKILL.md) 及其发布列车契约。

## 何时触发

在以下情况使用此 Skill：

- 需要创建、评估、集成、提升、发布或打标 Android 版本列车；
- 涉及 Android 功能或修复分支、`dev/<version>` 或 `release/<version>` 分支、AAB/APK 签名、应用商店、企业 MDM、直接接收人或产物归档的分发，或发布标签；
- 需要 Android 版本列车 CI、发布配置、分支门禁或就绪状态盘点。

## 何时不触发

在以下情况不要使用此 Skill：

- 只是一般的 Android 构建、测试或代码修改，且不涉及版本列车或发布编排；
- 只管理 Skill 的副本或元数据；此时应使用 `sync-skills`。
