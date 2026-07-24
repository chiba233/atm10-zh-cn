# -*- coding: utf-8 -*-
"""资源蜜蜂汉化生成器 —— 单一真源，产出双端脚本。

真源：resourcepacks/ATM10汉化包-7.2/.../productivebees/lang/zh_cn.json 的
entity.productivebees.* 键（463 个权威译名）。禁止在别处手写第二份蜂名表。

产出：
  kubejs/client_scripts/pb_hanhua_tooltip.js   显示层（tooltip/名牌），四种形态精确映射
  kubejs/server_scripts/pb_hanhua_cage_migrate.js  数据迁移（按 ID 查权威译名，不猜字符串）

架构原则（2026-07-24 重构，教训见 git log）：
  - 数据层不注入中文：服务端不装语言 mod，上游数据保持英文/ID，
    否则服务端烙的名字与 JEI/配方（客户端由数据现算）分裂，玩家查不到配方
  - 迁移只动纯显示字段（蜂笼 name / 实体 CustomName），按 NBT 里的 entity/type ID
    查权威译名——精准，绝不做贪婪字符串替换
  - 显示层"类型行"（基因样本/蜜蜂小食/JEI 配方 ghost）只做整段精确匹配

用法: python3 scripts/gen_pb_hanhua.py <PB jar 路径>
CI 校验: 重跑生成器后 git diff 必须干净（防手改漂移）
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PACK_LANG = ROOT / 'resourcepacks/ATM10汉化包-7.2/assets/productivebees/lang/zh_cn.json'

# 旧版 PB 的梗名（现版本已改名，只存在于早年存档 NBT 中）→ 对应的蜂 id
LEGACY_EN = {
    'Redastone Bee': 'redstone',
    'The Ter-Bee-Nator': 'wither',  # 若 id 不存在则译名回退到下方 LEGACY_EN_FALLBACK
}
LEGACY_EN_FALLBACK = {'The Ter-Bee-Nator': '终结者蜜蜂'}
# 历史上用过、后被否掉的中文译名 → 归一到权威译名（联调蜂/神蜂特工队 均为 fbi 旧译）
LEGACY_ZH = ['联调蜂', '神蜂特工队']
LEGACY_ZH_TARGET_ID = 'fbi'


def title_case(base: str) -> str:
    return ' '.join(w.capitalize() for w in base.split('_') if w)


def main() -> None:
    if len(sys.argv) < 2:
        sys.exit('用法: gen_pb_hanhua.py <productivebees jar 路径>')
    import zipfile
    jar = zipfile.ZipFile(sys.argv[1])
    en = json.loads(jar.read('assets/productivebees/lang/en_us.json'))
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

    # 英文名精确表: en_us 真名 + Title Case 派生名（长名优先正则用）
    en2zh = {}
    for base, zh in id2zh.items():
        if base == 'bee':
            continue  # 裸 'Bee' 由 "(Bee)" 整名规则单独处理
        en2zh[title_case(base) + ' Bee'] = zh
    for key, env in en.items():
        if not key.startswith('entity.productivebees.'):
            continue
        bid = key[len('entity.productivebees.'):]
        base = bid[:-4] if bid.endswith('_bee') else bid
        if '%' in env or len(env) < 4:
            continue
        if base in id2zh:
            en2zh[env] = id2zh[base]
    for env, base in LEGACY_EN.items():
        en2zh[env] = id2zh.get(base) or LEGACY_EN_FALLBACK[env]

    # 类型行专用表（无 Bee 后缀的 Title Case，如 "Kamikaz"/"Benitoite Crystal"）
    # 只在 "类型: X (N%)" 整段精确匹配中使用，绝不进通用正则
    type2zh = {title_case(base): zh for base, zh in id2zh.items() if base != 'bee'}

    zh_alias = {old: id2zh[LEGACY_ZH_TARGET_ID] for old in LEGACY_ZH}

    # 迁移表: NBT entity/type 的完整 id -> 中文名
    bid2zh = {}
    for base, zh in id2zh.items():
        bid2zh['productivebees:' + base] = zh
        bid2zh['productivebees:' + base + '_bee'] = zh
    bid2zh['minecraft:bee'] = pack.get('entity.minecraft.bee', '蜜蜂')

    j = lambda o: json.dumps(o, ensure_ascii=False)

    shared_translate = '''
// 长名优先 + 词边界（防止 "Ancient Bee" 命中 "Ancient Beekeeper"）
const PB_EN_RE = new RegExp('\\\\b(?:' + Object.keys(PB_EN2ZH)
    .sort(function (a, b) { return b.length - a.length })
    .map(function (k) { return k.replace(/[.*+?^${}()|[\\]\\\\]/g, '\\\\$&') })
    .join('|') + ')(?![A-Za-z])', 'g')

function pbTranslate(s) {
    // 形态1: 原始 ID (productivebees:xxx)
    let ns = s.replace(/productivebees:([a-z0-9_]+)/g, function (mm, base) {
        let stripped = base.endsWith('_bee') ? base.substring(0, base.length - 4) : base
        return PB_ID2ZH[stripped] || PB_ID2ZH[base] || mm
    })
    // 形态2: 英文名整词（en_us 真名/派生名/旧版梗名）
    ns = ns.replace(PB_EN_RE, function (mm) { return PB_EN2ZH[mm] || mm })
    // 形态3: 类型行 "类型: Kamikaz (100%)" —— 无 Bee 后缀形态，整段精确匹配
    ns = ns.replace(/(类型|Type)([:：]\\s*)([A-Za-z][A-Za-z' .-]*?)(\\s*\\(\\d+%\\))/g,
        function (mm, a, b, c, d) {
            return a + b + (PB_TYPE2ZH[c] || c) + d
        })
    // 形态4: 已废弃的旧中文译名归一
    for (let old in PB_ZH_ALIAS) {
        if (ns.indexOf(old) >= 0) ns = ns.split(old).join(PB_ZH_ALIAS[old])
    }
    // 形态5: 原版蜜蜂括号整名
    return ns.replace(/\\(Bee\\)/g, '(蜜蜂)')
}
'''

    client = ('// ATM10 汉化补丁 · 资源蜜蜂显示层 (蜂笼/基因样本/蜜蜂小食 tooltip + 实体名牌)\n'
              '// !! 本文件由 scripts/gen_pb_hanhua.py 生成，勿手改；译名真源是资源包 zh_cn !!\n'
              'const PB_ID2ZH = ' + j(id2zh) + ';\n'
              'const PB_EN2ZH = ' + j(en2zh) + ';\n'
              'const PB_TYPE2ZH = ' + j(type2zh) + ';\n'
              'const PB_ZH_ALIAS = ' + j(zh_alias) + ';\n'
              + shared_translate + '''
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

NativeEvents.onEvent($RenderNameTagEvent, function (event) {
    try {
        let ent = event.getEntity()
        if (String(ent.getType().toString()).indexOf('productivebees') < 0) return
        let c = event.getContent()
        if (c === null) return
        let s = String(c.getString())
        let ns = pbTranslate(s)
        if (ns !== s) event.setContent($Component.literal(ns))
    } catch (err) {
    }
})
console.info('[pb_hanhua] 显示层已注册 (ID:' + Object.keys(PB_ID2ZH).length
    + ' EN:' + Object.keys(PB_EN2ZH).length + ' TYPE:' + Object.keys(PB_TYPE2ZH).length + ')')
''')

    server = ('// ATM10 汉化补丁 · 资源蜜蜂数据迁移 (服务端)\n'
              '// !! 本文件由 scripts/gen_pb_hanhua.py 生成，勿手改；译名真源是资源包 zh_cn !!\n'
              '// 只动纯显示字段（蜂笼 custom_data.name / 实体 CustomName），按 NBT 的\n'
              '// entity/type ID 查权威译名 —— 不做任何字符串猜测替换。\n'
              '// entity 等协议字段绝不碰。\n'
              'const PB_BID2ZH = ' + j(bid2zh) + ';\n'
              '''
const $DataComponents = Java.loadClass('net.minecraft.core.component.DataComponents')
const $CustomData = Java.loadClass('net.minecraft.world.item.component.CustomData')
const $Component = Java.loadClass('net.minecraft.network.chat.Component')

// 从蜂笼 NBT 得到权威中文名: configurable bee 看 type 字段, 其余看 entity 字段
function cageZh(tag) {
    if (tag.contains('type')) {
        let t = PB_BID2ZH[String(tag.getString('type'))]
        if (t) return t
    }
    if (tag.contains('entity')) {
        return PB_BID2ZH[String(tag.getString('entity'))] || null
    }
    return null
}

// 玩家背包里的蜂笼: name 改写为权威译名
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

// 实体加载进世界时: 带 CustomName 的老蜜蜂按其真实类型改写
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
                    zh = PB_BID2ZH[String(nbt.getString('type'))] || null
                }
            } else {
                zh = PB_BID2ZH[full] || null
            }
        }
        if (zh === null) return
        let nm = String(ent.getCustomName().getString())
        if (zh !== nm) {
            ent.setCustomName($Component.literal(zh))
            console.info('[pb_hanhua] 实体迁移: ' + nm + ' -> ' + zh)
        }
    } catch (err) {
    }
})
console.info('[pb_hanhua] 数据迁移已注册 (ID表:' + Object.keys(PB_BID2ZH).length + ')')
''')

    (ROOT / 'kubejs/client_scripts/pb_hanhua_tooltip.js').write_text(client, encoding='utf-8')
    (ROOT / 'kubejs/server_scripts/pb_hanhua_cage_migrate.js').write_text(server, encoding='utf-8')
    print(f'已生成: ID {len(id2zh)} | EN {len(en2zh)} | TYPE {len(type2zh)} | 迁移ID {len(bid2zh)}')
    print('样例: kamikaz =', id2zh.get('kamikaz'), '| Kamikaz(类型行) =', type2zh.get('Kamikaz'),
          '| fbi =', id2zh.get('fbi'))


if __name__ == '__main__':
    main()
