# Android 版本列车

语言：[English](README.md) | **中文**

`android-release-train` 用于编排受保护的 Android 交付路径：从功能或修复分支，经版本集成和发布提升，到签名 AAB、Google Play 发布及已验证的发布标签。

## 如何使用

请尽可能提供版本号、分支、仓库和期望的发布阶段。常见请求包括：

```text
使用 $android-release-train 列出可进入 1.4.0 版本的功能分支。
为这个 Android 需求创建功能分支并发起 PR。
将 feature/login 和 feature/report 集成到 dev/1.4.0。
在检查通过后提升 release/1.4.0，并将签名 AAB 发布到内部测试轨道。
```

该 Skill 会解析仓库的默认分支，而不是假定为 `main` 或 `master`。它会在选择功能前盘点分支就绪状态，将版本元数据修改限制在受保护的发布流程中，并使用同一个已验证 AAB 完成轨道提升。远程写入会先明确说明，并要求满足相应发布门禁和凭据条件。详细流程参见 [SKILL.md](SKILL.md) 及其发布列车契约。

## 何时触发

在以下情况使用此 Skill：

- 需要创建、评估、集成、提升、发布或打标 Android 版本列车；
- 涉及 Android 功能或修复分支、`dev/<version>` 或 `release/<version>` 分支、AAB 签名、Play 轨道提升或发布标签；
- 需要 Android 版本列车 CI、发布配置、分支门禁或就绪状态盘点。

## 何时不触发

在以下情况不要使用此 Skill：

- 只是一般的 Android 构建、测试或代码修改，且不涉及版本列车或发布编排；
- 只管理 Skill 的副本或元数据；此时应使用 `sync-skills`。
