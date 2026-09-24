# PR 评审闭环

语言：[English](README.md) | **中文**

`pr-review-loop` 审查指定的 Pull Request。当前托管账号是 PR 作者，且项目级 Skill 或配置适用，或整机配置列出了该仓库时，可审查、修复、推送并复审。`max_rounds` 限制完成的审查次数；独立的 `comment` 开关控制是否向 PR 评论。本 Skill 定义流程，不定义审查标准。适用于：指明某个 PR 并要求审查、审查并修复，或继续已有闭环。不适用于：只要本地报告、同时禁止 PR 评论和代码改动，或只做 PR 管理。

## 如何使用

指明一个 PR 和关注点：

```text
审查 PR #25。
审查 https://github.com/<owner>/<repo>/pull/42 并修复确认的问题。
审查 PR #25 是否泄露 token，不改代码。
继续这个 PR 的评审闭环。
```

完整闭环锁定 PR 的 base/head 提交，修复确认的问题并推送；尚有轮次时审查新的提交对。先检查用户本次指定的项目，再补充仓库必需规范和项目文档的其他适用检查；说明冲突和跳过项。

## 配置与评审模式

项目级 Skill 生成的配置放在其 `SKILL.md` 旁的 `pr-review-loop.yml`，默认把实际路径写入项目 `.gitignore`。在本仓库中，该路径是 `<项目根>/skills/pr-review-loop/pr-review-loop.yml`。用户可移除忽略规则并提交文件，使其成为项目共享配置。已跟踪配置只从 PR base 读取；未跟踪的本地配置须在审查开始前存在。两者都不会进入通用 Agent 构建产物或同步到其他 Skill 副本。兼容旧项目：Skill 旁的文件不存在时，仍可读取 PR base 中已提交的 `<项目根>/.pr-review-loop.yml`。当前 Agent 平台按 `metadata.sync_id: pr-review-loop` 发现的项目级 Skill 也默认适用于本项目；这些项目级来源都不需要 `comment_targets`。项目 Skill 即使没有相邻的 `pr-review-loop.yml`，也不会继承整机配置。没有项目 Skill 时才选整机 Skill；整机配置必须通过 `projects` 或旧版 `comment_targets` 命中 PR 仓库，才能进入修复闭环。

通用 Skill 生成的配置放在该 Skill 的本机安装目录旁。选择配置时，先取项目 Skill 旁的文件；若不存在，再取 PR base 中的旧项目根文件，之后才取选中通用 Skill 安装目录旁的 `pr-review-loop.yml`。只有整机 Skill 在相邻文件不存在时才使用 `$XDG_STATE_HOME/skill/pr-review-loop.yml`（未设置时为 `$HOME/.local/state/skill/pr-review-loop.yml`）；两者都存在时相邻文件优先。PR 不能靠自身新增 Skill 或配置来改变本次评审；未跟踪文件须预先存在，已跟踪文件只认 base。

```yaml
comment: false
max_rounds: 10
review_retries: 3
```

整机 Skill 建议使用[按项目配置示例](assets/pr-review-loop.machine.example.yml)：`projects` 用 `host/owner/repo` 标识仓库，每个项目独立设置 `comment`、`max_rounds`、`review_retries`；未设置的键依次取 `defaults`、旧版顶层键、内置默认值。项目条目即使设置 `comment: false` 也允许修复闭环。旧版 `comment_targets` 仍可作为目标列表使用。归一化后重复的项目键或无效值不能授权评论或修复。

`comment: true` 开启 PR 评论，`false` 或省略则关闭；`max_rounds` 不影响评论。本次用户明确提出的评论偏好优先。只要项目配置存在，它就独立决定本项目是否评论；没写 `comment` 也不会继承安装级授权。整机 Skill 的有效 `comment: true` 只对 `projects` 或 `comment_targets` 命中的仓库生效；用户本次明确要求评论可允许未列出仓库的评论，但不能让它进入修复闭环。仅命中项目条目或目标列表不会自动开启评论。项目级模板见[示例配置](assets/pr-review-loop.example.yml)。

整机目标归一化为 `host/owner/repo` 后比较，忽略协议、`user@`、大小写、结尾斜杠和 `.git`。只有指向 PR 自身仓库的 remote 才算命中，fork remote 不算；无法核实则视为不匹配。

修复还要求当前托管账号等于 PR 作者、`max_rounds` 大于零、有推送权限且用户未要求禁止改代码。账号未知或不同、项目或整机目标不适用、`max_rounds: 0` 或用户要求只读时，只审查一次，不编辑、提交、推送。两种模式是否评论都由独立策略决定。每条 PR 评论以 `[<平台>][<模型>]` 开头；提交遵守仓库惯例并标明同一身份。

## 审查轮次与终止

`max_rounds` 统计完成的 review，包含通过的一轮，默认 10。`0` 表示只读审查一次、不修复；`1` 表示审查一次并可修复，但推送后的 head 不再复审；`10` 表示最多审查十次。若一轮无问题则提前停止；上限轮刚推送修复时，报告该 head 尚未复审。失败尝试不计轮次；`review_retries` 默认允许再尝试三次，失败尝试不能当作通过。无效上限不会启动修复闭环。

若有无法修复的问题，先完成并验证能修复的部分；仅当确有验证通过的改动时才推送，然后停止并报告遗留问题。没有改动时不制造空提交。只有独立策略允许才向 PR 评论，否则在对话中报告。

复用旧的「通过」结论必须确认 PR base 和 head、本次要求的检查项及范围、适用标准、已完成检查的证据都未变。新增检查要求或 base 变化时，即使 head 没变也必须重审。完整流程和终止条件见 [SKILL.md](SKILL.md)。

## 何时触发

- 指明一个 Pull Request 并要求审查。
- 要求审查并修复，或修复后继续审查，且账号、项目或整机目标与轮次上限允许闭环。
- 要求单次审查；是否发 PR 评论由独立策略决定。

## 何时不触发

- 未指明 Pull Request，只需审查本地 diff、分支、文件或代码片段。
- 用户只要本地或对话中的报告，或同时禁止 PR 评论和代码改动。
- 只需创建、批准、合并等 PR 管理操作。
- 未要求 PR 审查，只需解决冲突、变基、修复工作区，或制定审查标准。
