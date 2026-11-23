# 版本专属层

一份公共译文，发给 5 个整合包版本。这个目录存放两类东西，让同一份译文对每个版本都成立：
手写的该版差异，以及 CI 扫描出的该版事实。

构建目标由目录决定：

```bash
ls -d versions/[0-9]*        # 即 MC_VERSIONS。新建一个目录，就多一个构建目标
```

## 三层

| 层 | 位置 | 谁写 | 性质 |
|---|---|---|---|
| 公共 | `src/` | 人 | 译文本体，按最新版本写 |
| 该版手写 | `versions/<版本>/` | 人 | 只写这一版与公共层不同的部分 |
| 该版事实 | `versions/db/<版本>/` | CI | 按该版实际的 jar 扫描出的基线，人只负责核对并提交 |

改译文就改 `src/`。只有这一版的上游与别的版本不同时，才往 `versions/<版本>/` 加东西。

## 手写层：文件说明

| 文件 | 作用 | 谁读 |
|---|---|---|
| `overrides.sha256` | 该版官方 overrides 的内容指纹。下载后对不上就失败 | `fetch_pack.py`、三个工作流 |
| `neoforge.txt` | 该版的 NeoForge 版本号，打包时填进出货说明 | `build_dist.sh` |
| `default_resource_packs.txt` | 该版 `options.txt` 里 `resourcePacks` 的默认顺序。没实测就留空并写明原因，这串顺序必须真正启动一次实例、正常退出才拿得到。照抄上一版会让汉化包被压在别的包下面，而且没有任何提示。留空时安装器不写这一行，只提示玩家先启动一次 | `build_dist.sh`、`test_installer.py` |
| `quest_overrides.snbt` | 该版专属的任务书中文（见下文「什么时候把译文分叉」） | `gen_quest_lang_patches.py` 等 |
| `pack_overrides.json` | 该版专属的资源包差异：`lang` 覆盖单个键，`files` 引用 `src/pack_overrides/<层名>/` 整页覆盖散文。每项都必须写 `why` | `gen_pack_overrides.py` |
| `unobtainable.json` | 该版在 CurseForge 上已被删除的 jar，按 fileID 逐个登记并写 `why` | `fetch_pack.py`、`build_version_db.py` |
| `unpatchable.json` | `src/upstream/` 里某条改动在这一版套不上，逐条登记并写 `why` | `gen_upstream_patches.py` |
| `upstream/<原文件路径>.json` | 该版专属的上游映射，在通用映射之后对同一段文本再套一次 | `gen_upstream_patches.py` |

后三个是登记表，规则相同，两个方向都检查：登记了但实际还在，会失败（登记过期）。
没登记又确实缺，也会失败（否则等于未经登记就放行）。反例见 `scripts/compliance/test_gates.py`。

`pack_overrides.json` 的检查同样严格：文件层不存在或为空、目标不在公共资源包、
内容与公共页相同、两层写同一个路径，都会失败。公共页如果因为与模组自带中文
逐字节相同而被版权检查剔除，只有该次构建的剔除清单里路径与 SHA-256 都匹配时，才允许恢复。
散文整页分叉只放在 `src/pack_overrides/<层名>/assets/`。公共页仍留在 `src/pack/`，
老版本不会被新版正文覆盖。

## 机器层：`versions/db/<版本>/`

| 文件 | 内容 | 生成者 |
|---|---|---|
| `jars.json` | 该版每个 jar 的 sha256 与 CurseForge fileID | `build_version_db.py` |
| `vaultpatcher.json` | 每个 VaultPatcher 模块在该版的 target_class 实际位置，以及每条 key 在不在常量池里 | 同上 |
| `lang_baseline_local.json` | 该版全部 mod 的英文底本（不入库，十几万条，随时可重建） | `build_en_baseline.py` |
| `quest_baseline.json` | 该版任务书英文底本，用于漂移检测 | 同上 |
| `keybinds.json` | 该版按键分类的注册名 | `scan_keybinds.py` |
| `productive_trees.json` | 该版资源树的育种结构 | `scan_productive_trees.py` |

