#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# atm10-zh-cn — All the Mods 10 简体中文汉化补丁「绿油油版」
# Copyright (C) 2026 星野夢華 (Hoshino Yumeka)
# SPDX-License-Identifier: GPL-3.0-or-later
"""把 src/upstream/ 里的映射套到目标版本的官方文件上。

仓库里没有上游文件的副本（原因见 extract_upstream_patch.py），构建时取官方文件，套上本包的改动。

找不到原文就退出：上游改了某一行时构建失败，否则发出去的是「旧上游 + 本包改动」，会覆盖上游的修复。

唯一的例外是 `versions/<版本>/unpatchable.json`：上游在某个版本里删除或重写了这段原文，而别的版本
还在，删映射会连老版本一起删，所以按版本逐条登记。登记两个方向都检查：

- 登记了但原文其实还在，失败（登记过期，上游又加回来了）
- 没登记又找不到原文，失败
- 登记的文件不在 src/upstream 里、序号越界、没写 why，失败

登记只表示「这一版不改」。上游只在某一版把那段改成了别的样子，而本包仍要翻译时（例如 8.0 给公告
清单每行加了分号），在 `versions/<版本>/upstream/` 下按同样格式放一份该版专属映射：先套通用映射
（登记过的跳过），再在同一份文本上套该版的。找不到原文同样退出。改动的文件在 `src/upstream/`
下没有对应映射也退出，那种映射永远不会执行。

用法:
    python3 scripts/gen_upstream_patches.py <整合包根目录> <输出目录> <整合包版本>
    # 整合包根目录 = 解出来的 overrides/，或装好的实例目录
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / 'src' / 'upstream'


def apply_one(text, edits, rel, skip=frozenset()):
    lines = text.splitlines(keepends=True)
    for k, e in enumerate(edits, 1):
        find, repl = e['find'], e['replace']
        n, m = len(lines), len(find)
        at = [i for i in range(n - m + 1) if lines[i:i + m] == find]
        if k in skip:
            # 登记为该版不适用的也先查一遍，查得到说明登记过期了（上游又加回来了，或者登记错了），
            # 必须失败，否则登记过的条目会被静默跳过。
            if at:
                sys.exit('❌ %s 第 %d 处改动登记成了「该版不适用」，但在官方文件里找得到（%d 处）。\n'
                         '   登记已经过期：去掉 versions/<版本>/unpatchable.json 里的这一条，'
                         '让它照常生效。' % (rel, k, len(at)))
            continue
        # all=true：这一段在文件里出现几次就换几次。例如任务书的 hover，同一件物品在一章里被提到
        # 好几次，英文相同，中文也应相同。为了唯一去拼上下文，会让映射在上游改一行时全部失效。
        if e.get('all'):
            if not at:
                sys.exit('❌ %s 第 %d 处改动在官方文件里找不到\n   原文首行: %r'
                         % (rel, k, (find[0] if find else '').rstrip('\r\n')[:100]))
            for i in reversed(at):
                lines[i:i + m] = repl
            continue
        if len(at) != 1:
            head = (find[0] if find else '').rstrip('\r\n')[:100]
            sys.exit(
                '❌ %s 第 %d 处改动在官方文件里%s\n'
                '   原文首行: %r\n'
                '   多半是上游改了这一段。请拿新版官方文件重做映射：\n'
                '     python3 scripts/extract_upstream_patch.py <官方文件> <改过的文件> %s'
                % (rel, k, '找不到' if not at else '出现了 %d 次' % len(at), head, rel))
        i = at[0]
        lines[i:i + m] = repl
    return ''.join(lines)


def load_unpatchable(version, sizes):
    """读该版的不适用条目登记，返回 {映射的 src 路径: {序号…}}。

    sizes = {src 路径: 该映射有几处改动}，用来检查序号确实存在。登记了不存在的序号，
    与登记错文件一样等于没登记上，必须失败。
    """
    p = ROOT / 'versions' / version / 'unpatchable.json'
    if not p.is_file():
        return {}
    doc = json.loads(p.read_text(encoding='utf-8'))
    out = {}
    for rel, ent in (doc.get('edits') or {}).items():
        if rel not in sizes:
            sys.exit('❌ %s 登记了 %s，但 src/upstream 下没有哪份映射改这个文件。'
                     % (p.relative_to(ROOT), rel))
        if not str(ent.get('why') or '').strip():
            sys.exit('❌ %s 里 %s 没写 why。登记一条不适用，必须写清楚上游在这一版'
                     '把它改成了什么样，下一版才能判断该不该撤掉登记。'
                     % (p.relative_to(ROOT), rel))
        n, which = sizes[rel], ent.get('which')
        if which == 'all':
            out[rel] = set(range(1, n + 1))
            continue
        if not (isinstance(which, list) and which
                and all(isinstance(i, int) and 1 <= i <= n for i in which)):
            sys.exit('❌ %s 里 %s 的 which 不对：要么写 "all"，要么写 1 起算的序号列表'
                     '（这份映射共 %d 处改动，序号就用报错信息里的「第 N 处」）。'
                     % (p.relative_to(ROOT), rel, n))
        out[rel] = set(which)
    return out


def main(pack_root, out_dir, version):
    pack_root, out_dir = Path(pack_root), Path(out_dir)
    if not SRC.is_dir():
        sys.exit('❌ 没有 %s' % SRC)
    maps = sorted(SRC.rglob('*.json'))
    if not maps:
        sys.exit('❌ %s 下一个映射都没有' % SRC)
    docs = [json.loads(mp.read_text(encoding='utf-8')) for mp in maps]
    skips = load_unpatchable(version, {d['src']: len(d['edits']) for d in docs})
    # 该版专属的映射：上游只在这一版把某段改成了别的样子（例如 8.0 给公告清单每行加了分号），
    # 通用映射不能同时匹配两版，所以按版本另给一份。格式与规则同 src/upstream/，找不到原文同样退出。
    vdir = ROOT / 'versions' / version / 'upstream'
    vmaps = sorted(vdir.rglob('*.json')) if vdir.is_dir() else []
    vdocs = {}
    for vp in vmaps:
        d = json.loads(vp.read_text(encoding='utf-8'))
        if d['src'] in vdocs:
            sys.exit('❌ %s 与 %s 都改 %s，同一个文件只能有一份该版映射。'
                     % (vp.relative_to(ROOT), vdocs[d['src']][0], d['src']))
        vdocs[d['src']] = (vp.relative_to(ROOT), d)
    total = skipped = vtotal = 0
    for mp, doc in zip(maps, docs):
        rel = doc['src']
        official = pack_root / rel
        if not official.is_file():
            sys.exit('❌ 目标版本里没有这个官方文件：%s\n'
                     '   （整合包根目录: %s）\n'
                     '   上游删掉了它的话，把 %s 一起删掉。' % (rel, pack_root, mp.relative_to(ROOT)))
        skip = skips.get(rel, frozenset())
        text = apply_one(official.read_text(encoding='utf-8'), doc['edits'], rel, skip)
        if rel in vdocs:
            # 在同一份文本上接着套该版专属的改动，不另写文件：覆盖写会丢掉上面通用映射的改动。
            vp, vd = vdocs.pop(rel)
            text = apply_one(text, vd['edits'], rel)
            vtotal += len(vd['edits'])
        t = out_dir / rel
        t.parent.mkdir(parents=True, exist_ok=True)
        t.write_text(text, encoding='utf-8', newline='')
        total += len(doc['edits']) - len(skip)
        skipped += len(skip)
    if vdocs:
        # 该版映射改的文件在 src/upstream 里没有对应映射，它永远不会执行，必须失败。
        sys.exit('❌ 这些该版映射改的文件，src/upstream 下没有任何映射，永远不会被套用：\n   %s'
                 % '\n   '.join('%s（%s）' % (r, v[0]) for r, v in sorted(vdocs.items())))
    print('上游文件汉化：%d 个文件、%d 处改动 → %s' % (len(maps), total, out_dir))
    if vtotal:
        print('  另按 versions/%s/upstream/ 套用该版专属改动 %d 处（%d 个文件）'
              % (version, vtotal, len(vmaps)))
    if skipped:
        # 出货时少套用的条数要打印出来，否则「这一版比别的版本少 37 条」只有翻日志才看得到。
        print('  按 versions/%s/unpatchable.json 不出货 %d 处（上游在这一版删了或重写了原文）：%s'
              % (version, skipped, '、'.join(sorted(skips))))


if __name__ == '__main__':
    # 版本必填：少传一个参数就读不到登记表，unpatchable.json 等于失效。
    if len(sys.argv) != 4:
        sys.exit(__doc__)
    main(sys.argv[1], sys.argv[2], sys.argv[3])
