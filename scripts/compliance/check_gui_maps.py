#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# atm10-zh-cn — All the Mods 10 简体中文汉化补丁「绿油油版」
# Copyright (C) 2026 星野夢華 (Hoshino Yumeka)
# SPDX-License-Identifier: GPL-3.0-or-later
"""界面 XML 映射的三条硬规矩，套用前先在本机拦住。

`gen_literal_books.py` 是全量 replace（`text.replace(en, zh)`，不带 count），
所以这三件事必然出事，而且都要等玩家打开那个界面才炸：

1. 同一份原文在一个文件里映射两次，第一条把两处都换掉了，第二条「套不上」，
   构建直接红（2026-07-28 实际发生过一次）。
2. 改出重复属性，上游标签本来就有 `textoffset`，我们又插一个，同一个
   `<button>` 两个同名属性，blockui 抛 `Can't parse xml at: …`，
   玩家一右键市政厅游戏就崩（2026-07-28 实际发生过）。
3. 套用后不是合法 XML，同上，构建时看不出来，开界面才炸。

用法:
    python3 scripts/compliance/check_gui_maps.py [<mods 目录>]
    # 缺省读 ATM_PACK_ROOT/mods
"""
import json
import os
import re
import sys
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
MAPS = {'structurize.json': 'structurize', 'minecolonies_gui.json': 'minecolonies'}
ATTR = re.compile(r'\b([a-zA-Z_]+)="')


def main(argv):
    mods = Path(argv[0]) if argv else Path(os.environ.get('ATM_PACK_ROOT', '')) / 'mods'
    if not mods.is_dir():
        # 没有 jar 的环境里真查不了。但流水线里 jar 本该已经下好，缺了就是下载/
        # 缓存那步出了问题，而这道闸会跟着静默消失，退出码跟「查过了没问题」一样。
        # 所以生成之后的环节一律传 GATE_STRICT=1（同 check.py 里的 absent()）。
        if (os.environ.get('GATE_STRICT') or '').strip() not in ('', '0'):
            print('❌ 界面 XML 映射检查没跑成：没有 mods 目录 %s。'
                  '本环境声明了 GATE_STRICT——jar 本该已备好，缺了不算通过' % mods)
            return 1
        print('ℹ️ 跳过：没有 mods 目录（给个参数或设 ATM_PACK_ROOT）')
        return 0
    jars = {}
    for j in sorted(mods.glob('*.jar')):
        for pre in MAPS.values():
            if j.name.startswith(pre):
                jars.setdefault(pre, zipfile.ZipFile(j))
    bad = ok = 0
    skipped = []
    for mapf, pre in MAPS.items():
        p = ROOT / 'src' / 'books' / 'literal' / mapf
        if not p.is_file():
            continue
        doc = json.loads(p.read_text(encoding='utf-8'))
        if pre not in jars:
            # 有条目要查却没有 jar，记下来，末尾按 GATE_STRICT 决定红不红
            if doc.get('files'):
                skipped.append((mapf, len(doc['files'])))
            continue
        for rel, info in doc['files'].items():
            try:
                text = jars[pre].read(rel).decode('utf-8')
            except KeyError:
                print('❌ %s：jar 里没有这个文件' % rel)
                bad += 1
                continue
            seen = set()
            for en, zh in info['t']:
                if en in seen:
                    print('❌ %s：同一份原文映射了两次 %r' % (rel, en[:60]))
                    bad += 1
                seen.add(en)
                if en not in text:
                    print('❌ %s：映射套不上 %r' % (rel, en[:60]))
                    bad += 1
                names = ATTR.findall(zh)
                dup = sorted({a for a in names if names.count(a) > 1})
                if dup:
                    print('❌ %s：改出重复属性 %s（上游本来就有，别再插一个）' % (rel, dup))
                    bad += 1
                text = text.replace(en, zh)
            try:
                ET.fromstring(text.encode('utf-8'))
                ok += 1
            except Exception as e:                                 # noqa: BLE001
                print('❌ %s：套用后不是合法 XML —— %s' % (rel, e))
                bad += 1
    if bad:
        print('\n共 %d 处问题。这三类都要等玩家开那个界面才炸，必须在这里拦住。' % bad)
    elif not skipped:
        print('✅ %d 个界面 XML 套用后全部合法' % ok)
    if skipped:
        # 上面那个 GATE_STRICT 只挡住了「没有 mods 目录」。目录在、却没有该
        # mod 的 jar 时，上面的循环是 `continue` 静默跳过的，有映射要查却一条
        # 都没查，退出码与「查过了没问题」不可分辨。指到一个只放了单个 mod 的
        # build/packsrc/<版本>/mods 就会这样。
        #
        # 注意判据是待查条目数不是映射文件数：blockui 那条路撤回后两份映射
        # 的 files 都是空的，此时 0 条待查是正确状态，不该红。
        msg = ('%s：%s 下没有它的 jar，%d 条映射一条都没查'
               % ('；'.join('%s（%d 条）' % s for s in skipped), mods,
                  sum(n for _, n in skipped)))
        if (os.environ.get('GATE_STRICT') or '').strip() not in ('', '0'):
            print('❌ ' + msg + '——本环境声明了 GATE_STRICT，跳过不算通过')
            return 1
        print('ℹ️ ' + msg + '（没声明 GATE_STRICT，只作提示）')
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
