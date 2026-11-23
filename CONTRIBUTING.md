# 贡献指南

感谢你愿意让这份汉化更好。下面几条每一条都对应一次真实事故。
CI 能拦住其中大部分，但请先读完再动手。

## 不能做的事

1. **不翻译枚举协议值。**
   McJtyLib 系（RFTools 等）GUI 里的模式选项（`Ignored` / `Off` / `On` /
   `Copy` / `Move` / `Swap`…）是存储与网络协议值，翻译会导致
   `IllegalStateException` 崩溃。资源包 `.gui` 文件里 `choice('...')`
   的参数同样必须保持英文。`scripts/check.py` 会检查。
2. **不改写玩家自定义名。**
   命名牌、铁砧起的名字不允许被改写或翻译。资源蜜蜂的迁移与显示
   都由「系统生成名封闭集合」（PB_SYS）判断，不要绕过它。
3. **不往服务端数据层注入中文。**
   服务器侧的语言表与配方数据必须保持上游英文。服务端算出的文本是中文时，
   JEI 与配方（客户端按英文数据算）仍是英文，玩家查不到配方。
   因此不在服务端注入语言表。
   `mysticalcustomization/`（作物名）是纯客户端配置，不能放进服务端包，
   否则所有玩家进服都会刷 `error creating crop with id null`。
4. **不做贪婪字符串替换。**
   显示层替换必须整词、整段精确匹配：按词边界、长名优先，用
   hasOwnProperty 防止原型链穿透。半截替换（`Ter-蜜蜂-Nator`）比不翻译更糟。
   同一个词在不同上下文里可能是两回事：`星辉`是 Starlight（星辉水晶、符文星辉祭坛），
   也被误用于 Starry Bee。`遗迹`是废墟，Relics 模组说的是随身`遗物`。
   `冰与火`在沉浸工程里是热逆转附魔的风味文字，与那个模组无关。全局替换会把它们一起改坏。
5. **不翻译下面几类字符串，它们译了会崩溃或不生效。**
   - 建筑棒（structurize）以 `/` 开头的路径键是 Map 的键，译了会 NPE 闪退。
   - blockui 的 `top` / `horizontal` 这类对齐标志是字符串枚举，译了会让整个
     MineColonies / 建筑棒界面错位。
   - 物品 tooltip 里不能有 `\n`，会被画成 LF 方框。GUI 提示和聊天才支持换行。
     物品说明太长只能改措辞压短。
   - CC: Tweaked 的终端字形表只有 256 格，没有汉字，`help` 一类整体不译。
6. **不删除 `src/` 下的文件。**
   `src/` 有一份保护清单（`scripts/compliance/protect.py`），文件只许加不许删，删了 CI 会失败。
   新加文件要先 `git add`，再运行 `protect.py --update` 登记。它靠 `git ls-files` 列文件，
   顺序反了会登记 0 个。CI 失败通常说明删错了文件，不要去改检查。

## 仓库结构：只有源，没有出货树

仓库里没有出货用的目录树。`kubejs/`、`config/`、`resourcepacks/`、`mods/`
这些整合包目录都在构建时生成，放在 `build/` 下，不入库。
仓库里只有 `src/`（手写的源文件与改动映射）和 `scripts/`（生成器）。

