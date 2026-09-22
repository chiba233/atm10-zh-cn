---
navigation:
  title: "大型蒸汽锅炉"
  icon: "modern_industrialization:large_steam_boiler"
  position: 103
  parent: modern_industrialization:electric_age.md
item_ids:
  - modern_industrialization:large_steam_boiler
  - modern_industrialization:bronze_plated_bricks
  - modern_industrialization:bronze_machine_casing_pipe
  - modern_industrialization:heatproof_machine_casing
---

# 大型蒸汽锅炉

<GameScene zoom="2" interactive={true} fullWidth={true}>
    <MultiblockShape controller="large_steam_boiler" />
</GameScene>

大型蒸汽锅炉是较小型的青铜和钢锅炉的升级版本。其燃料消耗速度是熔炉的8倍，但在完全加热时能以256 mB/t的速度产生蒸汽。大型蒸汽锅炉燃烧物品燃料（如煤炭）时还能产生两倍的能量，但燃烧流体燃料时没有这项增益。

<Recipe id="modern_industrialization:electric_age/machine/large_steam_boiler_asbl" />

与单方块版本不同，在大型蒸汽锅炉中，任何未消耗热量的80%都会损失掉。这意味着，当输出功率降至最大值以下时，燃料消耗产生的能量比例将大幅下降。这种情况会在锅炉未以最大输出功率持续运行时发生。

主要方块是镀青铜砖块，但你还需要青铜管道机器外壳和耐热机器外壳。

<Recipe id="modern_industrialization:electric_age/casing/bronze_plated_bricks_asbl" />



<Recipe id="modern_industrialization:steam_age/bronze/casing_pipe_asbl" />

<Recipe id="modern_industrialization:electric_age/casing/heatproof_machine_casing_asbl" />

大型蒸汽锅炉由一层耐热机器外壳和三层镀青铜砖块组成。

控制器放在第二层（即镀青铜砖块的第一层）。

中间的两个方块是青铜管道机器外壳。

仓室必须放在底层。
