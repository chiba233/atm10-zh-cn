# 致谢与技术说明

本文件随发布包一起分发，说明语言文件之外的改动都动了什么、为什么这么动，以及本包依赖了谁的成果。

## 一、本包不含广告，也不含任何加载器 / 启动器模组

本包只有一个 jar：`mods/vaultpatcher.jar`（[VaultPatcher](https://modrinth.com/mod/vault-patcher) 1.5.3-fix，
作者 [FengMing3093](https://github.com/3093FengMing/VaultPatcher)，GPL-3.0-only，
字节码文本替换框架，替换表全部在 `vaultpatcher/modules/` 里，明文可查）。
构建时按 `src/mods.lock.json` 记录的 sha256 从 Modrinth 下载并校验，不存放在本仓库。
随它分发的 `mods/LICENSE-vault-patcher.txt` 是 GPL-3.0 许可证正文本身（FSF 原文），
不含本项目的版权声明，那个 jar 不是本项目的作品。
资源包的启用与语言设置由安装器直接改 `options.txt` 完成，不需要任何常驻模组代劳。

## 二、语言文件处理不了的三类文本

Minecraft 的 `assets/<模组>/lang/zh_cn.json` 只能翻译使用翻译键的文本。以下三类不能用语言文件翻译，本包分别这样处理：

### 1. 硬编码在 Java 字节码里的界面文字（VaultPatcher）

有些模组把界面字符串直接写死在 class 里。`vaultpatcher/modules/*.json` 给出「英文原文 → 中文」的替换表，由 VaultPatcher 在类加载时改写常量池。

- 共 151 个模块、1,452 条，以 RFTools 系为主。
- 枚举协议值（如 RedstoneMode 的 `Ignored`/`Off`/`On`）不能翻译：McJtyLib 按名字反查，翻译后存档会崩溃。`scripts/check.py` 会检查这一条。

### 2. 写死在 data 包里的成就 / 法术书文本

部分模组的 `advancements/`、`recipes/` 直接在 JSON 里写英文，不引用翻译键。本包提供覆盖版数据文件。

- 只改显示文本。配方产物、条件、数量等游戏逻辑保持原样。
- 模组更新新增内容时，新内容会显示英文，需要重新提取。

### 3. KubeJS 运行时替换（客户端脚本）

`kubejs/client_scripts/` 里的脚本监听 `ItemEvents.tooltip`，按行匹配英文原文并替换成中文。只在客户端运行，不影响服务器。

- 需要整合包自带的 KubeJS（ATM10 本身就带）。
- 模组更新改了原文时，匹配失效，显示回英文，不报错。

## 三、翻译来源与致谢

| 来源 | 说明 | 许可 |
|---|---|---|
| BBSMC 汉化组（[ATM10 汉化包](https://bbsmc.net/language/all-the-mods-10-cn)） | 起步阶段参考过其译文。本包现有内容由各模组自带官方中文、CFPA 社区翻译与本包自译构成。这是翻译上的参考，不是安装上的依赖，用本包不需要安装它。 | 保留所有权益 / 无许可证（项目页标注） |
| CFPA 社区翻译（[Minecraft-Mod-Language-Package](https://github.com/CFPAOrg/Minecraft-Mod-Language-Package)） | 本包 28.6% 的词条与 CFPA 1.21 语言包一致。感谢 CFPA 团队与众多贡献者。 | CC BY-NC-SA 4.0（署名—非商业性使用—相同方式共享） |
| All the Mods 团队 | 整合包本身，以及任务书的官方中文。 | 见整合包 |
| [十一月の风筝](https://space.bilibili.com/2041176282) | 测试。 | — |
| 各模组原作者 | 233 个模组自带官方中文，共 89,430 条。本包 47.1% 的词条与之一致，不做重复翻译。 | 各自许可 |

### 统计口径

`scripts/compliance/audit_base.py` 把出货包与底本逐条比对：文件按字节比，字符串做三方比对。
译文与底本相同、同时也与模组自带中文或 CFPA 社区翻译相同的，算作这两个来源的译法，
不算底本的。151,828 条译文的分布：

| | 条数 | 占比 |
|---|---:|---:|
| 与模组自带中文一致 | 71,574 | 47.1% |
| 与 CFPA 社区翻译一致 | 43,457 | 28.6% |
| 本包自有（改写或新增） | 16,514 | 10.9% |
| 与之相同、但属通用译法的功能性名称 | 20,283 | 13.4% |

末一类为「奖杯」「熔融石榴石桶」这类只有一种自然译法的功能性名称：任何一份
汉化包译出来都是同一串字，字符串相同不足以判定来源。有独创性的成段文字（导览书
正文、长描述）均由本包自行撰写。

### 授权

按目录拆开，详见 [LICENSE](LICENSE)：代码（脚本与安装器）GPL-3.0-or-later，
译文内容 CC BY-NC-SA 4.0（署名—非商业性使用—相同方式共享）。

两者分列而非合并声明为单一许可证：GPL-3.0 第 7 条禁止在分发时附加额外限制，
而 CC BY-NC-SA 4.0 含有非商业性使用限制，二者不能并存于同一份声明。

Copyright © 2026 星野夢華 (Hoshino Yumeka)。

## 四、反馈

汉化问题（漏翻 / 错译 / 崩溃）请提到本项目：

- Issues：<https://github.com/chiba233/atm10-zh-cn/issues>

请附截图与位置（哪个模组、哪个界面）。本包的问题不要反馈给底本作者：本包译文与底本已有大量差异，他们无法复现。
