#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# atm10-zh-cn — All the Mods 10 简体中文汉化补丁「绿油油版」
# Copyright (C) 2026 星野夢華 (Hoshino Yumeka)
# SPDX-License-Identifier: GPL-3.0-or-later
"""自动化之火：把 tooltip 上那行橙色的仪式 ID 换成中文仪式名。

## 为什么语言文件够不着

无产物的仪式做完会掉一个 `occultism:flame_of_automation`，它在 AE2 终端里长得
一模一样，唯一能区分的就是 tooltip 上那行橙色字。那行字是这么来的
（`SummonWildRitual` / `SummonRitual` / `CommandRitual` / `FamiliarRitual` /
`ResurrectFamiliarRitual` 五处写法完全一致）：

    ItemNBTUtil.setBoundSpiritName(stack,
        recipe.getRitualDummy().toString().substring(2)
              .replace("occultism:ritual_dummy/", ""))

也就是把仪式象征物的注册名原样写进数据组件，例如 `wild_drowned`。
`FlameAutomationItem.appendHoverText` 再拿它去填 `%s`：

    item.occultism.flame_of_automation.tooltip = "%s"

`TextUtil.formatDemonName(String)` 只是套一层 `§6§l…§r`，不查任何表。
所以这行字是数据不是翻译键，资源包再全也翻不到它。

## 绕法

`wild_drowned` 正是仪式象征物 `occultism:ritual_dummy/wild_drowned` 的路径，
而那个物品名我们已经译了：`item.occultism.ritual_dummy.wild_drowned` =
「仪式: 呼唤溺尸集群」。于是这里按资源包现有译文生成一张
`注册名 → 中文仪式名` 的表，客户端脚本在 `ItemTooltipEvent` 里拿它换字。

替换是精确匹配的：去掉 § 码后整行必须恰好等于表里的某个注册名才动。
上游哪天改了 tooltip 的格式，匹配落空、脚本什么都不做，退化成今天的样子，
不会把别的行改坏。

真源只有一处：资源包的 `assets/occultism/lang/zh_cn.json`。这里只做派生，
跟 gen_pb_hanhua.py 是同一个约定。

用法:
    python3 scripts/gen_occultism_flame.py
"""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from paths import COMMON, PACK, need_common                          # noqa: E402

LANG = 'assets/occultism/lang/zh_cn.json'
OUT = 'kubejs/client_scripts/occultism_flame_tooltip.js'

# 物品名键：item.occultism.ritual_dummy.<注册名>（再往下就是 .tooltip 之类的后缀了）
KEY = re.compile(r'^item\.occultism\.ritual_dummy\.([a-z0-9_]+)$')
# 「仪式: 呼唤溺尸集群」→「呼唤溺尸集群」。冒号后面才是仪式名。
PREFIX = re.compile(r'^仪式[:：]\s*')
CJK = re.compile(r'[一-鿿]')

# 报告里那一条：拿它当锚，键被上游改名/译文被改坏时当场红，而不是静默少几条。
ANCHOR = ('wild_drowned', '呼唤溺尸集群')
MIN_ENTRIES = 150


def build(lang):
    out = {}
    for k, v in lang.items():
        m = KEY.match(k)
        if not m or not isinstance(v, str):
            continue
        name = PREFIX.sub('', v).strip()
        if not name:
            raise SystemExit('❌ %s 的译文是空的' % k)
        if '§' in name or '\n' in name or '%' in name:
            # 这行字会被原样塞回 §6§l…§r 里，带格式码/换行/占位符都会当场穿帮
            raise SystemExit('❌ %s 的译文里有 §/换行/%% —— 不能直接当仪式名用: %r' % (k, v))
        if not CJK.search(name):
            raise SystemExit('❌ %s 还没译成中文: %r' % (k, v))
        out[m.group(1)] = name
    return out


def main():
    need_common()
    p = PACK / LANG
    if not p.is_file():
        raise SystemExit('❌ 出货树里没有 %s——先跑 assemble.py' % LANG)
    table = build(json.loads(p.read_text(encoding='utf-8')))

    if len(table) < MIN_ENTRIES:
        raise SystemExit('❌ 只认出 %d 条仪式象征物（至少该有 %d 条）——'
                         '上游是不是改了键名？' % (len(table), MIN_ENTRIES))
    if table.get(ANCHOR[0]) != ANCHOR[1]:
        raise SystemExit('❌ 锚点对不上：%s 应为 %r，实为 %r'
                         % (ANCHOR[0], ANCHOR[1], table.get(ANCHOR[0])))

    js = ('// ATM10 汉化补丁 · 自动化之火：tooltip 上那行橙色仪式 ID → 中文仪式名\n'
          '// Copyright (C) 2026 星野夢華 (Hoshino Yumeka) '
          '· SPDX-License-Identifier: GPL-3.0-or-later\n'
          '// !! 本文件由 scripts/gen_occultism_flame.py 生成，勿手改；'
          '真源是资源包 occultism/zh_cn.json !!\n'
          '// 那行字是数据（仪式象征物的注册名）不是翻译键，语言文件够不着，只能在显示层换。\n'
          '// ⚠️ KubeJS 的 client_scripts 共用**同一个全局作用域**：两个文件各写一句\n'
          '//    `const $Component = ...`，第二个就抛 "redeclaration of const $Component"，\n'
          '//    而且是**整批客户端脚本一起加载失败**（连蜂名 tooltip 都跟着没）。\n'
          '//    所以整份包在 IIFE 里，一个全局符号都不留。\n'
          '(function () {\n'
          'const FLAME_ID2ZH = '
          + json.dumps(table, ensure_ascii=False, sort_keys=True)
          + ';\n' + r'''
function own(o, k) { return Object.prototype.hasOwnProperty.call(o, k) }

const TooltipEvent = Java.loadClass('net.neoforged.neoforge.event.entity.player.ItemTooltipEvent')
const Comp = Java.loadClass('net.minecraft.network.chat.Component')

NativeEvents.onEvent(TooltipEvent, function (event) {
    try {
        let stack = event.getItemStack()
        if (String(stack.getDescriptionId()) !== 'item.occultism.flame_of_automation') return
        let lines = event.getToolTip()
        for (let i = 0; i < lines.size(); i++) {
            let line = lines.get(i)
            let s = String(line.getString())
            // 去掉 §6§l…§r 后必须整行就是那个注册名才换，免得误伤别的行
            let plain = s.replace(/§./g, '')
            if (!own(FLAME_ID2ZH, plain)) continue
            lines.set(i, Comp.literal(s.replace(plain, FLAME_ID2ZH[plain])).setStyle(line.getStyle()))
            break
        }
    } catch (err) {
    }
})
console.info('[occultism_flame] 仪式名显示层已注册 (' + Object.keys(FLAME_ID2ZH).length + ' 条)')
})()
''')

    out = COMMON / OUT
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(js, encoding='utf-8')
    print('✅ 自动化之火仪式名 %d 条 → %s' % (len(table), OUT))


if __name__ == '__main__':
    main()
