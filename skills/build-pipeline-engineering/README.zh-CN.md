# 构建流水线工程

语言：[English](README.md) | **中文**

`build-pipeline-engineering` 用于配置和执行 Android、Windows、Linux 及插件的可复现可分发构建流水线：从一个确定源码引用完成 build variant 选择、安装包格式选择、环境配置、签名、运行依赖处理、安装校验与输出上传。对于支持 variant 的目标，未指定时默认使用 `release`；在 GitHub Actions 中，构建输出默认上传到 GitHub Actions Artifacts。

## 如何使用

请尽可能提供仓库、源码 Tag 或提交，以及目标产物或构建变体：

```text
使用 build-pipeline-engineering 配置 CI，构建签名 Android release AAB。
从指定 Tag 构建 qa variant APK，并上传到 GitHub Actions Artifacts。
审计这个 AAR 流水线的签名、校验和与保留时间。
排查 Gradle 插件产物为什么没有出现在 workflow run 中。
把这个提交打包成 Windows x64 MSI，并验证静默安装和升级。
构建 Windows EXE 安装包和免安装 ZIP；将这次内部测试产物标记为未签名。
把这个 Tag 打包成 Ubuntu 22.04 amd64 的 DEB 和 AppImage，并验证运行依赖。
配置 Linux x86_64/ARM64 的 RPM 和 tar 产物，将校验和一起存入 GitHub Actions Artifacts。
```

该 Skill 会检查构建系统和 CI，确定精确输入输出，把签名材料保存在受保护 Secret 中，校验产物，并记录源码 SHA、清单、校验和、上传目标与保留策略。详细构建契约见 [SKILL.md](SKILL.md)。

Windows/Linux 打包请尽可能提供技术栈和构建命令、目标系统或发行版版本、架构、安装包或免安装格式、应用信息和资源、运行时是否内置、安装范围、升级卸载预期及签名要求。优先沿用仓库现有配置，影响交付的缺失选项会在打包前确认。Windows 支持 EXE 安装包、MSI、MSIX 和免安装包；Linux 支持 DEB、RPM、AppImage 和 tar 归档。单个应用 EXE 不一定是安装程序。

Windows 公开分发签名使用受信任的代码签名机构或已有签名服务；自签名证书需要受控的目标信任配置。未签名测试包会明确记录，不能满足正式签名要求。安装和升级检查在可丢弃的目标环境中执行，无法执行的检查会标为未验证。平台细节见 [Windows 指南](references/windows-app-build.md)和 [Linux 指南](references/linux-app-build.md)。

## 何时触发

适用于 CI 构建配置、build variant、签名环境、可分发打包、APK/AAB/AAR/JAR/插件/原生输出、Windows 安装包和免安装包、Linux 软件包和归档、运行依赖与安装检查、校验和、构建清单、保留策略、GitHub Actions Artifacts，或用户明确指定的其他目标。对于支持 variant 的目标，未指定时默认使用 `release`（或构建系统中的等效名称）。

## 何时不触发

不要用于实现需求、选择 Android 版本代码、创建或提升源码分支与 PR、修改源码版本文件、合并代码或创建发布 Tag；这些工作使用 `android-code-release-train`。不保留可分发产物的普通编译或测试也不触发本 Skill。

没有构建任务的单纯 EXE/MSI 格式比较或证书知识问答不触发。仅管理 Skill 副本或元数据的请求使用 `sync-skills`。