```
src/pack/                       资源包内容（译文。lang 按命名空间索引，各版本通用）
src/config/                     本包独有的 config（任务书 delta、VaultPatcher 主配置…）
src/kubejs/                     本包独有的 KubeJS 脚本
src/upstream/<路径>.json        整合包自带文件的行级改写映射
src/books/<路径>.json           导览书的「位置 + 原文 + 译文」映射
src/vaultpatcher/modules/       硬编码文本模块（只存译文与目标类）。内容哈希记在 src/module_hashes.json
src/keep_english.json           刻意保留英文的词及其理由（MekaSuit 之类）
src/protected.json              保护清单：src/ 下不许消失的文件
src/mods.lock.json              随包分发的第三方 jar：项目 / 版本 / 地址 / sha256
src/rules/*.json                发版校验规则（check.py 是它们的解释器）
src/toolchain.lock.json         构建工具链：容器 digest / Pillow / 字体哈希
requirements.lock               Pillow 的全平台 wheel 哈希（安装时必须加 --require-hashes）
versions/<版本>/                手写的版本专属层（任务书覆盖、默认资源包顺序）
versions/<版本>/overrides.sha256 该版官方 overrides 的整棵树指纹（CI 缓存键与门控）
versions/<版本>/unobtainable.json 该版 manifest 里已从 CurseForge 消失的 jar（必须逐个登记）
versions/<版本>/unpatchable.json 该版官方文件里已经不存在的上游改动（必须逐条登记并写理由）
versions/<版本>/upstream/       该版专属的上游映射（上游只在这一版把那段改成了别的样子）
versions/db/<版本>/             该版的核对数据库与英文原文
versions/db/<版本>/jars.json    该版每个 jar 的 sha256 与不可变的 CurseForge fileID
versions/db/<版本>/keybinds.json 该版全部按键分类与注册名（含拼名字用的字符串片段）
scripts/                        生成器
scripts/compliance/             检查脚本与它们的反例测试

build/common/                   组装好的出货树（各版本通用的部分）
build/v/<版本>/                 该版的完整出货树，check.py 查的就是它
build/packsrc/<版本>/           该版官方 overrides（由 fetch_pack.py --no-jars 下载）
```

动手前先组装一次：

```bash
python3 scripts/assemble.py                             # 只组装源文件（不需要整合包）
ATM_PACK_ROOT=<整合包目录> ./scripts/generate_all.sh    # 组装并运行全部生成器
```

### 生成器一览

`scripts/` 下是生成器与下载脚本，`scripts/compliance/` 下是检查脚本。入口只有两个：
`generate_all.sh`（组装源文件，再依次运行全部生成器）与 `build_dist.sh`（逐版合成、校验、打 zip）。

**组装与出货**

| 脚本 | 作用 |
|---|---|
| `assemble.py` | 把 `src/` 组装成出货树（`build/common/`）|
| `paths.py` | 全仓库统一的目录约定，所有脚本从这里取路径 |
| `mkzip.py` | 打 zip，并让中文文件名带 UTF-8 标志位 |
| `build_in_container.sh` | 在按 digest 钉死的容器里构建。只有这里构建出的产物，哈希才能拿来比对 |
| `toolchain.py` | 核对本次构建的工具链，判断产物能不能按字节比对 |

**下载上游素材**

| 脚本 | 作用 |
|---|---|
| `fetch_pack.py` | 把某个版本的 ATM10 下载成可当 `ATM_PACK_ROOT` 用的目录 |
| `fetch_one_jar.py` | 只需要某一个 mod 的 jar 时用：按 `versions/db/<版本>/jars.json` 的 fileID 下载一个并核对 sha256。缓存按内容寻址，各版本共用 |
| `fetch_mods.py` | 按 `src/mods.lock.json` 下载随包分发的第三方 jar，逐个核对 sha256 |
| `fetch_fonts.sh` | 下载生成 PNG 用的字体（都是 OFL，不入库）|
| `vanilla.py` | 取原版 Minecraft 的语言文件与字体资源（被 5 个生成器 import，不单独运行）|
| `build_version_db.py` | 为某版建核对数据库：每个 jar 的 sha256 与不可变 fileID、字节码常量、按键表 |
| `build_en_baseline.py` | 记下每条译文翻译时对着的英文原文 |
| `scan_productive_trees.py` | 扫描该版资源树的育种结构（哪个任务对应哪棵树、父本是谁），写进 `versions/db/<版本>/productive_trees.json`。产出里没有中文。只在该版基线缺失时运行 |
| `gen_format_snapshot.py` | 上游英文的格式快照，供 `check.py` 离线核对占位符与颜色码 |

**语言文件以外的汉化**（本包的主要工作量）

