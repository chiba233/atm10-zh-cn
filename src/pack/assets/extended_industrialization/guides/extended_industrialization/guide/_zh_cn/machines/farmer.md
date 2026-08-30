---
navigation:
  title: "农耕机"
  icon: "steam_farmer"
  parent: extended_industrialization:machines.md
categories:
  - machines
item_ids:
  - extended_industrialization:steam_farmer
  - extended_industrialization:electric_farmer
---

# 农耕机

<Row>
	<RecipeFor id="extended_industrialization:steam_farmer" />
	<RecipeFor id="extended_industrialization:electric_farmer" />
</Row>

农耕机不是那种运行配方的典型机器，它做的是耕地、保湿土壤、种植、施肥，以及收获作物、植物和树木。这些任务并不是全都得用上农耕机才能工作，事实上有时你反而会想避开其中某些任务。例如在打理树木时，你就不会希望农耕机去耕地或保湿土壤。

能量不足时农耕机不会运转。蒸汽农耕机需要 32 EU/t 的蒸汽，电动农耕机需要 64 EU/t。

农耕机多方块结构中所需的泥土，可以换成任何带有 `#extended_industrialization:farmer_dirt` 标签的方块。

## 任务

### 耕地

在多方块结构的形状设置中启用后，属于该多方块结构的泥土方块会像被锄头锄过一样，转化为耕地。

### 保湿

当农耕机通过输入仓获得水时，它会让所有耕地保持湿润，无需在附近放水。

### 种植

当农耕机的输入仓中有可种植的物品时，它会把它们种到作业范围内任何合适的方块上。只有带 `#extended_industrialization:farmer_plantable` 物品标签的物品才能被种植。

### 施肥

施肥是电动农耕机独有的。当输入仓中提供了可用的流体肥料（可在 EMI 中查看）时，农耕机会对作业范围内的植物施加类似骨粉的效果。这种类似骨粉的效果，对仙人掌、甘蔗这类通常无法使用骨粉的植物同样有效。

### 收获

当有植物已经完全成熟（比如长好的小麦，或是树苗已经长成树），并且输出仓中有足够的存放空间时，它就会被破坏并收进仓里。

带有 `#extended_industrialization:farmer_voidable` 标签的物品在存入输出仓时优先级较低，若在被收获的方块掉落它时已经没有空位，它会被直接丢弃。<ItemLink id="minecraft:stick" /> 和 <ItemLink id="minecraft:apple" /> 就是这类物品的例子——这意味着你可以把输出仓的输出槽位锁定为只放原木和树苗，不必操心怎么存放那些东西。

## 蒸汽农耕机

<GameScene zoom="1" interactive={true} fullWidth={true}>
    <MultiblockShape controller="extended_industrialization:steam_farmer" />
    <MultiblockShape controller="extended_industrialization:steam_farmer" useBigShape={true} x="-10" z="-10" />
</GameScene>

## 电动农耕机

<GameScene zoom="1" interactive={true} fullWidth={true}>
    <MultiblockShape controller="extended_industrialization:electric_farmer" />
    <MultiblockShape controller="extended_industrialization:electric_farmer" useBigShape={true} x="-12" z="-12" />
</GameScene>
