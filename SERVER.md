# 服务端汉化包 · 安装说明

[![GitHub](https://img.shields.io/badge/GitHub-chiba233%2Fatm10--zh--cn-181717?logo=github)](https://github.com/chiba233/atm10-zh-cn)
[![Contributing](https://img.shields.io/badge/Contributing-guide-blue.svg)](./CONTRIBUTING.md)
[![Security](https://img.shields.io/badge/Security-policy-red.svg)](./SECURITY.md)
[![License](https://img.shields.io/badge/License-GPL--3.0-green.svg)](./LICENSE)

> 适用于 ATM10 7.2 **专用服务器**（dedicated server）。**单机玩家不需要本包**——
> 单机时你自己的客户端就兼任逻辑服务端，蜂名迁移脚本已包含在客户端包里。

## 目录

- [兼容版本](#兼容版本)
- [为什么服务端也要单独装](#为什么服务端也要单独装)
- [包里有什么](#包里有什么)
- [安装](#安装)
- [验证](#验证)
- [不包含什么 · 为什么](#不包含什么--为什么)
- [安全性说明](#安全性说明)

## 兼容版本

| 项 | 版本 |
|---|---|
| 整合包 | All the Mods 10 **v7.2** 专用服务器 |
| Minecraft | 1.21.1 |
| 加载器 | NeoForge 21.1.241 |

**客户端包与服务端包必须匹配同一版本**，且服务器每个玩家的客户端也要装对应的客户端汉化包。

## 为什么服务端也要单独装

有两类文本是**服务端生成后直接发给客户端**的，客户端装什么都救不回来：

1. **资源蜜蜂的蜂笼 / 实体名**：抓蜂时服务端把蜂名解析成纯字符串烙进物品 NBT。
   `kubejs/server_scripts/pb_hanhua_cage_migrate.js` 会按 NBT 里的真实蜂种 ID，
   把蜂笼名与实体名改写为权威译名（与客户端资源包**同源**）。
   老蜂笼把它放进背包待几秒即自动转正；**玩家用命名牌起的名字绝不会被改**。
2. **RFTools 建造机 / 形状卡的聊天反馈**（「未选择建造机！」等）：由服务端逻辑发送。
   `mods/vaultpatcher.jar` + `vaultpatcher/modules/` 里的 RFTools 定向模块让服务端发出的就是中文。

> **为什么不用「服务端语言注入 mod」？** 那会让服务端**现算**的文本变中文，而 JEI / 配方
> （客户端由英文数据现算）不变，两边名字对不上、玩家查不到配方。本包早已废弃该方案，
> 只做「按 NBT ID 精确改写纯显示字段」这一件事。

## 包里有什么

```
mods/vaultpatcher.jar                          # 字节码文本补丁工具（上游原版，未改）
vaultpatcher/modules/*.json                    # 仅 10 个 RFTools/mcjty 类定向模块（清单见 scripts/server_modules.txt）
kubejs/server_scripts/pb_hanhua_cage_migrate.js # 蜂笼/实体显示名按 NBT ID 迁移
config/ftbquests/…                             # 任务书中文（服务端也要，否则任务标题/描述回退英文）
config/vaultpatcher_asm/…                       # VaultPatcher 主配置
README-服务端.md · LICENSE · 项目主页与反馈.url
```

## 安装

1. **先备份**服务器数据目录里的 `config/`、`kubejs/`、`vaultpatcher/`、`mods/vaultpatcher.jar`
   （若已存在）。本包不带自动安装器，请手动备份以便回退。
2. 把本包内的 `mods/` `vaultpatcher/` `kubejs/` `config/` **覆盖**到服务器数据目录
   （含 `mods/`、`server.properties` 的那一层）。
3. **完整重启服务器**（VaultPatcher 在类加载时生效，热重载无效）。

## 验证

- 服务器**能正常启动、无报错**（尤其别出现 `error creating crop with id null`——若出现，
  说明误把客户端包的 `config/mysticalcustomization` 上了服务器，见下）。
- 进服后：任务书标题 / 描述为中文；建造机未选择时的聊天提示为中文；
  抓到的新蜂 / 放进背包的老蜂笼名字为中文。

## 不包含什么 · 为什么

⚠️ **神秘农业作物名配置（`config/mysticalcustomization`）是纯客户端的，绝不能上服务器**。
服务器带上改名后的作物配置，会让**所有玩家进服时刷**
`An error occurred creating crop with id null`（2026-07-24 实测定位）。
**本服务端包已不含该目录**；请也确认你没从客户端包手动拷贝它上去。

## 安全性说明

服务端只附带**类定向**（target_class 指向具体 GUI/逻辑类）的 VaultPatcher 模块，
清单与准入标准见 `scripts/server_modules.txt`。**全局替换模块**（如客户端的蜂名基因模块）
绝不能装到服务端——会污染 NBT / 注册名导致存档损坏。CI 会拦截对该清单的越界变更。
