# 贡献指南

感谢你愿意让这份汉化更好。下面几条是**高压线**，每一条都对应一次真实事故；
CI 能拦住其中大部分，但请先读完再动手。

## 高压线

1. **枚举协议值绝不可翻译。**
   McJtyLib 系（RFTools 等）GUI 里的模式选项（`Ignored` / `Off` / `On` /
   `Copy` / `Move` / `Swap`…）是存储与网络协议值，翻译会导致
   `IllegalStateException` 崩溃。资源包 `.gui` 文件里 `choice('...')`
   的参数同理必须保持英文。`scripts/check.py` 有硬检查。
2. **玩家自定义名神圣不可侵犯。**
   命名牌 / 铁砧起的名字绝不允许被改写或"翻译"。资源蜜蜂的迁移与显示
   都通过"系统生成名封闭集合"（PB_SYS）把关——不要绕过它。
3. **服务端数据层禁止注入中文。**
   服务器侧的语言表 / 配方数据必须保持上游英文，否则服务端现算的文本
   与 JEI / 配方（客户端由英文数据现算）分裂，玩家查不到配方。
   在服务端注入语言表的做法因此一律不予采纳。
   同理：`mysticalcustomization/`（作物名）是纯客户端配置，
   **绝不能进服务端包**——会让所有玩家进服刷
   `error creating crop with id null`。
4. **禁止贪婪字符串替换。**
   所有显示层替换必须整词 / 整段精确匹配（词边界、长名优先、
   hasOwnProperty 防原型链穿透）。半截替换（`Ter-蜜蜂-Nator`）比不翻译更糟。
   同一个词在不同上下文里可能是两回事：`星辉`既是 Starlight（星辉水晶、符文星辉祭坛）
   又被误用于 Starry Bee；`遗迹`是废墟，Relics 那个模组说的是随身`遗物`；
   `冰与火`在沉浸工程里是热逆转附魔的风味文字，与那个模组无关。全局替换会把它们一并破坏。
5. **有几类字符串翻译后会崩溃，或翻译了也不生效。**
   - 建筑棒（structurize）以 `/` 开头的**路径键**是 Map 的键，译了直接 NPE 闪退。
   - blockui 的 `top` / `horizontal` 这类**对齐标志**是字符串枚举，译了会让整个
     MineColonies / 建筑棒界面错位。
   - **物品 tooltip 里不能有 `\n`**，会被画成 LF 方框；GUI 提示和聊天才认换行。
     物品说明太长只能改措辞压短。
   - CC: Tweaked 的终端字形表只有 256 格，**没有任何汉字**，`help` 一类整体不译。
6. **删除文件会让 CI 直接失败。**
   `src/` 有一份保护清单（`scripts/compliance/protect.py`），汉化**只许加不许删**。
   新加文件要 `git add` 之后再跑 `protect.py --update` 登记（它靠 `git ls-files`，
   顺序反了会「新收 0 个」）。CI 报红通常意味着删错了文件，不要去改闸。

## 仓库结构：只有源，没有出货树

仓库里**没有任何一棵出货用的目录树**。`kubejs/`、`config/`、`resourcepacks/`、`mods/`
这些整合包目录都是**产物**，构建时现摊、现产、现打补丁，全部落在 `build/` 下（不入库）。
仓库里只有 `src/`（手写的真源与改动映射）和 `scripts/`（生成器）。

