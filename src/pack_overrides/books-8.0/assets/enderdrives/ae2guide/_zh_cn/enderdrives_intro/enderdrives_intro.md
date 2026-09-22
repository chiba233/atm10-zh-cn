---
navigation:
  parent: enderdrives_intro/enderdrives_intro-index.md
  title: 末影物品存储元件
  icon: enderdrives:ender_disk_1k
categories:
- enderdrives
item_ids:
- enderdrives:ender_disk_1k
- enderdrives:ender_disk_4k
- enderdrives:ender_disk_16k
- enderdrives:ender_disk_64k
- enderdrives:ender_disk_256k
- enderdrives:ender_disk_creative
- enderdrives:ender_fluid_disk_1k
- enderdrives:ender_fluid_disk_4k
- enderdrives:ender_fluid_disk_16k
- enderdrives:ender_fluid_disk_64k
- enderdrives:ender_fluid_disk_256k
- enderdrives:ender_fluid_disk_creative
---

# 末影驱动器

末影驱动器是强大的驱动器，允许通过频率在各个 ME 系统、维度，甚至不同玩家之间实现全局同步存储。

<Row gap="10">
  <Column>
    <ItemImage id="enderdrives:ender_disk_1k" />
  </Column>
  <Column>
    <ItemLink id="enderdrives:ender_disk_1k" />
  </Column>
</Row>

<Row gap="10">
  <Column>
    <ItemImage id="enderdrives:ender_disk_4k" />
  </Column>
  <Column>
    <ItemLink id="enderdrives:ender_disk_4k" />
  </Column>
</Row>

<Row gap="10">
  <Column>
    <ItemImage id="enderdrives:ender_disk_16k" />
  </Column>
  <Column>
    <ItemLink id="enderdrives:ender_disk_16k" />
  </Column>
</Row>

<Row gap="10">
  <Column>
    <ItemImage id="enderdrives:ender_disk_64k" />
  </Column>
  <Column>
    <ItemLink id="enderdrives:ender_disk_64k" />
  </Column>
</Row>

<Row gap="10">
  <Column>
    <ItemImage id="enderdrives:ender_disk_256k" />
  </Column>
  <Column>
    <ItemLink id="enderdrives:ender_disk_256k" />
  </Column>
</Row>

<Row gap="10">
  <Column>
    <ItemImage id="enderdrives:ender_fluid_disk_1k" />
  </Column>
  <Column>
    <ItemLink id="enderdrives:ender_fluid_disk_1k" />
  </Column>
</Row>

<Row gap="10">
  <Column>
    <ItemImage id="enderdrives:ender_fluid_disk_4k" />
  </Column>
  <Column>
    <ItemLink id="enderdrives:ender_fluid_disk_4k" />
  </Column>
</Row>

<Row gap="10">
  <Column>
    <ItemImage id="enderdrives:ender_fluid_disk_16k" />
  </Column>
  <Column>
    <ItemLink id="enderdrives:ender_fluid_disk_16k" />
  </Column>
</Row>

<Row gap="10">
  <Column>
    <ItemImage id="enderdrives:ender_fluid_disk_64k" />
  </Column>
  <Column>
    <ItemLink id="enderdrives:ender_fluid_disk_64k" />
  </Column>
</Row>

<Row gap="10">
  <Column>
    <ItemImage id="enderdrives:ender_fluid_disk_256k" />
  </Column>
  <Column>
    <ItemLink id="enderdrives:ender_fluid_disk_256k" />
  </Column>
</Row>

<Row gap="10">
  <Column>
    <ItemImage id="enderdrives:ender_fluid_disk_creative" />
  </Column>
  <Column>
    <ItemLink id="enderdrives:ender_fluid_disk_creative" />
  </Column>
</Row>

---

## 工作原理
每个末影驱动器都配置有频率、范围和模式。
- **频率**：具有相同频率的驱动器共享同一个容器。
- **范围**：决定谁可以访问该驱动器（全局、私有或队伍）。
- **模式**：控制物品流动方式（双向、输入、输出）。

所有具有相同频率和作用域的驱动器都会访问**同一个虚拟容器**，无论它们位于何处。

---

## 类型上限
不同于传统的 AE2 驱动器，末影驱动器的限制仅基于类型数。由于物品在后端的存储方式，其唯一的硬性限制就是类型数量。也就是说，每种类型你实际上最多可以存储 2^63 - 1，也就是 9,223,372,036,854,775,807 个物品。不过要注意，驱动器在该频率下存储的物品越多，耗电也会越高！

每个服务器开始产生压力的类型数量都不同。你可以使用 autobenchmark 命令来测试你的服务器。为了得到准确结果，你需要打开一个终端，并在所选频率下放置一个作用域设为 Private 的驱动器。测试会一直进行，直到 TPS 降到 18 以下。这可能需要几分钟。

我个人的平均值大约是 275,000 种。275,000/255 ≈ 1078。这意味着我得把 107.8 个 ME 驱动器装满 256k 末影驱动器和已分类物品之后，才会开始看到性能问题。我也见过更高或更低的建议最大类型数。这个上限由同一世界中所有使用这些驱动器的玩家共享。

---

## 磁盘驱动器模式
每个磁盘驱动器都可以设置为以下三种**传输模式**之一：

- ![PEGui1](../pic/transport_bidirectional_alt.png) **双向** _（默认）_
  标准的 ME 驱动器行为。可自由插入和提取物品。


- ![PEGui1](../pic/transport_input_alt.png) **仅输入**
  物品可以插入，但无法取出。适用于缓冲或同步输入。


- ![PEGui1](../pic/transport_output_alt.png) **仅输出**
  物品可以被提取，但不能插入。非常适合作为输出缓冲区或只读访问。

---

## 范围与隐私

每个驱动器还有一个**作用域**，用于控制谁可以访问其中的容器：
-  **全局** _（默认）_
   公开！任何使用相同频率的玩家都可以访问这个共享容器。


-  **私有**
  与你的 UUID 绑定。只有你可以创建用于访问该频率的驱动器。你的 ME 系统中的其他用户仍然可以访问这个存储


-  **队伍**
  与你的 FTB队伍 共享。所有成员都可以创建能够访问同一频率的驱动器。
