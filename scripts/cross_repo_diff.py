#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# atm10-zh-cn — All the Mods 10 简体中文汉化补丁「绿油油版」
# Copyright (C) 2026 星野夢華 (Hoshino Yumeka)
# SPDX-License-Identifier: GPL-3.0-or-later
"""和另一个同源汉化仓库对账：同一个模组，两边的译文差在哪。

## 为什么要它

两个仓库（本仓库与 atmons-zh-cn）翻的是**很多相同的模组**，各自独立推进。
一边修好的东西，另一边不会自动知道——2026-08-25 就整整重做了一遍：
气动工艺手册的 6 个坏跳转链接、以及把 Drone 从「雄蜂」改成「无人机」的 153 处，
那边早就修完了，这边从零查了一遍才发现，连处数都一模一样。

重做一遍还只是浪费时间；更糟的是**同一个模组在两个包里叫不同的名字**，
而且谁都不知道。

## 它做什么、不做什么

只**报告**，永远退 0，不设闸。要不要跟、跟哪一边，是人的判断——两个包的模组
版本不同，差异未必是「漏同步」，也可能是各自的正常措辞取舍。

比两样东西：

- `src/pack/assets/<ns>/lang/zh_cn.json` —— 两边都有的命名空间，逐键比
- `src/books/assets/<ns>/**/*.json.json` —— 两边都有的导览书文件，按条目路径比译文

分三类报出来：

- **只有对面有的键**：这边可能漏了一整块
- **两边都有、值不同的键**：风格分叉，或者一边修过一边没修
- **只有这边有的键**：反过来，对面可能要同步

用法:
    python3 scripts/cross_repo_diff.py <另一个仓库的路径>
    python3 scripts/cross_repo_diff.py ../atmons-zh-cn --ns productivelib
    python3 scripts/cross_repo_diff.py ../atmons-zh-cn --books      # 只比导览书
    python3 scripts/cross_repo_diff.py ../atmons-zh-cn --full       # 逐条列出，不截断
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PREVIEW = 3          # 每个命名空间默认最多列几条，--full 取消


def load(p):
    try:
        return json.loads(Path(p).read_text(encoding='utf-8'))
    except Exception:
        return None


def lang_pairs(root):
    """<命名空间> -> {键: 值}"""
    out = {}
    for f in sorted((root / 'src' / 'pack' / 'assets').glob('*/lang/zh_cn.json')):
        d = load(f)
        if isinstance(d, dict):
            out[f.parts[-3]] = d
    return out


def book_pairs(root):
    """<相对路径> -> {条目路径元组: 译文}"""
    base = root / 'src' / 'books' / 'assets'
    out = {}
    for f in sorted(base.glob('**/*.json.json')):
        d = load(f)
        if not isinstance(d, dict) or 't' not in d:
            continue
        out[str(f.relative_to(base))] = {tuple(t[0]): t[2] for t in d['t']
                                         if isinstance(t, list) and len(t) >= 3}
    return out


def report(title, mine, theirs, full, only_ns=None):
    names = sorted(set(mine) & set(theirs))
    if only_ns:
        names = [n for n in names if only_ns in n]
    n_miss = n_conf = n_extra = 0
    body = []
    for name in names:
        a, b = mine[name], theirs[name]
        miss = [k for k in b if k not in a]
        conf = [k for k in b if k in a and a[k] != b[k]]
        extra = [k for k in a if k not in b]
        n_miss += len(miss)
        n_conf += len(conf)
        n_extra += len(extra)
        if not (miss or conf):
            continue
        body.append('  %s   缺 %d，值不同 %d，本仓库独有 %d'
                    % (name, len(miss), len(conf), len(extra)))
        show = conf if full else conf[:PREVIEW]
        for k in show:
            body.append('      %s' % (k,))
            body.append('        本仓库: %s' % str(a[k])[:110])
            body.append('        对    面: %s' % str(b[k])[:110])
        if not full and len(conf) > PREVIEW:
            body.append('      …另有 %d 条值不同未列出（--full 全列）' % (len(conf) - PREVIEW))
        show = miss if full else miss[:PREVIEW]
        for k in show:
            body.append('      %s  ← 本仓库没有' % (k,))
            body.append('        对    面: %s' % str(b[k])[:110])
        if not full and len(miss) > PREVIEW:
            body.append('      …另有 %d 条只有对面有未列出' % (len(miss) - PREVIEW))
    print('── %s ──' % title)
    print('  两边共有 %d 个；本仓库缺 %d 键，值不同 %d 键，本仓库独有 %d 键'
          % (len(names), n_miss, n_conf, n_extra))
    print('\n'.join(body) if body else '  没有差异')
    print()


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    if not args:
        sys.exit(__doc__)
    other = Path(args[0]).expanduser().resolve()
    if not (other / 'src').is_dir():
        sys.exit('❌ %s 下没有 src/，不像是同源的汉化仓库' % other)
    full = '--full' in sys.argv
    only_ns = None
    if '--ns' in sys.argv:
        i = sys.argv.index('--ns')
        if i + 1 < len(sys.argv):
            only_ns = sys.argv[i + 1]

    print('本仓库: %s' % ROOT)
    print('对    面: %s\n' % other)

    want_books = '--books' in sys.argv
    want_lang = not want_books or '--lang' in sys.argv
    if want_lang:
        report('资源包 lang', lang_pairs(ROOT), lang_pairs(other), full, only_ns)
    if want_books or '--lang' not in sys.argv:
        report('导览书', book_pairs(ROOT), book_pairs(other), full, only_ns)

    print('只报告，不判对错——两个整合包的模组版本不同，差异未必是漏同步。')


if __name__ == '__main__':
    main()
