# Release Engineering Skill 双向同步设计

日期：2026-07-10

## 1. 背景

本机现有 Skill 位于 `~/.codex/skills/release-publishing`，覆盖软件发布的规划、校验、构建、制品发布、标签与分支同步、发布后处理和故障恢复。`release-publishing` 容易被理解为只负责上传制品，不能准确表达完整职责，因此重命名为 `release-engineering`。

仓库 `/Users/chengpeng/project/wk/skill` 用于集中管理个人 Skills。此次将该 Skill 作为首个真实 Skill 同步进仓库，并建立本机 Codex 目录与仓库源码之间的即时双向可见关系。

## 2. 目标

- 在仓库中以 `skills/release-engineering` 保存完整、可被 Git 跟踪的 Skill 源码。
- 将 Skill 名称、展示名称、默认提示和标题统一为 `release-engineering` / `Release Engineering`。
- 在 `SKILL.md` 的 `metadata.version` 中设置独立版本 `1.0.0`。
- 让 `~/.codex/skills/release-engineering` 指向仓库中的真实目录，使修改任一路径都立即反映到另一处。
- 提供安全、幂等的本机链接脚本，以便重新建立链接。
- 移除旧的 `~/.codex/skills/release-publishing` 路径，避免重复发现和旧名称继续生效。

## 3. 非目标

- 不实现 README 中规划的完整 TypeScript CLI、MCP Server、registry 或 Codex 聚合插件。
- 不推送远端、不创建远端标签、不发布制品。
- 不引入后台文件监听器，也不维护两份需要合并的 Skill 副本。
- 不保留旧名称兼容别名；同一 Skill 以两个目录被发现可能导致重复或歧义。

## 4. 选定方案

仓库目录是单一事实源，本机 Codex Skill 路径是指向它的符号链接：

```text
/Users/chengpeng/project/wk/skill/skills/release-engineering
                           ↑
                           │ symbolic link
                           │
/Users/chengpeng/.codex/skills/release-engineering
```

该结构只有一份物理文件，因此不存在双向冲突、同步延迟或覆盖顺序。Git 跟踪仓库中的真实内容；本机 Codex 直接读取同一内容。

不采用“仓库链接到本机”，因为 Git 只能记录链接本身，无法保存 Skill 内容。不采用双副本同步脚本，因为双方同时修改时需要额外的冲突检测与合并协议。

## 5. 文件与职责

```text
skills/release-engineering/
├── SKILL.md                 # 通用入口、触发描述和 1.0.0 版本
├── agents/openai.yaml       # Codex 展示名称、简述和默认提示
└── references/*.md          # 各发布目标和工作流参考资料
scripts/
└── link-codex-skill.sh      # 安全、幂等地建立本机符号链接
tests/
└── release-engineering-sync.sh # 元数据、内容和链接行为契约测试
```

`link-codex-skill.sh` 根据自身所在仓库计算绝对源目录，默认链接到 `${CODEX_HOME:-$HOME/.codex}/skills/release-engineering`。目标不存在时创建链接；目标已经指向正确源目录时成功退出；目标是其他文件、目录或不同链接时拒绝覆盖并返回非零退出码。

## 6. 迁移流程

1. 将本机旧目录的全部文件复制到仓库新目录。
2. 更新 `SKILL.md` 的 `name`、标题和 `metadata.version`。
3. 更新 `agents/openai.yaml` 的展示名称和默认提示。
4. 比较迁移前后的文件集合与除重命名字段外的内容，确保 references 无丢失。
5. 只有在仓库副本校验通过后，移除旧本机目录。
6. 运行链接脚本，建立新路径符号链接。
7. 验证本机路径和仓库路径解析为同一目录。

旧目录的删除发生在完整复制和校验之后。若任一校验失败，停止迁移并保留旧目录。

## 7. 错误处理与安全边界

- 仓库源目录不存在时，链接脚本报错且不修改本机目录。
- 本机目标已存在但不是预期链接时，脚本拒绝覆盖并输出冲突路径。
- 脚本不得删除或移动未知内容，也不得自动调用 `sudo`。
- 测试使用临时 `CODEX_HOME`，不得触碰真实本机 Skill 目录。
- 真实迁移只处理用户明确指定的 `release-publishing` 旧目录和 `release-engineering` 新链接。
- Git 操作限于本地；不执行 push、tag、PR 或发布操作。

## 8. 测试与验收

- `skills/release-engineering/SKILL.md` 存在，目录名与 `name` 完全一致。
- `metadata.version` 等于字符串 `1.0.0`。
- Skill 中不再包含 `release-publishing` 或 `Release Publishing`。
- 原有 6 个 reference 文件与 `agents/openai.yaml` 均存在。
- 链接脚本在临时 `CODEX_HOME` 中首次运行可创建链接，第二次运行保持幂等。
- 链接脚本遇到已有普通文件或错误链接时拒绝覆盖。
- 通过本机路径和仓库路径读取的文件内容一致；任一路径写入的临时探针在另一侧可见，清理探针后工作树恢复干净。
- `git diff --check` 通过，仓库内不存在意外的旧名称引用。

## 9. 发布契约

- **Source：** 当前本地 `main` 提交及本次本地变更，不涉及远端发布。
- **Version：** `skills/release-engineering/SKILL.md` 中的 `metadata.version: "1.0.0"`。
- **Artifact：** 仓库内完整 Skill 目录和可重复执行的链接脚本。
- **Destination：** 本仓库源码目录，以及本机 Codex Skill 链接。
- **Gates：** 元数据契约测试、文件完整性检查、脚本安全测试、真实链接验证。
- **Success point：** 仓库真实文件通过测试，且本机新路径正确链接到仓库目录。
- **Aftercare：** 确认旧路径不存在、工作树无意外变更并报告未执行任何远端操作。
- **Failure policy：** 在仓库副本验证前不移除旧目录；遇到目标冲突立即停止，禁止盲目覆盖。