| 脚本 | 作用 |
|---|---|
| `gen_vaultpatcher.py` | 生成某版的 VaultPatcher 模块，处理写死在字节码常量池里的界面文本 |
| `gen_books.py` · `books.py` · `extract_books.py` | 导览书：把 `src/books/` 的映射套到模组 jar 里的书上。`extract_books.py` 反向提取成映射 |
| `gen_literal_books.py` | 正文直接写在 JSON 里的那类书 |
| `gen_quest_banners.py` | 任务书章节横幅上的艺术字（画进 PNG）|
| `gen_menu_buttons.py` | 主菜单按钮图上的中文 |
| `gen_mod_textures.py` | 模组把英文画进贴图的那几张：擦掉英文，写上中文 |
| `gen_quest_lang_patches.py` | 把本包的任务书覆盖打进 ATM 自己的章节文件，按原文件名出货 |
| `gen_productive_trees_quest_lang.py` | 任务书里「甲 + 乙」形式的育种公式：用 `versions/db/<版本>/productive_trees.json` 填入树名。名字必须与 JEI 逐字一致，手写一定会出错 |
| `gen_quest_space_fix.py` | 去掉中文里从英文原文带过来的半角空格 |
| `gen_rootsclassic_wrap.py` | 根源经典的教程书不给中文断行：按行宽预先切分，在断点插 ASCII 空格 |
| `gen_occultism_flame.py` | 自动化之火 tooltip 上那行橙色的仪式 ID 换成中文仪式名 |

**运行时才拼出名字的**

| 脚本 | 作用 |
|---|---|
| `gen_pb_hanhua.py` | 资源蜜蜂：以 lang 实体键为唯一来源，生成客户端与服务端脚本 |
| `gen_trophy_names.py` | Jonn's Trophies 奖杯名（四种烘焙形态）|
| `gen_wood_names.py` | 精致存储木桶、箱子的木头名 |
| `scan_keybinds.py` | 扫描全部按键的注册名与分类标题，供规则使用 |

**按目标版本填入的**

| 脚本 | 作用 |
|---|---|
| `gen_upstream_patches.py` | 把 `src/upstream/` 的映射套到目标版本的官方文件上 |
| `gen_vanilla_assets.py` | 字体 provider 列表与 `pack.mcmeta` 跟随该版原版 |
| `gen_hanhua_update_check.py` | 给游戏内的汉化更新检查器填补丁版本号 |

