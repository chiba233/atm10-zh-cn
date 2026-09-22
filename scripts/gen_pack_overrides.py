#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# atm10-zh-cn — All the Mods 10 简体中文汉化补丁「绿油油版」
# Copyright (C) 2026 星野夢華 (Hoshino Yumeka)
# SPDX-License-Identifier: GPL-3.0-or-later
"""把 versions/<版本>/pack_overrides.json 叠到该版出货树的资源包上。

资源包译文按**命名空间 + 键**索引，同一个键在哪个整合包版本都是同一个键，
所以 src/pack 是版本中立的、一份通吃六个版本。这个前提会被上游打破：

同一个键在两版里**参数个数不同**时，一份中文没法同时对两版成立。少写参数只是
漏掉一段文字；多写参数会让 TranslatableContents 抛 TranslatableFormatException，
那一行直接显示成未替换的模板。此时只能按版本分叉。

任务书那一侧早就有 versions/<版本>/quest_overrides.snbt，这里是同一个东西的
资源包版。除了 lang 单键，还允许引用 `src/pack_overrides/<层名>/` 里的整文件覆盖：
散文导览书没有可定点替换的键，上游改写正文时只能整页分叉。

**它是例外口子，不是常规去处**：能在 src/pack 里一份写对的，就不要往这里写——
每多一条，七个版本之间就多一处要各自核对的分叉。

口子两头都 fail-closed：

- 覆盖的命名空间在出货树里没有 zh_cn.json → 红（写错了地方，这条永远不生效）
- 覆盖的值/文件与公共树里的**完全相同** → 红（登记过期了）
- 文件层不存在、为空、目标不在公共树、两层撞同一路径 → 红
- 没写 why、值不是字符串、JSON 坏了 → 红

用法:
    python3 scripts/gen_pack_overrides.py <版本> <出货树>
"""
import json
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main(ver, tree):
    p = ROOT / 'versions' / ver / 'pack_overrides.json'
    if not p.is_file():
        return
    try:
        doc = json.loads(p.read_text(encoding='utf-8'))
    except Exception as e:                                       # noqa: BLE001
        sys.exit('❌ %s 解析失败：%s' % (p.relative_to(ROOT), e))
    tree = Path(tree)
    n = 0
    for ns, entries in sorted((doc.get('lang') or {}).items()):
        f = next(tree.glob('resourcepacks/*/assets/%s/lang/zh_cn.json' % ns), None)
        if f is None:
            sys.exit('❌ %s 覆盖了命名空间 %s，但出货树里没有它的 zh_cn.json——'
                     '这条覆盖永远不会生效。' % (p.relative_to(ROOT), ns))
        d = json.loads(f.read_text(encoding='utf-8'))
        for key, ent in sorted(entries.items()):
            if not isinstance(ent, dict) or not isinstance(ent.get('value'), str):
                sys.exit('❌ %s 里 %s/%s 的 value 不是字符串。'
                         % (p.relative_to(ROOT), ns, key))
            if not str(ent.get('why') or '').strip():
                sys.exit('❌ %s 里 %s/%s 没写 why。覆盖一条，必须写清这一版为什么'
                         '不能跟公共树一样——否则下一版没人知道该不该撤掉它。'
                         % (p.relative_to(ROOT), ns, key))
            if d.get(key) == ent['value']:
                sys.exit('❌ %s 里 %s/%s 与公共树的值完全相同，这条覆盖是白写的。\n'
                         '   多半是公共树已经改成同样的写法了：去掉这一条。'
                         % (p.relative_to(ROOT), ns, key))
            d[key] = ent['value']
            n += 1
        f.write_text(json.dumps(d, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

    # 散文书页这类没有 lang key，只能整文件分叉。先把**所有层**完整预检完再写：
    # 若第二层坏了才退出，第一层已经写进树，会留下半套覆盖供后续步骤误用。
    layers = doc.get('files') or {}
    if not isinstance(layers, dict):
        sys.exit('❌ %s 的 files 不是对象。' % p.relative_to(ROOT))
    packs = sorted(x for x in (tree / 'resourcepacks').glob('*') if x.is_dir())
    planned = {}
    for name, ent in sorted(layers.items()):
        if not re.fullmatch(r'[a-z0-9][a-z0-9._-]*', name):
            sys.exit('❌ %s 的文件层名 %r 非法；只许小写字母、数字、点、横线、下划线。'
                     % (p.relative_to(ROOT), name))
        if not isinstance(ent, dict) or not str(ent.get('why') or '').strip():
            sys.exit('❌ %s 里的文件层 %s 没写 why。整页分叉必须说明版本边界。'
                     % (p.relative_to(ROOT), name))
        src = ROOT / 'src' / 'pack_overrides' / name
        files = sorted(x for x in src.rglob('*') if x.is_file()) if src.is_dir() else []
        if not files:
            sys.exit('❌ %s 登记了文件层 %s，但 %s 不存在或为空。'
                     % (p.relative_to(ROOT), name, src.relative_to(ROOT)))
        if len(packs) != 1:
            sys.exit('❌ %s 要套文件层 %s，但出货树里资源包目录应恰有一个，实际 %d 个。'
                     % (p.relative_to(ROOT), name, len(packs)))
        for source in files:
            if source.is_symlink():
                sys.exit('❌ 文件层 %s 里不许放符号链接：%s' % (name, source))
            rel = source.relative_to(src)
            if not rel.parts or rel.parts[0] != 'assets':
                sys.exit('❌ 文件层 %s 的 %s 不在 assets/ 下。' % (name, rel))
            dest = packs[0] / rel
            if not dest.is_file():
                sys.exit('❌ %s 的文件层 %s 要覆盖 %s，但公共树里没有这个文件——'
                         '路径写错或公共层已变。' % (p.relative_to(ROOT), name, rel))
            if dest.read_bytes() == source.read_bytes():
                sys.exit('❌ %s 的文件层 %s 里 %s 与公共树完全相同，这条覆盖是白写的。'
                         % (p.relative_to(ROOT), name, rel))
            if rel in planned:
                sys.exit('❌ %s 的文件层 %s 与 %s 都覆盖 %s；同一路径只能有一个所有者。'
                         % (p.relative_to(ROOT), name, planned[rel][0], rel))
            planned[rel] = (name, source, dest)
    for _, source, dest in planned.values():
        shutil.copyfile(source, dest)
    nfiles = len(planned)
    if n:
        # 覆盖了几条一定要打印。不打印的话，「这一版跟别版不一样」就成了只有翻代码
        # 才看得见的事。
        print('  按 versions/%s/pack_overrides.json 覆盖资源包译文 %d 条' % (ver, n))
    if nfiles:
        print('  按 versions/%s/pack_overrides.json 覆盖资源包文件 %d 个（%s）'
              % (ver, nfiles, '、'.join(sorted(layers))))


if __name__ == '__main__':
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    main(sys.argv[1], sys.argv[2])
