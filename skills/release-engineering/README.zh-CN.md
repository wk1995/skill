# 发布工程

语言：[English](README.md) | **中文**

`release-engineering` 用于规划、校验、自动化、记录和排查受控发布流程。它覆盖 Android 应用、Android 库与 SDK、Gradle 插件、构建产物、发布分支和标签、CI 门禁、发布、回滚计划及发布后处理。

## 如何使用

请说明发布目标，并尽可能提供对应仓库。常见请求包括：

```text
使用 $release-engineering 为这个 Android 应用制定发布演练计划。
审计这个 Android 库的 Maven 发布流程。
排查 Gradle 插件发布任务为什么没有上传产物。
```

在 OpenAI Codex 中可以用 `$release-engineering` 显式调用。在 ZCode 中，同样的请求会依据 `description` 与 `when_to_use` 元数据自动触发；在本仓库执行一次 `scripts/link-zcode-skill.sh` 即可链接到 `~/.zcode/skills/`。

此 Skill 会先识别发布目标和操作类型，检查相关构建配置、CI、版本来源、签名和发布配置，再制定或校验发布契约。仅在需要时读取对应资料：

- Android APK/AAB 应用
- Android 库、SDK、AAR 和 Maven 组件
- Gradle 和构建插件
- Enter Flowtime 及 Android 父/子模块发布流程

上传产物、推送标签、创建远程发布或修改分支保护等远程操作，必须获得用户明确授权。

## 何时触发

在以下情况使用此 Skill：

- 需要规划、校验、自动化、记录或排查发布/发包流程；
- 涉及 Android 应用、组件或插件发布，构建产物、标签、发布分支或 CI 发布门禁；
- 需要发布契约、发布演练、发布安全检查、回滚计划或发布后处理。

## 何时不触发

在以下情况不要使用此 Skill：

- 只讨论本 Skill 管理仓库的架构或元数据约定；
- 只是普通代码修改，且不涉及发布、发包、构建产物、标签或发布自动化。

完整的执行步骤和安全规则见 [SKILL.md](SKILL.md)。
