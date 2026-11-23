#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# atm10-zh-cn — All the Mods 10 简体中文汉化补丁「绿油油版」
# Copyright (C) 2026 星野夢華 (Hoshino Yumeka)
# SPDX-License-Identifier: GPL-3.0-or-later
"""核对 src/vaultpatcher/modules/ 的内容哈希。

保护清单（protect.py）管的是文件在不在，这份管的是内容对不对。
两者缺一不可：这个仓库出过「撤回一项汉化只撤了一半」「以为改好了其实改的是另一份」
这类事故，文件都还在，内容却已经不是预期的了。

任何模块内容变化都会让这里变红。红了不代表要改闸，先确认那处改动是不是自己
有意做的。确认无误再跑 gen_module_hashes.py 重新钉。

用法:
    python3 scripts/compliance/check_module_hashes.py
"""
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent


def main():
    man = ROOT / 'src' / 'module_hashes.json'
    if not man.is_file():
        print('❌ 缺少 src/module_hashes.json —— 跑 gen_module_hashes.py 生成')
        return 1
    want = json.loads(man.read_text(encoding='utf-8'))['sha256']
    got = {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
           for p in sorted((ROOT / 'src' / 'vaultpatcher' / 'modules').glob('*.json'))}
    bad = 0
    for name, h in sorted(want.items()):
        if name not in got:
            print('❌ 模块消失了：%s' % name)
            bad += 1
        elif got[name] != h:
            print('❌ 模块内容被改过：%s\n     钉的是 %s\n     实际是 %s' % (name, h[:16], got[name][:16]))
            bad += 1
    for name in sorted(set(got) - set(want)):
        print('❌ 新模块未入清单：%s —— 跑 gen_module_hashes.py' % name)
        bad += 1
    if bad:
        print('\n共 %d 处不一致。确认这些改动都是有意的之后，再跑 '
              'scripts/compliance/gen_module_hashes.py 重新钉哈希。' % bad)
        return 1
    print('✅ 模块内容哈希：%d 个模块与清单逐字节一致' % len(want))
    return 0


if __name__ == '__main__':
    sys.exit(main())
