---
name: add-pack-version
description: 给本仓库加一个新的 All the Mods 10 整合包版本（例如 8.3）：声明构建目标、取 CI 生成的基线入库、处理 CI 报红、补译新版带进来的文本、写文档，全部放在一个「适配 <版本>」的 PR 里。用于 ATM10 发了新版、要让汉化包支持它的时候。
---

# 新版本入库

ATM10 发了新版，要让汉化包支持它。整个适配放在**一个分支、一个 PR** 里，标题写 `feat: 适配 <版本>`。不按模组拆成多个 PR。

先读 `AGENTS.md`，尤其是「覆盖率与缺口的口径」和「Git 与 PR」。

## 第零步：确认这一版已经发布

ATM 有时发了版却不写更新日志，所以以 CurseForge 上的文件为准，不看 GitHub 的 changelog。

```bash
python3 scripts/fetch_pack.py <版本> build/packsrc/<版本> --no-jars
```

版本还没发布时，它会报「CurseForge 上找不到」，并列出最近 50 个文件里已有的版本号。

还没发布时，可以先做第五步里能确定的补译：对照 `AllTheMods/ATM-10` 的 main 分支，以及各模组仓库里对应版本的标签。已经装好的整合包还是旧版，不能拿来当新版的底本。

## 第一步：声明构建目标

每样东西一个提交：

1. `versions/<版本>/.keep`：空文件。CI 看到这个目录，才会把这一版当作构建目标。
2. `versions/<版本>/neoforge.txt`：manifest 里的 NeoForge 版本号，例如 `21.1.259`。
3. `versions/<版本>/default_resource_packs.txt`：这一版首次启动后，游戏写进 `options.txt` 的 `resourcePacks` 顺序，不含汉化包。这个值要在装好的这一版整合包里实测，CI 拿不到。文件头的注释写明与上一版的差别。

## 第二步：取 CI 生成的基线入库

推送后，`build` 会故意报红。它会上传 artifact `new-version-baseline-<版本>`，里面有：

- `versions/<版本>/overrides.sha256`：官方 overrides 的内容指纹
- `versions/db/<版本>/`：`jars.json`、`keybinds.json`、`quest_baseline.json`、`vaultpatcher.json`

下载下来，核对后提交，再推送。基线只取 CI 的产物，不在本机生成。

之后按 CI 的报错逐项处理。常见的有：

| CI 报错 | 怎么处理 |
|---|---|
| manifest 里有 jar 下不来（`/download` 返回 404） | 写进 `versions/<版本>/unobtainable.json`，`_why` 写明 fileID、projectID、缺的是哪部分 |
| 上游改写映射在这一版套不上 | 这一版确实没有这段原文：在 `versions/<版本>/unpatchable.json` 登记，写明 `why`。原文改了样子、仍要译：写 `versions/<版本>/upstream/<路径>.json`。两者常常要一起做，例如进服公告 |
| 任务书章节没有 hover 字段可改 | 同样登记进 `unpatchable.json` |
| artifact `productive-trees-baseline` | 提交 `versions/db/<版本>/productive_trees.json` |
| artifact `quest-baseline` 或 `vaultpatcher-db` | 提交对应的 `versions/db/*/` 文件 |

闸红了是包不达标。改内容，不改闸。

## 第三步：版本层沿用上一版

逐项对照上一版的 `versions/<上一版>/`，判断哪些在新版仍然适用：

- `pack_overrides.json`：每一层都按新版 jar 判断是否仍适用，写明 `why`（哪个 jar、与哪一版逐字节相同）。
- `quest_overrides.snbt`：上一版有、新版仍需要的覆盖照抄。例如转位器任务的失效副标题，8.1、8.2、8.3 各要一份。漏掉的话，旧问题会在新版里回来。

## 第四步：找出新版带进来的文本

底本用这一版钉的 jar：

- 新版 jar：`versions/db/<版本>/jars.json` 入库后，用 `fetch_one_jar.py <版本> <文件名> <目录>` 取。装好的整合包确实是这一版时，才能直接读它的 `mods/`。
- 旧版 jar：`fetch_one_jar.py <上一版> <文件名> <目录>`。

用 `crash_assistant/modlist.json` 或两版的 `jars.json` 比出新增、移除、升级的模组，然后按下表逐类查：

| 表面 | 怎么查 |
|---|---|
| 模组 lang | 按 `AGENTS.md`「覆盖率与缺口的口径」求差：新版 `en_us` 减旧版，再减模组自带 `zh_cn`、本包 `zh_cn`、整合包 `kubejs/assets` |
| 任务书 | 对比上游 `lang/en_us` 与 ATM 自带的 `lang/zh_cn`。新章节和新任务键常常整章没有中文 |
| 任务书标题横幅 | 新章节的横幅在 `scripts/gen_quest_banners.py` 登记 |
| 导览书 | 只补**完全没有中文**的新页。模组自带中文跟不上新英文时，不覆盖，除非这份中文公认很烂 |
| VaultPatcher | 升级了的 jar 由 CI 重新核对，按 `vaultpatcher-db` 的结果处理 |
| 可选的拼音搜索 JEC | 查有没有新版，以及新版是否还能注入升级后的 JEI、终端类模组 |

## 第五步：补译

- 每个模组一个提交，标题写模组名和版本，例如 `feat: 补神化 8.9.0 新加的词缀与提示`。
- 物品名用游戏内显示的中文。本包有覆盖的用本包的，没有的用模组自带的。不为了任务书去覆盖物品名。
- 任务书增量放 `zz_hanhua_<章节>.snbt`。新文件先 `git add`，再跑 `python3 scripts/compliance/protect.py --update`。
- 导览书新页：散文页写进 `src/pack/…/_zh_cn/`，在 `src/books/_prose.json` 登记英文的 sha1 与路径。JSON 页写结构型映射 `src/books/<路径>.json`，用 `scripts/books.py` 的 `dump()` 写回。
- `gen_books.py` 只按最新版 jar 生成，产物会发给所有版本。交付时说明旧版本会看到新页。

## 第六步：文档

- `README.md` 的兼容版本表加上新版。
- `CHANGELOG.md`：按 [`write-changelog`](../write-changelog/SKILL.md) 写进下一版本节，开 `### 支持 All the Mods 10 **<版本>**`。一个模组或一个表面一行，例如任务书新章节、某模组新加的界面、导览书。

## 第七步：收尾

- `上游漂移 + 汉化校验` 与 `build` 两项检查都通过。
- 下载 `build` 的 artifact，核对新加的横幅等生成物。
- PR 正文写清做了什么、还缺什么、依据在哪。squash 合并时，提交信息就取 PR 标题与正文。
- 不打 tag，不发 release。发版由维护者做。

## 不要做的

- 本机不跑 `generate_all.sh`。构建只在 CI 里验证。
- 不在本机生成基线，只提交 CI 的 artifact。
- 不拿旧版整合包当新版的底本。
- 版本还没发布时，不写依赖 `jars.json` 的东西。
