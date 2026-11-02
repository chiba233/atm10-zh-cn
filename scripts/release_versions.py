#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# atm10-zh-cn — All the Mods 10 简体中文汉化补丁「绿油油版」
# Copyright (C) 2026 星野夢華 (Hoshino Yumeka)
# SPDX-License-Identifier: GPL-3.0-or-later
"""列出要打包、发布的整合包版本：versions/whitelist.txt 里列出的那些。

versions/ 下没列进白名单的版本是维护版本，版本层与校验照常保留，只是不出包。
build_dist.sh 与 release.yml 都从这里取清单，两边不会各算各的。

取不到就失败，不回落到「versions/ 下全部」：白名单不存在、一个版本都没有、
列了 versions/ 下没有的版本、同一版本列了两次，都退出非 0。

用法:
    python3 scripts/release_versions.py            # 空格分隔，按版本号升序
    python3 scripts/release_versions.py <仓库根>   # 测试用
"""
import sys
from pathlib import Path


def main(root):
    vdir = Path(root) / 'versions'
    wl = vdir / 'whitelist.txt'
    if not wl.is_file():
        sys.exit('❌ 没有 %s，不知道该打包哪些版本' % wl)
    declared = {d.name for d in vdir.iterdir() if d.is_dir() and d.name[:1].isdigit()}
    seen = []
    for n, line in enumerate(wl.read_text(encoding='utf-8').splitlines(), 1):
        v = line.strip()
        if not v or v.startswith('#'):
            continue
        if v in seen:
            sys.exit('❌ %s 第 %d 行：%s 列了两次' % (wl.name, n, v))
        if v not in declared:
            sys.exit('❌ %s 第 %d 行：versions/ 下没有 %s 这个版本' % (wl.name, n, v))
        seen.append(v)
    if not seen:
        sys.exit('❌ %s 里一个版本都没有' % wl.name)
    print(' '.join(sorted(seen, key=lambda s: [int(x) for x in s.split('.')])))


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else Path(__file__).resolve().parent.parent)
