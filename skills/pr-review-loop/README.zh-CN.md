# PR 评审闭环

语言：[English](README.md) | **中文**

`pr-review-loop` 用于对 Pull Request 执行评审闭环：审查当前 head、修复确认的问题、提交推送，再重新审查，直到某一轮不再发现确认问题为止。它只定义闭环本身——身份标注、轮次顺序、评论决策、终止条件与汇报，刻意不定义「该怎么审查」；评论默认关闭，只有评论策略为该仓库开启时才会把问题写到 PR 上，且每条评论都标注触发这次评论的平台与模型。

## 如何使用

指向一个 Pull Request 并说明诉求即可：

```text
review PR #25，有问题就修复，直到没问题为止。
review https://github.com/<owner>/<repo>/pull/42，把问题评论到 PR 再修。
继续这个 PR 的评审闭环，接着上一轮往下走。
```

请通过编号或链接指明 Pull Request，如果不是当前检出仓库，再补上仓库名。闭环会锁定确切的 head 提交、完成审查、修复并推送，然后重复，直到某一轮无问题或命中终止条件。

## 评论策略

**默认不评论。** 只有策略来源为该仓库开启评论时，闭环才会把问题写到 PR 上，因此整机通用安装不会往你没有列出的仓库里写评论。只指明 PR 并要求「审查」不构成评论授权；针对本次 review 明确要求评论才算。

策略按以下顺序解析，第一个有决断的来源生效：

1. **本次 review** —— 你针对这一次明确说明是否评论。
2. **项目级配置** —— `<项目根>/.pr-review-loop/comment-targets.yml`。
3. **安装级配置** —— 正在运行的 Skill 目录下的 `comment-targets.yml`；若该目录需要保持干净或只读，可用 `$XDG_STATE_HOME/skill/pr-review-loop/comment-targets.yml`（未设置 `XDG_STATE_HOME` 时为 `$HOME/.local/state/...`）。
4. **默认** —— 不评论。

两个层级使用同一文件名与同一组键：

```yaml
comment: false
comment_targets:
  - https://github.com/wk1995/skill.git
```

命中 `comment_targets` 的 remote 会收到评论；否则由 `comment` 决定该层级；再否则交给下一个来源。remote 一律归一化为 `host/owner/repo` 后按大小写不敏感比较，忽略协议、`user@`、结尾斜杠与结尾 `.git`。带注释的模板见 [assets/comment-targets.example.yml](assets/comment-targets.example.yml)。

只想让某个仓库收到评论，就把它的 remote 写进安装级配置；想为某个项目开关评论，就把项目级配置连同 `comment: true` 或 `comment: false` 提交进仓库。

闭环发出的每条评论首行都带 `[<平台>][<模型>]`——即运行本闭环的智能体平台与当前实际使用的模型详细名；提交信息则遵循仓库自身的提交约定并携带同一身份。完整闭环契约、终止条件与边界见 [SKILL.md](SKILL.md)。

## 何时触发

- 明确指向某个 Pull Request，并要求对其进行代码审查。
- 要求审查并修复某个 Pull Request，或要求把问题作为 PR 评论提出后再修复。
- 要求反复审查某个 Pull Request 直到没有问题，或继续一个未完成的评审闭环。

## 何时不触发

- 没有指明 Pull Request：只审查本地 diff、分支、文件或代码片段，并在对话里给出结论。
- 用户只要只读审查或报告，并明确说明不评论、不提交、不改代码。
- 属于 Pull Request 的日常管理而非审查：创建、编辑、改标题、打标签、批准、关闭或合并。
- 在未要求审查的情况下解决冲突、变基或修复工作区。
- 用户想制定或修改「代码审查应当检查什么」的标准。

只是只读审查时，请使用仓库自带的评审标准，而不是本闭环；本 Skill 止步于闭环边界，不决定一次审查必须检查哪些内容。
