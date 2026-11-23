#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# atm10-zh-cn — All the Mods 10 简体中文汉化补丁「绿油油版」
# Copyright (C) 2026 星野夢華 (Hoshino Yumeka)
# SPDX-License-Identifier: GPL-3.0-or-later
"""打 zip，并保证中文文件名带 UTF-8 标志位。

macOS / 多数 Linux 自带的 Info-ZIP `zip` 没编进 UNICODE_SUPPORT：文件名按 UTF-8 字节
写进去，却不置 general purpose bit 11。Windows 自带的「提取全部」看不到这个标志，
就按系统 ANSI 代码页（简中是 GBK）去解，`双击安装-Windows.bat` 到用户手里变成乱码，
而那正是他要双击的文件。

Python 的 zipfile 遇到非 ASCII 文件名会自动置 bit 11，用它打包即可。

用法:
    python3 scripts/mkzip.py <输出.zip> <要打包的目录> [zip 内前缀]
      不给前缀 → 目录内容直接放在 zip 根（资源包用）
      给前缀   → 内容放在 <前缀>/ 下（分发包用）
"""
import os
import sys
import zipfile
from pathlib import Path

SKIP = {'.DS_Store'}


def main():
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    out = Path(sys.argv[1])
    src = Path(sys.argv[2])
    prefix = sys.argv[3] if len(sys.argv) > 3 else ''

    out.parent.mkdir(parents=True, exist_ok=True)
    if out.exists():
        out.unlink()

    files = []
    for dp, dns, fns in os.walk(src):
        dns.sort()
        for fn in sorted(fns):
            if fn in SKIP:
                continue
            p = Path(dp) / fn
            rel = p.relative_to(src).as_posix()
            files.append((p, (prefix + '/' + rel) if prefix else rel))

    with zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for p, arc in files:
            # 固定时间戳，保证同样的输入产出同样的 zip（可复现）
            zi = zipfile.ZipInfo(arc, date_time=(1980, 1, 1, 0, 0, 0))
            zi.compress_type = zipfile.ZIP_DEFLATED
            zi.external_attr = (0o755 if os.access(p, os.X_OK) else 0o644) << 16
            with open(p, 'rb') as f:
                z.writestr(zi, f.read())

    bad = [i.filename for i in zipfile.ZipFile(out).infolist()
           if any(ord(c) > 127 for c in i.filename) and not (i.flag_bits & 0x800)]
    if bad:
        sys.exit('❌ 仍有 %d 个中文名没带 UTF-8 标志位: %s' % (len(bad), bad[:3]))
    print('  %s (%d 个文件)' % (out, len(files)))


if __name__ == '__main__':
    main()
