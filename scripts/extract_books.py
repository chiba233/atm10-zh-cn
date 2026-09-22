#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# atm10-zh-cn — All the Mods 10 简体中文汉化补丁「绿油油版」
# Copyright (C) 2026 星野夢華 (Hoshino Yumeka)
# SPDX-License-Identifier: GPL-3.0-or-later
"""把导览书译文反解成映射，存进 src/books/。

## 为什么导览书不能整份提交

Patchouli / AE2 Guide / Modonomicon 这类导览书，译文是**上游 JSON 的整份副本**，
只有里面的字符串换成了中文。结构、页码、配方引用全是上游的。这意味着：

- 模组更新导览书（加一页、改配方、拆章节），我们那份旧副本会把新内容整个盖掉，
  玩家永远看不到，**而且没有任何报错**。
- 已现形的实例（2026-07-27 实测）：
  `pneumaticcraft/…/programming/conditions.json` 上游多出 `pages[8].entries[9]`，
  `pneumaticcraft/…/tools/drone.json` 上游的 `pages[7].title` / `pages[8]` 整段变了
  而我们那份错位——这两页此刻就在吞掉上游内容。

所以仓库里只留「哪个位置、原文是什么、译成什么」，构建时拿**目标版本 jar 里的
那份 JSON** 重新套一遍：上游加的页原样保留（暂时是英文），上游改过的位置会被点名。

## 三种文件、三种存法

| 类型 | 例子 | 存什么 |
|---|---|---|
| 结构型 JSON | patchouli 条目、`_meta.json` | `src/books/<路径>.json`：路径 + 原文 + 译文 |
| 散文 | `.md` / `.mdx` / `.txt` / `.gui` | 译文留在 `src/pack`，`_prose.json` 记英文源指纹 |
| 与上游完全相同 | 没翻的条目副本 | 只记一行路径，构建时从 jar 拷，不入库 |

## 怎么用

改导览书译文的正确流程是**改构建出来的那份**，再反解回映射：

    ATM_PACK_ROOT=<整合包目录> ./scripts/generate_all.sh     # 书生成到 build/common
    $EDITOR build/common/resourcepacks/ATM10汉化包/assets/…/x.json
    python3 scripts/extract_books.py <整合包目录>/mods        # 反解回 src/books/

本脚本**只更新它在译文树里真正看到的那些文件**，不动其余映射。早先它是「先清空
src/books/ 再从 src/pack 重建」，转换完成后 src/pack 里已经没有导览书了，
再跑一次就会把 988 份映射全删掉（2026-07-27 真踩了一次，靠 git 捞回来的）。

用法:
    python3 scripts/extract_books.py <该版 mods 目录> [译文树，默认 build 出来的资源包]
"""
import json
import sys
from collections import Counter
from pathlib import Path

import books
from paths import PACK as PACK_BUILT, SRC

PACK = SRC / 'pack'
# 这些前缀下的东西是导览书/手册，归本脚本管；lang/ 与本包独有资源不动
BOOK_DIRS = ('patchouli_books', 'ae2guide', 'modopedia', 'books', 'guides',
             'guidebook', 'guide', 'mi_guidebook', 'mj_guide', 'text',
             'manual', 'gui', '_zh_cn')
PROSE_EXT = {'.md', '.mdx', '.txt', '.gui', '.snbt'}


def is_book(rel):
    parts = rel.split('/')
    return len(parts) > 2 and parts[0] == 'assets' and parts[2] in BOOK_DIRS


def candidates(p):
    out = []
    if '/.translated/zh_cn/' in p:
        out.append(p.replace('/.translated/zh_cn/', '/'))
    if '/_zh_cn/' in p:
        out.append(p.replace('/_zh_cn/', '/', 1))
    if '/zh_cn/' in p:
        out.append(p.replace('/zh_cn/', '/en_us/'))
        out.append(p.replace('/zh_cn/', '/'))
    if p.endswith('-zh_cn.txt'):
        out.append(p[:-len('-zh_cn.txt')] + '.txt')
    out.append(p)
    seen, r = set(), []
    for c in out:
        if c not in seen:
            seen.add(c)
            r.append(c)
    return r


