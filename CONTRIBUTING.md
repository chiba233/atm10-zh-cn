# 贡献指南

感谢你想让这份汉化更好。这个仓库有几条**高压线**——都是真实炸过的雷，
CI 会拦截其中大部分，但请先读完再动手。

## 高压线（违反即炸游戏或毁玩家数据）

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
   曾经的"服务端语言注入 mod"就是因此被废除的。
   同理：`config/mysticalcustomization/`（作物名）是纯客户端配置，
   **绝不能进服务端包**——会让所有玩家进服刷
   `error creating crop with id null`。
4. **禁止贪婪字符串替换。**
   所有显示层替换必须整词 / 整段精确匹配（词边界、长名优先、
   hasOwnProperty 防原型链穿透）。半截替换（`Ter-蜜蜂-Nator`）比不翻更糟。

## 架构与单一真源

- **资源蜜蜂译名唯一真源** = 资源包
  `assets/productivebees/lang/zh_cn.json` 的实体键。改蜂名只改这里，然后跑
  `python3 scripts/gen_pb_hanhua.py scripts/pb_upstream_en_us.json`
  重新生成双端 kubejs 脚本。**手改生成文件会被 CI 拒绝**（快照重跑 diff）。
- 资源包在仓库中是**源码目录**（`resourcepacks/ATM10汉化包-7.2/`），
  zip 由构建脚本现场压缩，**任何 zip / jar 产物不入 git**。
- 任务书补丁放 `config/ftbquests/quests/lang/zh_cn/chapters/*.snbt`
  （分章 delta，langsplitter 启动时合并进单体文件）。
- 同一数据出现在多个表面（tooltip / JEI / 快捷栏 / 名牌 / Jade / GUI）时，
  修复必须**一次修齐所有表面**并逐面自测——不接受打地鼠式补丁。
- 译名统一：同一事物在任务书、罗盘、物品名中的叫法必须一致
  （例：iceandfire 的 graveyard 统一为「墓园」）。

## 本地开发

```bash
python3 scripts/check.py            # CI 同款校验（全部硬检查）
python3 scripts/gen_pb_hanhua.py scripts/pb_upstream_en_us.json  # 重生成蜂名脚本
python3 scripts/test_installer.py   # 安装器端到端测试
./scripts/build_dist.sh 7.2-beta1   # 打客户端+服务端两个分发包
```

- **ci.yml**：校验 + 蜂名生成器一致性 + 试打包，每个 PR / push 必跑
- **installer-test.yml**：`installer/` 一动就在 macOS / Windows / Linux
  三系统跑端到端测试
- **release.yml**：推 tag `v7.2-release1` / `v7.2-beta1` 自动构建发布，
  Release 说明自动取 `CHANGELOG.md` 对应版本段落——**发版前记得写 CHANGELOG**

## PR 约定

- 一个 PR 只做一件事；用户可见改动更新 `CHANGELOG.md`
- 版本号格式：`<整合包版本>-<release|beta|rc><序号>`（如 `7.2-release1`）
- commit 说明写清"为什么"，尤其是译名决策（附投票 / 出处更好）