这些文件只由 CI 生成，不用开发机下载的文件入库。开发机下载可能被限速、中断或少几个 jar，
从结果上看不出来。用它做基线，之后的核对都不可靠。

## 该版缺少目标时，三个生成器的处理不同

改这几个生成器之前，先分清是哪一种。

| 生成器 | 该版缺目标时 | 原因 |
|---|---|---|
| `gen_vaultpatcher.py` | 降级：`mods` 字段留空，模块照常发布 | 按 target_class 匹配，类不存在就不生效，没有副作用 |
| `gen_books.py` | 跳过：该版没有这本书就不生成 | 该版没有这本书，译文就没有地方放，这不是错误 |
| `gen_upstream_patches.py` | 失败，除非在 `unpatchable.json` 里登记过 | 上游文件改了而本包没跟上时，发出去的是旧的上游文件。这条不许放宽 |

## 什么时候把译文分叉

整合包升级会改英文原文。7.1→7.2 之间 ATM 改了 13 条任务书正文，其中 5 条是机制变了：

| 键 | 7.1 的行为 | 7.2 的行为 |
|---|---|---|
| `18246A48…` 灌注塔 | 无视距离，走到哪都生效 | 只在设定的区块范围内生效 |
| `30582B5F…` 御腐 | 挖矿或怪物掉落 | 9 御腐破片合 1 御腐片簇，再用凝注台合成 |
| `104EBBC0…` 模拟室 | 没有模式之分 | 分训练 / 推演两种模式 |
| `51236544…` AE2 陨石 | 地表或地下都有 | 埋在地下、通常靠近地表 |
| `76CDC18D…` 御腐感染 | 简述，用澄腐团质治疗 | 详列四种怪、红条阶段、Y<0 获取途径 |

公共内容按最新版本写。原样发给老版本，玩家读到的是一段通顺、但描述的行为不对的中文。
这比漏翻危险，因为看不出来。所以这几条放进 `quest_overrides.snbt`。

判据是行为变了，而不是英文变了。查漂移：

```bash
python3 scripts/check_en_drift.py 7.3 8.0
```

它列出的条目有一半不用改：拼写修正（`Ingrediant`→`Ingredient`）、语法润色，
中文译的是意思，原样就是对的。只有行为或数值真的变了才分叉。

覆盖的生效方式：打包时放进 `config/ftbquests/quests/lang/zh_cn/chapters/`，
文件名是 `zz_hanhua_zzz_version_override.snbt`。ftbquestslangsplitter 按文件名字母序
合并，后合并的覆盖先合并的，`zzz_` 让它排在本包其余 `zz_hanhua_*` 之后。

## 检查失败时怎么办

| 报错 | 意思 | 怎么做 |
|---|---|---|
| `第 N 处改动在官方文件里找不到` | 上游改了这一段 | 行为变了，就往 `versions/<版本>/upstream/` 加该版映射。这一版根本没有这段，就登记进 `unpatchable.json` 并写 `why` |
| `登记成了「该版不适用」，但在官方文件里找得到` | 登记过期，上游又把它加回来了 | 删掉 `unpatchable.json` 里这一条 |
| `没写 why` / `which 不对` | 登记不完整 | `which` 要么是 `"all"`，要么是从 1 开始的序号列表。`why` 必须写清上游在这一版是什么样 |
| `在该版数据库里没有记录，数据库过期了` | 新增了带 `target_class` 的 VaultPatcher 模块，5 个版本的库同时过期 | 推送后，CI 会为缺的版本下载 jar，用 `--only-missing` 补库，上传 artifact 并失败，等人提交。核对后提交 `versions/db/*/vaultpatcher.json` |
| `jar 没下齐，以下 fileID 没有登记原因` | 少下载了 jar | 403/429 是限速，重新运行。确认是 404，就写进 `unobtainable.json` |
| `N 个 jar 不在这一版的官方 manifest 里` | 用开发机上装好的整合包建了库 | 用 CI 下载的干净整合包重建 |
| `overrides 内容与仓库记录的指纹对不上` | 下载到的官方文件不是这一版的 | 不要改指纹，先查下载 |
| `N 个散文页的英文原稿与提取时不同` | 这是警告，不是错误 | 人工核对，结论记到本文末尾 |

