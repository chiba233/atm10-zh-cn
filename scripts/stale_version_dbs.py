#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# atm10-zh-cn — All the Mods 10 简体中文汉化补丁「绿油油版」
# Copyright (C) 2026 星野夢華 (Hoshino Yumeka)
# SPDX-License-Identifier: GPL-3.0-or-later
"""列出「VaultPatcher 库缺模块记录」的整合包版本，一行一个。

`gen_vaultpatcher.py` 打包时会对每个模块查 `versions/db/<版本>/vaultpatcher.json`，
查不到就红——因为没有记录就等于没对着那一版真实的 jar 核过 target_class 与 key，
此时把模块发给那一版的用户，是闭着眼睛发。

那道闸只会在构建到某一版时才炸，一次报一版；而加一个带 target_class 的模块会让
**五版**同时过期。这里把「哪几版缺、缺哪几个」一次性算出来，CI 拿它决定要为哪些
版本取 jar 补库。

判据必须和那道闸**同一份**：跳过哪些模块（SRC_ONLY / PERF_HOLD）直接从
`gen_vaultpatcher` 导入，不在这里另抄一份清单——两份清单迟早会漂。

    python3 scripts/stale_version_dbs.py          # 缺的版本，一行一个
    python3 scripts/stale_version_dbs.py --why    # 连缺哪几个模块一起打印
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'scripts'))
from gen_vaultpatcher import MODULES, SRC_ONLY, PERF_HOLD       # noqa: E402


def missing_by_version():
    want = sorted(p.name for p in MODULES.glob('*.json')
                  if p.name not in SRC_ONLY and p.name not in PERF_HOLD)
    out = {}
    for d in sorted((ROOT / 'versions').glob('[0-9]*')):
        f = ROOT / 'versions' / 'db' / d.name / 'vaultpatcher.json'
        # 库整份不存在，是「新版本首次入库」那一步的活，不归这里管。
        if not f.is_file():
            continue
        db = json.loads(f.read_text(encoding='utf-8'))
        miss = [m for m in want if m not in db]
        if miss:
            out[d.name] = miss
    return out


if __name__ == '__main__':
    for ver, miss in missing_by_version().items():
        if '--why' in sys.argv:
            print('%s 缺 %d 个：%s' % (ver, len(miss), '、'.join(miss)))
        else:
            print(ver)