def main(mods_dir, tree=None):
    jars = books.Jars(mods_dir)
    print('jar 内条目 %d 条' % len(jars.index))
    src = Path(tree) if tree else PACK_BUILT
    if not src.is_dir():
        sys.exit('❌ 译文树不在: %s\n'
                 '   先跑: ATM_PACK_ROOT=<整合包目录> ./scripts/generate_all.sh' % src)
    print('译文取自: %s' % src)
    # **增量更新**：只动本次看到的文件，其余映射原样保留
    books.BOOKS.mkdir(parents=True, exist_ok=True)
    copies = json.loads(books.MAP_COPIES.read_text(encoding='utf-8')) \
        if books.MAP_COPIES.exists() else {}
    prose = json.loads(books.MAP_PROSE.read_text(encoding='utf-8')) \
        if books.MAP_PROSE.exists() else {}

    stat = Counter()
    odd = []
    for f in sorted(src.rglob('*')):
        if not f.is_file() or f.name == '.DS_Store':
            continue
        rel = f.relative_to(src).as_posix()
        if not is_book(rel):
            continue
        data = f.read_bytes()
        up_path = next((c for c in candidates(rel) if c in jars.index), None)
        if up_path is None:
            stat['上游没有（本包独有或模组不在整合包里）'] += 1
            continue
        up = jars.read(up_path)
        if books.sha1(up) == books.sha1(data):
            copies[rel] = up_path
            stat['与上游完全相同'] += 1
            continue
        if f.suffix.lower() in PROSE_EXT:
            ent = {'src': up_path, 'sha1': books.sha1(up)}
            # 版本文件层登记的是「另一份原稿指纹该去哪个中文整页」。重跑提取只更新
            # 当前底本，不能顺手把已核过的跨版本关系抹掉。
            old = prose.get(rel) or {}
            for field in ('equivalent_sha1', 'variants'):
                if old.get(field):
                    ent[field] = old[field]
            prose[rel] = ent
            stat['散文（记指纹）'] += 1
            continue
        if f.suffix.lower() != '.json':
            stat['二进制且与上游不同（本包重绘，原样保留）'] += 1
            continue
        try:
            en = json.loads(up.decode('utf-8-sig'))
            zh = json.loads(data.decode('utf-8-sig'))
        except Exception as e:
            odd.append((rel, 'JSON 解析失败: %r' % e))
            stat['解析失败（原样保留）'] += 1
            continue
        pe = dict(books.walk(en))
        matched = list(books.pair(en, zh))
        t = [[p, a, b] for p, a, b in matched if a != b]
        # 上游有、我们没对上的字符串位置：上游新加的内容，暂时保持英文
        untr = len(pe) - len(matched)
        if untr:
            odd.append((rel, '上游有 %d 处字符串我们没有对应译文（上游新增/改过，保持英文）' % untr))
            stat['上游有新内容（保持英文）'] += 1
        if not t:
            copies[rel] = up_path       # 结构同、字符串也同 → 等价于纯拷贝
            stat['与上游完全相同'] += 1
            continue
        books.dump(rel, {'src': up_path, 'sha1': books.sha1(up), 't': t})
        stat['结构型 JSON（转成映射）'] += 1

    books.MAP_COPIES.write_text(
        json.dumps(copies, ensure_ascii=False, indent=1, sort_keys=True) + '\n',
        encoding='utf-8')
    books.MAP_PROSE.write_text(
        json.dumps(prose, ensure_ascii=False, indent=1, sort_keys=True) + '\n',
        encoding='utf-8')

    print()
    for k, v in stat.most_common():
        print('  %-40s %5d' % (k, v))
    if odd:
        print('\n⚠️ 需要人工看的 %d 个：' % len(odd))
        for rel, why in odd:
            print('   %s\n      %s' % (rel, why))


if __name__ == '__main__':
    if len(sys.argv) not in (2, 3):
        sys.exit(__doc__)
    main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None)
