---
navigation:
  title: 原油处理
  icon: modern_industrialization:diesel_bucket
  position: 109
  parent: modern_industrialization:electric_age.md
item_ids:
- modern_industrialization:oil_drilling_rig
- modern_industrialization:mv_diesel_generator
---

# 原油处理

<GameScene zoom="1.5" interactive={true} fullWidth={true}>
    <MultiblockShape controller="oil_drilling_rig" />
</GameScene>

石油钻机是一种巨大的多方块结构，可以使用钻头在基岩下方开采原油。没错，本质上它就是一台石油采石场。石油加工会带来大量副产物和能量！

<Recipe id="modern_industrialization:oil/oil_drilling_rig_asbl" />

如你放置控制器并手持扳手所见，这个多方块结构由以下部分构成：钢制机器外壳、钢管道方块和链锁。各种仓口都可以替换成钢制机器外壳，但请务必至少保留物品输入仓、流体导出模块和能源输入仓！

原油可以被转化为各种燃料，并用于更高效地生产橡胶垫。

柴油发电机可以燃烧多种燃料，你可以在 REI 中查看每种燃料能产生多少 EU。这些燃料在柴油发电机中产生的 EU 会翻倍。柴油发电机最高可产出 256 EU/t，并且只能连接中压导线。

<Recipe id="modern_industrialization:electric_age/machine/mv_diesel_generator_asbl" />

柴油发电机只会在需要时消耗燃料，但如果你需要持续稳定地供应能量，也可以把液体燃料放进大型蒸汽锅炉里，而不是使用物品燃料。

一台完全预热的大型蒸汽锅炉，使用相同数量的燃料时，产能大约只有柴油发电机的一半。
