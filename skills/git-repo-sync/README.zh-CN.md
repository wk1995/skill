# Git Repo Sync

语言：**简体中文** | [English](README.md)

审计并同步多设备或团队共用的 Git 克隆：识别落后、领先、分歧、上游被改写以及上游分支已删除的分支，安全快进落后分支，并在归档分支顶端后删除已进入默认分支的本地与远端分支；未合并的陈旧分支只报告，除非显式点名。适用于多设备漂移、squash 合并后的清理和陈旧分支审计；不用于推送提交、解决冲突或同步 Skill 副本。

一个仓库被多台设备或多人共用时，漂移会很快累积：一台设备合并功能，另一台 rebase，第三台在评审后 force-push，远端和每个克隆里都会留下无效分支。仅执行 `git fetch` 无法判断哪些分支可以安全删除。本 Skill 把三件事分开：读取状态、快进只是落后的分支、删除内容已确实进入默认分支的分支；未合并分支只有显式点名时才会删除。

## 如何使用

可以对 Agent 说：“审计当前克隆与 origin 的差异，列出陈旧和已合并的分支，先快进安全的分支；我确认之前不要删除任何分支。”也可以直接执行命令。

先做只读审计。它会刷新远端跟踪引用，分类每个本地分支，并列出可清理项与阻断原因：

```sh
python3 <skill-dir>/scripts/repo_sync.py audit --repo . --check-prs
```

只做快进。不会推送提交，也不会改写历史：

```sh
python3 <skill-dir>/scripts/repo_sync.py sync --apply
```

删除已合并分支。默认只演练；加 `--apply` 后会先把分支顶端归档到 `refs/repo-sync/archive/`，再删除：

```sh
python3 <skill-dir>/scripts/repo_sync.py prune --target local --apply
python3 <skill-dir>/scripts/repo_sync.py prune --target remote --apply --check-prs
```

恢复被删除的分支：

```sh
python3 <skill-dir>/scripts/repo_sync.py archive list --repo .
python3 <skill-dir>/scripts/repo_sync.py restore feature/old --repo . --branch feature/old
```

典型审计输出：

```text
Local branches (4)
  main          up-to-date    merged        [current, protected]
  feature/a     behind 2      merged
  feature/b     diverged      unmerged
  old/c         upstream gone merged

Remote branches (7)
  feature/a     12d  merged (squash)
  feature/b      3d  unmerged

Cleanup candidates (merged, unprotected, no uncommitted work)
  local   feature/a
  remote  feature/a
```

加 `--json` 可得到供脚本消费的同构数据。完整状态模型、安全边界、命令参数和退出码见 [SKILL.md](SKILL.md)。

### 为什么用 merge-tree 判断

`git branch --merged` 看不到 squash 合并和 cherry-pick，而 GitHub 上这两种做法很常见。本工具会先抓取远端，再判断“把这个分支合并进默认分支是否会改变目录树”。结果相同，说明该分支已经没有可贡献的内容，可以归档后删除；会新增内容或产生冲突的分支则保持不动。与默认分支没有共同祖先的分支（例如 orphan 的 `gh-pages`）根本无法合并，会被标记为未合并并保持不动，而不会让整个审计失败。

### 哪些分支永远不会被删除

受保护分支（检测到的仓库默认分支、`main`、`master`、`develop`、`trunk`、`release/*`、`hotfix/*`、`gh-pages`，以及额外的 `--protect` glob）、当前分支，以及使用 `--check-prs` 时存在开放 PR 的分支。本地删除与远端删除使用同一套保护；`--default-branch` 只改变合并判定的基准，不会解除远端真实默认分支的保护。未合并分支不能批量删除：`--allow-unmerged` 必须配合明确的 `--branch` 名称。

在其他工作树中检出的分支按普通分支处理，唯一例外是未提交的工作不会被悄悄删掉：只要该工作树存在已跟踪的改动，或仓库里存在 stash，该分支就会被标记为阻断并保留。干净的工作树只是一次检出，因此其分支可以被裁剪；此时该工作树会解绑到归档顶端，文件原样保留。未跟踪文件不参与判定，也不会被解绑影响。只有本地删除会解绑工作树，`--target remote` 完全不动检出。工作树目录已被删除时只剩一条陈旧记录：它既不阻断分支，也没有可解绑的检出，由 `git worktree prune` 另行清理。

删除远端分支时会对审计到的顶端加租约。若另一台设备在审计后向该分支推送，删除会被拒绝，而不是把新工作删掉。

### 运行要求

- Git 2.38+，用于 squash 合并检测；更旧的 Git 会退化为祖先检查，并把 squash 合并的分支视为未合并。
- Python 3.10+。
- 仅在使用 `--check-prs` 时需要已认证的 `gh`，且远端为 GitHub。
- 需要带工作树的普通克隆；bare 仓库会被拒绝。

已在 Windows 和 Linux 上验证，包括仓库门禁。归档是本地引用，不会被推送，但 `git push --mirror` 会把它们发布出去；需要长期共享归档时，请显式创建并推送 tag。

## 何时触发

- 克隆落后于远端、已经分歧，或存在远端已不存在的分支。
- 多台设备或多名成员对同一仓库执行 push、merge、rebase、squash merge 或 force-push。
- 用户要求清理已合并、陈旧、废弃或“无效”的本地与远端分支。
- 中心分支被删除后，本地留下 upstream 已消失的分支。
- 需要在上游被改写时区分“上游重写”和“确实有本地新工作”，再决定 reset 或 rebase。
- 被删除的分支顶端需要归档，并在之后恢复。

## 何时不触发

- 推送本地提交、force-push 历史、创建 PR，或检查提交信息格式。
- 解决正在进行的 merge/rebase 冲突、编辑文件或评审 PR。
- 同步 Skill 副本或其他目录树；请使用 `sync-skills`。
- bare 仓库、submodule、Git LFS 对象、发布 tag 或文件同步工具。
- 为新工作创建分支；使用普通 Git 命令即可。
