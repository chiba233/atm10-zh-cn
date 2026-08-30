---
navigation:
  title: "批量处理多方块"
  icon: "processing_array"
  parent: extended_industrialization:machines.md
categories:
  - machines
item_ids:
  - extended_industrialization:large_steam_furnace
  - extended_industrialization:large_steam_macerator
  - extended_industrialization:large_electric_furnace
  - extended_industrialization:large_electric_macerator
  - extended_industrialization:processing_array
---

# 批量处理多方块

某些多方块结构能像同类型的普通机器那样运作，但会给它一次能处理的输入量乘上一个倍数。也就是说，一台能以 Y 份为一批运行某类配方的多方块结构，一次可以消耗 1 到 Y 倍的输入，并按当前的批量大小产出对应的结果。机器消耗的 EU/t 同样会乘上它当前运行的批数。

批量处理多方块能跑多少批各不相同。具体数值请查看该机器物品上的提示。

和其他机器完全一样，它们也无法同时运行一个以上的配方。

## 大型炉

大型电炉能跑多少批，取决于多方块结构中使用的线圈，与电力高炉的搭建方式类似。某种线圈在炉中能提供多大的批量，请查看该线圈的提示。

<Row>
	<RecipeFor id="extended_industrialization:large_steam_furnace" />
	<RecipeFor id="extended_industrialization:large_electric_furnace" />
</Row>

<GameScene zoom="2" interactive={true} fullWidth={true}>
    <MultiblockShape controller="extended_industrialization:large_steam_furnace" />
    <MultiblockShape controller="extended_industrialization:large_electric_furnace" x="-6" y="-1" z="-6" />
</GameScene>

## 大型研磨机

<Row>
	<RecipeFor id="extended_industrialization:large_steam_macerator" />
	<RecipeFor id="extended_industrialization:large_electric_macerator" />
</Row>

<GameScene zoom="2" interactive={true} fullWidth={true}>
    <MultiblockShape controller="extended_industrialization:large_steam_macerator" />
    <MultiblockShape controller="extended_industrialization:large_electric_macerator" x="-6" z="-6" />
</GameScene>

## 处理阵列

处理阵列能批量运行任何放入其界面的单方块电动合成机器的配方。它能跑多大的批量，受自身尺寸以及放入的机器数量限制。

<RecipeFor id="extended_industrialization:processing_array" />

<GameScene zoom="2" interactive={true} fullWidth={true}>
    <MultiblockShape controller="extended_industrialization:processing_array" />
    <MultiblockShape controller="extended_industrialization:processing_array" useBigShape={true} x="-6" z="-8" />
</GameScene>
