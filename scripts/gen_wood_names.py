# -*- coding: utf-8 -*-
# atm10-zh-cn — All the Mods 10 简体中文汉化补丁「绿油油版」
# Copyright (C) 2026 星野夢華 (Hoshino Yumeka)
# SPDX-License-Identifier: GPL-3.0-or-later
"""精致存储（Sophisticated Storage）木桶/箱子的木头名生成器。

## 为什么需要它

sophisticatedstorage 1.5.80 反编译结论
（`WoodStorageBlockItem.getDisplayName` / `GenericWoodStorageHelper`）：

    getDisplayName(id, woodType):
        # 注意第二个参数是**一个空格**，不是内容
        return Component.translatable(id, getWoodDisplayName(woodType), " ")

    getWoodDisplayName(woodType):
        key = "wood_name.sophisticatedstorage." + woodName.translationKeyName()
        return Component.translatableWithFallback(key, prettify(woodName.path))

`block.sophisticatedstorage.barrel` = `"%s%sBarrel"` —— 第一个 %s 是木头名，
第二个 %s 只是分隔空格。**中文不需要那个空格**，所以译文只保留一个 %s 是对的，
不要"补参数"（2026-07-25 踩过：补成 %s%s 后变成「限类Pink Ipe 木桶 I」）。

真正的问题在 `getWoodDisplayName`：jar 里只定义了 11 种原版木头的 `wood_name.*`，
模组木头（productivetrees 等）没有键 → `translatableWithFallback` 回退成把注册名
美化后的英文（"Jackfruit" / "Pink Ipe"），于是满屏英文木桶。

## 键名格式（已实测确认）

`/data get entity @s SelectedItem` 拿到的 NBT 是
`"sophisticatedstorage:wood_type": "productivetrees:red_banana"`，
字节码里 `translationKeyName` 的拼接配方是 `\\u0001.\\u0001`（namespace + "." + path），
所以：

  * 原版木头   → `wood_name.sophisticatedstorage.oak`
  * 模组木头   → `wood_name.sophisticatedstorage.productivetrees.red_banana`

## 译名从哪来（单一真源）

不另起一套木头译名，直接从**该木头的木板名**推导——木板名整合包里基本都翻好了：

    橡木木板 → 橡木     云杉木板 → 云杉木     竹板 → 竹     绯红菌板 → 绯红菌

规则：结尾 `木木板` 去掉 `木板`；结尾 `木板` 去掉 `板`；结尾 `板` 去掉 `板`。

本包 `assets/sophisticatedstorage/lang/zh_cn.json` 里手写的键**优先**，
生成器不覆盖（那 11 个原版木头是手工定的译名）。

用法:
    python3 scripts/gen_wood_names.py --scan "<实例目录>"   # 刷新快照并生成
    python3 scripts/gen_wood_names.py                       # 只按快照生成（CI）
"""
import json
import os
import re
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SNAPSHOT = ROOT / 'scripts' / 'wood_planks_names.json'
PACK = ROOT / 'resourcepacks' / 'ATM10汉化包-7.2'
HAND = PACK / 'assets' / 'sophisticatedstorage' / 'lang' / 'zh_cn.json'
OUT = PACK / 'assets' / 'hanhua_wood_names' / 'lang' / 'zh_cn.json'

PLANKS_RE = re.compile(r'^block\.([a-z0-9_-]+)\.([a-z0-9_/]+)_planks$')
CJK = re.compile(r'[一-鿿]')


def wood_from_planks(zh):
    """木板名 → 木头名。"""
    if zh.endswith('木木板'):
        return zh[:-2]
    if zh.endswith('木板'):
        return zh[:-1]
    if zh.endswith('板'):
        return zh[:-1]
    return zh


