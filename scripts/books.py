#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# atm10-zh-cn — All the Mods 10 简体中文汉化补丁「绿油油版」
# Copyright (C) 2026 星野夢華 (Hoshino Yumeka)
# SPDX-License-Identifier: GPL-3.0-or-later
"""导览书汉化的共用部分：jar 索引、JSON 路径遍历、映射文件读写。

被 extract_books.py（提取，开发时用）与 gen_books.py（套用，构建时用）共用。
"""
import hashlib
import json
import zipfile
from pathlib import Path

from paths import SRC

BOOKS = SRC / 'books'
MAP_COPIES = BOOKS / '_copies.json'      # 与上游字节相同：不入库，构建时从 jar 拷
MAP_PROSE = BOOKS / '_prose.json'        # 散文型：译文在 src/pack，这里只记英文源指纹


class Jars:
    """把一堆 mod jar 当成一个只读文件系统用。"""

    def __init__(self, mods_dir):
        self.dir = Path(mods_dir)
        self.index = {}
        self._open = {}
        for jar in sorted(self.dir.glob('*.jar')):
            try:
                z = zipfile.ZipFile(jar)
            except Exception:
                continue
            for n in z.namelist():
                if not n.endswith('/'):
                    self.index.setdefault(n, jar.name)

    def read(self, path):
        jar = self.index.get(path)
        if jar is None:
            return None
        if jar not in self._open:
            self._open[jar] = zipfile.ZipFile(self.dir / jar)
        return self._open[jar].read(path)

    def text(self, path):
        b = self.read(path)
        return None if b is None else b.decode('utf-8-sig')


def sha1(b):
    return hashlib.sha1(b).hexdigest()


def walk(obj, pre=()):
    """产出 (JSON 路径, 字符串值)。路径是 ('pages', 0, 'text') 这样的元组，
    不能用 `.pages[0].text` 那种拼接串：Oracle Index 的 `_meta.json` 里
    键名本身就带点（`addons.mdx`），拼出来的路径没法还原。"""
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield from walk(v, pre + (k,))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from walk(v, pre + (i,))
    elif isinstance(obj, str):
        yield pre, obj


def signature(o):
    """一个 JSON 结点的「形状」，用来在列表里给中英文元素配对。
    译文和原文的字符串完全不同，只能靠形状对齐。"""
    if isinstance(o, dict):
        return 'd:' + ','.join(sorted(o))
    if isinstance(o, list):
        return 'l:%d' % len(o)
    return 't:' + type(o).__name__


def pair(en, zh, pre=()):
    """同时走中英文两棵树，产出 (英文路径, 英文串, 中文串)。

    列表按形状对齐（difflib），所以上游在中间插一页不会让后面的译文整体错位，
    这正是 pneumaticcraft 的 drone.json 踩到的坑：上游在 pages[7] 插了一页，
    按下标硬对会把第 8 页的中文糊到第 7 页上。

    只产出两边都有的位置：上游新增的（没译文）保持英文，我们多出来的（上游已删）丢弃。
    """
    if isinstance(en, dict) and isinstance(zh, dict):
        for k in en:
            if k in zh:
                yield from pair(en[k], zh[k], pre + (k,))
        return
    if isinstance(en, list) and isinstance(zh, list):
        from difflib import SequenceMatcher
        se = [signature(x) for x in en]
        sz = [signature(x) for x in zh]
        for tag, i1, i2, j1, j2 in SequenceMatcher(None, se, sz, autojunk=False).get_opcodes():
            if tag != 'equal':
                continue
            for a, b in zip(range(i1, i2), range(j1, j2)):
                yield from pair(en[a], zh[b], pre + (a,))
        return
    # Oracle Index 的 _meta.json：上游用字符串简写，我们那份用 {"name": …} 完整形态
    if isinstance(en, str) and isinstance(zh, dict) and isinstance(zh.get('name'), str):
        yield pre, en, zh['name']
        return
    if isinstance(en, str) and isinstance(zh, str):
        yield pre, en, zh


def get_at(obj, path):
    """按 walk 产出的路径取值。取不到返回 None。"""
    cur = obj
    for step in path:
        try:
            cur = cur[step]
        except (KeyError, IndexError, TypeError):
            return None
    return cur


def set_at(obj, path, value):
    cur = obj
    for step in path[:-1]:
        cur = cur[step]
    cur[path[-1]] = value


def load(rel):
    """读一个导览书映射（rel 是资源包内相对路径）"""
    p = BOOKS / (rel + '.json')
    return json.loads(p.read_text(encoding='utf-8')) if p.exists() else None


def dump(rel, doc):
    # 条目按 JSON 路径排序：重跑提取必须逐字节幂等，否则每次都出一堆纯顺序的假 diff
    if 't' in doc:
        doc['t'] = sorted(doc['t'], key=lambda e: [(1, str(x)) if isinstance(x, str)
                                                   else (0, '%09d' % x) for x in e[0]])
    p = BOOKS / (rel + '.json')
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(doc, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
