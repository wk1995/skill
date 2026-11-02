# Git Commit Message

语言：**简体中文** | [English](README.md)

在执行 Git 提交前检查并规范提交信息，添加 AI 客户端、可选客户端版本和模型身份前缀，支持按仓库开启的整机前缀、仓库额外前缀、分组开关、仅检查模式及关闭约束。用于执行 git commit 前或配置整机/仓库策略、安装 commit-msg Hook；不用于 Git 只读操作、单独暂存或 PR 评论。

## 如何使用

可以对 Agent 说：“提交前使用 git-commit-message，带上本次会话的客户端、已知版本和模型。”或：“为当前仓库启用提交信息自动检查，再加一个 PROJ-42 前缀。”详细操作与边界见 [SKILL.md](SKILL.md)。

便携 Skill 提供 Agent 指令；仅将 Skill 放进发现目录，**不会**注册 Git Hook。每个克隆安装一次 Hook 后，终端等方式执行提交也会自动触发。运行环境需要 `PATH` 上可用的 Python 3.10+ 和 Git 2.45+（macOS/Linux，原生 Windows 未验证）。在目标工作区操作，将 `tool` 变量设为本 Skill 内 `scripts/commit_message.py` 的绝对路径：

```sh
python3 "$tool" install

# 这里只是示例值，执行时使用当前真实客户端和模型。
AI_AGENT_CLIENT='Codex' AI_AGENT_CLIENT_VERSION='1.2.3' \
AI_AGENT_MODEL='example-model' git commit -m 'fix: 修复登录'
```

生成格式如下，客户端与版本之间使用一个空格：

| 已知身份 | 提交标题 |
| --- | --- |
| 客户端、版本、模型 | `[Codex 1.2.3][example-model] fix: 修复登录` |
| 客户端、模型 | `[Codex][example-model] fix: 修复登录` |
| 只有模型 | `[example-model] fix: 修复登录` |

身份由**每次执行时**的上述环境变量提供。未知客户端或版本直接省略；只有版本而没有客户端时忽略版本。启用 AI 前缀时，`AI_AGENT_MODEL` 必填，缺失会阻止提交，不猜测身份。安装不会保存身份。人工提交也会遇到已安装策略：应提供相应身份、配置 `ai_prefix: false` 或关闭策略，不能沿用之前 Agent 的身份。

### 整机配置

创建 `$XDG_CONFIG_HOME/git-commit-message/config.json`；若 `XDG_CONFIG_HOME` 未设置或为空，则使用 `~/.config/git-commit-message/config.json`。非空的 `XDG_CONFIG_HOME` 必须是绝对路径。同一台设备的所有 Agent 客户端共用该文件，每次执行重新读取：

```json
{"schema_version": 1, "extra_prefixes": ["work"]}
```

另一台设备可以配置成 `{"extra_prefixes": ["home"]}`。整机文件只接受 `schema_version` 和 `extra_prefixes`，两者均可省略；文件不存在时没有整机前缀。该文件放在仓库和 Skill 目录之外，不会随 Skill 同步到其他设备。

**默认不添加整机前缀**，即使整机文件中已经配置 `work`。仓库须显式设置 `"machine_prefix": true` 才会使用。开启后的顺序固定为 `[整机前缀][仓库前缀][客户端 版本][模型]`。整机和仓库配置了相同值时，只在最前面的首次位置保留一次。

### 仓库自定义配置

在工作区根目录创建 `.git-commit-message.json`。每次执行都会重新读取，在子目录和关联工作树中同样如此。**这个文件可以入库，也可以不入库**：入库后供团队共享；不入库时仅供本地使用，两种方式的读取和校验行为一致。仅本地使用时，可在 `git rev-parse --git-path info/exclude` 定位的本机忽略文件中加入 `/.git-commit-message.json`；团队也可以将该规则写入 `.gitignore`。忽略规则只影响尚未跟踪的文件。配置中只保存策略，不要存放会话身份。未配置时使用以下默认值：

```json
{
  "schema_version": 1,
  "machine_prefix": false,
  "repo_prefix": true,
  "ai_prefix": true,
  "extra_prefixes": [],
  "mode": "fix",
  "skip_autosquash": true
}
```

| 配置项 | 含义 |
| --- | --- |
| `machine_prefix` | 默认 `false`；设为 `true` 后，将本设备整机前缀放在最前面。 |
| `repo_prefix` | 默认 `true`；设为 `false` 后，不要求仓库 `extra_prefixes`。 |
| `ai_prefix` | `false` 不要求 AI 客户端/模型前缀，也不要求身份。 |
| `extra_prefixes` | 默认 `[]`，即没有仓库前缀；字符串不写方括号，顺序在整机前缀之后、AI 前缀之前。 |
| `mode` | `fix` 自动规范前缀；`check` 仅检查，格式不符时拒绝且不修改消息。 |
| `skip_autosquash` | 默认 `true`，跳过以 `fixup! `、`squash! `、`amend! ` 开头的标题，保留自动压缩的目标匹配。 |

所有配置项均可省略。未知/重复键、错误类型、重复前缀值，以及前缀或身份中的方括号、控制字符、首尾空白都会被拒绝。即使三个分组开关全部为 false，两个配置文件的错误也不会放行。消息检查和 Hook 安装均不会修改配置文件。

