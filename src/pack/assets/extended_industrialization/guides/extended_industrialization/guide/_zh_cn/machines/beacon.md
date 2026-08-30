---
navigation:
  title: "电力信标"
  icon: "electric_beacon"
  parent: extended_industrialization:machines.md
categories:
  - machines
item_ids:
  - extended_industrialization:electric_beacon
---

# 电力信标

<RecipeFor id="extended_industrialization:electric_beacon" />

电力信标消耗药水，以每种效果 256 EU/t 的代价，把效果提供给附近所有玩家。一瓶药水在信标里能持续多久，取决于它最短的那个效果，再减半。多数情况下药水只有一种效果。举个例子，一瓶 8 分钟的迅捷药水被信标消耗后，会在范围内提供总共 4 分钟的效果，代价是 256 EU/t。同样地，一瓶 40 秒的龟仙人药水只能维持 20 秒，却要花 512 EU/t，因为它有两种效果（缓慢和抗性提升）。由于药水会被信标消耗掉，建议用[酿造机](brewery.md)搭一套自动化循环，好让信标一直运转下去。

信标的范围比普通信标更大，由它下方的层数决定（不含钢制机器外壳）。

| 层数 | 范围 |
|------|------|
| 1    | 30   |
| 2    | 50   |
| 3    | 70   |
| 4    | 90   |

<GameScene zoom="1.5" interactive={true} fullWidth={true}>
    <MultiblockShape controller="extended_industrialization:electric_beacon" />
    <MultiblockShape controller="extended_industrialization:electric_beacon" useBigShape={true} x="-9" y="2" z="-9" />
</GameScene>