`gen_config_ui.py` 与 `gen_blockui_patch.py` 不在任何入口里，原因见[已废弃的做法](#已废弃的做法)。

### 能算出来的值不写进仓库

**这个值换个整合包版本还对吗？能从官方文件、字节码或 manifest 算出来吗？**
任一个答案是「是」，就写生成器，不写文件。算不出来时报错退出，不回退成默认值。

版本相关的字段写死后，多版本发布时会出现「三个包里两个是错的」，而且不报错。
已知会出错的做法：

| 做法 | 后果 | 应当怎么做 |
|---|---|---|
| `kubejs/*.js`、`config/*.json` 改几个字符串后整份提交 | ATM 升级后，发出去的是「旧上游 + 本包的改动」，上游的修复被整份覆盖。例如 7.1→7.2 之间 ATM 改了 `CustomAdditions.js` 里冰与火的类名，把 7.2 的副本发给 7.1 会直接 `ClassNotFound` | `src/upstream/` 存「找这几行，换成这几行」，套到目标版本的官方文件上，找不到原文就退出 |
| 写了生成器，又把它的输出提交进 `src/` | 入库的那份迟早被手改，然后与生成器不一致，而两边看着都对 | 产物只写出货树，路径登记进 `assemble.py` 的 `FORBIDDEN_IN_SRC`。要删已入库的，走 `src/protected.json` 的 `released`，写明谁批准、为什么 |
| 每次构建都读 mod jar，重算该版不会变的东西 | 多下几十 MB，构建还依赖网络与 CurseForge。而且为了省事，往往就不再加检查 | 当成该版基线：版本入库时扫描一次，存进 `versions/db/<版本>/`。CI 扫描后上传 artifact 并失败，等人提交（照 `build.yml` 里 `NEW_VERSION` 的做法）。构建时只读基线 |
| 导览书整份副本 | 模组更新导览书后，旧副本把新内容整份覆盖，玩家看不到，也不报错。PneumaticCraft 的「切换维度」整页就因此不显示过 | `src/books/` 只存「位置 + 原文 + 译文」，构建时套到 jar 里的书上 |
| VaultPatcher 模块头部写死带版本号的 jar 名 | 按 7.2 写的，7.1 只有 116/152 对得上，7.0 只有 83/152 | 按 `versions/db/<版本>/` 填入 |
| 安装器界面写死「ATM10 7.2」 | 7.0 / 7.1 的包印着别的版本号 | 用 `@@MCVER@@` 占位，打包时填入 |
| `pack.mcmeta` 写死 `pack_format: 34`、字体照抄一份原版 provider 列表 | 换 MC 版本后资源包被判为不兼容。原版新加的 provider 会被覆盖掉 | 读原版客户端的 `version.json` 与 `font/*.json` |

### 改上游自带的文件

```bash
python3 scripts/gen_upstream_patches.py build/packsrc/7.2 build/v/7.2 7.2  # 生成官方文件加现有改动
$EDITOR build/v/7.2/kubejs/startup_scripts/CustomAdditions.js          # 在出货树里改
python3 scripts/extract_upstream_patch.py \
    build/packsrc/7.2/kubejs/startup_scripts/CustomAdditions.js \
    build/v/7.2/kubejs/startup_scripts/CustomAdditions.js \
    kubejs/startup_scripts/CustomAdditions.js \
    > src/upstream/kubejs/startup_scripts/CustomAdditions.js.json      # 反向提取成映射
```

映射要能套到每个出货版本上。上游只在某一版改了那段原文时，不要改映射
（改了会让老版本套不上），在 `versions/<那一版>/unpatchable.json` 里逐条登记，
写明上游改成了什么样。登记两头都会检查：登记了但原文其实还在，会失败（该撤登记）。
没登记又找不到原文，也会失败。

登记只表示「这一版不改」。如果上游把那段原文改成了别的样子，而本包仍然要译，
就在 `versions/<那一版>/upstream/` 下放一份同格式的该版专属映射。构建时先套通用映射
（登记过的跳过），再在同一份文本上套该版的。找不到原文同样退出。
改动的文件在 `src/upstream/` 下没有对应映射，也会退出。反例见 `test_gates.py` 的第九组。

### 改导览书译文

```bash
ATM_PACK_ROOT=<整合包目录> ./scripts/generate_all.sh    # 先把书生成到 build/common
$EDITOR build/common/resourcepacks/ATM10汉化包/assets/<模组>/patchouli_books/…/x.json
python3 scripts/extract_books.py <整合包目录>/mods       # 从构建树反向提取到 src/books/
```

`gen_books.py` 会列出哪些位置套不上（上游改了那一段），以及哪些散文页的英文原稿变了。
命中率低于 90% 时构建失败。

### 单一真源

- 资源蜜蜂译名以 `src/pack/assets/productivebees/lang/zh_cn.json` 的实体键为准。
  改蜂名只改这里，再重跑 `generate_all.sh`。客户端与服务端的 kubejs 脚本是生成的，
  不在仓库里，不能手改。
- 任务书补丁放在 `src/config/ftbquests/quests/lang/zh_cn/chapters/*.snbt`
  （分章 delta，langsplitter 启动时按文件名字母序合并，文件名必须以 `zz_hanhua_` 开头）。
- 同一数据出现在多个位置（tooltip、JEI、快捷栏、名牌、Jade、GUI）时，
  要一次改齐所有位置，并逐个位置测试。
- 同一事物在任务书、罗盘、物品名里的叫法必须一致
  （例如 iceandfire 的 graveyard 统一为「墓园」）。
- 任务书、图鉴、界面里提到某件东西，用的必须是玩家在 JEI 里搜得到的那个名字。
  判据是机械的：英文原文出现某物品名，中文就必须出现它的中文名，已经有检查脚本。
  有些名字是运行时拼出来的，lang 里没有单独的键
  （资源蜜蜂的蜜脾块 = 本地化蜂名去掉 `" Bee"` 再套模板），扫描静态键表找不到它们。

## 译文规矩

### 名字从哪里来

优先级从高到低，上一级有答案就不往下查：

1. 玩家在游戏里看到的名字：模组自带 lang、创造模式物品栏、JEI 搜索结果。
   ATM 会用 kubejs 覆盖物品名（`kubejs/assets/*/lang/zh_cn.json`），
   它优先于模组 jar 和本资源包，物品名以它为准。
2. 本包已经发布过的译名。改一个已发布的译名，老玩家的搜索习惯就失效了。
   要改就连同任务书、图鉴、罗盘一次改齐。
3. 社区通用译法（CFPA、中文百科）。
4. 以上都查不到，保持英文。自己编的译名玩家在 JEI 里搜不到，
   比不译更糟。`src/keep_english.json` 记录这类词及其理由。

### 一致性优先于文采

同一事物在物品名、任务书、图鉴、罗盘、成就里必须写法相同。
两个译法都可以时，选物品名已经在用的那个。

玩家已经习惯的品牌译名照用（ATM、振金、难得素、挖矿维度、彼岸）。
不要因为原文是专有名词就整串保留英文，除非它属于上面第 4 条。

### 拿不准就不译

不做推断式翻译。例如第三方建筑包的 3375 个蓝图名里，只有 54 个能对上官方译名，
其余是 `argo_mid_b` 这类段落代号，不打开蓝图判断不出指什么。
所以整层保持原文：半译半英比全英更破坏一致性，猜错的译名比漏翻严重得多。

### 玩梗要落到中文的梗上

英文原文玩梗的地方，中文也要用对应的梗，意思可以稍有偏差。
纯功能描述（配方、数值、操作步骤）不玩梗，直接写。

### 问题分级

| 级别 | 什么算 | 处理 |
|---|---|---|
| P0 | 崩溃、卡死、掉帧。译文把事情说错了（配方、维度、机制）| 立刻修，并检查同一批译文里有没有同类问题 |
| P0 | 按译文在 JEI 里搜不到东西 | 同上。物品名检查就是为此加的 |
| issue | 漏翻、英文残留 | 按顺序修 |
| 不做 | 纯观感（排版更整齐、方向更顺眼）| 为观感在生成器里加规则，以后每次上游改动都要重新验证，代价太高 |

## 开发命令

```bash
./scripts/fetch_fonts.sh                                # 下载字体（都是 OFL，不入库）
ATM_PACK_ROOT=<整合包目录> ./scripts/generate_all.sh    # 组装并运行全部生成器，输出到 build/common
python3 scripts/check.py build/v/7.2                    # 与 CI 相同的校验
python3 scripts/test_installer.py                       # 安装器端到端测试
./scripts/build_dist.sh r18                             # 打包全部声明过的整合包版本
./scripts/build_dist.sh r18 7.3                         # 只打包 7.3
```

`build_dist.sh` 为每个目标版本下载一份官方 `overrides`，在 `build/v/<版本>/` 合成
该版完整出货树，逐版运行 `check.py`，最后由 `verify_dist.py` 解开每个 zip 清点内容，
内容数量不够就失败。

### 机械校验清单

| 脚本 | 查什么 |
|---|---|
| `check.py` | 规则解释器，规则在 `src/rules/*.json`。加同类规则只改 JSON，不改脚本 |
| `toolchain.py` | 本次构建是否用标准工具链。不是的话，明确说明产物哈希不能比对 |
| `scan_keybinds.py` | 扫描全部按键分类与注册名，供 `vp-keybind-registration-names` 规则使用 |
| `gen_upstream_patches.py` | 整合包自带文件的改动能否套上，找不到原文就构建失败。只有在 `versions/<版本>/unpatchable.json` 里逐条登记过的才能跳过。登记过期（原文又出现了）同样构建失败 |
| `gen_books.py` | 导览书译文能否套到上游的 JSON 上，命中率低于 90% 就构建失败 |
| `gen_vaultpatcher.py` | 模块头部写的 jar 名是否是该版实际存在的那个 |
| `gen_vanilla_assets.py` | 原版字体 provider 列表与 `pack_format` 是否跟上原版 |
| `check_vaultpatcher_strings.py` | 硬编码文本的 key 是否还在目标模组的字节码里（对不上时游戏不报错） |
| `check_en_drift.py` | 英文原文变了而译文没跟着变时报出来 |
| `verify_dist.py` | 打好的 zip 里每一类内容数量够不够。标准工具链下还比对内容指纹 |
| `build_version_db.py --verify` | 一个 mods 目录是否与那一版官方的 jar 逐字节相同 |

`scripts/compliance/` 下是检查脚本，与生成器分开放。除上表外还有：

| 检查 | 查什么 |
|---|---|
| `protect.py` | 保护清单：`src/` 的文件只许加不许删 |
| `check_module_hashes.py` | VaultPatcher 模块是否被改过。改了要运行 `gen_module_hashes.py` 重新记录哈希 |
| `check_bee_names_in_quests.py` | 任务书提到某只蜜蜂时，用的是不是 JEI 里的名字。蜜脾、蜜脾块、刷怪蛋的名字由蜂名拼出，一起检查 |
| `check_item_names_in_quests.py` | 同一判据用到其他模组（mob_grinding_utils / occultism / relics）。另外按任务键核对工业先锋无限工具的档位与实际 tooltip 译名 |
| `check_jetpack_tiers.py` | Iron Jetpacks 的等级名在整合包 config 里，不在 lang 里，缺了会回退成英文且不报错 |
| `check_oracle_index_paths.py` | 神谕目录的书有两套目录约定，放错路径的译文不会被读取，也不报错 |
| `check_kubejs_classfilter.py` | 脚本里 loadClass 了被 KubeJS 类过滤表拒绝的类。这种错误运行时才报，加载阶段不报 |
| `check_dynamic_substrings.py` | dynamic 模块的 `@` 子串键互不为子串 |
| `check_quest_formatting.py` / `check_gui_maps.py` / `check_injected_lang.py` / `check_minecolonies_paths.py` / `check_name_divergence.py` | 各自那一类的检查 |

加检查就要同时加反例：`test_gates.py` 里每一条都复现一次真实问题，验证检查确实会失败，
也验证前提取不到时会失败（fail-closed）。CI 运行 `test_gates.py` 和 `test_protect.py`，
少一条反例就通不过。扫描不到就当作没问题的检查，等于没有检查。
报数之前先用已知结果验证扫描器，数不准就说数不准。

### CI

- ci.yml：依次运行保护清单检查的反例测试、检查保护清单、模块内容哈希、检查脚本的反例测试、
  从 src/ 组装出货树，再逐版本做上游漂移检测、汉化校验与任务书颜色码检查，最后检查安装脚本语法。
  每个 PR 和 push 都运行（不下载 jar，速度快）。必须 `fetch-depth: 0`：浅克隆下
  「清单不许变短」这条检查取不到基准，会被跳过且不报错。
- build.yml：完整构建全部版本，下载整合包与 480 个 mod jar。
  运行在 `src/toolchain.lock.json` 按 digest 钉死的容器里，Pillow 按
  `requirements.lock` 的哈希安装。产物 PNG 的字节由 Pillow 自带的 freetype/zlib 决定，
  工具链不固定，产物哈希就没有意义。
- installer-test.yml：`installer/` 有改动时，在 macOS / Windows / Linux 三个系统运行端到端测试。
- release.yml：推 tag 时自动构建并发布全部整合包版本的包。
  tag 形式：新式 `vR12` / `vR12-beta1`（补丁版本号与整合包版本无关，`r` 大小写都可以），
  旧式 `v7.2-release11` 仍然识别。Release 说明从 `CHANGELOG.md` 取 `## <版本>` 段，
  标题按整串比对（不区分大小写），tag `vR12` 对应 `## R12`。取不到时取文件里
  第一个 `## ` 段（当前正在写的那一段），不会取 `## 7.2`，那是冻结的历史段。
  发版前先写 CHANGELOG。
  发布前逐个确认每个声明过的版本都有客户端和服务端两个包，缺一个就不发布。

## 已废弃的做法

下面的做法都实际用过，其中几条随版本发布过。记在这里，避免再做一遍。

### blockui 的按钮对齐：归因错误

`scripts/gen_blockui_patch.py` 不被任何入口调用，也不参与构建，文件保留。

当时的判断是：blockui 1.0.211 完全忽略 XML 里的 `textalign`，界面文字只能左对齐，
只能改字节码。于是在 `com/ldtteam/blockui/controls/Button` 的构造器里注入 7 字节，
把默认对齐改成居中，并按 sha256 钉死 blockui 的 jar（版本一变就构建失败）。
手算的 121 条 `textoffset` 也一起撤掉了。

这个归因是错的，原因在本包。blockui 的 `Alignment` 不做枚举比较，
而是用 `tag.contains("horizontal")`、`contains("right")` 这样的字符串判断决定行为。
本包把 `top horizontal` 这类标志串当成界面文字译成了中文，`contains` 全部不成立，
整个 MineColonies / 建筑棒的对齐失效：文字一律左对齐，标题超出装饰框。
去掉那 9 条译文后，上游的对齐恢复，字节码补丁就不需要了。

现在：`src/config/vaultpatcher_asm/config.json` 的 `class_patch` 为 `false`。
`vp-class-patch-off` 与 `vp-no-stray-class-patch` 两条规则禁止随包分发字节码补丁。
`vp-blockui-alignment-tags` 禁止再翻译那 9 条标志串。
`blockui_legacy_labels.json` 是只留在 `src/` 的模块，不出货。

脚本保留，因为文件头记着当时的实测数据与注入点。
**如果再判断「这个界面只有改字节码才能修」，先读这个脚本，再检查是不是本包把什么译坏了。**
上游功能在装了本包之后才坏，先怀疑本包。

### 模组配置界面的 744 条标签：译文已有，性能代价太高

`scripts/gen_config_ui.py` 同样不在入口里。它能翻译「模组配置」列表里那些配置页的标签。
这些标签没有翻译键，是把字段名按驼峰拆开拼出来的，只能用 VaultPatcher 的 `dynamic` 替换。

`dynamic` 是全局开销：替换表越大，游戏里每一次文本绘制都越慢。这 744 条
实测让单次替换的开销增加数倍，界面文字一多就掉帧，`vr14` 的全场景掉帧就是这个原因。

译文已生成并留在 `src/` 里，等有不需要全局开销的实现方式再用。
判据：只在某个界面出现的文字，不值得让全局文字渲染变慢。同样被否掉的还有
Observable 性能浮层上那两行计时：它们没有翻译键，只能靠 ` seconds` 这类到处都有的子串拼凑。
为一个按快捷键才打开的调试浮层付出全局帧率代价，不值得。

### 服务端注入语言表：JEI 与配方会对不上

在服务端装过语言注入 mod。结果服务端算出的文本变成中文，而 JEI 与配方
（客户端按英文数据算）没变，两边名称不一致，玩家用服务器显示的名称在 JEI 里搜不到。

现在服务端只做一件事：按 NBT 里的 ID 精确改写纯显示字段，不改别的。
所以服务端包内容很少（见 `SERVER.md`）。

### 模组不在 mods/ 里，不是删译文的理由

按「扫描三个版本 jar 的存在状态」删过 238 个命名空间，结果误删 104 条。
英文原文扫描看不到 jar-in-jar，被内嵌进别的 jar 的模组在扫描结果里整个消失。
`r12` 的事故就是这样来的：罗盘、成就、JEI 读的是表，表里少一个命名空间，对应界面就是空白。

现在的规矩：发版前和上一版的产物逐命名空间 diff，少了哪个都要说清原因。
删除类改动先给出证据清单，不在其他改动里顺带删。

### 任务书 delta 靠合并顺序生效：结果不确定

任务书的分章 delta 由 `ftbquestslangsplitter` 合并。它合并同目录下的 `*.snbt` 时
不排序（`Files.list(...).forEach(...)`，没有 comparator）。`Files.list` 不保证顺序：
NTFS / APFS 按名字返回，ext4 按哈希序返回。同一个键同时出现在两份文件里时，
在 Linux 服务器上哪份生效是随机的。

现在服务端包整份替换任务书语言文件，一个键只出现在一份文件里，与顺序无关。
旧版本发过的 delta 文件，按原名发一个内容为 `{}` 的空文件覆盖，不删除任何文件。

## PR 约定

- 一个 PR 只做一件事。玩家能看到的改动写进 `CHANGELOG.md` 最上面那一节
  （节名是下次要发的补丁版本号，如 `## R18`。`## 7.2` 及更早的是冻结的历史，不要改）。
- 版本号格式：`R<序号>`，与整合包版本无关（一个 `R18` 为 versions/ 下声明过的每个整合包版本各出一个包）。
  tag 写 `vR18` / `vR18-beta1`。`7.2-release1` 这种旧格式仍能识别，新版本不要再用。
- CHANGELOG 写给玩家：一句结论、「哪里 / 之前 / 现在」表格、受影响版本、要做什么
  （要不要重装、服主要不要处理）。机制、根因、扫描口径写进 commit 正文和代码注释，
  不写进更新日志。发版那一节末尾写致谢（提反馈的人）。
- commit 说明写清为什么，尤其是译名决策（最好附上投票或出处）。
  译名以游戏里显示的名字为准（模组自带 lang / 创造栏 / JEI），不以百科或其他汉化为准。
  查不到中文名的模组名保留英文，自己编的名字玩家在游戏里搜不到。