```
src/pack/                       资源包内容（译文；lang 按命名空间索引，跨版本通用）
src/config/                     本包独有的 config（任务书 delta、VaultPatcher 主配置…）
src/kubejs/                     本包独有的 KubeJS 脚本
src/upstream/<路径>.json        整合包自带文件的行级改写映射
src/books/<路径>.json           导览书的「位置 + 原文 + 译文」映射
src/vaultpatcher/modules/       硬编码文本模块（只留译文与目标类）；内容哈希钉在 src/module_hashes.json
src/keep_english.json           刻意保留英文的词及其理由（MekaSuit 之类）
src/protected.json              保护清单：src/ 下不许消失的文件
src/mods.lock.json              随包分发的第三方 jar：项目 / 版本 / 地址 / sha256
src/rules/*.json                发版校验的**规则**（check.py 只是它们的解释器）
src/toolchain.lock.json         构建工具链：容器 digest / Pillow / 字体哈希
requirements.lock               Pillow 的全平台 wheel 哈希（装的时候必须 --require-hashes）
versions/<版本>/                手写的版本专属层（任务书覆盖、默认资源包顺序）
versions/<版本>/overrides.sha256 该版官方 overrides 的整棵树指纹（CI 缓存键 + 门控）
versions/<版本>/unobtainable.json 该版 manifest 里已从 CurseForge 消失的 jar（必须逐个登记）
versions/<版本>/unpatchable.json 该版官方文件里已经不存在的上游改动（必须逐条登记 + 写理由）
versions/<版本>/upstream/       该版专属的上游映射（上游只在这一版把那段改成了别的样子）
versions/db/<版本>/             该版的核验数据库与英文底本
versions/db/<版本>/jars.json    该版每个 jar 的 sha256 + 不可变的 CurseForge fileID
versions/db/<版本>/keybinds.json 该版全部按键分类与注册名（含拼名字用的字符串原子）
scripts/                        生成器
scripts/compliance/             闸（gate）与它们的反例测试

build/common/                   摊好的出货树（版本中立部分）
build/v/<版本>/                 该版的完整出货树，check.py 查的就是它
build/packsrc/<版本>/           该版官方 overrides（fetch_pack.py --no-jars 取）
```

动手前先摊一次：

```bash
python3 scripts/assemble.py                             # 只摊源（不需要整合包）
ATM_PACK_ROOT=<整合包目录> ./scripts/generate_all.sh    # 摊 + 跑全部生成器
```

### 生成器一览

`scripts/` 下是生成器与取材脚本，`scripts/compliance/` 下是闸。入口只有两个：
`generate_all.sh`（摊源 + 依次跑全部生成器）与 `build_dist.sh`（逐版合成、校验、出 zip）。

**摊源与出货**

| 脚本 | 作用 |
|---|---|
| `assemble.py` | 把 `src/` 的真源摊成一棵出货树（`build/common/`）|
| `paths.py` | 全仓库统一的目录约定，所有脚本从这里取路径 |
| `mkzip.py` | 打 zip，并保证中文文件名带 UTF-8 标志位 |
| `build_in_container.sh` | 在按 digest 钉死的容器里构建——产物哈希只有从这里出来才作数 |
| `toolchain.py` | 核对本次构建的工具链，决定产物**能不能拿字节去比** |

**取上游素材**

| 脚本 | 作用 |
|---|---|
| `fetch_pack.py` | 把某个版本的 ATM10 备齐成一个可当 `ATM_PACK_ROOT` 用的目录 |
| `fetch_one_jar.py` | 只需要某一个 mod 的 jar 时用它：按 `versions/db/<版本>/jars.json` 的 fileID 单取一个并核 sha256；缓存按内容寻址，跨版本命中 |
| `fetch_mods.py` | 按 `src/mods.lock.json` 取随包分发的第三方 jar，逐个核 sha256 |
| `fetch_fonts.sh` | 取生成 PNG 用的字体（全 OFL，不入库）|
| `vanilla.py` | 取**原版** Minecraft 的语言文件与字体资源（被 5 个生成器 import，不单独运行）|
| `build_version_db.py` | 为某版建核验数据库：每个 jar 的 sha256 与不可变 fileID、字节码常量、按键表 |
| `build_en_baseline.py` | 给每一条译文记下它翻译时对着的英文底本 |
| `scan_productive_trees.py` | 扫该版资源树的育种结构（哪个任务对应哪棵树、父本是谁）→ `versions/db/<版本>/productive_trees.json`。**产出里一个中文都没有**；只在该版基线缺失时跑 |
| `gen_format_snapshot.py` | 上游英文的格式快照，供 `check.py` 离线核占位符与颜色码 |

