#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# atm10-zh-cn — All the Mods 10 简体中文汉化补丁「绿油油版」
# Copyright (C) 2026 星野夢華 (Hoshino Yumeka)
# SPDX-License-Identifier: GPL-3.0-or-later
"""任务正文 ↔ 绑定物品 反查（check_quest_item_names.py 只查标题，这个补正文）。

标题对齐了不代表正文对齐。实测大量任务是标题写着物品真名、正文里另起一个名字：
「生命补片」的正文写「生命幻片」、「虚空模块」的正文写「真空模块」、
「耀光下界书架」的正文写「发光下界书架」…… 玩家照正文去 JEI 搜，搜不到。

做法：拿该任务绑定物品的中文真名，在标题 / 副标题 / 正文里找「只差一个字」的变体。
作用域必须限定在「这条任务绑定的那几个物品」，拿全整合包 6 万条物品名去比，
任意四字词都能撞上邻居，全是噪声（第一版就是这么翻车的）。

误报仍会有（例如真名是更长真名的子串），需人工过一遍，但量级在几百条以内。

triage 的教训：不要用「变体在全书出现次数」当筛子。曾经按「只出现 1 次 = 句子碎片」
过滤，结果把「充能台的正文写成充能球」这种单次出现的真错误一起滤掉了。
输出去重后只有两百多组，必须整份读完，别再图省事做二次过滤。

用法:
    python3 scripts/check_quest_desc_terms.py
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from check_quest_item_names import (QDIR, REPO, CODE, strip, parse_chapter,   # noqa: E402
                                    build_item_names, name_of, parse_lang)

PURE = re.compile(r'^[一-鿿]+$')
NAMEKEY = re.compile(r'^(item|block|entity|fluid|biome)\.')
# 虚词：真正的译名变体不会只差在虚词上，差在虚词上的基本是句子片段被切出来了
STOP = set('的了和与或在是个你我它他们有为以所这那就都也而把被从到对能会可不没过着地得很更'
           '最再又还只才并等及后前上下里外中内出去来做用将向由如若则者之此某每各多少大小新老好同')


def variants(text, name):
    """text 里所有与 name 只差一个字的片段"""
    L, out = len(name), set()
    for i in range(len(text) - L + 1):
        g = text[i:i + L]
        if g == name or not PURE.match(g):
            continue
        d = [(a, b) for a, b in zip(name, g) if a != b]
        if len(d) == 1 and d[0][0] not in STOP and d[0][1] not in STOP:
            out.add(g)
    return out


def main():
    eff, jar_en = build_item_names()
    allnames = {CODE.sub('', v).strip() for k, v in eff.items()
                if NAMEKEY.match(k) and isinstance(v, str)}

    q2i = {}
    for f in sorted(os.listdir(os.path.join(QDIR, 'chapters'))):
        if f.endswith('.snbt'):
            q2i.update(parse_chapter(os.path.join(QDIR, 'chapters', f)))

    zh = parse_lang(os.path.join(QDIR, 'lang/zh_cn.snbt'))
    delta = os.path.join(REPO, 'config/ftbquests/quests/lang/zh_cn/chapters')
    for f in sorted(os.listdir(delta)):        # 本包 delta 覆盖上游
        if f.endswith('.snbt'):
            zh.update(parse_lang(os.path.join(delta, f)))

    n = 0
    for qid, items in sorted(q2i.items()):
        if not items:
            continue
        blob = ' '.join(zh.get('quest.%s.%s' % (qid, s), '')
                        for s in ('title', 'quest_subtitle', 'quest_desc'))
        if not blob.strip():
            continue
        t = strip(blob).replace('\\n', ' ')
        for it in dict.fromkeys(items):
            zh_name = name_of(eff, jar_en, it)[0]
            if not zh_name:
                continue
            zh_name = CODE.sub('', zh_name).strip()
            if len(zh_name) < 3 or not PURE.match(zh_name):
                continue
            for g in variants(t, zh_name):
                if g in allnames:
                    continue               # 是另一个正经物品，不是笔误
                n += 1
                print('%s  %-16s 真名「%s」→ 正文写「%s」' % (qid, it, zh_name, g))
    print('可疑 %d 处（含误报，需人工过）' % n)
    return n


if __name__ == '__main__':
    main()
