#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# atm10-zh-cn — All the Mods 10 简体中文汉化补丁「绿油油版」
# Copyright (C) 2026 星野夢華 (Hoshino Yumeka)
# SPDX-License-Identifier: GPL-3.0-or-later
"""把 src/books/ 的映射套到模组 jar 里的导览书上，产出资源包里的中文版。

仓库里没有导览书副本（原因见 extract_books.py）。这里读取上游 JSON，逐条套译文：上游新加的页
原样保留（显示英文），上游改过的位置会列出来。

每条映射都记着提取时上游文件的 sha1：

- sha1 一致：上游文件与提取时相同，每条译文都必须落位，落不下说明本脚本有 bug，直接失败。
- sha1 不一致：上游改过（或者是另一个整合包版本，模组版本不同）。尽量套用，逐条统计落不下的，
  整体命中率低于下限就失败。

用法:
    python3 scripts/gen_books.py <mods 目录>
    # 不给参数就用 ATM_PACK_ROOT/mods
"""
import json
import os
import sys
from pathlib import Path

import books
from paths import PACK, ROOT

# 命中率下限：低于这个数说明不是零星漂移，而是整块对不上了
MIN_HIT = 0.90


def apply_one(doc, entries, rel, strict, miss):
    """把 [路径, 英文原文, 中文] 逐条套到 doc 上。返回落位条数。"""
    ok = 0
    for path, en, zh in entries:
        path = tuple(path)
        cur = books.get_at(doc, path)
        if cur == en:
            books.set_at(doc, path, zh)
            ok += 1
            continue
        # 位置漂了（上游插了一页之类）：全文找这段原文，唯一命中就照样翻
        where = [p for p, v in books.walk(doc) if v == en]
        if len(where) == 1:
            books.set_at(doc, where[0], zh)
            ok += 1
            continue
        if strict:
            sys.exit('❌ %s 的 %s 套不上，但上游文件与提取时逐字节相同。\n'
                     '   这是 gen_books.py 自己的 bug。\n'
                     '   原文: %r' % (rel, list(path), en[:80]))
        miss.append((rel, path, en[:60]))
    return ok


def main(mods_dir):
    jars = books.Jars(mods_dir)
    if not books.BOOKS.is_dir():
        sys.exit('❌ 没有 %s' % books.BOOKS)

    n_copy = n_skip = n_same = 0
    # 与英文逐字节相同的页不从 jar 里复制：它们没有可译内容（纯图纸、纯配方），复制等于重新分发
    # 上游文件，而各模组的许可各不相同，有 26 个命名空间是 All Rights Reserved。
    #
    # 不发也没有损失：Patchouli 与 AE2 导览都按文件回落到 en_us。整合包里有 21 本书自带的翻译
    # 只翻了一部分（Apotheosis 的土耳其语 152 页缺 72 页，LaserIO 自己的中文 42 页缺 6 页），照样能用。
    copies = json.loads(books.MAP_COPIES.read_text(encoding='utf-8'))
    n_skip += len(copies)

    drift = []
    resolved = {}
    prose = json.loads(books.MAP_PROSE.read_text(encoding='utf-8'))
    for rel, info in prose.items():
        data = jars.read(info['src'])
        if data is None:
            n_skip += 1
            continue
        got = books.sha1(data)
        # 纯 BOM 或英语文法润色不需要另存一份中文页，但老版本仍带着旧字节。逐页核对过语义等价的
        # 历史指纹单独登记。variants 不同：它必须有对应的整页中文版本层，不能用来放过正文改写。
        if got == info['sha1'] or got in (info.get('equivalent_sha1') or []):
            continue
        layer = (info.get('variants') or {}).get(got)
        if layer:
            translated = ROOT / 'src' / 'pack_overrides' / layer / rel
            if not translated.is_file():
                sys.exit('❌ %s 把当前英文指纹登记到文件层 %s，但对应译文不存在：%s'
                         % (rel, layer, translated.relative_to(ROOT)))
            resolved[layer] = resolved.get(layer, 0) + 1
            continue
        drift.append(rel)

    total = ok = n_json = 0
    miss = []
    for mp in sorted(books.BOOKS.rglob('*.json')):
        if mp.parent == books.BOOKS and mp.name.startswith('_'):
            continue
        # books/literal/ 是另一套东西（正文写死在 JSON 里的书，见
        # gen_literal_books.py），格式不同，不能按书本 doc 读
        if 'literal' in mp.relative_to(books.BOOKS).parts[:1]:
            continue
        rel = mp.relative_to(books.BOOKS).as_posix()[:-len('.json')]
        doc = json.loads(mp.read_text(encoding='utf-8'))
        up = jars.read(doc['src'])
        if up is None:
            n_skip += 1
            continue
        obj = json.loads(up.decode('utf-8-sig'))
        strict = books.sha1(up) == doc['sha1']
        total += len(doc['t'])
        ok += apply_one(obj, doc['t'], rel, strict, miss)
        # 套完映射仍是原文（这一页没有可译文本）就不写：写了等于重新分发上游文件，
        # 而玩家看到的内容一样，Patchouli 与 AE2 导览都按文件回落到 en_us。
        out = json.dumps(obj, ensure_ascii=False, indent=2) + '\n'
        if json.loads(out) == json.loads(up.decode('utf-8-sig')):
            n_same += 1
            continue
        t = PACK / rel
        t.parent.mkdir(parents=True, exist_ok=True)
        t.write_text(out, encoding='utf-8')
        n_json += 1

    rate = (ok / total) if total else 1.0
    print('导览书：结构型 %d 个文件、%d/%d 条译文落位（%.1f%%），'
          '与原文相同没写 %d 个，该版本没有的跳过 %d 个'
          % (n_json, ok, total, rate * 100, n_same, n_skip))
    for layer, count in sorted(resolved.items()):
        print('  散文页：%d 个当前原稿已由版本文件层 %s 接管' % (count, layer))
    if drift:
        print('  ⚠️ %d 个散文页的英文原稿与提取时不同（上游改过，译文可能已过时）：' % len(drift))
        for r in drift[:15]:
            print('       ' + r)
        if len(drift) > 15:
            print('       …另外 %d 个' % (len(drift) - 15))
    if miss:
        print('  ⚠️ %d 条译文没落位（上游改了那一段）：' % len(miss))
        for r, p, e in miss[:15]:
            print('       %s %s  %r' % (r, list(p), e))
        if len(miss) > 15:
            print('       …另外 %d 条' % (len(miss) - 15))
    if rate < MIN_HIT:
        sys.exit('❌ 导览书译文命中率 %.1f%% 低于下限 %.0f%%，整块对不上了'
                 % (rate * 100, MIN_HIT * 100))


if __name__ == '__main__':
    d = sys.argv[1] if len(sys.argv) > 1 else (
        os.path.join(os.environ.get('ATM_PACK_ROOT', ''), 'mods'))
    if not d or not Path(d).is_dir():
        sys.exit(__doc__)
    main(d)
