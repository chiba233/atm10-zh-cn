#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# atm10-zh-cn — All the Mods 10 简体中文汉化补丁「绿油油版」
# Copyright (C) 2026 星野夢華 (Hoshino Yumeka)
# SPDX-License-Identifier: GPL-3.0-or-later
"""重算 src/module_hashes.json。

模块是玩家实际加载的替换表。这份哈希清单的作用是让任何模块内容变化都变成
一次显式动作：改了就必须重跑本脚本，顺手逼自己确认「这处改动是有意的吗」。

历史上这个仓库因为「我觉得这批没用」被删过 1033 个文件，也出过「撤回一项汉化时
只撤了一半」的事故。文件在不在有保护清单管，内容对不对由这份哈希管。

用法:
    python3 scripts/compliance/gen_module_hashes.py
"""
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent


def main():
    mods = sorted((ROOT / 'src' / 'vaultpatcher' / 'modules').glob('*.json'))
    h = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in mods}
    out = ROOT / 'src' / 'module_hashes.json'
    doc = json.loads(out.read_text(encoding='utf-8')) if out.is_file() else {}
    doc['sha256'] = h
    out.write_text(json.dumps(doc, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    print('已更新 %d 个模块的哈希 → %s' % (len(h), out.relative_to(ROOT)))
    return 0


if __name__ == '__main__':
    sys.exit(main())