def scan(instance):
    inst = Path(instance)
    mcroot = inst.parent.parent
    jar_en, jar_zh, pack_zh = {}, {}, {}

    def load(raw):
        try:
            return json.loads(raw.decode('utf-8-sig'))
        except Exception:
            return {}

    def take(d, sink):
        for k, v in d.items():
            if isinstance(v, str) and PLANKS_RE.match(k):
                sink.setdefault(k, v)

    for jar in sorted((inst / 'mods').glob('*.jar')):
        try:
            zf = zipfile.ZipFile(jar)
        except Exception:
            continue
        with zf:
            for n in zf.namelist():
                if not n.startswith('assets/'):
                    continue
                if n.endswith('/lang/en_us.json'):
                    take(load(zf.read(n)), jar_en)
                elif n.endswith('/lang/zh_cn.json'):
                    take(load(zf.read(n)), jar_zh)

    client_jar = next(inst.glob('*.jar'))
    with zipfile.ZipFile(client_jar) as zf:
        take(load(zf.read('assets/minecraft/lang/en_us.json')), jar_en)
    ver = json.loads((inst / (client_jar.stem + '.json')).read_text(encoding='utf-8'))
    idx = json.loads((mcroot / 'assets' / 'indexes'
                      / (ver['assetIndex']['id'] + '.json')).read_text(encoding='utf-8'))
    h = idx['objects']['minecraft/lang/zh_cn.json']['hash']
    take(json.loads((mcroot / 'assets' / 'objects' / h[:2] / h).read_text(encoding='utf-8')),
         jar_zh)

    for base in (PACK, ROOT / 'kubejs' / 'assets'):
        for p in base.rglob('lang/zh_cn.json'):
            take(json.loads(p.read_text(encoding='utf-8')), pack_zh)

    snap = {}
    for key in sorted(set(jar_en) | set(jar_zh) | set(pack_zh)):
        zh = pack_zh.get(key) or jar_zh.get(key)
        if not zh or not CJK.search(zh):
            continue                       # 木板名本身没汉化 → 推不出中文木头名
        snap[key] = zh
    SNAPSHOT.write_text(json.dumps(snap, ensure_ascii=False, indent=0, sort_keys=True) + '\n',
                        encoding='utf-8')
    print('快照: %d 种木板 -> %s' % (len(snap), SNAPSHOT.relative_to(ROOT)))
    return snap


def build(snap):
    # 模组注册 WoodType 有两种风格，键名跟着变，两种都要覆盖：
    #   new WoodType("productivetrees:red_banana", …) → wood_name.….productivetrees.red_banana
    #   new WoodType("bloom", …)                      → wood_name.….bloom
    # （deeperdarker 的繁花木就是裸名那种，只发带命名空间的键不生效）
    hand = json.loads(HAND.read_text(encoding='utf-8')) if HAND.exists() else {}
    full, bare = {}, {}
    for key, zh in snap.items():
        m = PLANKS_RE.match(key)
        ns, path = m.group(1), m.group(2)
        name = wood_from_planks(zh)
        if ns != 'minecraft':
            full['wood_name.sophisticatedstorage.%s.%s' % (ns, path)] = name
        bare.setdefault('wood_name.sophisticatedstorage.' + path, {}).setdefault(name, []).append(ns)

    out, dropped = dict(full), []
    for k, vals in bare.items():
        if len(vals) > 1:                 # 不同模组同名木头、译名还不一样 → 宁可显英文也不张冠李戴
            dropped.append((k, sorted(vals)))
            continue
        out[k] = next(iter(vals))

    skipped = 0
    for k in list(out):
        if k in hand:                     # 手写的优先（11 种原版木头），生成器不覆盖
            del out[k]
            skipped += 1

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(dict(sorted(out.items())), ensure_ascii=False, indent=2) + '\n',
                   encoding='utf-8')
    print('生成: %d 条 -> %s（手写优先跳过 %d，裸名歧义丢弃 %d）'
          % (len(out), OUT.relative_to(ROOT), skipped, len(dropped)))
    for k, vals in sorted(dropped)[:15]:
        print('  歧义 %-52s %s' % (k.split('storage.')[1], ' / '.join(vals)))


if __name__ == '__main__':
    if len(sys.argv) > 2 and sys.argv[1] == '--scan':
        data = scan(sys.argv[2])
    else:
        if not SNAPSHOT.exists():
            sys.exit('缺少快照 %s，先跑 --scan <实例目录>' % SNAPSHOT)
        data = json.loads(SNAPSHOT.read_text(encoding='utf-8'))
    build(data)
