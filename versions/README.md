# 版本专属层

一份公共译文，发给 5 个整合包版本。这个目录装的是「让同一份译文对每个版本都成立」
所需要的两样东西：**手写的该版差异**，和**机器扫出来的该版事实**。

构建目标由目录决定，没有别处再写一遍：

```bash
ls -d versions/[0-9]*        # 这就是 MC_VERSIONS，新建一个目录＝多一个构建目标
```

## 三层

| 层 | 位置 | 谁写 | 性质 |
|---|---|---|---|
| 公共 | `src/` | 人 | 译文本体，按**最新**版本写 |
| 该版手写 | `versions/<版本>/` | 人 | 只写「这一版跟公共层不一样」的部分 |
| 该版事实 | `versions/db/<版本>/` | CI | 对着该版真实的 jar 扫出来的基线，人只负责过目并提交 |

改译文改 `src/`。只有当**这一版的上游与别版不同**时，才往 `versions/<版本>/` 加东西。

## 手写层：文件逐个说明

| 文件 | 干什么 | 谁读 |
|---|---|---|
| `overrides.sha256` | 该版官方 overrides 的内容指纹。下载回来对不上就当场红 | `fetch_pack.py`、三个工作流 |
| `neoforge.txt` | 该版的 NeoForge 版本号，出货说明里按版本现填 | `build_dist.sh` |
| `default_resource_packs.txt` | 该版 `options.txt` 里 `resourcePacks` 的默认顺序。**没实测就留空并写明原因**——那串顺序必须真起一次实例、干净退出才拿得到；抄上一版会让汉化包被压在别的包下面，而且没有任何提示。留空时安装器不伪造这一行，只提示玩家先启动一次 | `build_dist.sh`、`test_installer.py` |
| `quest_overrides.snbt` | 该版专属的任务书中文（见下「什么时候该分叉」） | `gen_quest_lang_patches.py` 等 |
| `unobtainable.json` | 该版在 CurseForge 上**已被删除**的 jar，按 fileID 逐个登记并写 `why` | `fetch_pack.py`、`build_version_db.py` |
| `unpatchable.json` | `src/upstream/` 里某条改动**在这一版套不上**，逐条登记并写 `why` | `gen_upstream_patches.py` |
| `upstream/<原文件路径>.json` | 该版专属的上游映射，在通用映射**之后**对同一段文本再套一次 | `gen_upstream_patches.py` |

后三个是登记表，共同的规矩：**双向 fail-closed**。登记了但实际还在 → 红（登记过期）；
没登记又确实缺 → 红（有人在偷偷放行）。反例见 `scripts/compliance/test_gates.py`。

## 机器层：`versions/db/<版本>/`

| 文件 | 内容 | 生成者 |
|---|---|---|
| `jars.json` | 该版每个 jar 的 sha256 + CurseForge fileID | `build_version_db.py` |
| `vaultpatcher.json` | 每个 VaultPatcher 模块在该版的 target_class 实际位置、每条 key 在不在常量池里 | 同上 |
| `lang_baseline_local.json` | 该版全部 mod 的英文底本（**不入库**，十几万条，随时可重建） | `build_en_baseline.py` |
| `quest_baseline.json` | 该版任务书英文底本，漂移检测用 | 同上 |
| `keybinds.json` | 该版按键分类的注册名 | `scan_keybinds.py` |
| `productive_trees.json` | 该版资源树的育种结构 | `scan_productive_trees.py` |

**这些一律由 CI 生成，不许拿开发机的下载入库。** 本机可能限速、断流、少下几个 jar，
而这些都看不出来——把一次不干净的下载钉成永久基线，后面所有核对都建立在沙子上。

## 「这一版没有这个东西」有三种正确行为

同一句话在三个生成器里是三种处理，动它们之前先分清是哪一种。

| 生成器 | 该版缺目标时 | 为什么 |
|---|---|---|
| `gen_vaultpatcher.py` | **自动降级**：`mods` 字段留空，模块照发 | 匹配靠 target_class，类不存在就不生效，无害 |
| `gen_books.py` | **跳过**：该版没有这本书就不产 | 书不在 = 没有落点，不是错误 |
| `gen_upstream_patches.py` | **红**，除非在 `unpatchable.json` 里登记过 | 上游文件改了而我们没跟，套不上就意味着**发给用户的是旧上游**——这条是整套结构的支点，不许放宽 |

## 什么时候该把译文分叉

整合包升级会改英文原文。7.1→7.2 之间 ATM 改了 13 条任务书正文，其中 5 条是**机制变了**：

