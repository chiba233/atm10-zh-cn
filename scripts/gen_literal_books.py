#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# atm10-zh-cn — All the Mods 10 简体中文汉化补丁「绿油油版」
# Copyright (C) 2026 星野夢華 (Hoshino Yumeka)
# SPDX-License-Identifier: GPL-3.0-or-later
"""把正文写死在 JSON 里的那类书翻出来。

大多数导览书（Patchouli / AE2 Guide / Oracle Index）的文本要么走语言文件，
要么按语言分目录，`gen_books.py` 已经覆盖。但有的模组自己造了一套书：
文件放在 `assets/<ns>/books/` 这种与语言无关的路径下，字段里一半是语言键、
一半是直接写死的英文。写死的那一半，资源包的 `lang/zh_cn.json` 根本够不着，
玩家看到的就是「目录和章节名是中文、正文全是英文」。

要翻只能整份文件覆盖。这里的做法：

- 仓库里不存这些文件的副本，只存 `原文 → 译文` 的成对映射
  （`src/books/literal/<ns>.json`），构建时现取 jar 里那一份来套。
- 套用是带引号的整串替换（`"原文"` → `"译文"`），不做 JSON 解析重排。
  一来保住上游的排版与字段顺序，二来 herbsandharvest 有两份文件上游自己就
  不是合法 JSON（尾部多一段），解析一遍再吐出来会把它们改坏。
- 每份文件记了提取时的 sha1。对得上就要求每条映射至少命中一次，
  落不下即硬失败。对不上说明上游改过，落不下的逐条列出，
  命中率跌破下限一样失败，不允许「悄悄少翻一半」。

用法:
    python3 scripts/gen_literal_books.py <mods 目录>
    # 不给参数就用 ATM_PACK_ROOT/mods
"""
import json
import os
import sys
from pathlib import Path

import books
from paths import COMMON, PACK, SRC

MAPS = SRC / 'books' / 'literal'
MIN_HIT = 0.90


def main(mods_dir):
    if not MAPS.is_dir():
        print('（没有 %s，跳过）' % MAPS)
        return 0
    jars = books.Jars(mods_dir)
    n_file = n_ok = n_all = 0
    miss = []
    drift = []
    for mp in sorted(MAPS.glob('*.json')):
        spec = json.loads(mp.read_text(encoding='utf-8'))
        for rel, info in sorted(spec['files'].items()):
            raw = jars.read(rel)
            if raw is None:
                continue                       # 这一版没有这个模组
            text = raw.decode('utf-8-sig')
            strict = books.sha1(raw) == info['sha1']
            if not strict:
                drift.append(rel)
            # JSON 文件按「带引号整串」替换，引号把字段值的边界钉死，不会误伤别的串。
            # XML 之类没有这层边界，用 raw 模式原样替换，由映射自己写足上下文
            raw = info.get('raw', False)
            for en, zh in info['t']:
                n_all += 1
                needle, sub = (en, zh) if raw else ('"%s"' % en, '"%s"' % zh)
                if needle in text:
                    text = text.replace(needle, sub)
                    n_ok += 1
                elif strict:
                    sys.exit('❌ %s 的一条映射套不上，但上游文件与提取时逐字节相同——\n'
                             '   这是本脚本自己的 bug，不是上游漂移。\n'
                             '   原文: %r' % (rel, en[:80]))
                else:
                    miss.append((rel, en[:60]))
            # assets/ 是资源包能覆盖的。data/ 只有数据包能覆盖，
            # 走整合包自带 KubeJS 的 kubejs/data（本仓库既有做法）
            t = (PACK / rel) if rel.startswith('assets/') else \
                (COMMON / 'kubejs' / rel)
            t.parent.mkdir(parents=True, exist_ok=True)
            t.write_text(text, encoding='utf-8')
            n_file += 1

    rate = (n_ok / n_all) if n_all else 1.0
    print('写死正文的书：%d 个文件、%d/%d 条译文落位（%.1f%%）'
          % (n_file, n_ok, n_all, rate * 100))
    if drift:
        print('  ⚠️ 上游改过（sha1 对不上）：%s' % '、'.join(sorted(set(drift))[:5]))
    for rel, en in miss[:10]:
        print('     套不上 %s ← %r' % (rel, en))
    if n_all and rate < MIN_HIT:
        sys.exit('❌ 命中率 %.1f%% 低于下限 %.0f%%——不是零星漂移，是整块对不上了'
                 % (rate * 100, MIN_HIT * 100))
    return 0


if __name__ == '__main__':
    d = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
        os.environ.get('ATM_PACK_ROOT', 'pack'), 'mods')
    sys.exit(main(d))
