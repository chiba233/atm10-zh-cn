#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# atm10-zh-cn — All the Mods 10 简体中文汉化补丁「绿油油版」
# Copyright (C) 2026 星野夢華 (Hoshino Yumeka)
# SPDX-License-Identifier: GPL-3.0-or-later
"""按版本画像取单个 jar，而不是为了一个 jar 去下整包。

有些闸只需要某一个 mod 的数据文件（配方 / trees.json / lang），却要求
「该版本用的那一份」。以前这类闸只能挂在 build.yml 里 $NEWEST 那份完整包上，
于是只覆盖最新版，不是因为别的版本查不了，而是因为懒得单独取 jar。

`versions/db/<版本>/jars.json` 里每个 jar 都钉了 projectID / fileID / sha256，
够直接把那一个文件取回来并核到字节。fileID 在 CurseForge 是不可变的（重传会
得到新 ID），所以「fileID + sha256 都对上」＝拿到的就是该版本官方用的那一份。

核不上就红，绝不退而求其次：这类脚本一旦在取不到时静默返回，靠它的闸就
变成了「有网就查、没网就过」，比没有闸更糟。

同一个 fileID 在多个版本间常是同一份字节（7.1/7.2/7.3 的 Productive Trees 都是
fileID 8190022），但它们各去各的 build/packsrc/<版本>/mods，「目标位置已有」
判断不到，于是同一份字节会被下三遍。所以缓存按内容寻址放在
build/jarcache/<sha256>.jar，跨版本、跨多次运行都命中。

缓存条目自带校验：文件名就是它应有的 sha256，读出来对不上就当没有这个缓存、
重新下载覆盖，损坏的缓存不许被信任，也不许因为「有个文件在那儿」就跳过下载。

    python3 scripts/fetch_one_jar.py 7.0 productivetrees build/packsrc/7.0/mods
"""
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from fetch_pack import fetch                                     # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / 'build' / 'jarcache'
DL = 'https://www.curseforge.com/api/v1/mods/%d/files/%d/download'


def die(msg):
    sys.exit('❌ %s' % msg)


def pick(ver, prefix):
    """从该版本的 jar 基线里挑出唯一一个匹配项。

    要求恰好一个：前缀写宽了会同时命中 productivetrees 与
    productivebees 这类邻居，取第一个等于让闸去查一个不相干的 mod。
    """
    db = ROOT / 'versions' / 'db' / ver / 'jars.json'
    if not db.is_file():
        die('没有 %s——这个版本还没入库，谈不上按画像取文件' % db)
    jars = json.loads(db.read_text(encoding='utf-8')).get('jars')
    if not isinstance(jars, dict) or not jars:
        die('%s 里没有 jars 表' % db)
    hit = sorted(n for n in jars if n.lower().startswith(prefix.lower()))
    if len(hit) != 1:
        die('ATM10 %s 里以 %r 开头的 jar 应恰有一个，实际 %d 个：%s'
            % (ver, prefix, len(hit), '、'.join(hit) or '（无）'))
    name = hit[0]
    rec = jars[name]
    for field in ('projectID', 'fileID', 'sha256'):
        if not rec.get(field):
            die('%s 的 %s 条目缺 %s，无法锚定字节' % (db, name, field))
    return name, rec


def cached(sha):
    """内容寻址缓存里取字节。每次都重算哈希，缓存条目自证，不认文件名。"""
    p = CACHE / (sha + '.jar')
    if not p.is_file():
        return None
    data = p.read_bytes()
    if hashlib.sha256(data).hexdigest() == sha:
        return data
    print('⚠️ 缓存 %s 内容与文件名不符，当作没有，重新下载覆盖' % p, file=sys.stderr)
    return None


def main(argv):
    if len(argv) != 3:
        die(__doc__.strip().splitlines()[-1].strip())
    ver, prefix, outdir = argv
    name, rec = pick(ver, prefix)
    out = Path(outdir)
    out.mkdir(parents=True, exist_ok=True)
    dest = out / name

    if dest.is_file():
        got = hashlib.sha256(dest.read_bytes()).hexdigest()
        if got == rec['sha256']:
            print('✅ %s 已在 %s 且哈希正确，跳过下载' % (name, outdir))
            return 0
        die('%s 已存在但哈希不符：本地 %s，基线 %s' % (dest, got, rec['sha256']))

    data = cached(rec['sha256'])
    source = '缓存命中'
    if data is None:
        source = '已下载'
        data, final = fetch(DL % (rec['projectID'], rec['fileID']), required=False)
        if not data:
            die('取 %s（fileID %d）失败：%s' % (name, rec['fileID'], final))
        got = hashlib.sha256(data).hexdigest()
        if got != rec['sha256']:
            # 不写盘：留下一个哈希不符的文件，下一次运行会被上面那条当成
            # 「已存在但不符」再红一次，看着像两个问题。
            die('%s（fileID %d）字节与基线不符：拿到 %s，基线 %s'
                % (name, rec['fileID'], got, rec['sha256']))
        if len(data) != rec.get('size', len(data)):
            die('%s 大小与基线不符：拿到 %d，基线 %d' % (name, len(data), rec['size']))
        CACHE.mkdir(parents=True, exist_ok=True)
        (CACHE / (rec['sha256'] + '.jar')).write_bytes(data)
    dest.write_bytes(data)
    print('✅ ATM10 %s 的 %s → %s（%d 字节，%s，sha256 已核）'
          % (ver, name, outdir, len(data), source))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
