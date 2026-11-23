#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# atm10-zh-cn — All the Mods 10 简体中文汉化补丁「绿油油版」
# Copyright (C) 2026 星野夢華 (Hoshino Yumeka)
# SPDX-License-Identifier: GPL-3.0-or-later
"""产出资源包里必须跟着原版走的那几个文件：字体覆盖 + pack.mcmeta。

中文标点（。：。！？「」……）在原版字体里是等宽全角，挤在一起很难看，
本包用 `include/cjk-punctuations` 换成紧凑的一套。做法是在原版的 provider 列表
最前面插一条引用，后面的 provider 覆盖前面的，所以必须插在最前。

问题在于：这么做需要把原版的 provider 列表整份写下来。写死在仓库里的话，
Mojang 哪天在 `default.json` 里加一个 provider，我们这份就把它整个吞掉，
而且不会有任何报错。所以这里现取原版客户端 jar 里的那份，插一条再写出去。

`pack.mcmeta` 里的 `pack_format` 同理：它由 Minecraft 版本决定，写死一个数字，
将来整合包换 MC 版本时资源包会被判成「不兼容」并弹警告。现取客户端 `version.json`
里的 `pack_version.resource`。

用法:
    python3 scripts/gen_vanilla_assets.py <整合包实例目录> <输出目录>
"""
import json
import sys
import zipfile
from pathlib import Path

import vanilla

# 要往哪几个原版字体前面插我们的标点 provider。这是本包的设计选择，不可推导。
PREPEND = {
    'default.json': {'type': 'reference', 'id': 'minecraft:include/cjk-punctuations'},
    'uniform.json': {'type': 'reference', 'id': 'minecraft:include/cjk-punctuations'},
}


def _client_font(inst, name):
    """原版客户端 jar 里的 assets/minecraft/font/<name>"""
    loc = vanilla._local(inst)
    if loc:
        jar = loc[0]
    else:
        ver = vanilla._version_json()
        jar = vanilla._cached('client-%s.jar' % vanilla.MCVER,
                              lambda: vanilla._get(ver['downloads']['client']['url']))
    with zipfile.ZipFile(jar) as z:
        return json.loads(z.read('assets/minecraft/font/' + name).decode('utf-8-sig'))


# pack.mcmeta 的模板。`@@MCVER@@` 由 build_dist.sh 按整合包版本填，
# pack_format 由原版客户端现取，两个版本号，各有各的来源，都不许手写死。
PACK_MCMETA = {
    'pack': {
        'pack_format': None,
        'description': 'ATM10 @@MCVER@@ 汉化包 · 绿油油版（星野夢華整理）',
        'supported_formats': None,
    },
    'language': {
        'zh_cn': {'name': 'Chinese (Simplified)', 'region': 'China', 'bidirectional': False},
    },
}


def _client_version_json(inst):
    loc = vanilla._local(inst)
    if loc:
        jar = loc[0]
    else:
        ver = vanilla._version_json()
        jar = vanilla._cached('client-%s.jar' % vanilla.MCVER,
                              lambda: vanilla._get(ver['downloads']['client']['url']))
    with zipfile.ZipFile(jar) as z:
        return json.loads(z.read('version.json'))


def main(inst, out_dir):
    fmt = _client_version_json(inst).get('pack_version', {}).get('resource')
    if not isinstance(fmt, int):
        sys.exit('❌ 原版 version.json 里读不出 pack_version.resource')
    meta = json.loads(json.dumps(PACK_MCMETA))
    meta['pack']['pack_format'] = fmt
    meta['pack']['supported_formats'] = [fmt]
    (Path(out_dir) / 'pack.mcmeta').write_text(
        json.dumps(meta, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print('  pack.mcmeta      pack_format=%d（取自原版 %s）' % (fmt, vanilla.MCVER))

    out = Path(out_dir) / 'assets' / 'minecraft' / 'font'
    out.mkdir(parents=True, exist_ok=True)
    for name, provider in PREPEND.items():
        doc = _client_font(inst, name)
        ps = doc.get('providers')
        if not isinstance(ps, list):
            sys.exit('❌ 原版 font/%s 里没有 providers 列表，格式变了' % name)
        if provider in ps:
            sys.exit('❌ 原版 font/%s 里已经有 %s 了，本包不该再插一遍' % (name, provider['id']))
        doc['providers'] = [provider] + ps
        (out / name).write_text(json.dumps(doc, ensure_ascii=False, indent=2) + '\n',
                                encoding='utf-8')
        print('  font/%-14s 原版 %d 个 provider + 本包 1 个' % (name, len(ps)))


if __name__ == '__main__':
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    main(sys.argv[1], sys.argv[2])
