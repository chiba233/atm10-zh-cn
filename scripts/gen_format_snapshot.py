# -*- coding: utf-8 -*-
# atm10-zh-cn — All the Mods 10 简体中文汉化补丁「绿油油版」
# Copyright (C) 2026 星野夢華 (Hoshino Yumeka)
# SPDX-License-Identifier: GPL-3.0-or-later
"""上游英文格式快照生成器，供 check.py 离线做占位符/颜色码安全校验。

只快照「本包翻了、且英文原文或译文里含 % 或 §」的键，文件体积可控。

用法: python3 scripts/gen_format_snapshot.py "<ATM10 实例目录>"
"""
import json
import os
import sys
import zipfile
from pathlib import Path

import vanilla
from paths import COMMON, PACK, snapshot
ROOT = Path(__file__).resolve().parent.parent
OUT = snapshot('upstream_format_en_us.json')



def loadb(b):
    try:
        return json.loads(b.decode('utf-8-sig'))
    except Exception:
        return None


def main(instance):
    inst = Path(instance)
    jar_en = {}
    for jar in sorted((inst / 'mods').glob('*.jar')):
        try:
            zf = zipfile.ZipFile(jar)
        except Exception:
            continue
        with zf:
            for n in zf.namelist():
                if n.startswith('assets/') and n.endswith('/lang/en_us.json'):
                    for k, v in (loadb(zf.read(n)) or {}).items():
                        if isinstance(v, str):
                            jar_en.setdefault(k, v)
    for k, v in vanilla.client_en(inst).items():
        if isinstance(v, str):
            jar_en.setdefault(k, v)

    pack_keys = set()
    for base in (PACK, COMMON / 'kubejs' / 'assets'):
        for p in base.rglob('lang/zh_cn.json'):
            d = json.loads(p.read_text(encoding='utf-8'))
            for k, v in d.items():
                if isinstance(v, str) and ('%' in v or '§' in v or '%' in jar_en.get(k, '')
                                           or '§' in jar_en.get(k, '')):
                    pack_keys.add(k)

    snap = {k: jar_en[k] for k in sorted(pack_keys) if k in jar_en}
    OUT.write_text(json.dumps(snap, ensure_ascii=False, indent=0, sort_keys=True) + '\n',
                   encoding='utf-8')
    print('快照 %d 键 -> %s' % (len(snap), OUT.relative_to(ROOT)))


if __name__ == '__main__':
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(sys.argv[1])
