---
item_ids:
  - auroral:ender_bloom
  - auroral:aurora_ender_shard
navigation:
  title: 末影花苞
  icon: auroral:aurora_ender_shard
  parent: index.md
  position: 33
---

# <Color id="gold">末影花苞</Color>

<Column alignItems="center" fullWidth={true}>
  <ItemImage id="ender_bloom" scale="2" />

  极光花苞被末影气息浸染后的表亲——紫色、不安分，还是一条可再生的末影珍珠来源。
</Column>

<ItemImage id="minecraft:air" scale="0.25"/>
***

<Column alignItems="center" fullWidth={true}>
  ## <Color id="gold">制作</Color>
</Column>

末影花苞不会自行生成。要得到一株：

1. 在极光事件期间找到或种出一株<ItemLink id="aurora_bloom" />。
2. 手持**末影珍珠**右键点击这株花苞。
3. 花苞会变成同一生长阶段的末影花苞，珍珠被消耗。

<ItemImage id="minecraft:air" scale="0.25"/>
***

<Column alignItems="center" fullWidth={true}>
  ## <Color id="gold">长期存在</Color>
</Column>

与极光花苞不同，末影花苞**永远留着**。它不会在日出时枯萎，极光结束后也照样在。

<ItemImage id="minecraft:air" scale="0.25"/>
***

<Column alignItems="center" fullWidth={true}>
  ## <Color id="gold">生长条件</Color>
</Column>

末影花苞只有种在下列方块上才会推进生长阶段：

* <ItemLink id="shimmer_soil" />
* **末地石**

种在其他能支撑它的方块上时，它可以无限期存活，但会一直停在种下时的那个阶段。除非种在上面两种方块之一，否则骨粉也没有效果。

<ItemImage id="minecraft:air" scale="0.25"/>
***

<Column alignItems="center" fullWidth={true}>
  ## <Color id="gold">收获</Color>
</Column>

在**任意**阶段打掉末影花苞，都会掉落一个末影花苞物品（重新种下时总是从第 0 阶段开始）。

在第 3 阶段打掉时，**还会**额外掉落：

* 一个<ItemLink id="aurora_ender_shard" />
* **5% 的几率**再多掉一株末影花苞

<ItemImage id="minecraft:air" scale="0.25"/>
***

<Column alignItems="center" fullWidth={true}>
  ## <Color id="gold">极光末影碎片</Color>
</Column>

<Row>
  <ItemImage id="aurora_ender_shard" />
  ### <Color id="aqua">可再生的末影珍珠</Color>
</Row>

两个极光末影碎片可以合成回一颗末影珍珠。一座成熟的末影花苞农场就是一条可再生的末影珍珠来源。

<Recipe id="auroral:ender_pearl_from_shards" />
