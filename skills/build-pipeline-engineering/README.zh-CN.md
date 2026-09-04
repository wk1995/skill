# 构建流水线工程

语言：[English](README.md) | **中文**

`build-pipeline-engineering` 用于配置和执行可复现的可分发构建流水线：从一个确定源码引用完成 build variant 选择、环境配置、签名、打包、校验与输出上传。对于支持 variant 的目标，未指定时默认使用 `release`；在 GitHub Actions 中，构建输出默认上传到 GitHub Actions Artifacts。

## 如何使用

请尽可能提供仓库、源码 Tag 或提交，以及目标产物或构建变体：

```text
使用 $build-pipeline-engineering 配置 CI，构建签名 Android release AAB。
从指定 Tag 构建 qa variant APK，并上传到 GitHub Actions Artifacts。
审计这个 AAR 流水线的签名、校验和与保留时间。
排查 Gradle 插件产物为什么没有出现在 workflow run 中。
```

该 Skill 会检查构建系统和 CI，确定精确输入输出，把签名材料保存在受保护 Secret 中，校验产物，并记录源码 SHA、清单、校验和、上传目标与保留策略。详细构建契约见 [SKILL.md](SKILL.md)。

## 何时触发

适用于 CI 构建配置、build variant、签名环境、可分发打包、APK/AAB/AAR/JAR/插件/原生输出、校验、校验和、构建清单、保留策略、GitHub Actions Artifacts，或用户明确指定的其他目标。未指定 variant 时默认使用 `release`。

## 何时不触发

不要用于实现需求、选择 Android 版本代码、创建或提升源码分支与 PR、修改源码版本文件、合并代码或创建发布 Tag；这些工作使用 `android-code-release-train`。不保留可分发产物的普通编译或测试也不触发本 Skill。