将整机 `work` 与可共享的项目标记叠加：

```json
{"machine_prefix": true, "extra_prefixes": ["PROJ-42"]}
```

结果：`[work][PROJ-42][Codex][example-model] fix: 修复登录`。同一仓库在家庭设备上会使用 `[home][PROJ-42]...`。仓库设为 `machine_prefix: false` 可仅保留项目和 AI 前缀；设为 `repo_prefix: false` 可关闭已配置的仓库前缀而无需删除列表；`ai_prefix` 独立控制 AI 组。

需要额外项目标记：

```json
{"extra_prefixes": ["PROJ-42", "backend"]}
```

结果：`[PROJ-42][backend][Codex 1.2.3][example-model] fix: 修复登录`。

只保留项目标记，不要 AI 前缀：

```json
{"ai_prefix": false, "extra_prefixes": ["PROJ-42"]}
```

关闭所有消息格式化和身份要求时，将三个分组开关全部关闭：

```json
{"machine_prefix": false, "repo_prefix": false, "ai_prefix": false}
```

此时保留消息原始字节，但仍验证配置和文件安全性。也可使用 `{"ai_prefix": false, "extra_prefixes": []}`，仍检查有效标题但不添加前缀。关闭某种前缀只停止要求该前缀，不会自动删除已写入的前缀或改写历史。

原来的 `enabled` 字段已在 1.0.0 删除，继续使用会被视为未知键而报错。旧 `{"enabled": false}` 改为上面的三个开关；旧 `"enabled": true` 直接删除该键，保留其他设置。

### 命令与已有 Hook

```sh
python3 "$tool" --repo /path/to/project install
python3 "$tool" --repo /path/to/project uninstall
python3 "$tool" check /absolute/path/to/message.txt
python3 "$tool" fix /absolute/path/to/message.txt
python3 "$tool" hook /absolute/path/to/message.txt
```

`--repo` 放在子命令前。消息相对路径以进程当前目录为准，不相对于 `--repo`。`hook` 遵循仓库 `mode`；`check` 始终只读；显式 `fix` 用于手动修正。Agent 必须遵循仅检查策略，不能偷偷用 `fix` 绕过它。

安装会把独立可执行脚本复制到默认 `commit-msg` 路径，之后移动或删除 Skill 源码不影响已安装 Hook。相同内容重复安装保持幂等，也会修复可执行权限。卸载只删除内容完全相同的副本；修改过或较旧的 Hook 会保留，需手动处理。Git 默认 Hook 由关联工作树共享，因此安装/卸载影响该克隆的关联工作树，每个工作树仍读取自己的配置。

遇到内容不同的已有 Hook、符号链接/硬链接 Hook、符号链接 Hook 目录，或任何已配置的 `core.hooksPath`，安装都会拒绝，且不覆盖文件或修改 Git 配置。使用 Husky、pre-commit 等管理器时，按其支持方式，将以下调用集成到已有 `commit-msg` 入口：

```sh
python3 /absolute/path/to/commit_message.py hook "$1"
```

必须传递非零退出状态以阻止失败的提交。手动集成要求脚本一直位于指定位置。不会自动串联其他 Hook。安装/卸载先验证配置再写入，但不要求身份。不支持直接覆盖内容不同的已安装版本来自动升级。

### 消息保留与限制

只规范第一个非空标题行，标题必须放在所有注释行之前。开头的注释行会被拒绝，因为 Git 的某些清理模式会将其保留为实际提交标题。已知的当前前缀会排序并去重；其他方括号内容会保留。已有不同客户端/模型前缀会被视为标题内容保留，修改归属时需显式删除。正文、尾注、注释、UTF-8 文本及 LF/CRLF 换行保留。空标题、纯注释和只有前缀的标题会被拒绝。消息文件须是普通 UTF-8 文件，不允许符号链接或硬链接。不支持非 UTF-8 的 Git 提交编码。遵循显式配置的 Git 注释前缀，不支持 `core.commentChar=auto`；如果要求的前缀会被 Git 当作注释删除，将在编辑前拒绝。

当 Git 调用该 Hook 时，合并和 amend 消息同样检查。默认豁免 autosquash 消息；设为 `skip_autosquash: false` 会规范这些消息，可能破坏自动压缩匹配。未调用 `commit-msg` 的 rebase/cherry-pick 路径不在覆盖范围。Git 的 `--no-verify` 或切换 Hook 目录等选项可以绕过本地 Hook；它是本地工作约定，不是服务端强制规则。依据为 [Git Hook 官方文档](https://git-scm.com/docs/githooks)、[Hook 路径配置](https://git-scm.com/docs/git-config#Documentation/git-config.txt-corehooksPath) 和 [autosquash 消息行为](https://git-scm.com/docs/git-commit)。

## 何时触发

- Agent 即将执行 `git commit`，包括 `--amend` 和 `-F`。
- 安装、卸载、配置、检查或修正提交信息归属 Hook。
- 配置整机前缀、按仓库开启整机标记，或分别关闭整机、仓库、AI 前缀组。

## 何时不触发

- Git 只读查询、单独暂存、新建分支或只推送已有提交。
- PR 评论/审查、发布说明及非 Git 文本格式化。
- 没有既有用户请求时，授权提交、amend 或发布。
