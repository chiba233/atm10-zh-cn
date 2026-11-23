#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# atm10-zh-cn — All the Mods 10 简体中文汉化补丁「绿油油版」
# Copyright (C) 2026 星野夢華 (Hoshino Yumeka)
# SPDX-License-Identifier: GPL-3.0-or-later
"""工具链核对，决定这次构建的产物能不能拿字节去比。

以前的说法是「PNG 跨平台字节不同，所以只能比像素不能比 sha256」。那是描述症状。
病因是工具链没进依赖图：Pillow 的 wheel 里打包着 freetype / zlib / libpng，
换一台机器就换一套栅格化，字节自然不一样。

治法：把工具链本身钉住（`src/toolchain.lock.json`），并且明确区分两种构建：

- 标准环境（锁里那个镜像 + 那个 Pillow + 那几份字体）：产物字节可复现，
  verify_dist 拿 sha256 硬比。
- 别的环境：照样能构建、能自己玩，但这里会明说「这不是标准环境」，
  产物哈希不作数。不许假装能比，假装能比才是最坏的那种。

用法:
    python3 scripts/toolchain.py            # 打印实况与差异
    python3 scripts/toolchain.py --strict   # 不是标准环境就退出 1
    python3 scripts/toolchain.py --stamp    # 输出一行指纹，写进产物报告
    python3 scripts/toolchain.py --fonts    # 只核字体哈希（fetch_fonts.sh 收尾用）
"""
import hashlib
import json
import os
import platform
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LOCK = ROOT / 'src' / 'toolchain.lock.json'


def load():
    return json.loads(LOCK.read_text(encoding='utf-8'))


def probe():
    """当前环境的实况。"""
    out = {
        'python': '%d.%d' % sys.version_info[:2],
        'platform': platform.system().lower(),
        'machine': platform.machine(),
        # CI 在锁定的容器里跑时由 workflow 置上，本机构建自然是空的
        'container_digest': os.environ.get('ATM_TOOLCHAIN_DIGEST', ''),
    }
    try:
        import PIL
        out['pillow'] = PIL.__version__
        try:
            from PIL import features
            out['freetype'] = features.version('freetype2') or ''
        except Exception:
            out['freetype'] = ''
    except Exception:
        out['pillow'] = out['freetype'] = ''
    return out


def font_diff(lock):
    """字体逐个核哈希。缺文件不算差异，没跑 fetch_fonts.sh 而已。"""
    bad, missing = [], []
    for rel, want in lock.get('fonts', {}).items():
        if rel.startswith('_'):
            continue
        p = ROOT / rel
        if not p.is_file():
            missing.append(rel)
            continue
        got = hashlib.sha256(p.read_bytes()).hexdigest()
        if got != want:
            bad.append((rel, want, got))
    return bad, missing


def status():
    """-> (是否标准环境, 实况, 差异清单)"""
    lock = load()
    env = probe()
    want = lock['canonical_env']
    diff = []
    if env['container_digest'] != want['digest']:
        diff.append('容器镜像: 期望 %s，实得 %s'
                    % (want['digest'][:19] + '…',
                       env['container_digest'][:19] + '…' if env['container_digest']
                       else '（不在锁定容器里）'))
    if env['python'] != want['python']:
        diff.append('Python: 期望 %s，实得 %s' % (want['python'], env['python']))
    if env['pillow'] and env['pillow'] != lock['pip']['pillow']:
        diff.append('Pillow: 期望 %s，实得 %s' % (lock['pip']['pillow'], env['pillow']))
    bad, missing = font_diff(lock)
    for rel, w, g in bad:
        diff.append('字体 %s 内容不符（期望 %s… 实得 %s…）' % (rel, w[:12], g[:12]))
    return (not diff), env, diff, missing


def stamp():
    """一行环境指纹，写进产物报告，出了事能回溯是哪套工具链造的。"""
    env = probe()
    return ('python=%s pillow=%s freetype=%s platform=%s/%s container=%s'
            % (env['python'], env['pillow'] or '无', env['freetype'] or '无',
               env['platform'], env['machine'], env['container_digest'] or '无'))


def main():
    if '--stamp' in sys.argv:
        print(stamp())
        return
    if '--fonts' in sys.argv:
        bad, missing = font_diff(load())
        for rel, w, g in bad:
            print('❌ %s 内容与锁不符\n   期望 %s\n   实得 %s' % (rel, w, g))
        if missing:
            print('❌ 缺字体: %s' % ' '.join(missing))
        if bad or missing:
            sys.exit('字体与 src/toolchain.lock.json 对不上——上游换过版本，'
                     '或者这次下载不干净。核对无误后再更新锁。')
        print('✅ 字体逐个与 src/toolchain.lock.json 一致')
        return
    ok, env, diff, missing = status()
    print('工具链实况: %s' % stamp())
    if missing:
        print('  ℹ️ 未取的字体 %d 个（要重跑 gen_quest_banners.py 才需要）: %s'
              % (len(missing), ' '.join(Path(m).name for m in missing)))
    if ok:
        print('✅ 标准构建环境，产物字节可复现，verify_dist 可以按 sha256 硬比。')
        return
    print('⚠️ **不是**标准构建环境，本次产物的 sha256 不作数：')
    for d in diff:
        print('   -', d)
    print('   要可复现的产物就在锁定镜像里构建: ./scripts/build_in_container.sh')
    if '--strict' in sys.argv:
        sys.exit(1)


if __name__ == '__main__':
    main()
