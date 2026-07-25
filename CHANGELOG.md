# Changelog

## 7.2

绿油油版汉化（基于 BBSMC 汉化二次修改，对应整合包 ATM10 7.2）。
客户端包与服务端包彻底分开发布，均附带三平台安装器 / 安装说明。

**覆盖规模（实测口径）**：整合包内 233 个模组自带官方中文，本包专注补齐其余部分——
语言文件层 **18 万余条**，其中约 409 个模组的中文完全依赖本包、142 个模组补齐官方缺翻的键；
硬编码文本 1,452 条（151 个 VaultPatcher 模块）；RFTools 24 个 .gui；467 种资源蜂；
799 条结构名；任务书补丁 195 条；主菜单按钮图 14 张。

**主要修复 / 新增**

- **主菜单首页汉化**：ATM 主菜单按钮文字烤进 PNG 贴图，重绘 14 张为中文
  （单人游戏 / 多人游戏 / 选项 / 退出 / 模组 / 语言 / 租用服务器）
- **系统性补译游戏内真实英文残留（~660 键）**：用 jar 感知扫描（有效中文 = 模组官方自带
  叠加资源包）找出真正显示英文的键——xtonesreworked 编号方块 496、Shiny 闪光热带鱼/村民 49、
  MineColonies 守卫职业与任务对话 80，及 ~35 个模组的零散标签。剔除品牌名 / 罗马数字 / 快捷键 /
  歌曲署名 / 技术缩写等本应保留英文的项，不盲翻。
- **补齐模组漏定义、会露原始键的名字（约 375 个）**：Ender IO 灵魂瓶、Reliquary 护符、
  Corail 墓碑卷轴、AE2 流体筛选等用 `entity/block/fluid_type/effect.<ns>.<path>` 通用引用名字，
  但不少条目连模组自己都没在 en_us 定义 → 露出原始键。按可枚举真源（实体标签 / blockstates /
  mob_effect 纹理 / fluid.*_still）全模组扫描后补齐：59 实体 + 288 方块（含流体块，AE2 筛选流体用）
  + 3 流体类型 + 25 效果（含墓碑卷轴暴露的召唤计时效果）。
- **替上游修 bug**：修正一批模组官方 zh_cn 自带的错误——死亡提示误加 `%2$s` 占位符导致
  格式化失败（the_bumblezone / mcwfences / twilightforest）、minecolonies 指令取错参数、
  神秘农业「夜视→步行辅助」、农夫乐事「免疫饥饿→无视饥饿回血」、Reliquary 虚空之泪模式反了等。
- **清理重复翻译**：删除 17 个纯冗余文件（这些模组官方已全中文，资源包再盖属浪费）；
  逐键 CJK 比对确保零英文回退，官方半成品（英文占位）文件全部保留。
- 任务书：补全 cataclysm / undergarden / railcraft / 神化 等章节缺口；
  章节标题 XyCraft→晶工艺、Oritech→奥日科技、RailCraft→铁路工艺，补章节副标题；
  「墓地」→「墓园」等译名与结构罗盘统一。
- **任务书术语 / 品牌统一（跟物品名对齐，不再执着保留英文）**：以模组自译名 / 物品名 /
  社区标准为单一真源——Allthemodium→ATM（与物品 ATM锭 / ATM镐 / ATM透视药水 统一，含基础
  半吊子错译「所有modium」）、Just Dire Things→可怖之物（修正基础错译「极端事物」）、
  EnderIO→末影接口、PneumaticCraft→气动工艺、EvilCraft→邪恶工艺、
  Hostile Neural Networks→敌对神经网络、Ars Nouveau→新生魔艺、Pipez→管道、
  Mob Grinding Utils→刷怪塔实用设备；维度名按社区认可：Mining Dimension→挖矿维度、
  The Beyond→彼岸；「古代金字塔」与任务「远古金字塔」打架 → 统一为远古金字塔。
  模组自身也保留英文的（MekaSuit / QIO / LaserIO / MEGA）不强译。
