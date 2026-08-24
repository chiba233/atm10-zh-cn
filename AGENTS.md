# CLAUDE.md

写给在本仓库里干活的自动化助手。`AGENTS.md` 内容与本文件完全相同，只是换个文件名供不同工具读取。

内容限于**这个代码库的技术事实**：仓库怎么组织、改动怎么落、哪些东西一改就坏。

---

## 仓库结构：只有源，没有出货树

产出是 All the Mods 10 的简体中文资源包与若干配置文件，按整合包版本
（7.0 / 7.1 / 7.2 / 7.3）分别出货。

仓库里**没有任何一棵出货用的目录树**。`kubejs/` `config/` `resourcepacks/` `mods/`
都是产物，构建时现摊、现产、现打补丁，落在 `build/` 下且不入库。

```
src/pack/                    资源包译文（lang 按命名空间索引，跨版本通用）
src/config/                  本包独有的 config（任务书 delta、VaultPatcher 主配置…）
src/upstream/<路径>.json     整合包自带文件的行级改写映射
src/books/<路径>.json        导览书的「位置 + 原文 + 译文」映射
src/protected.json           保护清单：src/ 下不许消失的文件
src/rules/*.json             发版校验规则（scripts/check.py 是它们的解释器）
versions/<版本>/             该版的任务书覆盖等专属层
versions/db/<版本>/jars.json 该版每个 jar 的 sha256 + 不可变的 CurseForge fileID
scripts/compliance/          闸与它们的反例测试

build/v/<版本>/              摊好的该版出货树，check.py 查的就是它
```

动手前先摊一次：

```bash
python3 scripts/assemble.py                             # 只摊源
ATM_PACK_ROOT=<整合包目录> ./scripts/generate_all.sh    # 摊 + 跑全部生成器
```

---

## 译名的真源在哪里

1. **MC百科 mcmod.cn** —— 条目页 `/item/<id>.html`、列表页 `/item/list/<classid>-1.html`。
   收录不全，查不到很正常。
2. **CFPA 汉化项目** `CFPAOrg/Minecraft-Mod-Language-Package`。
3. **mod jar 自带的 `assets/<modid>/lang/zh_cn.json`** —— 兜底。
4. 学名 / 维基 —— 只用来判断是不是认错物种，不作译名。

真源是**按物品一件一件查的**。同一个 mod 里两件不同物品在真源上用了不同构词
不是矛盾——它们本来就是两个东西。现成的例子：神秘农业的 `witherproof_block`
与 `witherproof_glass` 在 mcmod 上都用「防凋灵」，而 `witherproof_bricks`
在 mcmod 上根本没有条目，所以它仍是「防凋零砖块」——同一系三件，两种写法。

真源查不到的（如 `witherproof_bricks`、`soulium_ingot_block`）保持现状，
不要用同族的前缀去推。

**真源会变，条目页才是真源，搜索列表页不是。** mcmod 的搜索索引落后于条目页：
`witherproof_block` 与 `awakened_supremium_ingot_block` 都在 2026-08 改过译名
（分别改成「防凋灵方块」「觉醒精华锭块」），而搜索页当时仍显示旧名。查一件东西
一定要点进 `/item/<id>.html`。译名改了就跟——但要先把这个名字的全部表面
（物品名、导览书、任务书标题与描述）一起找齐。

---

## 译了会崩、或译了也不生效的字符串

- **structurize 以 `/` 开头的路径键**是 Map 的键，译了 NPE 闪退。
- **blockui 的 `top` / `horizontal` 这类对齐标志**是字符串枚举，
  译了会让整个 MineColonies / 建筑棒界面错位。
- **McJtyLib 系（RFTools 等）GUI 的模式选项**（`Ignored` / `Off` / `On` /
  `Copy` / `Move` / `Swap`…）是存储与网络协议值，译了 `IllegalStateException` 崩溃。
  资源包 `.gui` 文件里 `choice('...')` 的参数同理必须保持英文。
- **物品 tooltip 里不能有 `\n`**，会被画成 LF 方框；GUI 提示和聊天才认换行。
  说明太长只能改措辞压短。
- **CC: Tweaked 终端字形表只有 256 格，没有汉字**，`help` 一类整体不译。
- **玩家自定义名**（命名牌 / 铁砧）不允许被改写。
- **服务端数据层不注入中文**：服务端现算的文本会与 JEI / 配方
  （客户端由英文数据现算）分裂，玩家查不到配方。

---

## 改动怎么落

### 定点替换

`json.dumps` 回写会改缩进，`write_text` 会把 CRLF 变成 LF，
全文 `replace` 会连上游原文那一侧一起改掉。

每处替换**断言命中次数**（通常是 1），命中 0 次或多次一律中止。
改完看 `git diff --numstat`，行数对不上就是替换范围错了。

### 子串扫描只能用来定位

同样的字出现在别的词里是常态：「生物静滞室」里有「静滞室」，
「熵变机械臂」里有「机械臂」，「遗忆守卫」里有「守卫」，「能量导管」里有「导管」。
拿这种命中批量替换会把正确的名字一起改坏。每条替换都要先看到它所在的整句。

### 一个名字有多处表面

FTB Quests 里**任务标题与任务描述是两个不同的键**
（`quest.<id>.title` / `quest.<id>.quest_desc`），分别落在上游底本与本仓库的 delta 里。
只覆盖描述、标题留在底本里，界面上就会标题一个名、正文另一个名。

物品名改了，任务书、导览书、成就、结构罗盘里引用它的地方都要跟着查一遍。

---

## 数值要查该版本钉的那份字节

血量、配方、材料数量这类数字不要照抄英文原文——英文写错的情况在本项目里出现过多次。

```bash
python3 scripts/fetch_one_jar.py <版本> <jar 名前缀> <输出目录>
```

`versions/db/<版本>/jars.json` 里每个 jar 钉了 `projectID` / `fileID` / `sha256`，
取回来会核到字节。多个版本钉同一份 jar 时值自然一致；
只有各版本确实不同，才用 `versions/<版本>/quest_overrides.snbt` 分开写。

---

## 闸

`scripts/check.py` 是规则解释器，规则数据在 `src/rules/*.json`；
`scripts/compliance/` 下是各个闸与它们的反例测试。

- 任何检查在**取不到基准时必须红**，不许打印一行提示然后退 0。
  CI 一律 `fetch-depth: 0`——浅克隆下拿不到历史等于闸失效。
  写反例测试时要测「前提取不到会不会红」，不只是「有问题会不会红」。
- `src/protected.json` 记录 `src/` 下不许消失的文件，由
  `scripts/compliance/protect.py` 把关。新加文件要先 `git add` 再跑
  `protect.py --update` 登记（它靠 `git ls-files`，顺序反了会「新收 0 个」）。
  这个闸红了通常意味着删错了文件。
