# -*- coding: utf-8 -*-
# atm10-zh-cn — All the Mods 10 简体中文汉化补丁「绿油油版」
# Copyright (C) 2026 星野夢華 (Hoshino Yumeka)
# SPDX-License-Identifier: GPL-3.0-or-later
"""Jonn's Trophies（modid: trophymanager）奖杯名汉化生成器。

## 为什么需要它

trophymanager 2.5.0 反编译结论（`TrophyItem.getName` / `TrophyBlock.createTrophy`
/ `TrophyManager$ModEventHandler`）：

  createTrophy(entity, nbt):
      name = entity.getDisplayName().getString()      # 在**服务端**求值并烘焙
      TrophyData.Name = name + " Trophy"              # 常量拼接 "\\u0001 Trophy"

  ModEventHandler(BuildCreativeModeTabContentsEvent, OP_BLOCKS):
      name = idToName("minecraft:polar_bear")         # = "Polar bear"
      TrophyData.Name = name + " Trophy"

  TrophyItem.getName(stack):
      return Component.translatable(TrophyData.Name)  # ← 整串当**翻译键**用

关键点：`Name` 是一个烘焙进物品 NBT 的**死字符串**，但它最终走的是
`Component.translatable()`。翻译键找不到时原样显示 —— 所以只要资源包提供一条
key 恰好等于那串烘焙文本的翻译，就能翻出来。资源包**能**汉化奖杯名。

（早期版本的 CHANGELOG 写过"资源包无法翻译"，那是错的；实测打怪掉落的奖杯
同样显示英文，本生成器就是为修这个而写。）

## 烘焙出的字符串有四种形态，全都要覆盖

`Name` 到底长什么样，取决于烘焙那一刻是谁在求值 `getDisplayName()`：

  1. `"Polar bear Trophy"`     创造栏预生成（idToName：冒号后首字母大写 + `_`→空格）
  2. `"Polar Bear Trophy"`     专用服务端打怪掉落，服务端 Language 命中 en_us
  3. `"entity.cataclysm.xxx Trophy"`  同上但服务端 Language 没这个键 → 原样返回键名
  4. `"北极熊 Trophy"`          单人/局域网：集成服务端用的是客户端 Language(zh_cn)

四种都生成，多余的键不匹配任何东西，无害。

## 单一真源

`scripts/trophy_entity_names.json`（id → {en, zh}）由本脚本从整合包 jar + 资源包
扫描生成；生成 lang 时**只读快照**，保证 CI 离线可复现。

用法:
    python3 scripts/gen_trophy_names.py --scan "<实例目录>"   # 刷新快照并生成
    python3 scripts/gen_trophy_names.py                       # 只按快照生成（CI）
CI:
    python3 scripts/gen_trophy_names.py && git diff --exit-code \\
        resourcepacks/*/assets/hanhua_trophies/lang/zh_cn.json
"""
import json
import os
import re
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SNAPSHOT = ROOT / 'scripts' / 'trophy_entity_names.json'
OUT = (ROOT / 'resourcepacks' / 'ATM10汉化包-7.2' / 'assets'
       / 'hanhua_trophies' / 'lang' / 'zh_cn.json')

# entity.<ns>.<path>；命名空间与注册名里都不可能有点，用它排除
# villager.farmer / tropical_fish.predefined.0 这类子键
KEY_RE = re.compile(r'^entity\.([a-z0-9_-]+)\.([a-z0-9_/-]+)$')

# 不是"生物"，做成奖杯没有意义/名字会串味的实体
SKIP_IDS = {
    'minecraft:player',            # 玩家奖杯走 createPlayerTrophy，名字是玩家名
}


def id_to_name(entity_id):
    """复刻 TrophyManager.idToName：冒号后首字母大写，其余 `_` 换空格。"""
    i = entity_id.index(':') + 1
    return entity_id[i:i + 1].upper() + entity_id[i + 1:].replace('_', ' ')