- **修任务书 3 个会崩溃的非法颜色码**：`&难得素秘术师护甲`（漏了 &5）、`&l&开裂&r石头`
  （漏了 &b）、`&高级磁盘外壳`（多余 &）——FTB 把 `&`+中文 当颜色码解析，报
  「Invalid formatting! Unknown formatting symbol」。
- **补 Silent Gear 章节副标题**：服务端缺 chapter_subtitle 键 → 显示英文
  "And Productive Metalworks"，补基础译名「以及高效金属加工」（做成可复现 delta）。
- 修错译（AE2 物质聚合器一系，对齐机器真名 `block.ae2.condenser`＝物质聚合器）：
  物质冷凝器→物质聚合器、冷凝物质/超冷凝物质→聚合物质/超聚合物质、「冷凝更多」→「聚合更多」
  （condensed 指高度聚合，非热学冷凝）；仅改 AE2 语境，保留别模组的「魔源冷凝器/饱和冷凝器」。
  结构罗盘补 `trial_chambers`→试炼密室（原版新结构，此前唯一漏网）。
- 正文对齐物品真名：ATM 星→**ATM之星**（`item.allthetweaks.atm_star`＝ATM之星，补漏「之」，13 处）。
- **全任务书正文机翻大扫除**：3428 条正文经 12 路对抗精修 + 自动化校验（格式码 / 占位符 / 换行 / 术语字节级比对），
  改写 **263 条**真机翻 / 错译——反译（灌注塔生效范围、弩穿透逻辑说反）、附魔名混淆（水下速掘↔水下呼吸、
  深海探索者）、数值错译（2700 颗心、9 格、540 血量等对齐英文）、漏译夹生英文词（overpowered / relentless /
  Titanium / read 等）、文化指代错译（Daredevil 敢死队→夜魔侠、Dr. Seuss→苏斯博士）、术语误译
  （Tile Entity→方块实体、Kibi→奇异果、Kobold 哥布林→狗头人）、Pipez 升级机制描述错误、人称 / 敬语不一致等。
  另修复 1 处 dict 转储污染（quest.6DB65926 的正文混入了一堆别的任务的 Python dict 垃圾文本）。
- flavor 文本本地化 / 修漏翻：ME 终端、武器?、无限增强器、无线终端（逐字彩虹）、脉动黑洞、
  龙魂等副标题的机翻占位 / 狗屁不通句改成接地气或通顺文案；
  修「武器?」正文漏翻的斜体 `&oused&r`（熵变机械臂那句）。
- 资源蜜蜂体系：译名单一真源 + 生成器派生双端脚本；服务端按 NBT ID 迁移旧蜂笼 / 实体显示名；
  玩家命名牌名字绝不触碰；JEI 类型行精确翻译。
- 结构罗盘 / 自然罗盘结构名；传送石碑维度名；The Bumblezone 维度统一为「嗡嗡领域」；
  Sodium 模组自定义粒子选项。
- 神秘农业作物名假翻译修复（纯客户端）；修复其配置误上服务器导致的进服刷屏报错。
- RFTools：24 个 .gui + 硬编码界面文本；建造机服务端聊天反馈汉化
  （服务端包 VaultPatcher 类定向模块）；协议值按设计保留英文防崩溃。