## 加一个新的整合包版本

1. 声明这个版本：

   ```bash
   mkdir -p versions/<新版本> && touch versions/<新版本>/.keep
   ```

   同时写 `neoforge.txt` 与 `default_resource_packs.txt`（没实测就留空并写明原因）。

2. 推送。`build.yml` 发现 `versions/db/<新版本>/jars.json` 不存在，就会下载整合包
   （含全部 jar），写 overrides 指纹，生成 jar 字节基线、VaultPatcher 数据库、
   英文底本与按键注册名，跟上一版比对一次英文漂移，打包成 artifact
   `new-version-baseline-<新版本>`，然后 exit 1。

   这里故意退出 1：基线还没入库，就无法证明打出的包对应的是干净的官方文件。
   CI 只负责计算，由人核对后提交。

3. 下载 artifact，核对后提交 `versions/<新版本>/overrides.sha256` 与
   `versions/db/<新版本>/`，重新运行流水线才会真正打包。

4. 比对一次漂移，决定哪些条目要分叉：`python3 scripts/check_en_drift.py <上一版> <新版本>`。

## 已核对过的上游漂移

`gen_books.py` 报「英文原稿与提取时不同」时，英文改了不一定说明译文错了。
核对过的结论记在这里。

纯 BOM 或不改变中文含义的英文润色，最新字节写入 `sha1`，旧版字节写入
`equivalent_sha1`，两者都视为同一份中文底本。正文实质变化不能登记为等价，必须用
`variants` 指向有译文的版本文件层。

| 何时 | 什么 | 结论 |
|---|---|---|
| ATM10 7.3（ExtendedAE 2.2.33 → 2.2.35） | `assets/extendedae/ae2guide/epp_intro/` 46 页里 41 页变了 | 纯英语文法润色，译文无需跟进 |
| ATM10 8.0（AdvancedAE 1.6.11 → 1.6.12） | 12 个散文页指纹变化 | 正文逐字相同，仅新增 UTF-8 BOM。更新底本指纹即可 |
| ATM10 8.0（EnderDrives 1.4.4 → 1.5.23） | 末影磁盘页新增 6 种流体磁盘 | 机制内容新增。8.0–8.2 由 `books-8.0` 文件层接管，7.0–7.3 保留旧页 |
| ATM10 8.0（Tombstone 9.5.3 → 9.5.4） | 4 组共 16 篇英文故事全部重写 | 正文实质变化。只以 `en_us` 为底本翻译，8.0–8.2 由 `books-8.0` 文件层接管 |
| ATM10 8.2（AE2 Import Export Card 1.6.0 → 1.9.0） | 输入输出卡总览新增“选取方块卡” | 新增功能。仅 8.2 由 `books-8.2` 文件层接管 |
| ATM10 8.2（Modern Industrialization 2.5.6 → 2.5.8） | 大型蒸汽锅炉与原油处理两页补充并修正燃料倍率 | 机制说明变化。仅 8.2 由 `books-8.2` 文件层接管 |
| ATM10 8.2（Oracle Index 1.3.1 → 1.4.0） | 开发设置、搜索、用户指南三页补充渲染兼容性、译文回落与搜索限制 | 实质新增。仅 8.2 由 `books-8.2` 文件层接管 |

ExtendedAE 2.2.35 的英文差异举例：`an combination` → `a combination`、补回 `at the same` 后漏掉的 `time`、
`can place block or drop items actively` → `can actively place blocks or drop items`、
`Edges composed of` → `Edges are composed of`。ExtendedAE 是国人模组，2.2.35 只修正了英文文法，机制、数值、结构描述没有变化。