# --------------------------------------------------------------------------
# 扫描：整合包 jar（en_us / zh_cn）+ 原版 + 本包资源包，产出快照
# --------------------------------------------------------------------------
def scan(instance):
    inst = Path(instance)
    mcroot = inst.parent.parent          # …/.minecraft
    jar_en, jar_zh, pack_zh = {}, {}, {}

    def take(data, sink):
        for k, v in data.items():
            if isinstance(v, str) and KEY_RE.match(k):
                sink.setdefault(k, v)

    def load(raw):
        try:
            return json.loads(raw.decode('utf-8-sig'))
        except Exception:
            return {}

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

    # 原版：en_us 在客户端 jar 里，zh_cn 在 assets objects 里
    client_jar = next(inst.glob('*.jar'))
    with zipfile.ZipFile(client_jar) as zf:
        take(load(zf.read('assets/minecraft/lang/en_us.json')), jar_en)
    ver = json.loads((inst / (client_jar.stem + '.json')).read_text(encoding='utf-8'))
    idx = json.loads((mcroot / 'assets' / 'indexes'
                      / (ver['assetIndex']['id'] + '.json')).read_text(encoding='utf-8'))
    h = idx['objects']['minecraft/lang/zh_cn.json']['hash']
    take(json.loads((mcroot / 'assets' / 'objects' / h[:2] / h).read_text(encoding='utf-8')),
         jar_zh)

    # 本包（资源包 + kubejs 覆盖）优先级最高
    for base in (ROOT / 'resourcepacks', ROOT / 'kubejs' / 'assets'):
        for p in base.rglob('lang/zh_cn.json'):
            take(json.loads(p.read_text(encoding='utf-8')), pack_zh)

    # 组合式实体名模板：`entity.<ns>.name` = "Shiny %s" 这种，实体的显示名是
    # 模板 + 一个参数拼出来的，参数常常是**没翻译的注册名**（实测 Shiny 的奖杯
    # 烘焙出来就是 "Shiny zombie_horse Trophy"）。模板本身不是实体，要单独记。
    tmpl = {}
    for key, en in jar_en.items():
        m = re.match(r'^entity\.([a-z0-9_-]+)\.name$', key)
        if m and en.count('%s') == 1:
            tmpl[m.group(1)] = {'en': en, 'zh': pack_zh.get(key) or jar_zh.get(key)}

    # 键的全集：只扫 jar_en 会漏掉「模组自己不出 en_us、由本包补的」实体
    snap = {}
    for key in sorted(set(jar_en) | set(jar_zh) | set(pack_zh)):
        m = KEY_RE.match(key)
        if not m or key.endswith('.name'):
            continue
        eid = '%s:%s' % (m.group(1), m.group(2))
        if eid in SKIP_IDS:
            continue
        en = jar_en.get(key)
        zh = pack_zh.get(key) or jar_zh.get(key)
        if not zh or zh == en:
            continue                      # 没中文 / 中文就是英文 → 没得翻
        rec = {'key': key, 'en': en or '', 'zh': zh}
        if m.group(1) in tmpl:
            rec['tmpl'] = tmpl[m.group(1)]
        snap[eid] = rec
    SNAPSHOT.write_text(json.dumps(snap, ensure_ascii=False, indent=1,
                                   sort_keys=True) + '\n', encoding='utf-8')
    print('快照: %d 个实体 -> %s' % (len(snap), SNAPSHOT.relative_to(ROOT)))
    return snap


# --------------------------------------------------------------------------
# 生成 lang
# --------------------------------------------------------------------------
def build(snap):
    # 同一条烘焙文本可能被多个实体撞上（不同模组同名怪）；值不一致就整条丢弃，
    # 宁可显示英文也不张冠李戴（与资源蜂"歧义英文名不入表"同一条红线）。
    cand = {}
    for eid, rec in snap.items():
        zh, en, key = rec['zh'], rec['en'], rec['key']
        val = zh + '奖杯'
        if '%' in val:                    # translatable 无参，含 % 会炸格式化
            continue
        ns, path = eid.split(':', 1)
        forms = [id_to_name(eid), en, key, zh]
        t = rec.get('tmpl')
        if t:
            # 参数可能是注册名、去掉命名空间前缀的注册名、也可能是基础实体的
            # 英文/中文显示名 —— 全部覆盖，多余的键不匹配任何东西，无害。
            bare = path[len(ns) + 1:] if path.startswith(ns + '_') else path
            args = {path, bare, bare.replace('_', ' ')}
            base = snap.get('minecraft:' + bare)
            if base:
                args |= {base['en'], base['zh']}
            for form_tmpl in (t.get('en'), t.get('zh')):
                if form_tmpl:
                    forms += [form_tmpl.replace('%s', a) for a in args if a]
        for form in forms:
            if form:
                cand.setdefault(form + ' Trophy', {}).setdefault(val, set()).add(eid)

    out, dropped = {}, []
    for name, vals in cand.items():
        if len(vals) == 1:
            out[name] = next(iter(vals))
        else:
            dropped.append((name, sorted(vals)))

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(dict(sorted(out.items())), ensure_ascii=False,
                              indent=2) + '\n', encoding='utf-8')
    print('生成: %d 条 -> %s' % (len(out), OUT.relative_to(ROOT)))
    if dropped:
        print('歧义丢弃 %d 条（多个实体撞同一串烘焙名且译名不同）：' % len(dropped))
        for name, vals in sorted(dropped)[:20]:
            print('  %-42s %s' % (name, ' / '.join(vals)))


if __name__ == '__main__':
    if len(sys.argv) > 2 and sys.argv[1] == '--scan':
        data = scan(sys.argv[2])
    else:
        if not SNAPSHOT.exists():
            sys.exit('缺少快照 %s，先跑 --scan <实例目录>' % SNAPSHOT)
        data = json.loads(SNAPSHOT.read_text(encoding='utf-8'))
    build(data)
