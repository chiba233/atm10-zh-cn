#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# atm10-zh-cn — All the Mods 10 简体中文汉化补丁「绿油油版」
# Copyright (C) 2026 星野夢華 (Hoshino Yumeka)
# SPDX-License-Identifier: GPL-3.0-or-later
"""dynamic 模块里的 `@` 子串对子不许互为子串。

VaultPatcher 的 `MatchUtils.matchPairs`：value 以 `@` 开头的对子走
`String.replace` 子串替换，而它遍历的是一个 HashSet，顺序不确定。
于是只要两条 `@` 键互为子串，结果就取决于遍历顺序：

    "Blueprint"                 -> "@蓝图"
    "Blueprint related settings"-> "@蓝图相关设置"

短的先跑，长的那条就再也匹配不上，屏幕上留下「蓝图 related settings」，
半中半英，而且每次启动都可能不一样。

两种正当解法：

1. 拆成互不重叠的片段（中文语序允许时）。例：`Farthest Frontier` 与 `Frontier`
   拆成 `Farthest ` + `Frontier`，任意顺序都拼回「最远边疆」。
2. 中文语序不允许拆的（`Teleportation Permitted` ≠ 传送 + 允许），把**短的那条
   降级为精确匹配**（去掉 `@`）：它单独出现时照样翻，也不会去啃长的那条。

用法:
    python3 scripts/compliance/check_dynamic_substrings.py
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent


def main():
    bad = 0
    for f in sorted((ROOT / 'src' / 'vaultpatcher' / 'modules').glob('*.json')):
        doc = json.loads(f.read_text(encoding='utf-8'))
        if not (isinstance(doc, list) and doc and doc[0].get('dynamic')):
            continue
        for blk in doc[1:]:
            subs = [p['key'] for p in blk.get('pairs', []) if p['value'].startswith('@')]
            for a in subs:
                for b in subs:
                    if a != b and a in b:
                        bad += 1
                        print('❌ %s / %s：%r 是 %r 的子串'
                              % (f.name, blk['target_class'][0].rsplit('.', 1)[-1], a, b))
    if bad:
        print('\n%d 组冲突。替换顺序不确定，会翻出半中半英且每次不一样——'
              '拆成互不重叠的片段，或把短的那条降级为精确匹配（去掉 @）。' % bad)
        return 1
    print('✅ dynamic 模块的 @ 子串键互不为子串')
    return 0


if __name__ == '__main__':
    sys.exit(main())
