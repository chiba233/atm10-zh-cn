#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# atm10-zh-cn — All the Mods 10 简体中文汉化补丁「绿油油版」
# Copyright (C) 2026 星野夢華 (Hoshino Yumeka)
# SPDX-License-Identifier: GPL-3.0-or-later
"""把 src/upstream/ 里的映射套用到**目标版本的官方文件**上。

仓库里没有任何一份上游文件的副本（见 extract_upstream_patch.py 里的原因），
构建时现取官方文件、套上我们的改动。

**找不到原文就退出，绝不静默跳过。** 这条是整套结构的支点：
上游哪天把某行改了，构建当场红给你看，而不是发出去一个「旧上游 + 我们的改动」
——那种包会把上游的修复整个覆盖掉，还没人发现。

唯一的例外走 `versions/<版本>/unpatchable.json`：上游在**某一个版本**里把这段原文
删了或重写了，而别的版本还在。这种情况不能靠删映射解决（删了老版本就一起没了），
只能按版本登记。登记是**逐条**的，而且两头都 fail-closed：

- 登记了、但那段原文其实还在 → 红（登记过期了，上游又把它加回来了）
- 没登记、又找不到原文 → 红（原来的行为，一个字没松）
- 登记的文件不在 src/upstream 里、序号越界、没写 why → 红

也就是说这个口子只能让「已经查清楚、写明了理由」的那几条过，越不过任何别的东西。

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
            # 登记成「该版不适用」的，**照样先查一遍**。查得到就说明登记过期了
            # （上游把这段又加回来了，或者当初登记错了），这时候必须红——
            # 登记过就无条件放过的话，这里就成了一个静默跳过的口子，
            # 而静默跳过正是这个脚本存在的理由要挡的东西。
            if at:
                sys.exit('❌ %s 第 %d 处改动登记成了「该版不适用」，但在官方文件里找得到（%d 处）。\n'
                         '   登记已经过期：去掉 versions/<版本>/unpatchable.json 里的这一条，'
                         '让它照常生效。' % (rel, k, len(at)))
            continue
        # all=true：这一段在文件里出现几次就换几次。任务书的 hover 就是这样——
        # 同一件物品在一章里被提到好几遍，英文一模一样，中文当然也该一模一样，
        # 为了「唯一」去凑上下文只会让映射变脆（上游动一行就全崩）。
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
    """读该版的「不适用条目」登记表，返回 {映射的 src 路径: {序号…}}。

    sizes = {src 路径: 该映射有几处改动}，用来验序号确实存在——登记一个不存在的
    序号，跟登记错文件一样是「以为登记了、其实没登记上」，必须当场红。
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
                     '把它改成了什么样——否则下一版没人知道该不该撤掉登记。'
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
    total = skipped = 0
    for mp, doc in zip(maps, docs):
        rel = doc['src']
        official = pack_root / rel
        if not official.is_file():
            sys.exit('❌ 目标版本里没有这个官方文件：%s\n'
                     '   （整合包根目录: %s）\n'
                     '   上游删掉了它的话，把 %s 一起删掉。' % (rel, pack_root, mp.relative_to(ROOT)))
        skip = skips.get(rel, frozenset())
        text = apply_one(official.read_text(encoding='utf-8'), doc['edits'], rel, skip)
        t = out_dir / rel
        t.parent.mkdir(parents=True, exist_ok=True)
        t.write_text(text, encoding='utf-8', newline='')
        total += len(doc['edits']) - len(skip)
        skipped += len(skip)
    print('上游文件汉化：%d 个文件、%d 处改动 → %s' % (len(maps), total, out_dir))
    if skipped:
        # 出货侧少了几处一定要说出来。不说的话，「这一版比别版少 37 条」就成了
        # 只有翻日志才看得见的事，跟静默跳过没区别。
        print('  按 versions/%s/unpatchable.json 不出货 %d 处（上游在这一版删了或重写了原文）：%s'
              % (version, skipped, '、'.join(sorted(skips))))


if __name__ == '__main__':
    # 版本是必填的：少传一个参数就当没有登记表，等于把 unpatchable.json 悄悄作废。
    if len(sys.argv) != 4:
        sys.exit(__doc__)
    main(sys.argv[1], sys.argv[2], sys.argv[3])
