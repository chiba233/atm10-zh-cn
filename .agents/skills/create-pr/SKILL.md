---
name: create-pr
description: 为本仓库准备并创建 PR：核对发布范围，按改动类型给出证据（译名的真源、名字的全部表面、增量口径），玩家可见的改动同时写更新日志，通过禁词检查，开 PR 后读 CI。用于需要开、创建、发布或准备 PR 的时候。
---

# 创建 PR

从要发布的那几个提交创建一个能审的 PR。PR 正文写依据，不只列改了哪些文件。

## 步骤

1. 读 `AGENTS.md`。查看状态、当前分支、远端与目标分支（`main`）。
2. 执行 `git fetch origin`。算出 merge base，记下这个 PR 要发布的范围 `origin/main...HEAD`。
3. 读完整 diff。按「改动类型与证据」给它分类，一个 PR 可以有多类。
4. 按类型收集证据。证据要能指到字节：文件路径与行号、jar 的 fileID 与 sha256、条目页链接。
5. 如果改动玩家看得见，按 [`write-changelog`](../write-changelog/SKILL.md) 写更新日志，放在同一个 PR 里。
6. 提交。一件事一个提交，标题格式见 `AGENTS.md`「Git 与 PR」。
7. 对提交消息与 PR 正文跑禁词检查，命令见 [`simple-chinese`](../simple-chinese/SKILL.md)「自检」。
8. 推送分支。按 [PR 正文模板](references/pr-body.md) 写正文，然后创建 PR。
9. 打开 PR 核对标题、base、head、正文，以及表格与图片的渲染。
10. 读 CI 必需检查的结果。如果检查失败，先读日志。闸失败说明内容不达标，改内容，不改闸。
11. 读评审意见。确认是错误的就改，推送后回复证据。

## 改动类型与证据

| 类型 | 证据 |
|---|---|
| 改译名 | 真源表：MC百科条目页 `/item/<id>.html`（不是搜索页）、CFPA、模组 jar 自带的 `zh_cn`，按这个顺序取。另附这个名字的全部表面清单。 |
| 补译 | 增量口径：新版 jar 的 `en_us` 减去旧版，再减去模组自带 `zh_cn`、本包、整合包 `kubejs/assets` 已有的键。占位符的数量和顺序都要核，闸只查数量。 |
| 版本适配 | 哪个整合包版本、哪个 jar（fileID 与 sha256）、上游哪里变了。 |
| 闸与脚本 | 反例测试。前提取不到时，闸必须失败。 |
| 安装器 | 三个系统的 `Installer test` 结果。 |
| 游戏内可见的界面 | 改动前后的截图。用 [`upload-github-attachment`](../upload-github-attachment/SKILL.md) 上传，不把图片提交进仓库。 |

### 一个名字的全部表面

改译名时，在下面这些地方查同一个名字。每一处的结论都写进 PR 正文，「没有引用」也写。

- 物品名所在的语言文件
- 任务书。`quest.<id>.title` 与 `quest.<id>.quest_desc` 是两个不同的键。
- 导览书、成就、结构罗盘
- 整合包注入的 `kubejs/assets/<命名空间>/lang/`。它的命名空间可能与模组 id 不同，译文会压过资源包。
- 版本层 `versions/<版本>/pack_overrides.json` 与 VaultPatcher 模块

「库存」这类常见词的子串命中只能用来定位。每一处都看到整句再判断。

## 验证

- 写出通过的 CI 检查名。`main` 的必需检查是 `上游漂移 + 汉化校验` 与 `build`。
- CI 通过只证明它配置的检查通过。游戏内是否生效，写成「未在游戏内验证」。
- 已验证的事实、推断、未验证的条件分开写。没有证据时，不写「已修复」「安全」「兼容」。

## 合并与发布

- `main` 只允许 squash 合并。维护者没有要求时，不开自动合并。
- 不 force push。不打 tag，不发 release，不触发 Release workflow。

## 来源

流程改写自 [moeru-ai/airi](https://github.com/moeru-ai/airi) 的同名 skill，按 MIT 许可再分发，许可全文见 `.agents/LICENSE-airi.txt`。
