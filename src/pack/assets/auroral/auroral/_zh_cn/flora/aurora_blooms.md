---
item_ids:
  - auroral:aurora_bloom
  - auroral:aurora_bloom_decorative
  - auroral:frozen_petals
navigation:
  title: 极光花苞
  icon: auroral:frozen_petals
  parent: index.md
  position: 30
---

# <Color id="gold">极光花苞</Color>

<Column alignItems="center" fullWidth={true}>
  <ItemImage id="aurora_bloom" scale="2" />

  极光期间在雪上自行冒出的魔法花朵。它是<ItemLink id="frozen_petals" />的来源，也是本模组绝大部分内容的入口。
</Column>

<ItemImage id="minecraft:air" scale="0.25"/>
***

<Column alignItems="center" fullWidth={true}>
  ## <Color id="gold">寻找极光花苞</Color>
</Column>

极光期间，极光花苞会在寒冷生物群系的地表自然生成。它要经过**四个阶段**才完全成熟。极光结束时还留在原地的花苞，会在日出时枯萎。

可供生成与存活的表面：

* 雪（要求下方那格本身也是合格的积雪表面，这样雪化了以后花苞才不会孤零零地留在泥土或石头上）
* 雪块
* 细雪（见下）
* 冰、浮冰与蓝冰（冻洋的表面可以）
* <ItemLink id="shimmering_ice" />

<Row>
  <ItemImage id="aurora_bloom" />
  ### <Color id="aqua">陷在雪里的花苞</Color>
</Row>

花苞种在**雪**上或长在**细雪**里时，会记住那种雪的类型。花苞被打掉或枯萎后，原来的雪会照原样回到那一格——是雪就还是雪，是细雪就还是细雪。被埋住的花苞会在上方冒出细细一缕雪花粒子，所以就算上面又积了雪也仍然找得到。

<ItemImage id="minecraft:air" scale="0.25"/>
***

<Column alignItems="center" fullWidth={true}>
  ## <Color id="gold">收获</Color>
</Column>

打掉完全成熟（第 3 阶段）的极光花苞会掉落：

* <ItemLink id="frozen_petals" />（带时运时为 1～4 个）
* **活的极光花苞**本身，可以再种回去
* 在此之上还有 **15% 的几率**多掉一株活花苞

打掉未成熟的花苞什么都不给——耐心才有回报。

<ItemImage id="minecraft:air" scale="0.25"/>
***

<Column alignItems="center" fullWidth={true}>
  ## <Color id="gold">保存花苞（精准采集）</Color>
</Column>

用带**精准采集**的工具打掉完全成熟的极光花苞，得到的不是冰冻花瓣，而是**装饰用极光花苞**。这个装饰变种：

* 日出时不会枯萎——它会一直留着
* 外观固定停在第 3 阶段
* 可以放进**花盆**里展示
* 打掉时掉落自身，所以可以随处复制

这是把极光花苞留到极光之外的唯一办法。

<ItemImage id="minecraft:air" scale="0.25"/>
***

<Column alignItems="center" fullWidth={true}>
  ## <Color id="gold">冰冻花瓣的用途</Color>
</Column>

* **粗制的药水** —— 在任意酿造台里像地狱疣一样把水瓶酿成粗制的药水
* <ItemLink id="cold_brewing_stand" /> —— 与辉光钢锭合成
* <ItemLink id="glow_leek_seeds" /> —— 与小麦种子合成
* <ItemLink id="frosted_cookies" /> —— 带着魔法微光的甜点
* <ItemLink id="aurora_shard" /> —— 在光环等级 1 的冰川盆地里灌注

<RecipeFor id="glow_leek_seeds" />

<ItemImage id="minecraft:air" scale="0.25"/>
***

<Column alignItems="center" fullWidth={true}>
  ## <Color id="gold">末影化</Color>
</Column>

<Row>
  <ItemImage id="aurora_ender_shard" />
  ### <Color id="aqua">用末影珍珠右键</Color>
</Row>

手持**末影珍珠**右键点击极光花苞，它会变成同一生长阶段的<ItemLink id="ender_bloom" />，珍珠在此过程中被消耗。完整的生长周期见[末影花苞](ender_bloom.md)。
