# All the Mods 10 · 7.2 汉化补丁 —— 绿油油版

整理／补译：**星野夢華 (Hoshino Yumeka)**，基于 BBSMC 汉化二次修改（改动幅度较大，
故独立命名）。BBSMC 原版说明与致谢见 [原版说明与致谢(BBSMC).txt](原版说明与致谢(BBSMC).txt)。

每个 [Release](../../releases) 提供两个**彼此独立**的压缩包：

| 包 | 给谁用 | 说明 |
|---|---|---|
| `…-客户端-vX.zip` | 每个玩家 | 附带三平台安装器，见下 |
| `…-服务端-vX.zip` | 开服的人 | 手动覆盖，见包内 `README-服务端.md` |

## 客户端安装

1. 下载 `…-客户端-vX.zip` 并解压；
2. 把解压出的**整个文件夹**放进 ATM10 实例根目录
   （含 `mods/`、`options.txt` 的那一层，通常是 `.minecraft/versions/All the Mods 10/`）；
3. 运行安装器：
   - **Windows**：双击 `双击安装-Windows.bat`
   - **macOS / Linux**：终端运行 `bash install.sh`
4. 选 **[1] 应用汉化**。安装器会自动备份将被覆盖的文件、在 `options.txt`
   里启用汉化资源包（不启用会全英文），并询问是否安装可选的 **JEI 拼音搜索** mod。

回退：菜单选 **[3] 恢复备份**（还原被覆盖文件、删除新增文件、还原 options.txt）。
命令行用法见脚本头部注释（`apply` / `apply-with-pinyin` / `backup` / `restore`）。

## 服务端安装

蜂笼蜂名、RFTools 建造机聊天反馈等文本由**服务端**生成，只装客户端包救不了。
下载 `…-服务端-vX.zip`，按包内 [README-服务端.md](SERVER.md) 覆盖到服务器并重启。

⚠️ 不要把客户端包覆盖到服务器：其中 `config/mysticalcustomization/`（作物名汉化）
是纯客户端配置，上了服务器会让所有玩家进服时刷
`An error occurred creating crop with id null`。

## 本版额外汉化 / 修复（相对 BBSMC）

- **RFTools 全系**：26 个 `.gui` 界面文件全部汉化；96 条字节码硬编码界面文本
  （形状卡、过滤器、存储扫描器、护盾、传送、移动仓等）。
  `Copy` / `Move` / `Ignored` 等模式选项是**协议值**，翻译会崩游戏，按设计保留英文。
- **结构罗盘**：补 114 个缺失结构名（CTOV / Towns & Towers / Explorify / BWG / Structory）。
- **传送石碑**：补 17 条维度分组名（挖矿维度 / 异界 / 彼岸 / 以太等，已进服实测）。
- **资源蜜蜂**：462 种蜂名。客户端渲染层替换 + 服务端语言注入 mod
  （服务端烙进 NBT 的蜂名直接是中文；旧蜂笼名字已烙死，只对新抓的生效）。
- **神秘农业**：修正 12 种作物种子假翻译（config `name` 字段，纯客户端）。
- **其他**：PotionsMaster 154 条、Shiny! 2000+ 实体名、灵视 / 穿墙等属性名、
  花粉筛升级 / 枫糖浆等漏配键、字体乱码清理。

## 汉化机制（给想二次修改的人）

汉化分三层，缺一不可：

1. **资源包** —— 仓库内是源码目录 `resourcepacks/ATM10汉化包-7.2/`
   （zip 由构建脚本 / CI 现场压缩，不入 git）。标准 lang 文件 + McJtyLib `.gui`。
2. **VaultPatcher**（`vaultpatcher/modules/*.json`）—— patch 硬编码在字节码里的文本。
   `load_all_modules` 必须为 `true`。**枚举协议值不可翻**，CI 有硬检查。
   服务端只能装类定向模块（清单：`scripts/server_modules.txt`）。
3. **KubeJS 客户端脚本**（`kubejs/client_scripts/`）—— 处理运行时拼接的文本。

服务端专属第四层：`server-lang-mod/` 语言注入 mod（lowcodefml 纯资源 jar），
让专用服务器把中文蜂名烙进物品 NBT。

## 开发 / 发版

```bash
python3 scripts/check.py            # CI 同款校验（协议值/配置/lang/.gui/服务端模块清单）
python3 scripts/test_installer.py   # 安装器端到端测试
./scripts/build_dist.sh 7.2-release1  # 打客户端+服务端两个分发包
```

- **ci.yml**：每个 PR / push 校验 + 试打包
- **installer-test.yml**：安装脚本一动就在 **macOS / Windows / Linux** 三系统跑端到端
- **release.yml**：推 tag `v*` 自动构建两个包并发布 Release（说明取自 CHANGELOG）

## 致谢与 License

BBSMC 汉化组（原始底本）· All the Mods 团队（整合包）· 各 mod 原作者。

本仓库以 [GPL-3.0](LICENSE) 发布；BBSMC 原始词条与各 mod 资源的权利归其原作者所有。
问题反馈请走 [Issues](../../issues)，附截图与具体物品 / 界面名。
