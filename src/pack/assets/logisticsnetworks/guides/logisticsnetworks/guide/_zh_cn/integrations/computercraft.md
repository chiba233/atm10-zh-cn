---
navigation:
  title: ComputerCraft
  parent: integrations/index.md
  position: 1
---

# ComputerCraft

装了 [CC: Tweaked](https://modrinth.com/mod/cc-tweaked) 后，电脑同时也是一个外设。脚本可以读取电脑界面上显示的全部内容：网络、频道、节点、节点图和实时 I/O 数据，并把它们画到显示器上。

## 连接

把一台 CC 计算机放在电脑旁边，或者用有线调制解调器把它们连起来。外设类型是 `logistics_computer`：

```lua
local lc = peripheral.find("logistics_computer")
```

## 所有权

电脑属于放置它的玩家。脚本能看到的网络，正好是这名玩家能打开的那些，遵循服务器的节点访问规则和 FTB Teams。任何人把 CC 计算机接到这台电脑上都能读取这些网络，所以要把它放在只有你能接触到的地方。

这次更新之前放置的电脑没有所有者。要配合 ComputerCraft 使用，把它拆下来重新放一次。

## 方法

`net` 是网络 id 或网络的完整名称。频道列表按界面上的顺序排列，每一项的 `index` 是 [I/O 监视器](../computer/io-monitor.md)里显示的 `CH` 编号，从 0 开始，所以 CH0 对应 `channels[1]`。图中边的 `channels` 存的也是 CH 编号。

| 方法 | 返回值 |
|---|---|
| `listNetworks()` | `{ {id, name, nodeCount, starred, color, createdAt}, ... }` |
| `getChannels(net)` | `{ {index, name, type, nodeCount}, ... }`：频道里没有启用的节点时，`type` 为 nil |
| `getNodes(net)` | `{ {id, label, block, pos, attachedPos, dimension, visible, highlighted}, ... }`：只含已加载的节点 |
| `getGraph(net)` | `{ name, totalNodes, vertices, edges }`：顶点含 `key, label, x, y, nodes`，边含 `from, to, type, channels` |
| `watch(net)` | 为这台计算机开始实时数据推送 |
| `unwatch(net)` | 停止推送 |
| `getFlow(net)` | 最近一次的数据样本，第一秒之前为 nil。网络没有被 watch 时报错 |

类型有 `item`、`fluid`、`energy`、`chemical` 和 `source`。

## 实时数据

调用 `watch` 后，每秒会收到一个 `logistics_flow` 事件：

```lua
local _, side, networkId, sample = os.pullEvent("logistics_flow")
-- sample.channels[1].total, sample.channels[1].resources[1].displayName
```

每个频道都有 `index`、`type`、`total`（这一秒搬运的数量，单位与 I/O 监视器相同）和 `resources`。`resources` 是数量最多的 16 种物品、流体或化学品，每项含 `kind`、`name`、`displayName` 和 `amount`。能量频道和魔源频道的资源列表为空。

计算机重启或断开连接时，watch 会结束，所以要在 `startup` 脚本里调用 `watch`。所有者失去这个网络的访问权限或网络被删除时，watch 也会停止，不报错。

## 示例

在连接的显示器上显示每个频道的实时速率：

```lua
local lc = peripheral.find("logistics_computer")
local mon = peripheral.find("monitor")
local net = "Main Base"

mon.setTextScale(0.5)
lc.watch(net)
while true do
  local _, _, _, sample = os.pullEvent("logistics_flow")
  mon.clear()
  for i, ch in ipairs(sample.channels) do
    mon.setCursorPos(1, i)
    mon.write(("CH%d %-8s %d/s"):format(ch.index, ch.type or "-", ch.total))
  end
end
```
