# 服务端汉化包 · 安装说明

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

> 任务书语言文件整份替换、覆盖同名文件是正常的；包里内容只有 `{}` 的
> `zz_hanhua_*.snbt` / `_*.snbt` 也是正常的。

**只改了任务书文本时可以不重启**，`ftbquests reload` 即可对在线玩家生效：

```bash
docker exec <容器名> rcon-cli ftbquests reload
```

（服务端控制台直接敲同名命令也行。VaultPatcher 与 kubejs 的改动仍需完整重启。）

## 验证

- 服务器能正常启动、无报错。
- 进服后：任务书标题 / 描述是中文；建造机未选择时的聊天提示是中文；抓到的新蜂、放进背包的老蜂笼名字是中文。
- 任务书里提到的物品名，应与你在 JEI 里搜到的完全一致。对不上请[提 Issue](https://github.com/chiba233/atm10-zh-cn/issues) 附截图。

## 注意

⚠️ **别把客户端包的 `config/mysticalcustomization` 传到服务器**——所有玩家进服会刷
`error creating crop with id null`。本包不含该目录，确认你没手动复制过去。

⚠️ **别把客户端的 VaultPatcher 模块装到服务端**——会污染 NBT 与注册名，损坏存档。
服务端只用类定向模块（清单见 `scripts/server_modules.txt`）。