**语言文件够不着的那些汉化**（本包的主要工作量都在这里）

| 脚本 | 作用 |
|---|---|
| `gen_vaultpatcher.py` | 产出某版的 VaultPatcher 模块——写死在字节码常量池里的界面文本 |
| `gen_books.py` · `books.py` · `extract_books.py` | 导览书：把 `src/books/` 的映射套到**模组 jar 里那份书**上；`extract_` 是反解回映射 |
| `gen_literal_books.py` | 正文直接写死在 JSON 里的那类书 |
| `gen_quest_banners.py` | 任务书章节横幅上的艺术字（烤进 PNG）|
| `gen_menu_buttons.py` | 主菜单按钮图上的中文 |
| `gen_mod_textures.py` | 模组把英文**画进贴图**的那几张，擦掉英文重写中文 |
| `gen_quest_lang_patches.py` | 把本包的任务书覆盖打进 ATM 自己那份章节文件，按**原文件名**出货 |
| `gen_productive_trees_quest_lang.py` | 任务书里「甲 + 乙」那种育种公式：拿 `versions/db/<版本>/productive_trees.json` 套上树名。名字必须与 JEI 逐字一致，手写必漂 |
| `gen_quest_space_fix.py` | 去掉中文里从英文原文带过来的半角空格 |
| `gen_rootsclassic_wrap.py` | 根源经典的教程书按行宽预切、在断点插 ASCII 空格（那本书自己不折中文）|
| `gen_occultism_flame.py` | 自动化之火 tooltip 上那行橙色的仪式 ID 换成中文仪式名 |

**运行时才拼出名字的**

| 脚本 | 作用 |
|---|---|
| `gen_pb_hanhua.py` | 资源蜜蜂：以 lang 实体键为单一真源，产出双端脚本 |
| `gen_trophy_names.py` | Jonn's Trophies 奖杯名（四种烘焙形态）|
| `gen_wood_names.py` | 精致存储木桶 / 箱子的木头名 |
| `scan_keybinds.py` | 扫出全部按键的注册名与分类标题，喂给规则 |

**跟着目标版本现填**

| 脚本 | 作用 |
|---|---|
| `gen_upstream_patches.py` | 把 `src/upstream/` 的映射套到**目标版本的官方文件**上 |
| `gen_vanilla_assets.py` | 字体 provider 列表与 `pack.mcmeta` 跟着该版原版走 |
| `gen_hanhua_update_check.py` | 给游戏内的汉化更新检查器填补丁版本号 |

