# Fork Repository Maintenance

语言：[English](README.md) | **简体中文**

Fork Repository Maintenance 支持选定分支 Fork，在不改变独立个人默认分支的前提下手动同步同名来源分支，单独整合个人功能，并保存或恢复经过验证的 Git bundle 快照。

## 如何使用

可以直接提出：

- “把 A 的 main 和 release/5 Fork 到 B，另建 personal-main 作为我的默认分支。”
- “同步全部已有对应来源分支，不引入 A 新建的分支。”
- “引入 A 新建的 develop，保留我的个人默认分支不变。”
- “把我的版本从上游 5 升级到 7，并保留功能 X。”
- “保存这个 Fork，然后离线恢复到新的目录。”

要求 Python 3.11+、Git 2.45+ 和 macOS/Linux。GitHub.com 操作还要求当前账号已登录的 gh CLI 及相应权限。本版使用真实隔离 Git 仓库和受控 API 夹具验证，尚未认证真实 GitHub 写入流程；不支持其他托管平台或原生 Windows 写操作。

使用本 Skill 的 scripts/fork_maintenance.py，计划和状态放在源码树外。下面的仓库和路径都应替换为用户授权的目标：

```bash
python3 scripts/fork_maintenance.py fork \
  --source acme/project --destination my-account/project \
  --scope selected --branch main --branch release/5 \
  --default-name personal-main --checkout /absolute/new-checkout \
  --dry-run --refresh --save-plan /absolute/fork-plan.json

python3 scripts/fork_maintenance.py fork \
  --plan /absolute/fork-plan.json --approve-plan <approval_digest>
```

`--refresh` 明确允许准备受控本地 Git 对象，不更新 B。没有该参数时使用已准备的对象，历史不足则明确失败。dry-run 不写远端；同时提供 refresh 时，只允许这一步已说明的本地准备。save-plan 不能覆盖已有文件。

Fork 成功后返回 profile_id，后续同步使用它：

```bash
python3 scripts/fork_maintenance.py plan-sync \
  --profile <profile_id> --scope all --new-branches existing-only \
  --refresh --save-plan /absolute/sync-plan.json

python3 scripts/fork_maintenance.py sync \
  --plan /absolute/sync-plan.json --approve-plan <approval_digest>
```

single 搭配一个 branch，selected 搭配显式分支集合，all 不附 branch。existing-only 为默认值，include-new 只在名字空闲时引入选中的来源新分支。“全部”不包含个人默认或功能分支。个人默认分支名必须与复制的来源名不同；未选择 A 默认分支时，须通过 default-base 指定已选基线。

保全与离线恢复：

```bash
python3 scripts/fork_maintenance.py preserve \
  --profile <profile_id> --snapshot-scope both --include-tags \
  --archive-root /absolute/owned-archive \
  --dry-run --refresh --save-plan /absolute/preserve-plan.json

python3 scripts/fork_maintenance.py preserve \
  --plan /absolute/preserve-plan.json --approve-plan <approval_digest>

python3 scripts/fork_maintenance.py restore \
  --snapshot /absolute/owned-archive/<snapshot_id> \
  --destination-path /absolute/new-restored-directory \
  --dry-run --save-plan /absolute/restore-plan.json
```

通过 restore --plan ... --approve-plan ... 执行恢复。恢复 B 要求快照包含 B 的个人默认分支；只保存 A 的快照仍是有效档案，但不能恢复未保存的个人代码。目标路径必须不存在，不覆盖已有目录，恢复不访问远端。Git 对象和引用独立校验；LFS 内容、子模块仓库、未提交工作、凭据和平台附件不在快照内，会明确报告。git_complete 不代表 project_complete。

个人整合通过 integrate --profile ... --source-name main --target personal-main --strategy merge --dry-run --refresh 生成计划，附带一个或多个 `--validation '["程序", "参数"]'`，再执行已授权计划。merge/cherry-pick 会留下候选供审查并按仓库规范提交；在候选内解决/继续和提交后，使用 resume --operation ... --approve-plan ...。线性 rebase 要指定 base-oid 和不同且空闲的 result-branch，不重写已发布默认分支；缺少验证命令的候选保持 unverified，不推送。

具体接口、结果和限制见[运行契约](references/runtime-contract.md)，分支角色见[分支模型](references/branch-model.md)，部分成功和结果不明的处理见[恢复说明](references/recovery.md)。完整 Agent 操作要求见 [SKILL.md](SKILL.md)。

## 何时触发

选定来源分支并建立独立个人默认分支的 Fork 初始化/接管；明确的手动来源同步；单独升级个人版本；Git 历史保全、盘点和离线恢复。

## 何时不触发

不涉及上述 Fork 生命周期的普通 Git 提交、rebase 或 PR；版本发布编排；Agent Skill 文件副本同步；自动定时来源同步；传播上游删除或破坏性替换已分歧共享历史。
