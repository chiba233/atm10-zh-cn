# AGENTS.md

写给在本仓库里干活的自动化助手。`CLAUDE.md` 只有一行 `@AGENTS.md`，各家工具读到的是同一份内容。

内容限于**这个代码库的技术事实与工作约定**：仓库怎么组织、改动怎么落、公开文本怎么写、哪些东西一改就坏。
动手前先在[任务路由](#任务路由)里找到对应的任务，读列出的文件。

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

## 覆盖率与缺口的口径

`versions/db/<版本>/lang_baseline_local.json` 只收本包已经译过的键，以及每个键翻译时对着的英文原文（见 `scripts/build_en_baseline.py`）。它用来查英文底本有没有变，不是该版的全量 `en_us`。

- 不拿它当分母算覆盖率。分母里只有本包已译的键，算出来必然是 100%。
- 不拿它回答「全包有多少条某类文本」。它只能回答本包译过的键。
- 覆盖率的分母是该版全部模组 jar 的 `en_us`，加上整合包 `kubejs/assets` 里的 `en_us`。

「某版新增且未译」要用两个版本的 jar 求差：

1. 新版 jar 的 `en_us` 键，减去旧版 jar 的 `en_us` 键。
2. 再减去新版模组自带的 `zh_cn`、本包的 `zh_cn`、整合包 `kubejs/assets` 里已有的键。

旧版 jar 用 `fetch_one_jar.py <旧版本> <jar 名前缀> <输出目录>` 取。`jars.json` 钉了每个 jar 的 fileID 与 sha256。整合包已经原地升级、旧 jar 不在了，也照样取得到。

「`en_us` 有这个键、`zh_cn` 没有」本身不是缺口。先减掉上面三个来源，再排除死键与只在开发环境注册的键。死键指被别名替换、游戏里不会显示的键。

扫描结果是 100% 或 0 时，先拿一个已知的正例验证扫描器，再报数。

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

---

## 写作

- 公开文本按 [`simple-chinese`](.agents/skills/simple-chinese/SKILL.md) 写。公开文本指 commit 消息、PR 与 issue 文本、CHANGELOG、README、文档与代码注释。
- 这条不管游戏内的译文。译文按上文「译名的真源在哪里」处理。
- 不改代码、标识符、命令、路径与报错原文。
- 本仓库最常犯的几条：
  - 写了人：谁提的、谁拍板、私下怎么沟通的。只写事和技术依据。
  - 写了本地环境：本地、本机路径、机器名。
  - 写了历史经过：「原先……现在……」。历史在 git 里。
  - 更新日志里写了根因和机制。它们写进 commit 正文和代码注释。
  - 标题写成疑问句。标题写陈述句。
  - 用分号连起两件事。写成两句。

---

## Git 与 PR

### 提交

- 标题用 Conventional Commits 的标准类型：`feat`、`fix`、`docs`、`chore`、`ci`、`refactor`、`test`。scope 可写可不写，例如 `fix(installer): …`。描述用中文，不用 gitmoji。历史上的 `doc:` 提交保持原样。
- 标题一行。关联 issue 时，在末尾写 `(#N)`。
- 一件事一个提交。顺手改的东西单独提交。
- 正文默认不写。只在改动看不出根因、代码注释里又放不下时写，三到五行。译名决策写上真源。
- 自动化助手提交时加 `--no-gpg-sign`。不改仓库或全局的 `commit.gpgsign`。
- 提交前对提交消息跑禁词检查，命令见 `simple-chinese`「自检」。

### 分支与推送

- 分支名：`<类型>/<issue 号>-<简短名>`。没有 issue 时省掉号，例如 `fix/59-pam-stock`、`docs/agent-skills`。
- 拉取用 `git pull --rebase`。
- 推送前先 `git fetch`。不 force push，`main` 的保护规则也禁止 force push。
- agent 配置（`AGENTS.md`、`CLAUDE.md`、`.agents/skills/`）的改动单独提交、单独开 PR。

### PR 与合并

- 开 PR 用 [`create-pr`](.agents/skills/create-pr/SKILL.md)。写更新日志用 [`write-changelog`](.agents/skills/write-changelog/SKILL.md)。
- `main` 只允许 squash 合并。合并前必须通过 `上游漂移 + 汉化校验` 与 `build` 两项检查。
- squash 合并的提交信息取 PR 标题与 PR 正文。PR 正文要写成能直接当提交正文读的样子。
- 不打 tag，不发 release，不触发 Release workflow。发版由维护者做。

---

## 任务路由

skill 在 `.agents/skills/<名字>/SKILL.md`，`.claude/skills` 指向同一个目录。开始任务前先读表里列出的文件。

| 任务 | 先读 |
|---|---|
| 写或改 commit 消息、PR 与 issue 文本、文档、代码注释 | [`simple-chinese`](.agents/skills/simple-chinese/SKILL.md) |
| 开、创建或准备 PR | [`create-pr`](.agents/skills/create-pr/SKILL.md) |
| 往 CHANGELOG 加条目、开新版本节、写致谢 | [`write-changelog`](.agents/skills/write-changelog/SKILL.md) |
| ATM10 发了新版，让汉化包支持它 | [`add-pack-version`](.agents/skills/add-pack-version/SKILL.md) |
| 给 issue、PR 或评论贴本地截图与文件 | [`upload-github-attachment`](.agents/skills/upload-github-attachment/SKILL.md) |
| 改译名 | 本文件「译名的真源在哪里」与「一个名字有多处表面」 |
| 算覆盖率、缺口或「某版新增且未译」 | 本文件「覆盖率与缺口的口径」 |
| 改上游自带的文件或导览书译文 | [`CONTRIBUTING.md`](CONTRIBUTING.md)「改上游自带的文件」「改导览书译文」 |
| 改闸 | 本文件「闸」，以及 `scripts/compliance/` 下的反例测试 |
