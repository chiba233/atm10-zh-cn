#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# atm10-zh-cn — All the Mods 10 简体中文汉化补丁「绿油油版」
# Copyright (C) 2026 星野夢華 (Hoshino Yumeka)
# SPDX-License-Identifier: GPL-3.0-or-later
"""底本漂移：英文原文改了，而我们的译文没跟着改。

## 这是最危险的一类问题

漏翻只是难看，玩家看到英文自己会查。底本漂移是玩家看到一句通顺的中文，
而它描述的行为已经不是现在的行为了，数值改了、单位改了、机制改了、参数顺序反了。
键还在、译文还在、游戏不报错、任何测试都不会失败，只有真在玩的人某天发现被坑了。

`build_en_baseline.py` 把每条译文对应的英文底本按版本快照下来，
这里逐条 diff：英文变了的那些，全部列进需复核。

分级：
- 实质变化：去掉大小写与首尾空白后仍然不同 → 必须人工复核
- 仅排版：只差大小写 / 空白 → 一般无需改译文，单独列出不混进主清单

用法:
    python3 scripts/check_en_drift.py 7.1 7.2            # 看 7.1→7.2 上游改了什么
    python3 scripts/check_en_drift.py 7.1 7.2 --md 报告.md
"""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # scripts/ 下的公共模块

ROOT = Path(__file__).resolve().parent.parent.parent
DB = ROOT / 'versions' / 'db'


def norm(s):
    return re.sub(r'\s+', ' ', s).strip().lower()


def load(v):
    """任务书底本入库，随时可查。模组 lang 底本是本地产物，没有就只查任务书。"""
    q = DB / v / 'quest_baseline.json'
    if not q.exists():
        sys.exit('❌ 没有 %s 的任务书底本，先跑 build_en_baseline.py %s' % (v, v))
    out = {'quest': json.loads(q.read_text(encoding='utf-8')), 'lang': {}}
    lp = DB / v / 'lang_baseline_local.json'
    has_lang = lp.exists()
    if has_lang:
        out['lang'] = json.loads(lp.read_text(encoding='utf-8'))['lang']
    return out, has_lang


def main(a, b, md=None):
    (A, fa), (B, fb) = load(a), load(b)
    full = True
    if not (fa and fb):
        print('（本地没有模组 lang 底本，只查任务书；要查 lang 先跑 build_en_baseline.py）')
    report = {}
    for sect in ('lang', 'quest'):
        real, cosmetic, gone, new = [], [], [], []
        for k, va in A[sect].items():
            vb = B[sect].get(k)
            if vb is None:
                gone.append(k)
            elif va != vb:
                same = norm(va) == norm(vb) if full else False
                (cosmetic if same else real).append((k, va, vb))
        new = [k for k in B[sect] if k not in A[sect]]
        report[sect] = dict(real=real, cosmetic=cosmetic, gone=gone, new=new)

    print('底本漂移 %s → %s' % (a, b))
    for sect, cn in (('lang', '资源包 lang'), ('quest', '任务书')):
        r = report[sect]
        print()
        print('== %s ==' % cn)
        print('  英文实质改写（**必须复核译文**）: %d' % len(r['real']))
        print('  仅大小写/空白变化              : %d' % len(r['cosmetic']))
        print('  该键在新版已不存在             : %d' % len(r['gone']))
        print('  新版新增、本包尚未翻           : %d' % len(r['new']))
        for k, va, vb in r['real'][:12]:
            print('    %s' % k)
            print('        旧: %s' % va.replace('\n', '⏎')[:96])
            print('        新: %s' % vb.replace('\n', '⏎')[:96])
    if md:
        lines = ['# 底本漂移 %s → %s' % (a, b), '',
                 '英文原文变了而译文没动的条目。**逐条复核**，不要批量替换。', '']
        for sect, cn in (('lang', '资源包 lang'), ('quest', '任务书')):
            r = report[sect]
            lines += ['## %s' % cn, '',
                      '| 项 | 数量 |', '|---|---|',
                      '| 英文实质改写（必须复核） | %d |' % len(r['real']),
                      '| 仅大小写/空白 | %d |' % len(r['cosmetic']),
                      '| 键已消失 | %d |' % len(r['gone']),
                      '| 新增未翻 | %d |' % len(r['new']), '']
            if r['real']:
                lines += ['### 需复核', '']
                for k, va, vb in r['real']:
                    lines += ['- `%s`' % k,
                              '  - 旧: `%s`' % va.replace('\n', '⏎')[:200],
                              '  - 新: `%s`' % vb.replace('\n', '⏎')[:200]]
                lines.append('')
        Path(md).write_text('\n'.join(lines) + '\n', encoding='utf-8')
        print('\n报告写入 %s' % md)
    return sum(len(report[s]['real']) for s in report)


if __name__ == '__main__':
    args = [x for x in sys.argv[1:] if not x.startswith('--')]
    if len(args) < 2:
        sys.exit(__doc__)
    m = sys.argv[sys.argv.index('--md') + 1] if '--md' in sys.argv else None
    main(args[0], args[1], m)
