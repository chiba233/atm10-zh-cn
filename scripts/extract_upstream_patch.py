#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# atm10-zh-cn — All the Mods 10 简体中文汉化补丁「绿油油版」
# Copyright (C) 2026 星野夢華 (Hoshino Yumeka)
# SPDX-License-Identifier: GPL-3.0-or-later
"""把「我改过的上游文件」反解成映射表，存进 src/upstream/。

## 为什么不能直接把改过的文件提交进仓库

整合包自己的 `kubejs/*.js`、`config/*.json` 是上游的东西。把改了几个字符串的
整份副本提交进来，等于把「上游内容」和「我们的改动」焊死在一起：

- ATM 一升级，我们发出去的就是「旧上游 + 我们的改动」，把人家的修复整个覆盖掉。
- 多版本更要命，`kubejs/startup_scripts/CustomAdditions.js` 在 7.1→7.2 之间被
  ATM 换掉了冰与火的类名（`iceandfire.data.DragonType` → `registry.IafDragonTypes`），
  拿 7.2 的副本发给 7.1 用户，`Java.loadClass` 当场找不到类。

所以仓库里只存改动本身：一组「找这几行 → 换成这几行」。构建时对着**目标版本
的官方文件**套用，上游改了哪一行都会立刻现形（见 gen_upstream_patches.py）。

## 映射格式

    {"src": "<相对整合包根的路径>",
     "edits": [{"find": ["原文行…"], "replace": ["译文行…"]}, …]}

`find` 是连续的原文行，不带行号、不带上下文标记，所以它跟版本无关，
上游在别处加减多少行都不影响定位。为保证唯一定位，`find` 会自动向两侧扩上下文，
直到该行块在整份文件里只出现一次。

用法:
    python3 scripts/extract_upstream_patch.py <官方文件> <改过的文件> <整合包内相对路径>
    # 批量见 --batch：拿一棵官方 overrides 和一棵改过的树做全量提取
    python3 scripts/extract_upstream_patch.py --batch <官方overrides目录> <改过的树> <输出目录> <路径…>
"""
import json
import sys
from difflib import SequenceMatcher
from pathlib import Path

MAX_CONTEXT = 60


def occurrences(hay, block):
    """block（行列表）在 hay（行列表）里出现了几次"""
    if not block:
        return -1
    n, m = len(hay), len(block)
    return sum(1 for i in range(n - m + 1) if hay[i:i + m] == block)


def hunks(a, b):
    """把 difflib 的操作码并成一段段「连续的改动」"""
    out = []
    cur = None
    for tag, i1, i2, j1, j2 in SequenceMatcher(None, a, b, autojunk=False).get_opcodes():
        if tag == 'equal':
            if cur:
                out.append(cur)
                cur = None
            continue
        if cur is None:
            cur = [i1, i2, j1, j2]
        else:
            cur[1], cur[3] = i2, j2
    if cur:
        out.append(cur)
    return out


def extract(a, b):
    """a=官方行, b=我们的行 → edits"""
    edits = []
    for i1, i2, j1, j2 in hunks(a, b):
        lo, hi, blo, bhi = i1, i2, j1, j2
        # 向两侧扩上下文，直到 find 非空且在原文里唯一
        for _ in range(MAX_CONTEXT):
            if occurrences(a, a[lo:hi]) == 1:
                break
            if lo > 0:
                lo -= 1
                blo -= 1
            elif hi < len(a):
                hi += 1
                bhi += 1
            else:
                break
        else:
            pass
        find, repl = a[lo:hi], b[blo:bhi]
        if occurrences(a, find) != 1:
            raise SystemExit('❌ 第 %d 行附近的改动扩到 %d 行上下文仍无法唯一定位'
                             % (i1 + 1, hi - lo))
        if find == repl:
            continue
        edits.append({'find': find, 'replace': repl})
    return edits


def one(official: Path, mine: Path, rel: str):
    a = official.read_text(encoding='utf-8').splitlines(keepends=True)
    b = mine.read_text(encoding='utf-8').splitlines(keepends=True)
    return {'src': rel, 'edits': extract(a, b)}


def main(argv):
    if argv[:1] == ['--batch']:
        ov, tree, out = Path(argv[1]), Path(argv[2]), Path(argv[3])
        rels = argv[4:]
        n = 0
        for rel in rels:
            doc = one(ov / rel, tree / rel, rel)
            t = out / (rel + '.json')
            t.parent.mkdir(parents=True, exist_ok=True)
            t.write_text(json.dumps(doc, ensure_ascii=False, indent=1) + '\n',
                         encoding='utf-8')
            n += len(doc['edits'])
            print('  %-78s %d 处改动' % (rel[:78], len(doc['edits'])))
        print('共 %d 个文件、%d 处改动 → %s' % (len(rels), n, out))
        return
    official, mine, rel = Path(argv[0]), Path(argv[1]), argv[2]
    print(json.dumps(one(official, mine, rel), ensure_ascii=False, indent=1))


if __name__ == '__main__':
    if len(sys.argv) < 4:
        sys.exit(__doc__)
    main(sys.argv[1:])
