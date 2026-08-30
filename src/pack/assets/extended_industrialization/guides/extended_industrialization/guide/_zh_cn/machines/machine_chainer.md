---
navigation:
  title: "机器链接器"
  icon: "machine_chainer"
  parent: extended_industrialization:machines.md
categories:
  - machines
item_ids:
  - extended_industrialization:machine_chainer
  - extended_industrialization:machine_chainer_relay
---

# 机器链接器

<GameScene zoom="2" interactive={true} fullWidth={true}>
	<ImportStructure src="machine_chainer_example.nbt" />
	<IsometricCamera yaw="180" pitch="30" />
</GameScene>

机器链接器能沿一条直线，在最多 64 格的范围内连接许多机器、木桶，或是任何带有 `#extended_industrialization:machine_chainer/linkable` 标签的容器方块。被连接的容器会与链接器合并成同一个共享容器。链接器可以朝向任意方向，包括朝上和朝下。

链接器支持物品、流体和能量的传输！不过能量传输被限制在同等级单根电缆传输速率的 3 倍以内，并且无法与电压不匹配的已连接机器交换能量。

## 机器链接中继器

中继器是一种能被链接器连接、但自身没有容器的方块。当你不想为了填补空隙而摆一台机器时，可以用它来充当已链接机器之间的填充物。

<RecipeFor id="extended_industrialization:machine_chainer_relay" />
