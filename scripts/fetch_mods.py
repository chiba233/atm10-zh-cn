#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# atm10-zh-cn — All the Mods 10 简体中文汉化补丁「绿油油版」
# Copyright (C) 2026 星野夢華 (Hoshino Yumeka)
# SPDX-License-Identifier: GPL-3.0-or-later
"""按 `src/mods.lock.json` 下载随包分发的第三方 jar，逐个核对 sha256，对不上就退出。

缓存在 `build/modcache/<sha256>.jar`。只在 CurseForge 上发布的 jar（如 jecharacters）
按 fileID 经 `/api/v1/mods/<id>/files` 与 `/files/<id>/download` 下载，搜索接口会拦截脚本。
许可证正文一起下载，放在 jar 旁边，MIT 要求再分发时附上。

用法:
    python3 scripts/fetch_mods.py <输出目录>       # 一般是 build/common
"""
import hashlib
import json
import sys
import urllib.request
from pathlib import Path

from paths import BUILD, ROOT, SRC

LOCK = SRC / 'mods.lock.json'
CACHE = BUILD / 'modcache'
UA = {'User-Agent': 'atm10-zh-cn/1.0 (+https://github.com/chiba233/atm10-zh-cn)'}


def sha256(b):
    return hashlib.sha256(b).hexdigest()


def get(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=180) as r:
        return r.read()


def main(out_dir):
    if not LOCK.is_file():
        sys.exit('❌ 没有 %s' % LOCK)
    lock = json.loads(LOCK.read_text(encoding='utf-8'))
    out = Path(out_dir)
    CACHE.mkdir(parents=True, exist_ok=True)
    for rel, info in sorted(lock.items()):
        want = info['sha256']
        cached = CACHE / (want + '.jar')
        if not cached.exists():
            data = get(info['url'])
            got = sha256(data)
            if got != want:
                sys.exit('❌ %s 哈希对不上，不要使用这个文件\n'
                         '   期望 %s\n   实得 %s\n   地址 %s\n'
                         '   上游换了同一地址的内容，或下载被篡改。'
                         % (rel, want, got, info['url']))
            cached.write_bytes(data)
        else:
            # 缓存也要复核，磁盘上的文件同样可能被改
            if sha256(cached.read_bytes()) != want:
                cached.unlink()
                sys.exit('❌ 缓存 %s 哈希对不上，已删除，请重跑' % cached)
        t = out / rel
        t.parent.mkdir(parents=True, exist_ok=True)
        t.write_bytes(cached.read_bytes())
        # MIT / Apache 这类许可要求再分发时附许可全文，jar 里没有就放在旁边
        if info.get('license_file'):
            # 仓库里已有这份许可证正文（如 GPL-3.0）就直接用：容器里取不到 gnu.org。
            # 正文必须逐字节等于许可证原文，用哈希固定：它随别人的 jar 分发，
            # 不能带本项目的版权声明。
            src = ROOT / info['license_file']
            data = src.read_bytes()
            want_lic = info.get('license_file_sha256')
            if not want_lic:
                sys.exit('❌ %s 记了 license_file，却没记 license_file_sha256' % rel)
            if sha256(data) != want_lic:
                sys.exit('❌ %s 的许可证正文 %s 哈希对不上\n'
                         '   期望 %s\n   实得 %s\n'
                         '   这份文件随第三方 jar 分发，必须是许可证原文本身，'
                         '不得掺入本项目的版权声明。'
                         % (rel, info['license_file'], want_lic, sha256(data)))
            (t.parent / ('LICENSE-%s.txt' % info.get('project', 'third-party'))
             ).write_bytes(data)
        elif info.get('license_url'):
            lic = CACHE / (info['license_sha256'] + '.txt')
            if not lic.exists():
                data = get(info['license_url'])
                if sha256(data) != info['license_sha256']:
                    sys.exit('❌ %s 的许可证正文哈希对不上' % rel)
                lic.write_bytes(data)
            (t.parent / ('LICENSE-%s.txt' % info.get('project', 'third-party'))
             ).write_bytes(lic.read_bytes())
        print('  %-28s %s %s (%d KB)'
              % (rel, info.get('project', ''), info.get('version', ''),
                 len(cached.read_bytes()) // 1024))
    print('随包 jar：%d 个，sha256 全部核对通过' % len(lock))


if __name__ == '__main__':
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(sys.argv[1])