- **Jonn's Trophies 奖杯名汉化（推翻上一版「无法汉化」的结论）**：反编译
  trophymanager 2.5.0 后确认 `TrophyItem.getName()` 是
  `Component.translatable(NBT.TrophyData.Name)` —— 烘焙进 NBT 的那串
  「<生物显示名> Trophy」是被当**翻译键**用的，资源包完全能翻。按四种烘焙形态
  （创造栏 `idToName` 的 `Polar bear`／专用服务端 en_us 的 `Polar Bear`／服务端
  查不到键时的原始键名／单人存档下的中文名）全量生成 **2.5 万条**映射，
  并补上 `entity.<ns>.name = "Shiny %s"` 这类**模板拼名**实体
  （实测烘焙成 `Shiny zombie_horse Trophy`，纯 en_us 扫描会整类漏掉）。
  多个实体撞同一串烘焙名且译名不同的 33 条按老规矩丢弃——宁显英文不张冠李戴。
  生成器 `scripts/gen_trophy_names.py` + 快照 `scripts/trophy_entity_names.json`，单一真源。
- **格式串对抗（用 Minecraft 自己的 `FORMAT_PATTERN` 逐键比对英文原文）**：
  - 修 **7 条结尾裸 `%`**：MC 的格式正则会匹配到字符串结尾并抛
    `TranslatableFormatException`（原版自带的反例键就是 `translation.test.invalid = "hi %"`），
    Create 随机填充、railcraft 轨道提示、reliquary 配置项等；
  - 修 **20 条致命格式错**：译文多出英文没有的参数（silentgear 蓝图书、oritech 无人机、
    integrateddynamics 签名/输入类型）、把 `%s` 降级成 `%d`/`%f` 导致类型对不上
    （modular routers 投掷器/调整值、silentgear 修理包与采掘等级、EI 循环时间）、
    以及**参数顺序搞反**（curios 加/删栏位把「数量」和「类型」对调、ftbchunks 把玩家名
    和区块数对调、ftbquests 队伍名与奖励数对调、MI 超频把倍率当刻数）；
  - 修 **8 条非法 `§` 颜色码**（`§` 后面跟中文 → 那个字被渲染器吞掉）：气动工艺
    「向左/右§侧展开」「§喷溅型」、实体过滤帮助、mekanistic routers 模块标题等；
  - 修 **50 条参数被译文吞掉**：精致存储双前缀 `%s%s`（38 条，染色/装饰前缀永远不显示）、
    DimStorage 储量/液体/亮度/温度**数值整个不显示**、JourneyMap 路径点 Id、
    刷怪塔锯片升级把上限写死成 10、artifacts 触发几率、工业先锋镭射透镜颜色前缀、
    MineColonies 用了**全角 `％s`** 导致界面直接显示「％s」、
    以及 `misc.refinedstorage.no_permission.open` 的译文竟然是「64k存储元件」这么个
    完全无关的物品名。
- **品牌名被按词典义机翻（8 条）**：作者社交链接按钮 `Discord`→「不和」
  （SFM 工厂管理器与 Observable **两处**）、`Ko-fi`→「咖啡相伴/天堂之路」
  （mss/mes/mns/mvs 四个模组）、`Patreon`→「赞助」。这类是点进去要能对上的平台名，
  一律还原英文——跟「不执着保留英文品牌名」不矛盾：玩家认的是译名，平台认的是原名。
- LICENSE / 各源文件加入作者署名（Copyright © 2026 星野夢華）。
- 安装器：三平台、自动备份 / 恢复、options.txt 自动启用、可选拼音搜索、
  实例目录自动检测失败时支持手动输入路径（含清洗复制/拖拽带来的引号与转义空格，配套 CI 回归测试）。
- 质量基建：踩过的雷转为 CI 硬检查（协议值 / 生成器漂移 / 旧译名残留 / 服务端模块安全）；
  安装脚本在 macOS / Windows / Linux 三系统跑端到端测试。

**已知限制**

- **Sodium「粒子效果」里的原版粒子名无法汉化**：sodium-extra 0.9.3 自身问题
  （它内置的原版粒子中文也渲染不出来），资源包无法干预；模组自定义粒子不受影响。
- **玩家奖杯**（击杀玩家掉落）名字是玩家 ID，本就不该翻译。
- 用命名牌改过名的生物，掉落奖杯会沿用你起的名字（`CustomName` 优先），不受本包影响。
