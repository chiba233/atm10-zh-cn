// This File has been authored by AllTheMods Staff, or a Community contributor for use in AllTheMods - AllTheMods 10.
// As all AllTheMods packs are licensed under All Rights Reserved, this file is not allowed to be used in any public packs not released by the AllTheMods Team, without explicit permission.

ItemEvents.modifyTooltips(allthemods => {

    //AllTheModium

    allthemods.add(['allthemodium:allthemodium_ore', 'allthemodium:allthemodium_slate_ore'],[
        Text.of('§7至少需要下界合金级才能挖掘'),
        Text.of('§6生成于深暗之域，且始终以暴露于空气中的方式生成'),
        Text.of('§6亦可在挖矿维度的深板岩层中发现')
    ])
    allthemods.add(['allthemodium:vibranium_ore', 'allthemodium:other_vibranium_ore'],[
        Text.of('§7至少需要ATM合金工具方可挖掘'),
        Text.of('§b可在任意下界生物群系中找到'),
        Text.of('§b也可在异界找到')
    ])
    allthemods.add('allthemodium:unobtainium_ore',[
        Text.of('§7至少需要振金级才能挖掘'),
        Text.of('§d可在末地高地找到')
    ])

    allthemods.add('kubejs:silent_allthemodium_plate',[
        Text.of("§7§o它现在没那么……多话了")
    ])
    allthemods.add('kubejs:silent_vibranium_plate',[
        Text.of("§7§o它现在没那么……多话了")
    ])
    allthemods.add('kubejs:silent_unobtainium_plate',[
        Text.of("§7§o它现在没那么……多话了")
    ])

    allthemods.add('allthemodium:allthemodium_ingot',[
        Text.of("§7§o（挥了挥手）这不是你要找的锭"),
        Text.of("§6去找那块[寂静ATM板]")
    ])
    allthemods.add('allthemodium:vibranium_ingot',[
        Text.of("§7§o（挥了挥手）这不是你要找的锭"),
        Text.of("§6去找那块[寂静振金板]")
    ])
    allthemods.add('allthemodium:unobtainium_ingot',[
        Text.of("§7§o（挥了挥手）这不是你要找的锭"),
        Text.of("§6去找那块[寂静难得素板]")
    ])


    allthemods.add('allthemodium:allthemodium_upgrade_smithing_template',[
        Text.of('§6在远古城市的可疑粘土中发现')
    ])
    allthemods.add('allthemodium:vibranium_upgrade_smithing_template',[
        Text.of('§b可在堡垒遗迹的可疑灵魂沙里找到')
    ])
    allthemods.add('allthemodium:unobtainium_upgrade_smithing_template',[
        Text.of('§d掉落自异界合金地牢图书馆内的试炼刷怪笼')
    ])

    //Forbidden Arcanus
    allthemods.add('forbidden_arcanus:hephaestus_forge_tier_1',[
        Text.of("§c§lShift-右击§r§c §c§l锻造台§r§c，并使用§l洁净粉末"),
        Text.of("§c█ = 镀金雕纹磨制暗黑石（上方放置锻造台）"),
        Text.of("§7█ = 磨制暗黑石"),
        Text.of("§5█§7 = 镀金雕纹磨制暗黑石"),
        Text.of("§6█§7 = 錾制神秘磨制暗黑石"),
        Text.of("§0███§7███§0███"),
        Text.of("§0█§7███§5█§7███§0█"),
        Text.of("§0█§7█§5█§7███§5█§7█§0█"),
        Text.of("§7████§6█§7████"),
        Text.of("§7█§5█§7█§6█§c█§6█§7█§5█§7█"),
        Text.of("§7████§6█§7████"),
        Text.of("§0█§7█§5█§7███§5█§7█§0█"),
        Text.of("§0█§7███§5█§7███§0█"),
        Text.of("§0███§7███§0███")

    ])
    allthemods.add('forbidden_arcanus:clibano_core',[
        Text.of("§c§lShift-右击§r§c §c§l克里巴诺核心§r§c，并使用§c§l洁净粉末"),
        Text.of("§5█§7 = 磨制暗黑石"),
        Text.of("§7█ = 磨制暗黑石砖"),
        Text.of("§6█§7 = 炽炉核心"),
        Text.of("§7从右到左 -> 从下到上"),
        Text.of("§5█§7█§5█§0█§7███§0█§5█§7█§5█"),
        Text.of("§7███§0█§7█§0█§7█§0█§7███"),
        Text.of("§5█§7█§5█§0█§7█§6█§7█§0█§5█§7█§5█"),
    ])
    allthemods.add('forbidden_arcanus:growing_edelwood',[
        Text.of("§4可从流浪商人处获得"),
        Text.of("§4或对橡树树苗使用腐化灵魂获得"),
    ])
    allthemods.add('forbidden_arcanus:magnetized_darkstone_pedestal',[
        Text.of("§7在暗黑石基座上使用铁磁性混合物"),
    ])
    allthemods.add('forbidden_arcanus:soul',[
        Text.of("§7对灵魂沙使用灵魂提取器"),
        Text.of("§7极少生成于世界中"),
    ])
    allthemods.add('forbidden_arcanus:enchanted_soul',[
        Text.of("§7对普通灵魂使用喷溅型辉光瓶")
    ])
    allthemods.add('forbidden_arcanus:corrupt_soul',[
        Text.of("§7击杀生物时极少生成")
    ])
    allthemods.add('forbidden_arcanus:blood_test_tube',[
        Text.of("§7副手持试管，然后击杀生物")
    ])
    allthemods.add('forbidden_arcanus:xpetrified_orb',[
        Text.of("§7只能通过黑洞获得"),
        Text.of("§7制作黑洞：将暗物质与腐化粉末一同投掷于地面"),
        Text.of("§7为其注入足够经验，使其吐出一个石化经验球")
    ])
    allthemods.add('forbidden_arcanus:dragon_scale',[
        Text.of("§7由末影龙掉落")
    ])
    allthemods.add('forbidden_arcanus:stella_arcanum',[
        Text.of("§7极罕见地生成于Y=-44至Y=42之间"),
        Text.of("§c挖掘时会爆炸！")
    ])
    allthemods.add(/forbidden_arcanus:runic_[sd]/,[
        Text.of("§7生成于世界底层，最高至Y=2"),
    ])
    allthemods.add(['forbidden_arcanus:arcane_crystal_ore', 'forbidden_arcanus:deepslate_arcane_crystal_ore'],[
        Text.of("§7极罕见地生成于Y=-40至Y=14之间"),
        Text.of("§7在 Y=-13 最常见")
    ])
    allthemods.add('forbidden_arcanus:artisan_relic',[
        Text.of("§a可在盔甲匠、工具匠或武器匠村民的房屋中找到"),
    ])
    allthemods.add('forbidden_arcanus:crescent_moon',[
        Text.of("§c不可获得"),
    ])
    allthemods.add('forbidden_arcanus:crimson_stone',[
        Text.of("§a可在掠夺者前哨站中找到"),
    ])
    allthemods.add('forbidden_arcanus:soul_crimson_stone',[
        Text.of("§c使用 1 次后会变成绯红之石"),
    ])
    allthemods.add('forbidden_arcanus:elementarium',[
        Text.of("§a可在丛林神庙、沙漠神殿及海底废墟中找到"),
    ])
    allthemods.add('forbidden_arcanus:divine_pact',[
        Text.of("§a可在异界的村庄和金字塔中找到"),
    ])
    allthemods.add('forbidden_arcanus:maledictus_pact',[
        Text.of("§a可在藏宝堡垒中找到"),
    ])

    //Mystical Agriculture
    allthemods.add(/mysticalagriculture:.*watering_can/,[
        Text.of("§c对假玩家无效"),
        Text.of("§c（如模块化路由器、点击器等方块）")
    ])

    allthemods.add('toolbelt:belt', [
        Text.of("§7拥有专属插槽可供放置"),
        Text.of("§7检查快捷键设置中的“打开传送带物品栏”绑定")
    ])

	//Easy Villagers
    allthemods.add(['easy_villagers:trader', 'easy_villagers:auto_trader'], [
        Text.of("§a使用对应职业站点方块右击，将其放入并启用交易补货")
    ])

	//Hyperbox
    if (Platform.isLoaded("hyperbox")) {
        allthemods.add('hyperbox:hyperbox', [
            Text.of("§a该模组将在6.0+版本中移除！")
        ])
    }

    //Eternal Starlight
    if (Platform.isLoaded("eternal_starlight")) {
        allthemods.add('eternal_starlight:loot_bag[eternal_starlight:loot_table="eternal_starlight:bosses/lunar_monstrosity"]', [
            Text.of('这个战利品袋来自“月藤巨物”。')
        ])
    }

    if (Platform.isLoaded('modular_machinery_reborn')) {
        allthemods.add('modular_machinery_reborn:controller[modular_machinery_reborn:machine="atm:runic_crucible"]', [
            Text.of('§c警告：该机器已被弃用。'),
            Text.of('请使用工作台转换为新版本。')
        ])
        allthemods.add('modular_machinery_reborn:controller[modular_machinery_reborn:machine="atm:runic_star_altar"]', [
            Text.of('§c警告：该机器已被弃用。'),
            Text.of('请使用工作台转换为新版本。')
        ])
        allthemods.add('modular_machinery_reborn:controller[modular_machinery_reborn:machine="atm:runic_enchanter"]', [
            Text.of('§c警告：该机器已被弃用。'),
            Text.of('请使用工作台转换为新版本。')
        ])
        allthemods.add('modular_machinery_reborn:controller[modular_machinery_reborn:machine="atm:auto_hepheastus_forge"]', [
            Text.of('§c警告：该机器已被弃用。'),
            Text.of('请使用工作台转换为新版本。')
        ])
    }
	// Apotheosis Gateway Warning
	allthemods.add([
	'gateways:gate_pearl[gateways:gateway="apotheosis:tiered/frontier"]',
	'gateways:gate_pearl[gateways:gateway="apotheosis:tiered/ascent"]',
	'gateways:gate_pearl[gateways:gateway="apotheosis:tiered/summit"]',
	'gateways:gate_pearl[gateways:gateway="apotheosis:tiered/pinnacle"]'],
	[
		Text.of("§c警告：在以下维度之外，第3波时将发生内爆："),
		Text.of("§c主世界、下界、末地、暮色森林")
	])
	// Botany Pot Sculk
	allthemods.add([
	"minecraft:sculk",
	"minecraft:sculk_sensor",
	"minecraft:sculk_catalyst",
	"minecraft:sculk_vein",
	"minecraft:sculk_shrieker",
	"deeperdarker:gloomy_sculk",
	"deeperdarker:gloomy_grass",
	"deeperdarker:glowing_flowers",
	"deeperdarker:sculk_vines",
	"deeperdarker:glowing_roots",
	"deeperdarker:bloom_berries",
	"deeperdarker:glowing_grass",
	"deeperdarker:sculk_tendrils"],
	[
		Text.of("§9在植物盆中：需使用附有精准采集魔咒的锄头方可收获")
	])
})


// This File has been authored by AllTheMods Staff, or a Community contributor for use in AllTheMods - AllTheMods 10.
// As all AllTheMods packs are licensed under All Rights Reserved, this file is not allowed to be used in any public packs not released by the AllTheMods Team, without explicit permission.
