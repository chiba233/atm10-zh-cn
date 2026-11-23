# -*- coding: utf-8 -*-
# atm10-zh-cn — All the Mods 10 简体中文汉化补丁「绿油油版」
# Copyright (C) 2026 星野夢華 (Hoshino Yumeka)
# SPDX-License-Identifier: GPL-3.0-or-later
"""资源蜜蜂汉化生成器：从唯一来源生成客户端与服务端脚本。

来源：src/pack/assets/productivebees/lang/zh_cn.json 的 entity.productivebees.* 键，不在别处另写蜂名表。

产出（都在出货树 build/common/ 里，不入 git）：
  kubejs/client_scripts/pb_hanhua_tooltip.js       显示层（tooltip、名牌）
  kubejs/server_scripts/pb_hanhua_cage_migrate.js  数据迁移（按 ID 查译名）
  build/snapshots/pb_upstream_en_us.json           上游 en_us 快照（离线重跑用）

规则：
  - 服务端数据保持上游英文和 ID，注入中文会与 JEI、配方对不上。
  - 玩家自定义名（命名牌、铁砧）不许改：服务端迁移与客户端名牌翻译都只处理 PB_SYS 里
    系统会生成的完整名字。系统从不生成裸 TitleCase 单词（Amber、Diamond 等），所以不收。
  - JS 查表一律用 hasOwnProperty，防止 Object.prototype 上的键穿透
    （玩家命名为 'constructor'、'toString' 时能穿透 `in`）。
  - 上游 en_us 里重名的英文（两只蜂都叫 'Amber Bee'）不进显示映射表，显示英文也不能张冠李戴。
    数据迁移按 ID，不受影响。
  - 显示层的类型行只做整段精确匹配。

用法: python3 scripts/gen_pb_hanhua.py [PB jar 路径 | en_us 快照.json]
      不给参数就用 ATM_PACK_ROOT/mods/productivebees-*.jar
"""
import json
import os
import sys
from pathlib import Path

from paths import COMMON, PACK, snapshot
ROOT = Path(__file__).resolve().parent.parent
PACK_LANG = PACK / 'assets/productivebees/lang/zh_cn.json'
SHINY_LANG = PACK / 'assets/shiny/lang/zh_cn.json'
SNAPSHOT = snapshot('pb_upstream_en_us.json')

# 用过后被否掉的中文译名，统一换成现行译名（都是 fbi 蜂的旧译）
LEGACY_ZH = ['联调蜂', '神蜂特工队', 'fbi蜜蜂']
LEGACY_ZH_TARGET_ID = 'fbi'


def title_case(base: str) -> str:
    return ' '.join(w.capitalize() for w in base.split('_') if w)


