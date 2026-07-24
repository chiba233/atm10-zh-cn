# Changelog

## 7.2-release1

首个绿油油版发布（基于 BBSMC 汉化二次修改，对应整合包 ATM10 7.2）。
客户端包与服务端包**彻底分开发布**。

**服务端包**（新）：
- `pb_hanhua_server` 语言注入 mod：462 种蜂名，服务端抓蜂烙进 NBT 的直接是中文
  （仅对新抓的蜂生效，旧蜂笼名字已烙死）
- VaultPatcher + RFTools 类定向模块：建造机/形状卡的服务端聊天反馈汉化
- 任务书语言 + VaultPatcher 主配置
- ⚠️ 作物名汉化（mysticalcustomization）为纯客户端配置，服务端包不含——
  部到服务器会让所有玩家进服刷 `error creating crop with id null`（实测定位并修复）

**客户端包**：

- **RFTools 全系**：26 个 `.gui` 界面文件全部汉化；96 条字节码硬编码界面文本汉化
  （形状卡 / 过滤器 / 存储扫描器 / 护盾 / 传送 / 移动仓等）；协议值按设计保留英文
- **结构罗盘**：补全 114 个缺失结构名（CTOV / Towns & Towers / Explorify / BWG / Structory）
- **传送石碑**：补全 17 条维度分组名（挖矿维度 / 异界 / 彼岸 / 以太等）
- **资源蜜蜂**：462 种蜂名汉化，基因样本 / 蜂笼不再显示英文 ID
- **神秘农业**：修正 12 种作物名假翻译根因（config `name` 字段）
- **其他**：PotionsMaster 154 条、Shiny! 2000+ 实体名、属性名补译、字体乱码清理
- **修复**：建造机 GUI 崩溃（误译协议值 `Ignored` 导致，已回退并加 CI 拦截）
