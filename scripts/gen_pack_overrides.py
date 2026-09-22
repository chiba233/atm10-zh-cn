#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# atm10-zh-cn — All the Mods 10 简体中文汉化补丁「绿油油版」
# Copyright (C) 2026 星野夢華 (Hoshino Yumeka)
# SPDX-License-Identifier: GPL-3.0-or-later
"""把 versions/<版本>/pack_overrides.json 叠到该版出货树的资源包译文上。

资源包译文按**命名空间 + 键**索引，同一个键在哪个整合包版本都是同一个键，
所以 src/pack 是版本中立的、一份通吃六个版本。这个前提会被上游打破：

同一个键在两版里**参数个数不同**时，一份中文没法同时对两版成立。少写参数只是
漏掉一段文字；多写参数会让 TranslatableContents 抛 TranslatableFormatException，
那一行直接显示成未替换的模板。此时只能按版本分叉。

任务书那一侧早就有 versions/<版本>/quest_overrides.snbt，这里是同一个东西的
资源包版。**它是例外口子，不是常规去处**：能在 src/pack 里一份写对的，就不要
往这里写——每多一条，六个版本之间就多一处要各自核对的分叉。

口子两头都 fail-closed：

- 覆盖的命名空间在出货树里没有 zh_cn.json → 红（写错了地方，这条永远不生效）
- 覆盖的值与公共树里的**完全相同** → 红（登记过期了，公共树已经改成一样的）
- 没写 why、值不是字符串、JSON 坏了 → 红

用法:
    python3 scripts/gen_pack_overrides.py <版本> <出货树>
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main(ver, tree):
    p = ROOT / 'versions' / ver / 'pack_overrides.json'
    if not p.is_file():
        return
    try:
        doc = json.loads(p.read_text(encoding='utf-8'))
    except Exception as e:                                       # noqa: BLE001
        sys.exit('❌ %s 解析失败：%s' % (p.relative_to(ROOT), e))
    tree = Path(tree)
    n = 0
    for ns, entries in sorted((doc.get('lang') or {}).items()):
        f = next(tree.glob('resourcepacks/*/assets/%s/lang/zh_cn.json' % ns), None)
        if f is None:
            sys.exit('❌ %s 覆盖了命名空间 %s，但出货树里没有它的 zh_cn.json——'
                     '这条覆盖永远不会生效。' % (p.relative_to(ROOT), ns))
        d = json.loads(f.read_text(encoding='utf-8'))
        for key, ent in sorted(entries.items()):
            if not isinstance(ent, dict) or not isinstance(ent.get('value'), str):
                sys.exit('❌ %s 里 %s/%s 的 value 不是字符串。'
                         % (p.relative_to(ROOT), ns, key))
            if not str(ent.get('why') or '').strip():
                sys.exit('❌ %s 里 %s/%s 没写 why。覆盖一条，必须写清这一版为什么'
                         '不能跟公共树一样——否则下一版没人知道该不该撤掉它。'
                         % (p.relative_to(ROOT), ns, key))
            if d.get(key) == ent['value']:
                sys.exit('❌ %s 里 %s/%s 与公共树的值完全相同，这条覆盖是白写的。\n'
                         '   多半是公共树已经改成同样的写法了：去掉这一条。'
                         % (p.relative_to(ROOT), ns, key))
            d[key] = ent['value']
            n += 1
        f.write_text(json.dumps(d, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    if n:
        # 覆盖了几条一定要打印。不打印的话，「这一版跟别版不一样」就成了只有翻代码
        # 才看得见的事。
        print('  按 versions/%s/pack_overrides.json 覆盖资源包译文 %d 条' % (ver, n))


if __name__ == '__main__':
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    main(sys.argv[1], sys.argv[2])
