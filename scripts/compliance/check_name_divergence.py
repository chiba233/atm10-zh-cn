#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# atm10-zh-cn — All the Mods 10 简体中文汉化补丁「绿油油版」
# Copyright (C) 2026 星野夢華 (Hoshino Yumeka)
# SPDX-License-Identifier: GPL-3.0-or-later
"""找出「同一个东西被译了两遍且不一致」的地方。

玩家反馈：建造机悬浮窗里的汉化和实际卡片的物品名不一样。成因是同一个东西走了
两条路，物品名走语言文件，界面硬编码文本走 VaultPatcher 替换表，两边各译一遍
就分叉了（形状卡 / 塑形卡片、合成卡 / 合成卡片）。玩家拿悬浮窗上的名字去 JEI
搜索，什么都搜不到。

判据：某条替换的英文原文正好等于某个物品/方块的英文名，而它的译文与我们给
那个物品的译名不同。物品名是单一真源，玩家用它搜东西，所以要改的是替换表那侧。

注意：命中不等于错。同一个英文在不同语境下本来就可能是两回事
（`Sewage` 作为蓝图类别是「下水道」，作为物品是「污水」。`Size` 在采矿机界面
是「尺寸」，在别处可能是「数量」）。所以这个脚本只报不改，逐条人工判。

用法:
    python3 scripts/compliance/check_name_divergence.py
"""
import json, pathlib, zipfile, glob, re
CJK=re.compile('[一-鿿]')
M='/Users/yumeka/Documents/minecraft/.minecraft/versions/All the Mods 10/mods'
en2zh={}
for f in glob.glob(M+'/*.jar'):
    try: z=zipfile.ZipFile(f)
    except Exception: continue
    for n in z.namelist():
        m=re.fullmatch(r'assets/([^/]+)/lang/en_us\.json', n)
        if not m: continue
        p=pathlib.Path('src/pack/assets')/m.group(1)/'lang/zh_cn.json'
        if not p.is_file(): continue
        try:
            en=json.loads(z.read(n).decode('utf-8-sig'))
            zh=json.loads(p.read_text(encoding='utf-8-sig'))
        except Exception: continue
        for k,v in en.items():
            if not k.startswith(('item.','block.')) or not isinstance(v,str): continue
            t=zh.get(k)
            if t and CJK.search(t): en2zh.setdefault(v.strip(), set()).add(t)
print('英文物品/方块名 -> 译文 索引 %d 条' % len(en2zh))
div=[]
for p in sorted(pathlib.Path('src/vaultpatcher/modules').glob('*.json')):
    for blk in json.loads(p.read_text(encoding='utf-8')):
        for pr in (blk.get('pairs') or []):
            if not isinstance(pr,dict): continue
            k=re.sub(r'[\x00-\x1f]','',str(pr.get('key',''))).strip()
            v=re.sub(r'[\x00-\x1f]','',str(pr.get('value',''))).strip()
            names=en2zh.get(k)
            if names and v and v not in names:
                div.append((p.stem,k,v,sorted(names)[0]))
print('原文正好等于某物品/方块名、但译文与物品名不一致：%d 处' % len(div))
for m,k,v,want in div[:30]:
    print('  %-24s %-28s 替换=%-18s 物品名=%s' % (m[:24],k[:28],v[:18],want))
