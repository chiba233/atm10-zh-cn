---
navigation:
  title: "多方块建造器"
  icon: "terminal"
  parent: "items/items-index.md"
  position: 1
item_ids:
  - terminal
---

# 多方块建造器

<RecipesFor id="terminal" />

多方块建造器可以帮你建造、复制、粘贴和拆除现代工业化的多方块结构。

## 模式

按 <KeyBind id="key.industrialization_overdrive.terminal_mode_switch" /> 在可用模式之间循环切换：

- **搭建**：补齐 MI 多方块缺少的部件。拿着建造器潜行右击多方块控制器，就会自动搭好。
- **复制／粘贴**：复制和粘贴完整的多方块结构。潜行右击已成形的多方块控制器复制结构，再对一个方块使用即可粘贴。
- **拆除**：拆掉已成形的多方块，把部件还给你。

## 复制与粘贴
复制／粘贴模式会尽量保留机器配置，包括朝向、物品与流体的自动提取、槽位锁定、升级、机壳，以及支持的其他模组的专属设置。

粘贴时，结构会按你面朝的方向旋转。对方块的侧面使用建造器，结构就放在它旁边。潜行时，目标方块会被当作结构下方的地面。

## 材料

搭建或粘贴结构前，建造器会先检查你的物品栏。
<OptionalSection modId="ae2">
它也可以通过<ItemLink id="ae2:wireless_access_point"/>链接到 ME 网络，从网络里取缺少的部件。
</OptionalSection>

<OptionalSection modId="extended_industrialization">
## 扩展工业化

潜行复制<ItemLink id="extended_industrialization:machine_chainer"/>时，会把它连接的机器、嵌套的机器链接器和带标签的中继方块一起复制。

配置项 `machine_chainer_copy_depth` 控制嵌套路径复制多深：
- `-1`：不限深度。
- `0`：不复制机器链接器。
- 正数：限制嵌套链接器路径的层数。
</OptionalSection>
