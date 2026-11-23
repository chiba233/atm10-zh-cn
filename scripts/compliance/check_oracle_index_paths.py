#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# atm10-zh-cn — All the Mods 10 简体中文汉化补丁「绿油油版」
# Copyright (C) 2026 星野夢華 (Hoshino Yumeka)
# SPDX-License-Identifier: GPL-3.0-or-later
"""神谕目录的书有两套目录约定，放错那条路径的译文永远不会被读。

## 为什么要这道闸

Oracle Index 按书里的 `sinytra-wiki.json` 选解析器（`DocsIndexer.detectDocsFormat`
读它的 `schema` 字段，`equals("1")` 才走 V1）：

    V1DocsFormat      content/      translated/       ← 不带点
    LegacyDocsFormat  .content/     .translated/      ← 带点

两套路径长得几乎一样，放错了不报错、不留日志，书照常显示，只是显示英文。
本仓库两套都有：正确路径下是生效的那份，另一条路径下留着历史遗留的旧文件。
旧文件是有意保留的（仓库主人的惯例是「不影响就不删」），所以这道闸只拦
「有译文放错了地方、导致该显示中文的地方显示英文」，对残留文件只报个数、不拦。

各版本的 mod 版本不同、schema 声明也可能不同，所以按版本各判一次。

## 判定

出货树里每个 `assets/oracle_index/books/<书>/` 下，我们放的译文目录必须与该版本
mod jar 里那本书声明的 schema 相符。不符就报出来，并写清该挪到哪。

## fail-closed

mods 目录不在、书在 jar 里找不到、sinytra-wiki.json 读不出来、
出货树里一本书都没有，全部当红。放错路径本来就是「静默失效」，
再让闸也静默跳过，等于两层都不设防。

用法:
    python3 scripts/compliance/check_oracle_index_paths.py <mods 目录> <出货树>
"""
import json
import sys
import zipfile
from pathlib import Path

BOOKS = 'resourcepacks/ATM10汉化包/assets/oracle_index/books'
IN_JAR = 'assets/oracle_index/books/%s/sinytra-wiki.json'


def die(msg):
    print('❌ %s' % msg)
    sys.exit(1)


def schema_of(mods, book):
    """从整合包的 jar 里现读那本书声明的 schema。找不到就红。"""
    want = IN_JAR % book
    found = []
    for jar in sorted(Path(mods).glob('*.jar')):
        try:
            with zipfile.ZipFile(jar) as z:
                if want in z.namelist():
                    found.append((jar.name, json.loads(z.read(want))))
        except Exception:
            continue
    if not found:
        die('%s 里没有任何 jar 提供 %s —— 这本书不在这一版整合包里，'
            '或者 mods 目录不对；判不了就不许放行' % (mods, want))
    if len({json.dumps(m, sort_keys=True) for _, m in found}) > 1:
        die('%s 被多个 jar 提供且内容不一致：%s' % (want, [n for n, _ in found]))
    return str(found[0][1].get('schema', '')), found[0][0]


def content_rels(base):
    """一本书的正文相对路径（只认 content/docs 那两棵，忽略别的杂物）。"""
    out = set()
    if not base.is_dir():
        return out
    for p in base.rglob('*'):
        if not p.is_file():
            continue
        rel = p.relative_to(base)
        if rel.parts and rel.parts[0].lstrip('.') in ('content', 'docs'):
            out.add(rel.as_posix())
    return out


def main(argv):
    if len(argv) != 3:
        die('用法: check_oracle_index_paths.py <mods 目录> <出货树>')
    mods, tree = argv[1], Path(argv[2])
    root = tree / BOOKS
    if not root.is_dir():
        die('%s 不在 —— 资源包没摊出来，这道闸等于没跑' % root)
    books = sorted(p.name for p in root.iterdir() if p.is_dir())
    if not books:
        die('%s 下一本书都没有' % root)

    bad = []
    for b in books:
        schema, jar = schema_of(mods, b)
        right = 'translated' if schema == '1' else '.translated'
        wrong = '.translated' if schema == '1' else 'translated'
        for lang in sorted({d.name for d in (root / b / wrong).glob('*') if d.is_dir()} |
                           {d.name for d in (root / b / right).glob('*') if d.is_dir()}):
            miss = content_rels(root / b / wrong / lang) - content_rels(root / b / right / lang)
            if miss:
                bad.append((b, jar, schema, wrong, right, lang, sorted(miss)))
        stale = sum(1 for p in (root / b / wrong).rglob('*') if p.is_file())
        n = sum(1 for p in (root / b / right).rglob('*') if p.is_file())
        print('%s 《%s》%s → 只读 %s/（%d 个文件）%s'
              % ('❌' if any(x[0] == b for x in bad) else '✅', b, 
                 'schema=%s' % (schema or '无'), right, n,
                 '；%s/ 下另有 %d 个不生效的旧文件（有意保留，不影响）' % (wrong, stale) if stale else ''))

    if bad:
        print()
        print('❌ 这些译文放在本版不会被读取的路径上，等于没翻：')
        for b, jar, schema, wrong, right, lang, miss in bad:
            print('   《%s》%s 声明 schema=%s，%s/%s/ 下有 %d 个正文文件在 %s/%s/ 里找不到'
                  % (b, jar, schema or '无', wrong, lang, len(miss), right, lang))
            for m in miss[:5]:
                print('      %s' % m)
            if len(miss) > 5:
                print('      …… 还有 %d 个' % (len(miss) - 5))
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