`gen_config_ui.py` 与 `gen_blockui_patch.py` **不在任何入口里**，原因见
[走过的弯路](#走过的弯路已废弃的做法与留在仓库里的脚本)。

### 一条判据：能算出来的，一律不写进仓库

**这个值换个整合包版本还对吗？能从官方文件 / 字节码 / manifest 算出来吗？**
两条任一为真，就写生成器，不写文件；而且算不出来要**报错退出**，不许回退成默认值。

手写死的版本相关字段，在多版本发布下必然「三个包里两个是错的」，而且**不报错**。
已知会出错的做法：

| 做法 | 后果 | 应当怎么做 |
|---|---|---|
| `kubejs/*.js`、`config/*.json` 改几个字符串后整份提交 | ATM 升级后，发出去的是「旧上游 + 我们的改动」，上游的修复被整份覆盖。7.1→7.2 之间 ATM 改过 `CustomAdditions.js` 里冰与火的类名，把 7.2 的副本发给 7.1 用户会直接 `ClassNotFound` | `src/upstream/` 存「找这几行 → 换成这几行」，对**目标版本的官方文件**套用，找不到原文就退出 |
| **写了生成器，又把它的输出提交进 `src/`** | 等于把 `.o` 签进源码树：入库那份迟早被人手改，然后与生成器悄悄分叉，而两边都还「看着对」。PR #17 与它的 review 先后踩了同一个坑——本节这条判据当时就写在这里，两个人都没打开过 | 产物只写出货树，路径钉进 `assemble.py` 的 `FORBIDDEN_IN_SRC`；要删已入库的，走 `src/protected.json` 的 `released` 并写明谁批的、为什么 |
| 每次构建都去读 mod jar 重算一遍**该版不会变的**东西 | 白下几十 MB，还把构建绑死在网络与 CurseForge 上；更糟的是没人会为了省事去补闸，于是干脆不查 | 当成该版**基线**：版本入库时扫一次进 `versions/db/<版本>/`，CI 扫完上传 artifact 并**红着等人提交**（照 `build.yml` 里 `NEW_VERSION` 那套）。构建期只读基线 |
| 导览书整份副本 | 模组更新导览书时，旧副本把新内容整份覆盖，玩家看不到、也不报错（PneumaticCraft 的「切换维度」整页曾因此不显示）| `src/books/` 只存「位置 + 原文 + 译文」，构建时拿 jar 里那份重新套 |
| VaultPatcher 模块头部写死带版本号的 jar 名 | 以 7.2 那份比对，7.1 只有 116/152 对得上，7.0 只有 83/152 | 按 `versions/db/<版本>/` 现填 |
| 安装器界面写死「ATM10 7.2」 | 7.0 / 7.1 的包印着别的版本号 | `@@MCVER@@` 占位，打包时填 |
| `pack.mcmeta` 写死 `pack_format: 34`、字体抄一份原版 provider 列表 | 换 MC 版本资源包被判不兼容；原版加 provider 会被我们吞掉 | 取原版客户端 `version.json` 与 `font/*.json` |

### 改上游自带的文件

```bash
python3 scripts/gen_upstream_patches.py build/packsrc/7.2 build/v/7.2 7.2  # 摊出官方文件+现有改动
$EDITOR build/v/7.2/kubejs/startup_scripts/CustomAdditions.js          # 在出货树里改
python3 scripts/extract_upstream_patch.py \
    build/packsrc/7.2/kubejs/startup_scripts/CustomAdditions.js \
    build/v/7.2/kubejs/startup_scripts/CustomAdditions.js \
    kubejs/startup_scripts/CustomAdditions.js \
    > src/upstream/kubejs/startup_scripts/CustomAdditions.js.json      # 反解回映射
```

映射对**每个**出货版本都要能套上。上游只在某一版改了那段原文时，别去动映射
（改了老版本就一起丢），在 `versions/<那一版>/unpatchable.json` 里**逐条登记**并写明
上游改成了什么样。登记两头都会红：登记了但原文其实还在 → 红（该撤登记）；
没登记又找不到原文 → 红。

登记只表示「这一版不改」。那段原文被上游**改成了另一副样子、我们仍然要译**的，
再在 `versions/<那一版>/upstream/` 下放一份同格式的该版专属映射：构建时先套通用的
（可带登记跳过），再在同一份文本上套该版的。它同样找不到原文就退出；
改的文件在 `src/upstream/` 下没有对应映射也退出。反例见 `test_gates.py` 的第九组。

### 改导览书译文

```bash
ATM_PACK_ROOT=<整合包目录> ./scripts/generate_all.sh    # 先把书生成到 build/common
$EDITOR build/common/resourcepacks/ATM10汉化包/assets/<模组>/patchouli_books/…/x.json
python3 scripts/extract_books.py <整合包目录>/mods       # 从**构建树**反解回 src/books/
```

`gen_books.py` 会告诉你哪些位置套不上（上游改了那一段），以及哪些散文页的英文原稿变了。
命中率跌破 90% 直接构建失败——不会让「悄悄少翻一半」的包发出去。

### 单一真源

- **资源蜜蜂译名** = `src/pack/assets/productivebees/lang/zh_cn.json` 的实体键。
  改蜂名只改这里，然后重跑 `generate_all.sh`。双端 kubejs 脚本是产物，
  **不在仓库里，也不许手改**。
- 任务书补丁放 `src/config/ftbquests/quests/lang/zh_cn/chapters/*.snbt`
  （分章 delta，langsplitter 启动时按文件名字母序合并，文件名必须 `zz_hanhua_` 打头）。
- 同一数据出现在多个表面（tooltip / JEI / 快捷栏 / 名牌 / Jade / GUI）时，
  修复必须**一次修齐所有表面**并逐面自测——不接受打地鼠式补丁。
- 译名统一：同一事物在任务书、罗盘、物品名中的叫法必须一致
  （例：iceandfire 的 graveyard 统一为「墓园」）。
- **物品名是单一真源**：任务书 / 图鉴 / 界面里提到某件东西，用的必须是玩家在 JEI 里
  搜得到的那个名字。判据是机械的（英文原文出现某物品名 → 中文必须出现它的中文名），
  已经做成闸。注意有些名字是**运行时拼出来的**、lang 里没有独立的键
  （资源蜜蜂的蜜脾块 = 本地化蜂名去掉 `" Bee"` 再套模板），扫静态键表扫不到它们。

## 译文规矩

### 名字从哪里来

优先级自高而低，**上一级有答案就不再往下看**：

1. **玩家在游戏里看到的那个名字**——模组自带 lang、创造模式物品栏、JEI 搜索结果。
   注意 ATM 会用 kubejs 覆盖物品名（`kubejs/assets/*/lang/zh_cn.json`），
   **它压过模组 jar，也压过本资源包**，物品真名以它为准。
2. **本包已经发过的译名**。改一个已发布的译名等于让老玩家的搜索习惯失效，
   要改就得连同任务书、图鉴、罗盘一次改齐。
3. **社区通用译法**（CFPA、中文百科）。
4. 以上都查不到——**保持英文**。自己编一个译名，玩家在 JEI 里反而搜不到，
   比不译更糟。`src/keep_english.json` 记着这类词及其理由。

### 一致性高于文采

同一事物在物品名、任务书、图鉴、罗盘、成就里必须是同一个写法。
两个都不难听的译法之间，选**已经用在物品名上的那个**。

品牌名不做病态保留：玩家已经习惯的译名照用（ATM、振金、难得素、挖矿维度、彼岸），
不要因为「原文是专有名词」就整串留英文——除非它落进上面的第 4 条。

### 拿不准就放弃

推断式翻译是本仓库明确否掉的做法。典型案例：第三方建筑包的 3375 个蓝图名里，
只有 54 个能对上官方译名，其余是 `argo_mid_b` 这类段落代号，不打开蓝图本体判断不出指什么。
结论是**整层保持原文**——半译半英比全英更破坏一致性，猜出来的错译比漏翻严重得多。

### 玩梗要落到中文的梗上

英文原文玩梗的地方，中文也要有对应的梗，意思可以略微漂移；
纯功能描述（配方、数值、操作步骤）**不玩梗**，照直说。

### 事故分级

| 级别 | 什么算 | 处理 |
|---|---|---|
| P0 | 崩溃、卡死、掉帧；**译文把事情说错了**（配方、维度、机制）| 立刻修，并回头查同一批译文里还有没有同类 |
| P0 | 照译文去 JEI 搜不到东西 | 同上；这是「物品名单一真源」那道闸存在的理由 |
| issue | 漏翻、英文残留 | 排队修，不插队 |
| 不做 | 纯观感（排版更整齐、方向更顺眼）| 为观感在生成器里加规则，以后每次上游改动都要重验一遍，代价不成比例 |

## 本地开发

```bash
./scripts/fetch_fonts.sh                                # 取字体（全 OFL，不入库）
ATM_PACK_ROOT=<整合包目录> ./scripts/generate_all.sh    # 摊 + 跑全部生成器 → build/common
python3 scripts/check.py build/v/7.2                    # CI 同款校验（全部硬检查）
python3 scripts/test_installer.py                       # 安装器端到端测试
./scripts/build_dist.sh r18                             # 出全部声明过的整合包版本
./scripts/build_dist.sh r18 7.3                         # 只出 7.3
```

`build_dist.sh` 会自动为每个目标版本取一份官方 `overrides`，在 `build/v/<版本>/` 合成
该版完整出货树，逐版跑 `check.py`，最后 `verify_dist.py` 拆开每个 zip 数内容——
一个没汉化的包发不出去。

### 机械校验清单

| 脚本 | 查什么 |
|---|---|
| `check.py` | 规则解释器；规则在 `src/rules/*.json`。加同类规则只改 JSON，不动脚本 |
| `toolchain.py` | 这次构建是不是标准工具链——不是就明说产物哈希不作数，绝不假装能比 |
| `scan_keybinds.py` | 扫出全部按键分类与注册名，喂给 `vp-keybind-registration-names` 规则 |
| `gen_upstream_patches.py` | 整合包自带文件被改动过没有——原文找不到就构建失败；只有 `versions/<版本>/unpatchable.json` 里逐条登记过的能过，而登记过期（原文又回来了）同样构建失败 |
| `gen_books.py` | 导览书译文能否落到上游那份 JSON 上——命中率跌破 90% 就构建失败 |
| `gen_vaultpatcher.py` | 模块头部写的 jar 名是否是**该版**真实存在的那个 |
| `gen_vanilla_assets.py` | 原版字体 provider 列表与 `pack_format` 跟不跟得上原版 |
| `check_vaultpatcher_strings.py` | 硬编码文本的 key 是否还在目标模组的字节码里（失配是**静默**的） |
| `check_en_drift.py` | 英文底本变了而译文没跟着变——上游改文案必然被发现 |
| `verify_dist.py` | 打好的 zip 里每一类内容够不够量——空壳包发不出去；标准工具链下还比内容指纹 |
| `build_version_db.py --verify` | 一个 mods 目录是不是**逐字节**就是那一版官方的那批 jar |

`scripts/compliance/` 下是**闸**（gate），跟生成器分开放。除上表外还有：

| 闸 | 查什么 |
|---|---|
| `protect.py` | 保护清单：`src/` 的文件只许加不许删 |
| `check_module_hashes.py` | VaultPatcher 模块被改动过没有——改了就得跑 `gen_module_hashes.py` 重钉 |
| `check_bee_names_in_quests.py` | 任务书提到某只蜜蜂时用的是不是 JEI 里那个名字；蜜脾／蜜脾块／刷怪蛋的名字是拿蜂名现拼的，一并判 |
| `check_item_names_in_quests.py` | 同一条判据推广到别的模组（mob_grinding_utils / occultism / relics）；另按任务键绑定工业先锋无限工具档位与实际 tooltip 译名 |
| `check_jetpack_tiers.py` | Iron Jetpacks 的等级名不在 lang 里而在整合包 config 里，缺了会静默回退英文 |
| `check_oracle_index_paths.py` | 神谕目录的书有两套目录约定，放错那条路径的译文永远不会被读、且不报错 |
| `check_kubejs_classfilter.py` | 脚本里 loadClass 了被 KubeJS 类过滤表拒掉的类——运行时才炸，加载阶段全绿 |
| `check_dynamic_substrings.py` | dynamic 模块的 `@` 子串键互不为子串 |
| `check_quest_formatting.py` / `check_gui_maps.py` / `check_injected_lang.py` / `check_minecolonies_paths.py` / `check_name_divergence.py` | 各自那一类的硬检查 |

**加闸就得同时加反例**：`test_gates.py` 里每一条都复刻一次真实事故，验它**真的会红**，
并且验「前提取不到时也红」（fail-closed）。CI 跑 `test_gates.py` 和 `test_protect.py`，
少一条反例过不去。写闸时最常见的错是**静默漏判**——扫不到就当没问题，那是假闸。
报数之前先拿已知真值验一遍扫描器；数不准就说数不准。

### CI

- **ci.yml**：保护闸自检 → 保护清单 → 模块哈希 → **闸的反例测试** → 摊出货树 →
  逐版本上游漂移检测 + 汉化校验 + 任务书/颜色码检查 → 安装脚本语法检查。
  每个 PR / push 必跑（不下 jar，快）。`fetch-depth: 0` 是硬要求：浅克隆下
  「清单不许变短」那道闸取不到基准，会变成静默跳过
- **build.yml**：完整构建全部版本，下整合包与 480 个 mod jar。
  跑在 `src/toolchain.lock.json` 里**按 digest 钉死**的容器里，Pillow 按
  `requirements.lock` 的哈希装——产物 PNG 的字节由 Pillow 自带的 freetype/zlib 决定，
  工具链不进依赖图，产物哈希就没有意义
- **installer-test.yml**：`installer/` 一动就在 macOS / Windows / Linux 三系统跑端到端
- **release.yml**：推 tag 自动构建并发布全部整合包版本的包。
  tag 形态：新式 `vR12` / `vR12-beta1`（补丁版本号与整合包版本解耦，`r` 大小写都认），
  旧式 `v7.2-release11` 继续认。Release 说明按**整串精确比对**（大小写不敏感）取
  `CHANGELOG.md` 的 `## <版本>` 段——tag `vR12` 对应 `## R12`；取不到就回落到文件里
  第一个 `## ` 段（当前在写的那一段），**不会**回落到 `## 7.2`，那是冻结的历史段。
  发版前记得写 CHANGELOG。
  发布前逐个点名检查「每个声明过的版本都有客户端 + 服务端两个包」，缺一个就不发。

## 走过的弯路：已废弃的做法与留在仓库里的脚本

下列做法都实际实施过，其中几条已经发布出去过。记录在此，是为了不再走第二遍。

### blockui 的按钮对齐：一次彻底错误的归因

`scripts/gen_blockui_patch.py` **不被任何入口调用**，也不参与构建，但文件还在。

当时的结论是：blockui 1.0.211 完全无视 XML 里的 `textalign`，界面文字只能贴左，
XML 层无解，只能改字节码。于是给 `com/ldtteam/blockui/controls/Button` 的构造器注入 7 字节
把默认对齐改成居中，并按 sha256 把 blockui 的 jar 钉死（版本一变就构建失败）；
此前手算的 121 条 `textoffset` 也随之撤掉。

**这个归因是错的，根因在本包自身。** blockui 的 `Alignment` 不做枚举比较，
而是拿 `tag.contains("horizontal")`、`contains("right")` 这样的**字符串判定**当行为开关。
本包把 `top horizontal` 这类**标志串**当成界面文字译成了中文，`contains` 于是全部落空，
整个 MineColonies / 建筑棒的对齐随之失效——文字一律贴左、标题压出装饰之外。
移除那 9 条译文之后，上游原本的对齐设计整体恢复，字节码补丁失去存在的意义。

现在的状态：`src/config/vaultpatcher_asm/config.json` 的 `class_patch` 为 `false`；
`vp-class-patch-off` 与 `vp-no-stray-class-patch` 两条规则禁止随包分发任何字节码补丁；
`vp-blockui-alignment-tags` 专门盯住那 9 条标志串不许再被译；
`blockui_legacy_labels.json` 是 src-only 模块，只留档不出货。

脚本没删，因为它的文件头记着当时的实测数据与注入点。
**下次再出现「这个界面只有改字节码才有救」的判断，先读它，再回头检查是不是自己译坏了什么。**
判据是通用的：**上游功能在装了本包之后才坏掉，第一嫌疑人永远是本包，不是上游。**

### 模组配置界面的 744 条标签：译文早就有，代价付不起

`scripts/gen_config_ui.py` 同样不在入口里。它能把「模组配置」列表里那些配置页的标签
全部译出来——那些标签没有翻译键，是把字段名按驼峰拆开现拼的，唯一的路子是
VaultPatcher 的 `dynamic` 替换。

而 `dynamic` 是**全局**开销：替换表越大，游戏内每一次文本绘制都随之变慢。这批 744 条
实测把单次替换成本抬高数倍，界面文字一多就掉帧——`vr14` 的全场景掉帧就是这么来的。

译文已生成并保留在 `src/` 中，等待一个不必付全局代价的实现方式。
**判据：只在某个界面出现的字，不值得让全局文字渲染变慢。** 同类被否掉的还有
Observable 性能浮层上那两行计时——它们没有翻译键，只能依赖 ` seconds` 这类随处可见的子串拼凑，
为一个需按快捷键才打开的调试浮层付出全局帧率代价，不成立。

### 服务端注入语言表：会把 JEI 和配方劈成两半

早期在服务端装过语言注入 mod。结果是服务端**现算**的文本变成中文，而 JEI 与配方
（客户端拿英文数据现算）不变，两侧名称不一致，玩家依服务器中的名称在 JEI 内检索不到。

现在服务端只做一件事：**按 NBT 里的 ID 精确改写纯显示字段**，别的一概不碰。
服务端包内容极少，原因即在于此（见 `SERVER.md`）。

### 「这个模组不在 mods/ 里」不是删译文的理由

曾经按「扫三版 jar 的存在状态」裁掉 238 个命名空间，判据看似严密，结果误删 104 条——
英文底本看不见 jar-in-jar，被内嵌进别的 jar 的模组在扫描里整个消失。
`r12` 的事故正由此而来：罗盘、成就、JEI 读的是**表**，表里少一个命名空间，对应界面直接空白。

现在的规矩：**发版前拿上一版的产物逐命名空间 diff**，少了哪个都要能说清为什么少。
删除类改动一律先出具证据清单，不在其他流程中顺带执行。

### 任务书 delta 靠合并顺序生效：结果不确定

任务书的分章 delta 由 `ftbquestslangsplitter` 合并，而它合并同目录下的 `*.snbt` 时
**不排序**（`Files.list(...).forEach(...)`，一个 comparator 都没有）。`Files.list` 不保证顺序：
NTFS / APFS 恰好按名字返回，**ext4 返回哈希序**。同一个键若同时躺在两份文件里，
谁生效在 Linux 服务器上是随机的。

现在服务端包**整份替换**任务书语言文件，一个键只由一份文件持有，顺序彻底不参与决策；
旧版本发过的 delta 文件名照原名发一个内容为 `{}` 的空壳盖住，全程不删任何文件。

## PR 约定

- 一个 PR 只做一件事；用户可见改动写进 `CHANGELOG.md` **最上面那一段**
  （段名就是下次要发的补丁版本号，如 `## R18`；`## 7.2` 及以下是冻结的历史，别动）
- 版本号格式：`R<序号>`，与整合包版本解耦（一份 `R18` 对应 versions/ 下声明过的每个整合包版本各一个包）。
  tag 写 `vR18` / `vR18-beta1`。`7.2-release1` 那种旧式仍能识别，但新版本别再用了。
- **CHANGELOG 是写给玩家的**：一句结论 + 「哪里 / 之前 / 现在」表格 + 受影响版本 +
  代价（要不要重装、服主要不要动）。机制、根因、扫描口径那些写进 commit 正文和代码注释，
  不要写进更新日志。发版那一节末尾按惯例写**致谢**（提反馈的人）。
- commit 说明写清"为什么"，尤其是译名决策（附投票 / 出处更好）。
  译名的真源是**游戏里显示的那个名字**（模组自带 lang / 创造栏 / JEI），不是百科也不是别家汉化；
  查不到中文名的模组名宁可留英文，自己编一个玩家在游戏里反而搜不到
