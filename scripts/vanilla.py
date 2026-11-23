#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# atm10-zh-cn — All the Mods 10 简体中文汉化补丁「绿油油版」
# Copyright (C) 2026 星野夢華 (Hoshino Yumeka)
# SPDX-License-Identifier: GPL-3.0-or-later
"""取原版 Minecraft 的语言文件与字体资源。

有几个生成器要读原版的东西：奖杯名与木头名要拿原版实体/方块的中英文对照，
横幅要拿原版渲染中文用的 Unifont 点阵。这些不在整合包里，在游戏本体里。

两条路径，结果一样：

1. 本机装好的实例（HMCL / CurseForge 布局），`<实例>/<版本>.jar` 加上
   `<.minecraft>/assets/{indexes,objects}/`。开发时直接用，不联网。
2. **CI**，实例里只有 mods/，没有客户端 jar 也没有 assets 仓库。
   这时按 Mojang 官方的版本清单现取，缓存在 `build/vanilla/`。

以前只有第 1 条路，于是 `gen_trophy_names.py` 等四个生成器在 CI 上必然
`StopIteration`（`next(inst.glob('*.jar'))` 找不到客户端 jar），Build 一直红。
"""
import json
import urllib.request
import zipfile
from pathlib import Path

from paths import BUILD

MANIFEST = 'https://launchermeta.mojang.com/mc/game/version_manifest_v2.json'
RESOURCES = 'https://resources.download.minecraft.net'
MCVER = '1.21.1'
CACHE = BUILD / 'vanilla'


def _get(url):
    with urllib.request.urlopen(url, timeout=180) as r:
        return r.read()


def _cached(name, make):
    CACHE.mkdir(parents=True, exist_ok=True)
    p = CACHE / name
    if not p.exists():
        p.write_bytes(make())
    return p


def _version_json():
    def make():
        vs = json.loads(_get(MANIFEST))['versions']
        url = next(v['url'] for v in vs if v['id'] == MCVER)
        return _get(url)
    return json.loads(_cached('%s.json' % MCVER, make).read_bytes())


def _asset_index():
    ver = _version_json()
    def make():
        return _get(ver['assetIndex']['url'])
    return json.loads(_cached('assets-%s.json' % ver['assetIndex']['id'], make).read_bytes())


def _local(inst):
    """本机实例布局。不成立就返回 None"""
    inst = Path(inst)
    jars = sorted(inst.glob('*.jar'))
    if not jars:
        return None
    jar = jars[0]
    vjson = inst / (jar.stem + '.json')
    mcroot = inst.parent.parent            # …/.minecraft/versions/<实例> → …/.minecraft
    if not vjson.is_file() or not (mcroot / 'assets' / 'indexes').is_dir():
        return None
    return jar, json.loads(vjson.read_text(encoding='utf-8')), mcroot


def client_en(inst):
    """原版 en_us.json（客户端 jar 内）"""
    loc = _local(inst)
    if loc:
        with zipfile.ZipFile(loc[0]) as z:
            return json.loads(z.read('assets/minecraft/lang/en_us.json').decode('utf-8-sig'))
    ver = _version_json()
    p = _cached('client-%s.jar' % MCVER, lambda: _get(ver['downloads']['client']['url']))
    with zipfile.ZipFile(p) as z:
        return json.loads(z.read('assets/minecraft/lang/en_us.json').decode('utf-8-sig'))


def asset_object(inst, name):
    """按名字取一个游戏资源对象（如 `minecraft/lang/zh_cn.json`），返回字节"""
    loc = _local(inst)
    if loc:
        _jar, ver, mcroot = loc
        idx = json.loads((mcroot / 'assets' / 'indexes'
                          / (ver['assetIndex']['id'] + '.json')).read_text(encoding='utf-8'))
        h = idx['objects'][name]['hash']
        return (mcroot / 'assets' / 'objects' / h[:2] / h).read_bytes()
    h = _asset_index()['objects'][name]['hash']
    return _cached('obj-%s' % h, lambda: _get('%s/%s/%s' % (RESOURCES, h[:2], h))).read_bytes()


def client_zh(inst):
    """原版 zh_cn.json（在资源仓库里，不在 jar 里）"""
    return json.loads(asset_object(inst, 'minecraft/lang/zh_cn.json').decode('utf-8-sig'))


def unifont_hex(inst):
    """原版渲染中日韩文用的 GNU Unifont 点阵（.hex 文本）"""
    raw = asset_object(inst, 'minecraft/font/unifont.zip')
    import io
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        name = next(n for n in z.namelist() if n.endswith('.hex'))
        return z.read(name).decode('ascii')