def main() -> None:
    if len(sys.argv) >= 2:
        src = Path(sys.argv[1])
    else:
        # 不给参数就去 ATM_PACK_ROOT/mods 里认那个 jar（generate_all.sh 走这条）
        root = os.environ.get('ATM_PACK_ROOT')
        cand = sorted((Path(root) / 'mods').glob('productivebees-*.jar')) if root else []
        if not cand:
            sys.exit('用法: gen_pb_hanhua.py <productivebees jar 路径 | en_us 快照.json>\n'
                     '      或设好 ATM_PACK_ROOT，让它自己去 mods/ 里认 productivebees-*.jar')
        src = cand[-1]
        print('  用 %s' % src.name)
    if src.suffix == '.json':
        en = json.loads(src.read_text(encoding='utf-8'))
    else:
        import zipfile
        jar = zipfile.ZipFile(src)
        full = json.loads(jar.read('assets/productivebees/lang/en_us.json'))
        en = {k: v for k, v in full.items() if k.startswith('entity.productivebees.')}
        SNAPSHOT.write_text(json.dumps(en, ensure_ascii=False, indent=1), encoding='utf-8')
    pack = json.loads(PACK_LANG.read_text(encoding='utf-8'))

    # 权威表: base id -> 中文名（来自资源包）
    id2zh = {}
    for key, zh in pack.items():
        if not key.startswith('entity.productivebees.'):
            continue
        bid = key[len('entity.productivebees.'):]
        base = bid[:-4] if bid.endswith('_bee') else bid
        if base in ('bee_configurable',) or '%' in zh:
            continue
        id2zh[base] = zh

    # 非实体的基因类型（配方里会把物品 id 当基因类型显示），显示名取自物品键
    for base, item_key in {'bee_bomb': 'item.productivebees.bee_bomb'}.items():
        if item_key in pack:
            id2zh[base] = pack[item_key]

    # 英文名候选（真名 + TitleCase 派生），按英文串聚合以检测歧义
    en_candidates = {}
    def cand(env, zh):
        en_candidates.setdefault(env, set()).add(zh)
    for base, zh in id2zh.items():
        if base == 'bee':
            continue  # 裸 'Bee' 由 "(Bee)" 整名规则单独处理
        cand(title_case(base) + ' Bee', zh)
    for key, env in en.items():
        bid = key[len('entity.productivebees.'):]
        base = bid[:-4] if bid.endswith('_bee') else bid
        if '%' in env or len(env) < 4:
            continue
        if base in id2zh:
            cand(env, id2zh[base])
    en2zh, ambiguous = {}, []
    for env, zhs in en_candidates.items():
        if len(zhs) == 1:
            en2zh[env] = next(iter(zhs))
        else:
            ambiguous.append((env, sorted(zhs)))

    # 类型行专用表（无 Bee 后缀 TitleCase，仅"类型: X (N%)"整段匹配用，不进通用正则）
    type2zh = {title_case(base): zh for base, zh in id2zh.items() if base != 'bee'}

    zh_alias = {old: id2zh[LEGACY_ZH_TARGET_ID] for old in LEGACY_ZH}

    # 迁移表: NBT entity/type 完整 id -> 中文名
    bid2zh = {}
    for base, zh in id2zh.items():
        bid2zh['productivebees:' + base] = zh
        bid2zh['productivebees:' + base + '_bee'] = zh
    bid2zh['minecraft:bee'] = pack.get('entity.minecraft.bee', '蜜蜂')

    # 例外：shiny 给原版蜜蜂做的闪光变体不是资源蜜蜂（蜂笼 NBT 里 isProductiveBee: 0b、
    # entity: "shiny:shiny_bee"），但会被抓进资源蜜蜂的蜂笼。
    #
    # 必须放在这张表（服务端），不能放在 en2zh（客户端 tooltip）：蜂笼名写在 custom_data.name
    # 里，以服务端为准。服务端包只有 server_scripts，客户端替换在服务器上不存在，而且客户端替换
    # 会让屏幕上照样显示中文，服务端没生效也看不出来。
    #
    # 只处理这一只：该 mod 的 en_us 有 132 个实体键，*_bee 只有这一条，其余都是原版生物的闪光
    # 变体，它的 class 里没有文件提到 productivebees。译名从资源包取。
    shiny_zh = json.loads(SHINY_LANG.read_text(encoding='utf-8')).get('entity.shiny.shiny_bee')
    if not shiny_zh:
        sys.exit('❌ %s 里没有 entity.shiny.shiny_bee，闪光蜜蜂的蜂笼名会显示英文'
                 % SHINY_LANG.relative_to(ROOT))
    bid2zh['shiny:shiny_bee'] = shiny_zh

    # 同一只蜂在基因样本、蜂蜜零食里还会出现在 productivebees.information.attribute.type
    # （Type: %s）这一行，%s 是基因的 value。value 决定这份基因属于哪种蜂，育种与基因索引机
    # 依赖它，数据迁移只能改纯显示字段，所以这一处只在客户端替换显示。蜂笼改的是
    # custom_data.name（纯显示），两者不冲突。
    #
    # 按名字整串替换，不放宽形态 3 的正则：形态 3 的字符类不含 ':' 与 '_'，放宽会让已有的
    # 467 条一起进入新的匹配范围，为一只蜂承担全局风险。
    extra_id2zh = {'shiny:shiny_bee': shiny_zh}

    # 安全集合只收系统会生成的完整名字，不收裸 TitleCase 单词。
    sys_names = set()
    for base, zh in id2zh.items():
        sys_names.add(zh)
        sys_names.add(title_case(base) + ' Bee')
        sys_names.add('productivebees:' + base)
        sys_names.add('productivebees:' + base + '_bee')
    sys_names.update(en_candidates.keys())   # 含歧义英文名：迁移按 ID 判名，改写安全
    sys_names.update(LEGACY_ZH)
    sys_names.add('Bee')
    sys_names.add('蜜蜂')
    # 蜂笼里写死的英文名，不收进安全集合的话，迁移会被拦下
    sys_names.add('Shiny Bee')
    sys_names.add(shiny_zh)

    j = lambda o: json.dumps(o, ensure_ascii=False)
    sys_obj = {n: 1 for n in sorted(sys_names)}

    shared = '''
function pbOwn(o, k) { return Object.prototype.hasOwnProperty.call(o, k) }

// 长名优先 + 词边界（防止 "Ancient Bee" 命中 "Ancient Beekeeper"）
const PB_EN_RE = new RegExp('\\\\b(?:' + Object.keys(PB_EN2ZH)
    .sort(function (a, b) { return b.length - a.length })
    .map(function (k) { return k.replace(/[.*+?^${}()|[\\]\\\\]/g, '\\\\$&') })
    .join('|') + ')(?![A-Za-z])', 'g')

function pbTranslate(s) {
    // 形态1: 原始 ID (productivebees:xxx)
    let ns = s.replace(/productivebees:([a-z0-9_]+)/g, function (mm, base) {
        let stripped = base.endsWith('_bee') ? base.substring(0, base.length - 4) : base
        if (pbOwn(PB_ID2ZH, stripped)) return PB_ID2ZH[stripped]
        if (pbOwn(PB_ID2ZH, base)) return PB_ID2ZH[base]
        return mm
    })
    // 形态2: 英文名整词（歧义名已在生成期剔除）
    ns = ns.replace(PB_EN_RE, function (mm) { return pbOwn(PB_EN2ZH, mm) ? PB_EN2ZH[mm] : mm })
    // 形态3: 类型行 "类型: Kamikaz (100%)"，整段精确匹配
    ns = ns.replace(/(类型|Type)([:：]\\s*)([A-Za-z][A-Za-z' .-]*?)(\\s*\\(\\d+%\\))/g,
        function (mm, a, b, c, d) {
            return a + b + (pbOwn(PB_TYPE2ZH, c) ? PB_TYPE2ZH[c] : c) + d
        })
    // 形态4: 已废弃的旧中文译名归一
    for (let old in PB_ZH_ALIAS) {
        if (pbOwn(PB_ZH_ALIAS, old) && ns.indexOf(old) >= 0) ns = ns.split(old).join(PB_ZH_ALIAS[old])
    }
    // 形态6: 点名的外来实体 ID（基因样本/蜂蜜零食的「类型」行）。
    // 整串精确替换，不进任何正则——这些 ID 带命名空间，只可能指那一只。
    for (let eid in PB_EXTRA_ID2ZH) {
        if (pbOwn(PB_EXTRA_ID2ZH, eid) && ns.indexOf(eid) >= 0) {
            ns = ns.split(eid).join(PB_EXTRA_ID2ZH[eid])
        }
    }
    // 形态5: 原版蜜蜂括号整名
    return ns.replace(/\\(Bee\\)/g, '(蜜蜂)')
}
'''

    client = ('// ATM10 汉化补丁 · 资源蜜蜂显示层 (蜂笼/基因样本/蜜蜂小食 tooltip + 实体名牌)\n'
              '// Copyright (C) 2026 星野夢華 (Hoshino Yumeka) · SPDX-License-Identifier: GPL-3.0-or-later\n'
              '// !! 本文件由 scripts/gen_pb_hanhua.py 生成，勿手改。译名来源是资源包 zh_cn !!\n'
              'const PB_ID2ZH = ' + j(id2zh) + ';\n'
              'const PB_EN2ZH = ' + j(en2zh) + ';\n'
              'const PB_TYPE2ZH = ' + j(type2zh) + ';\n'
              'const PB_ZH_ALIAS = ' + j(zh_alias) + ';\n'
              'const PB_EXTRA_ID2ZH = ' + j(extra_id2zh) + ';\n'
              'const PB_SYS = ' + j(sys_obj) + ';\n'
              + shared + '''
const $ItemTooltipEvent = Java.loadClass('net.neoforged.neoforge.event.entity.player.ItemTooltipEvent')
const $RenderNameTagEvent = Java.loadClass('net.neoforged.neoforge.client.event.RenderNameTagEvent')
const $Component = Java.loadClass('net.minecraft.network.chat.Component')

NativeEvents.onEvent($ItemTooltipEvent, function (event) {
    try {
        let stack = event.getItemStack()
        if (String(stack.getDescriptionId()).indexOf('productivebees') < 0) return
        let lines = event.getToolTip()
        for (let i = 0; i < lines.size(); i++) {
            let line = lines.get(i)
            let s = String(line.getString())
            let ns = pbTranslate(s)
            if (ns !== s) {
                lines.set(i, $Component.literal(ns).setStyle(line.getStyle()))
            }
        }
    } catch (err) {
    }
})

// 名牌只翻"系统生成名"：玩家命名牌起的名字原样显示（与 Jade/GUI 保持一致）
NativeEvents.onEvent($RenderNameTagEvent, function (event) {
    try {
        let ent = event.getEntity()
        if (String(ent.getType().toString()).indexOf('productivebees') < 0) return
        let c = event.getContent()
        if (c === null) return
        let s = String(c.getString())
        if (!pbOwn(PB_SYS, s)) return
        let ns = pbTranslate(s)
        if (ns !== s) event.setContent($Component.literal(ns))
    } catch (err) {
    }
})
console.info('[pb_hanhua] 显示层已注册 (ID:' + Object.keys(PB_ID2ZH).length
    + ' EN:' + Object.keys(PB_EN2ZH).length + ' TYPE:' + Object.keys(PB_TYPE2ZH).length + ')')
''')

    server = ('// ATM10 汉化补丁 · 资源蜜蜂数据迁移 (服务端)\n'
              '// Copyright (C) 2026 星野夢華 (Hoshino Yumeka) · SPDX-License-Identifier: GPL-3.0-or-later\n'
              '// !! 本文件由 scripts/gen_pb_hanhua.py 生成，勿手改。译名来源是资源包 zh_cn !!\n'
              '// 只动纯显示字段（蜂笼 custom_data.name / 实体 CustomName），按 NBT 的\n'
              '// entity/type ID 查译名。玩家自定义名由 PB_SYS 安全集合保护。\n'
              'const PB_BID2ZH = ' + j(bid2zh) + ';\n'
              'const PB_SYS = ' + j(sys_obj) + ';\n'
              '''
function pbOwn(o, k) { return Object.prototype.hasOwnProperty.call(o, k) }

const $DataComponents = Java.loadClass('net.minecraft.core.component.DataComponents')
const $CustomData = Java.loadClass('net.minecraft.world.item.component.CustomData')
const $Component = Java.loadClass('net.minecraft.network.chat.Component')

// 从蜂笼 NBT 得到权威中文名: configurable bee 看 type 字段, 其余看 entity 字段
function cageZh(tag) {
    if (tag.contains('type')) {
        let t = String(tag.getString('type'))
        if (pbOwn(PB_BID2ZH, t)) return PB_BID2ZH[t]
    }
    if (tag.contains('entity')) {
        let e = String(tag.getString('entity'))
        if (pbOwn(PB_BID2ZH, e)) return PB_BID2ZH[e]
    }
    return null
}

// 玩家背包里的蜂笼: 系统生成名改写为权威译名（玩家命名牌名绝不碰）
PlayerEvents.tick(function (event) {
    const p = event.player
    if (p.tickCount % 100 !== 0) return
    try {
        let inv = p.getInventory()
        let lists = [inv.items, inv.offhand]
        for (let li = 0; li < lists.length; li++) {
            let list = lists[li]
            for (let i = 0; i < list.size(); i++) {
                let stack = list.get(i)
                if (stack.isEmpty()) continue
                let did = String(stack.getItem().getDescriptionId())
                if (did.indexOf('productivebees') < 0 || did.indexOf('bee_cage') < 0) continue
                let cd = stack.get($DataComponents.CUSTOM_DATA)
                if (cd === null) continue
                let tag = cd.copyTag()
                if (!tag.contains('name')) continue
                let zh = cageZh(tag)
                if (zh === null) continue
                let name = String(tag.getString('name'))
                // 安全闸: 只改写已知系统生成名, 玩家自定义名(命名牌)绝不碰
                if (!pbOwn(PB_SYS, name)) continue
                if (zh !== name) {
                    tag.putString('name', zh)
                    stack.set($DataComponents.CUSTOM_DATA, $CustomData.of(tag))
                    console.info('[pb_hanhua] 蜂笼迁移: ' + name + ' -> ' + zh)
                }
            }
        }
    } catch (err) {
    }
})

// 实体加载进世界时: 带 CustomName 的老蜜蜂按其真实类型改写（玩家命名牌名绝不碰）
EntityEvents.spawned(function (event) {
    try {
        let ent = event.getEntity()
        let tid = String(ent.getType().toString())
        if (tid.indexOf('productivebees') < 0) return
        if (!ent.hasCustomName()) return
        let zh = null
        let m = tid.match(/entity\\.productivebees\\.([a-z0-9_]+)/)
        if (m) {
            let full = 'productivebees:' + m[1]
            if (full === 'productivebees:configurable_bee') {
                let nbt = ent.getNbt()
                if (nbt !== null && nbt.contains('type')) {
                    let t = String(nbt.getString('type'))
                    if (pbOwn(PB_BID2ZH, t)) zh = PB_BID2ZH[t]
                }
            } else if (pbOwn(PB_BID2ZH, full)) {
                zh = PB_BID2ZH[full]
            }
        }
        if (zh === null) return
        let nm = String(ent.getCustomName().getString())
        // 安全闸: 只改写已知系统生成名, 玩家自定义名(命名牌)绝不碰
        if (!pbOwn(PB_SYS, nm)) return
        if (zh !== nm) {
            ent.setCustomName($Component.literal(zh))
            console.info('[pb_hanhua] 实体迁移: ' + nm + ' -> ' + zh)
        }
    } catch (err) {
    }
})
console.info('[pb_hanhua] 数据迁移已注册 (ID表:' + Object.keys(PB_BID2ZH).length + ')')
''')

    (COMMON / 'kubejs/client_scripts').mkdir(parents=True, exist_ok=True)
    (COMMON / 'kubejs/server_scripts').mkdir(parents=True, exist_ok=True)
    (COMMON / 'kubejs/client_scripts/pb_hanhua_tooltip.js').write_text(client, encoding='utf-8')
    (COMMON / 'kubejs/server_scripts/pb_hanhua_cage_migrate.js').write_text(server, encoding='utf-8')
    print(f'已生成: ID {len(id2zh)} | EN {len(en2zh)} | TYPE {len(type2zh)} | 迁移 {len(bid2zh)} | 安全集合 {len(sys_names)}')
    if ambiguous:
        print(f'歧义英文名（已从显示映射剔除，共 {len(ambiguous)} 个）:')
        for env, zhs in ambiguous:
            print(f'  {env!r} -> {zhs}')
    print('样例: fbi =', id2zh.get('fbi'), '| Kamikaz(类型行) =', type2zh.get('Kamikaz'))


if __name__ == '__main__':
    main()