| 键 | 7.1 的行为 | 7.2 的行为 |
|---|---|---|
| `18246A48…` 灌注塔 | 无视距离，走到哪都生效 | 只在设定的区块范围内生效 |
| `30582B5F…` 御腐 | 挖矿或怪物掉落 | 9 御腐破片合 1 御腐片簇，再用凝注台合成 |
| `104EBBC0…` 模拟室 | 没有模式之分 | 分训练 / 推演两种模式 |
| `51236544…` AE2 陨石 | 地表或地下都有 | 埋在地下、通常靠近地表 |
| `76CDC18D…` 御腐感染 | 简述，用澄腐团质治疗 | 详列四种怪、红条阶段、Y<0 获取途径 |

公共内容按最新版本写。原样发给老版本用户，玩家读到的是一段通顺但**描述错误行为**
的中文——比漏翻危险得多，因为看不出来。这几条才进 `quest_overrides.snbt`。

**判据是行为变了，不是英文变了。** 查漂移：

```bash
python3 scripts/check_en_drift.py 7.3 8.0
```

它列出的东西**半数不用改**——拼写修正（`Ingrediant`→`Ingredient`）、语法润色，
中文译的是意思，原样正确。只有行为/数值真的变了才分叉。

覆盖怎么生效：打包时作为 `zz_hanhua_zzz_version_override.snbt` 放进
`config/ftbquests/quests/lang/zh_cn/chapters/`。ftbquestslangsplitter 按**文件名字母序**
合并、后合并的覆盖先合并的，`zzz_` 保证它排在本包其余 `zz_hanhua_*` 之后。

## 闸红了怎么办

| 报错 | 意思 | 做什么 |
|---|---|---|
| `第 N 处改动在官方文件里找不到` | 上游改了这一段 | 行为变了就往 `versions/<版本>/upstream/` 加该版映射；这一版压根没这段就登记进 `unpatchable.json` 并写 `why` |
| `登记成了「该版不适用」，但在官方文件里找得到` | 登记过期，上游又把它加回来了 | 删掉 `unpatchable.json` 里这一条 |
| `没写 why` / `which 不对` | 登记不完整 | `which` 要么 `"all"`，要么 1 起算的序号列表；`why` 必须写清上游在这一版是什么样 |
| `在该版数据库里没有记录——数据库过期了` | 新增了带 `target_class` 的 VaultPatcher 模块，5 个版本的库同时过期 | 推上去，CI 会为缺的版本取 jar、`--only-missing` 补库、上传 artifact 并**红着等人提交**；核对后提交 `versions/db/*/vaultpatcher.json` |
| `jar 没下齐，以下 fileID 没有登记原因` | 少下了 jar | 403/429 是限速，重跑；确认 404 就写进 `unobtainable.json` |
| `N 个 jar 不在这一版的官方 manifest 里` | 拿本机实例建库了 | 用 CI 下的干净包重建 |
| `overrides 内容与仓库记录的指纹对不上` | 下到的官方文件不是这一版的 | 别改指纹，先查下载 |
| `N 个散文页的英文原稿与提取时不同` | **警告不是错误** | 人看一眼；核过的结论记到本文末尾，免得下次重查 |

## 加一个新的整合包版本

1. 只声明「这个版本存在」：

   ```bash
   mkdir -p versions/<新版本> && touch versions/<新版本>/.keep
   ```

   顺手写 `neoforge.txt` 与 `default_resource_packs.txt`（没实测就留空写原因）。

2. 推上去。`build.yml` 发现 `versions/db/<新版本>/jars.json` 不存在，就会：取整合包
   （含全部 jar）→ 写 overrides 指纹 → 生成 jar 字节基线 / VaultPatcher 数据库 /
   英文底本 / 按键注册名 → 跟上一版跑一次英文漂移 → 打包成 artifact
   `new-version-baseline-<新版本>` → **然后 exit 1**。

   这个 exit 1 是有意的：基线没进仓库就等于没有基线，此时出的包没有任何东西能证明
   它对着的是干净的官方文件。机器负责算，人负责过目并提交。

3. 下载 artifact，核对后提交 `versions/<新版本>/overrides.sha256` 与
   `versions/db/<新版本>/`，重跑流水线才会真正出包。

4. 跑一次漂移，决定哪些条目要分叉：`python3 scripts/check_en_drift.py <上一版> <新版本>`。

## 已核过、不必再查的上游漂移

`gen_books.py` 报「英文原稿与提取时不同」是闸在正常工作，但**「英文改了」不等于
「译文错了」**。核过的结论记在这里。

| 何时 | 什么 | 结论 |
|---|---|---|
| ATM10 7.3（ExtendedAE 2.2.33 → 2.2.35） | `assets/extendedae/ae2guide/epp_intro/` 46 页里 41 页变了 | **纯英语文法润色，译文无需跟进** |

抽查的差异形状：`an combination` → `a combination`、`at the same` 漏掉的 `time` 补回、
`can place block or drop items actively` → `can actively place blocks or drop items`、
`Edges composed of` → `Edges are composed of`。ExtendedAE 是国人模组，2.2.35 有人把
英文文法过了一遍。机制、数值、结构描述一个字没变。
