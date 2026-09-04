<p align="center">
  <img src="src/pack/pack.png" width="96" height="96"
       alt="ATM10 汉化补丁「绿油油版」资源包图标">
</p>

# All the Mods 10 汉化补丁 —— 绿油油版

[![GitHub](https://img.shields.io/badge/GitHub-chiba233%2Fatm10--zh--cn-181717?logo=github)](https://github.com/chiba233/atm10-zh-cn)
[![Contributing](https://img.shields.io/badge/Contributing-guide-blue.svg)](./CONTRIBUTING.md)
[![Security](https://img.shields.io/badge/Security-policy-red.svg)](./SECURITY.md)
[![License](https://img.shields.io/badge/License-GPL--3.0-green.svg)](./LICENSE)

All the Mods 10 的简体中文汉化补丁，**同时支持 7.0 / 7.1 / 7.2 / 7.3 / 8.0 / 8.1**，每个整合包版本一个专属包。

> **装这一个就够。** 语言文件 18.4 万余条、任务书、19 本模组手册、467 种蜂、
> 799 条结构名、201 张图片艺术字都在里面，是完整的一份，不是叠加在别家之上的补充包。
> **不需要**先装 BBSMC 或任何其他汉化当前置——同时装两份会互相覆盖。
> 整合包装好后直接装本包即可。

## 兼容版本

Minecraft 均为 1.21.1。**必须下载与你整合包版本对应的那个包，不能跨版本用。**

| 整合包版本 | NeoForge | 状态 |
|---|---|---|
| All the Mods 10 **8.1** | 21.1.249 | ✅ 已实机验证 |
| All the Mods 10 **8.0** | 21.1.247 | ✅ 已实机验证 |
| All the Mods 10 **7.3** | 21.1.247 | ✅ 已实机验证 |
| All the Mods 10 **7.2** | 21.1.241 | ✅ 已实机验证 |
| All the Mods 10 **7.1** | 21.1.234 | ⚠️ 逐条核验，未实机验证 |
| All the Mods 10 **7.0** | 21.1.228 | ⚠️ 同上 |

## 我该下载哪个包？

[Releases](../../releases) 里每个版本有两个文件：

| 文件 | 装在哪 | 谁需要 |
|---|---|---|
| `atm10-zh_cn-**client**-<补丁版本>-atm<整合包版本>.zip` | 你自己电脑上的 ATM10 实例 | **所有人都要装。** 单人玩家只装这一个 |
| `atm10-zh_cn-**server**-<补丁版本>-atm<整合包版本>.zip` | 服务器那台机器 | 只有**开服的人**要装 |

文件名里有两个版本号：`R25` 是**补丁的版本**，`atm8.1` 才是**你的整合包版本**。认后者下载。

**单人玩家只装客户端包**——单人时你的客户端兼任服务端，蜂笼迁移脚本也已包含在客户端包里。

⚠️ **别把客户端包丢到服务器上**，会让所有玩家进服时刷 `error creating crop with id null`。

## 客户端安装

### 1. 找到实例文件夹

含 `mods` 文件夹和 `options.txt` 的那一层。启动器里右键实例 →「打开文件夹」。
路径通常长这样：`...\.minecraft\versions\All the Mods 10\`

### 2. 解压，把整个文件夹放进去

解压后得到一个 `atm10-zh_cn-client` 文件夹，**整个拖进实例目录**：

```
All the Mods 10\          ← 实例根目录
├─ mods\
├─ options.txt
└─ atm10-zh_cn-client\    ← 刚放进来的
   ├─ 双击安装-Windows.bat
   ├─ install.sh
   └─ ...
```

放错地方也没关系，安装器会提示你手动输入路径。

> ⚠️ **不要把压缩包内容直接解压覆盖到实例根目录**。那样虽然也能用，但**没有任何备份**，之后无法一键回退。

### 3. 运行安装器

- **Windows**：双击 `双击安装-Windows.bat`
- **macOS / Linux**：终端里 `bash install.sh`

选 **[1] 应用汉化**。它会备份原文件、复制汉化文件、自动启用资源包，并问你要不要装可选的 JEI 拼音搜索（能用拼音首字母搜物品，推荐装）。

### 4. 确认装上了

**资源包必须在「已选」一侧的最顶部，否则大部分汉化都不生效。**

进游戏 → 选项 → 资源包，确认「ATM10汉化包-<你的版本>」在最顶部；回主菜单，按钮应该是中文。

<p align="center">
  <img src="img/img.png" alt="资源包要在「已选」一侧的最顶部" width="720">
</p>

忘了这一步也不至于蒙在鼓里：进世界几秒后聊天栏会提示你资源包没生效。一切正常时它不会说话。

### 升级 / 卸载

再运行一次安装器：**[u] 一键下载并更新**（自动挑对应你整合包版本的包，校验 SHA-256 后安装），或 **[3] 恢复备份** 回到安装前。

## 服务端安装

**只有开服的人需要。单人玩家跳过。**

下载对应版本的 `...-server-...zip`，把包内的 `mods/` `vaultpatcher/` `kubejs/` `config/` 覆盖到服务器数据目录，然后**完整重启服务端**。详见包内的 `请安装前务必看我.md`。

装完后玩家仍需各自安装客户端包——服务器管不了你屏幕上的物品名。

## 常见问题

**装完还是英文？**
进游戏 → 选项 → 资源包，「ATM10汉化包」必须启用，**而且在「已选」那一侧的最顶部**。

**模组都是中文，唯独原版的方块 / 物品 / 界面是英文？**
不是汉化包的问题，是启动器没把原版中文语言文件下全。在启动器里对这个版本跑一次文件补全 / 修复即可。仍不行就删掉 `.minecraft/assets/indexes/<索引号>.json` 再启动。

**Windows 报 `Cannot overwrite the item ... with itself`？**
你把压缩包内容直接解压到了实例根目录，之后又运行了安装器。汉化其实已经装好了，只差资源包没启用——进游戏手动把它拖到「已选」最顶部即可。

**启动卡好几分钟，日志里一串 `ConnectException`？**
不是汉化包的事，是 IPv6 连不出去。在启动器的 **JVM 参数**里加一条：

```
-Djava.net.preferIPv4Stack=true
```

（HMCL 在「游戏特定设置 → Java 虚拟机参数」里填，**改完要重启 HMCL 本身**。或者直接在网卡上关掉 IPv6。）

**改动不生效？**
资源包类改动按 **F3+T** 重载；主菜单按钮图、硬编码文本需**完整重启游戏**；任务书需**重进世界 / 重连服务器**。

**蜂笼上的蜂名是英文？**
老蜂笼的名字是抓蜂时烙进 NBT 的，得靠脚本改写。把蜂笼放进背包待几秒自动转正。联机时需要服主装服务端包。**你用命名牌起的名字永远不会被改。**

**JEI 里有一行灰色的 `productivebees:xxx`？**
那是模组给所有语言玩家显示的 ID 行，不是漏翻。

**闪退且不留任何崩溃日志？**
先把 `mods/jecharacters-*.jar`（JEI 拼音搜索）挪走再试。它会推高启动时的内存峰值，内存紧张的机器可能被系统直接杀掉。它是可选的，不装不影响汉化。

## 仍是英文的部分

- **CC: Tweaked 电脑终端**——它自带的字形表只有 256 个字符，没有汉字。
- **模组配置界面**（Create 的「模组配置」列表打开的那些页）。
- **Sodium「粒子效果」里的原版粒子名**（Cloud / Ash / Crit…）。
- **建造工具**：第三方建筑包的单个蓝图名、顶部那行 `包名/类别/文件名` 路径。前三层（风格 / 分类 / 子分类）已汉化。
- **可视性能侦测浮层上的两行计时**。
- 极少数模组把英文画进了贴图。

发现漏翻 / 错译请[提 Issue](../../issues)，附截图与位置。

## 参与与反馈

- 汉化问题（漏翻 / 错译 / 崩溃）→ [Issues](../../issues)
- 想改译名或贡献翻译、了解仓库结构与构建流程 → [CONTRIBUTING.md](CONTRIBUTING.md)
- 安全问题 → [SECURITY.md](SECURITY.md)

## 许可证与致谢

授权**按目录拆开**（详见 [LICENSE](LICENSE)）：

| | |
|---|---|
| 代码（`scripts/`、`installer/`、CI） | GPL-3.0-or-later · © 2026 星野夢華 |
| 译文内容（`src/pack`、`src/config`、`src/kubejs`、`src/vaultpatcher`） | CC BY-NC-SA 4.0 |
| 随包第三方 jar | 各自许可，许可正文随包 |

整理／补译：**星野夢華 (Hoshino Yumeka)**。

致谢：**[十一月の风筝](https://space.bilibili.com/2041176282)**（测试）·
**[0xyk3r](https://github.com/0xyk3r)**（贡献者）· **BBSMC 汉化组**（早期参考）·
**All the Mods 团队**（整合包与任务书官方中文）·
各模组原作者与 CFPA 社区 · **Claude Fable 5**（fable5 老师，我还记得你）。
