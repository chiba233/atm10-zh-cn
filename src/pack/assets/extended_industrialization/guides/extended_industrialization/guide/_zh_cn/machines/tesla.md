---
navigation:
  title: "特斯拉"
  icon: "tesla_coil"
  parent: extended_industrialization:machines.md
categories:
  - machines
item_ids:
  - extended_industrialization:tesla_calibrator
  - extended_industrialization:tesla_handheld_receiver
  - extended_industrialization:tesla_interdimensional_upgrade
  - extended_industrialization:tesla_coil
  - extended_industrialization:tesla_receiver
  - extended_industrialization:lv_tesla_receiver_hatch
  - extended_industrialization:mv_tesla_receiver_hatch
  - extended_industrialization:hv_tesla_receiver_hatch
  - extended_industrialization:ev_tesla_receiver_hatch
  - extended_industrialization:superconductor_tesla_receiver_hatch
  - extended_industrialization:tesla_tower
  - extended_industrialization:aluminum_tesla_winding
  - extended_industrialization:annealed_copper_tesla_winding
  - extended_industrialization:copper_tesla_winding
  - extended_industrialization:electrum_tesla_winding
  - extended_industrialization:superconductor_tesla_winding
---

# 特斯拉

特斯拉线圈与接收器让你能以一定代价无线传输 EU。一个特斯拉网络只能有一个发射器（特斯拉线圈或特斯拉电塔），对特斯拉接收器的数量则没有固有限制。每种发射器都有各自的范围和被动损耗代价。

## 特斯拉校准器

要把特斯拉发射器和接收器链接起来，先手持特斯拉校准器，对发射器按 **<KeyBind id="key.sneak" />** + **<KeyBind id="key.use" />**。然后手持校准器对任意接收器按 **<KeyBind id="key.use" />**，即可完成链接。

<RecipeFor id="extended_industrialization:tesla_calibrator" />

## 特斯拉发射器

特斯拉发射器是每个特斯拉网络的源头。

发射器无法把能量传给电压不完全一致的接收器。举个例子，装了进阶机器框架的特斯拉线圈无法传给没有框架的特斯拉接收器，但可以传给同样装了进阶机器框架的那一个。

特斯拉线圈的被动 EU/t 损耗代价，由放入其中的框架电压决定（不放则另算）。

<RecipeFor id="extended_industrialization:tesla_coil" />

特斯拉电塔传输的电压，由所用的能量输入仓决定。

特斯拉电塔的被动 EU/t 损耗代价、传输上限和范围，由所用的绕组决定。每种绕组的具体数值写在它们各自的提示里。

<Row>
	<GameScene zoom="0.75" interactive={true} fullWidth={false}>
		<MultiblockShape controller="extended_industrialization:tesla_tower" />
	</GameScene>
	<RecipeFor id="extended_industrialization:tesla_tower" />
</Row>

## 特斯拉接收器

特斯拉接收器是你从发射器传出的能量的目的地。

特斯拉接收器会储存收到的能量，并从它的输出面排出。也可以像对待其他任何能量输出方块那样，用电缆从它那里抽取能量。

<RecipeFor id="extended_industrialization:tesla_receiver" />

特斯拉接收仓接收能量的方式与普通的特斯拉接收器相同，但它同时充当多方块结构的能量输入仓。它把两者合二为一，省得你既要一个接收器、又要一个能量输入仓来接收它排出的能量。

<RecipeFor id="extended_industrialization:lv_tesla_receiver_hatch" />
