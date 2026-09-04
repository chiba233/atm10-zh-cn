# 服务端汉化包 · 安装说明

[![GitHub](https://img.shields.io/badge/GitHub-chiba233%2Fatm10--zh--cn-181717?logo=github)](https://github.com/chiba233/atm10-zh-cn)
[![Contributing](https://img.shields.io/badge/Contributing-guide-blue.svg)](./CONTRIBUTING.md)
[![Security](https://img.shields.io/badge/Security-policy-red.svg)](./SECURITY.md)
[![License](https://img.shields.io/badge/License-GPL--3.0-green.svg)](./LICENSE)

> **单机玩家不需要本包**，装客户端包就够了。本包是给开**专用服务器**的人用的。

## 兼容版本

| 项 | 版本 |
|---|---|
| 整合包 | All the Mods 10 **v@@MCVER@@** 专用服务器 |
| Minecraft | 1.21.1 |
| 加载器 | NeoForge @@NEOFORGE@@ |

**必须与整合包版本严格对应，不能跨版本用。** 服务器上每个玩家也要各自装对应版本的客户端包。

## 安装

1. **先备份**服务器数据目录里的 `config/`、`kubejs/`、`vaultpatcher/`、`mods/vaultpatcher.jar`。本包不带自动安装器。
2. 把包内的 `mods/` `vaultpatcher/` `kubejs/` `config/` **覆盖**到服务器数据目录（含 `mods/`、`server.properties` 的那一层）。
3. **完整重启服务器。**

> 任务书语言文件是**整份替换**，会覆盖同名文件，这是正常的。包里那些内容只有 `{}` 的 `zz_hanhua_*.snbt` / `_*.snbt` 是有意为之，不是漏生成。

**只改了任务书文本时可以不重启**，执行 `ftbquests reload` 即可让在线玩家生效：

```bash
docker exec <容器名> rcon-cli ftbquests reload
```

在服务端控制台直接敲 `ftbquests reload` 效果相同。VaultPatcher 与 kubejs 的改动仍需完整重启。

## 验证

- 服务器能正常启动、无报错。
- 进服后：任务书标题 / 描述是中文；建造机未选择时的聊天提示是中文；抓到的新蜂、放进背包的老蜂笼名字是中文。
- 任务书里提到的物品名，应与你在 JEI 里搜到的完全一致。对不上请[提 Issue](https://github.com/chiba233/atm10-zh-cn/issues) 附截图。

## 注意

⚠️ **绝不能把客户端包的 `config/mysticalcustomization` 上传到服务器**，会让所有玩家进服时刷 `error creating crop with id null`。本服务端包已不含该目录，请确认你也没有手动复制上去。

⚠️ **绝不能把客户端的 VaultPatcher 模块装到服务端**。服务端只用类定向模块（清单见 `scripts/server_modules.txt`），全局替换模块会污染 NBT / 注册名导致存档损坏。
