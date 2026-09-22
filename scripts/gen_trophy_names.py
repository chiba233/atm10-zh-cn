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

import vanilla
from paths import COMMON, PACK, snapshot
ROOT = Path(__file__).resolve().parent.parent
# v2 只让已安装资产命名空间使用资源包补键，旧快照里的未安装模组候选必须失效。
SNAPSHOT = snapshot('trophy_entity_names_v2.json')
OUT = (PACK / 'assets'
       / 'hanhua_trophies' / 'lang' / 'zh_cn.json')

# entity.<ns>.<path>：命名空间与注册名里都不可能有点
KEY_RE = re.compile(r'^entity\.([a-z0-9_-]+)\.([a-z0-9_/-]+)$')
# entity.<ns>.<a>.<b>…：村民职业 / 热带鱼变种这类**子键**。它们不是注册名，
# 但确实会被拿来当实体显示名（实测服务器上真有 "Nitwit Trophy"），
# 所以只拿它们的中英文名字成键，不参与 idToName 推导。
SUBKEY_RE = re.compile(r'^entity\.([a-z0-9_-]+)\.([a-z0-9_/.-]+)$')

# 不是"生物"，做成奖杯没有意义/名字会串味的实体
SKIP_IDS = {
    'minecraft:player',            # 玩家奖杯走 createPlayerTrophy，名字是玩家名
}

# `entity.` 前缀并不代表就是实体名：MineColonies 用 `entity.<职业>.<消息>` 存工人台词、
# The Bumblezone 用 `entity.the_bumblezone.bee_queen.<事件>` 存蜂后对白。
# 这些混进来会造出「复活节快乐!奖杯」这种垃圾键。实体名一定是**短名词**，
# 不会有句子标点、也不会很长 —— 用这个把台词滤掉。
SENTENCEY = re.compile(r'[！!？?。，,；;：:…]')
MAX_NAME_LEN = 16

# TrophyData.Name 只剩这串英文，原实体 ID 已经丢失；同名实体不可能再按命名空间
# 区分。这里不是选某一个实体的译名，而是给**烘焙后的公共键**定一个能覆盖所有
# 候选的通名。各模组自己的实体名保持不动，带 translation key / 中文烘焙名的
# 另外几种形态仍会生成各自的精确译名。
BAKED_NAME_OVERRIDES = {
    'Abyss Blast Trophy': '深渊冲击波奖杯',
    'Amber Bee Trophy': '琥珀蜜蜂奖杯',
    'Ball Lightning Trophy': '球状闪电奖杯',
    'Ball lightning Trophy': '球状闪电奖杯',
    'Boat Trophy': '船奖杯',
    'Boat with Chest Trophy': '运输船奖杯',
    'Bullet Trophy': '子弹奖杯',
    'Chaos Bee Trophy': '混沌蜜蜂奖杯',
    'Chest boat Trophy': '运输船奖杯',
    'Echoing Strike Trophy': '回响打击奖杯',
    'Fireball Trophy': '火球奖杯',
    'Flame strike Trophy': '烈焰轰击奖杯',
    'Ice Crystal Trophy': '冰晶奖杯',
    'Ice Spike Trophy': '冰霜尖刺奖杯',
    'Ice crystal Trophy': '冰晶奖杯',
    'Ice spike Trophy': '冰霜尖刺奖杯',
    'Item frame Trophy': '物品展示框奖杯',
    'Mimic Trophy': '宝箱怪奖杯',
    'Sentry Trophy': '哨石奖杯',
    'Sheep Trophy': '绵羊奖杯',
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
    jar_en, jar_zh, pack_zh, kube_zh = {}, {}, {}, {}
    pack_sources = {}
    jar_namespaces = set()

    def take(data, sink, source=None):
        for k, v in data.items():
            if isinstance(v, str) and SUBKEY_RE.match(k):
                sink.setdefault(k, v)
                if source:
                    pack_sources.setdefault(k, set()).add(source)

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
                parts = n.split('/', 2)
                if len(parts) == 3 and parts[1]:
                    jar_namespaces.add(parts[1])
                if n.endswith('/lang/en_us.json'):
                    take(load(zf.read(n)), jar_en)
                elif n.endswith('/lang/zh_cn.json'):
                    take(load(zf.read(n)), jar_zh)

    # 原版：en_us 在客户端 jar 里，zh_cn 在 assets objects 里
    take(vanilla.client_en(inst), jar_en)
    take(vanilla.client_zh(inst), jar_zh)

    # 本包与 KubeJS 分开收：资源包会保留未安装模组的备用译文，不能直接证明实体存在；
    # KubeJS 则确实能定义 jar 里没有的实体键。资源包按文件所在 assets 命名空间
    # 记来源，不能只看键内命名空间：村民职业常写成 entity.minecraft.villager.<modid>.*。
    for p in PACK.rglob('lang/zh_cn.json'):
        rel = p.relative_to(PACK).parts
        source = rel[1] if len(rel) > 1 and rel[0] == 'assets' else None
        take(json.loads(p.read_text(encoding='utf-8')), pack_zh, source)
    for p in (COMMON / 'kubejs' / 'assets').rglob('lang/zh_cn.json'):
        take(json.loads(p.read_text(encoding='utf-8')), kube_zh)

    # 组合式实体名模板：`entity.<ns>.name` = "Shiny %s" 这种，实体的显示名是
    # 模板 + 一个参数拼出来的，参数常常是**没翻译的注册名**（实测 Shiny 的奖杯
    # 烘焙出来就是 "Shiny zombie_horse Trophy"）。模板本身不是实体，要单独记。
    tmpl = {}
    for key, en in jar_en.items():
        m = re.match(r'^entity\.([a-z0-9_-]+)\.name$', key)
        if m and en.count('%s') == 1:
            tmpl[m.group(1)] = {
                'en': en,
                'zh': pack_zh.get(key) or kube_zh.get(key) or jar_zh.get(key),
            }

    # 键的全集：已安装模组可以由本包补实体键，但未安装模组的备用译文不能混入。
    # 只看 jar 语言键会漏掉 shiny 这类由本包补齐大量实体名的已安装模组，所以用
    # jar 内实际出现过的 assets 命名空间作为存在性边界。
    snap = {}
    installed = set(jar_en) | set(jar_zh) | set(kube_zh)
    for key, sources in pack_sources.items():
        if sources & jar_namespaces:
            installed.add(key)
    for key in sorted(installed):
        m = KEY_RE.match(key)
        sub = m is None
        if sub:
            m = SUBKEY_RE.match(key)
        if not m or key.endswith('.name'):
            continue
        eid = '%s:%s' % (m.group(1), m.group(2))
        if eid in SKIP_IDS:
            continue
        en = jar_en.get(key)
        zh = pack_zh.get(key) or kube_zh.get(key) or jar_zh.get(key)
        if not zh or zh == en:
            continue                      # 没中文 / 中文就是英文 → 没得翻
        if SENTENCEY.search(zh) or len(zh) > MAX_NAME_LEN:
            continue                      # 是台词/对白，不是实体名
        # 英文侧同理。逗号要放行 —— "Echo of Tyros, First Flamebearer" 是正经 Boss 名
        if en and (re.search(r'[!?…]', en) or len(en) > 44):
            continue
        rec = {'key': key, 'en': en or '', 'zh': zh}
        if sub:
            rec['sub'] = True
        if m.group(1) in tmpl:
            rec['tmpl'] = tmpl[m.group(1)]
        snap[eid] = rec
    SNAPSHOT.write_text(json.dumps(snap, ensure_ascii=False, indent=1,
                                   sort_keys=True) + '\n', encoding='utf-8')
    print('快照: %d 个实体 -> %s' % (len(snap), SNAPSHOT))
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
        if rec.get('sub'):
            # 子键不是注册名，idToName 推不出有意义的东西（曾产出 "0 Trophy"）
            for form in (en, key, zh):
                if form:
                    cand.setdefault(form + ' Trophy', {}).setdefault(val, set()).add(eid)
            continue
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

    out, dropped, resolved = {}, [], []
    for name, vals in cand.items():
        if len(vals) == 1:
            out[name] = next(iter(vals))
        elif name in BAKED_NAME_OVERRIDES:
            out[name] = BAKED_NAME_OVERRIDES[name]
            resolved.append(name)
        else:
            dropped.append((name, sorted(vals)))

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(dict(sorted(out.items())), ensure_ascii=False,
                              indent=2) + '\n', encoding='utf-8')
    print('生成: %d 条 -> %s' % (len(out), OUT.relative_to(ROOT)))
    if resolved:
        print('同名烘焙键统一 %d 条（实体 ID 已丢失，采用公共通名）' % len(resolved))
    if dropped:
        print('歧义丢弃 %d 条（多个实体撞同一串烘焙名且译名不同）：' % len(dropped))
        for name, vals in sorted(dropped)[:20]:
            print('  %-42s %s' % (name, ' / '.join(vals)))


def refresh_zh(snap):
    """拿当前资源包里的译文，覆盖快照里缓存的那份。

    快照缓存的是**扫 jar 很慢**的那部分（有哪些实体、英文名叫什么）。译文不能跟着
    缓存住：缓存住的话，改了资源包却没删快照，产物纹丝不动——2026-07-27 实测被坑过
    （tempad 的「时空门」统一成「时门」后，本机重跑六次产物都没变）。
    """
    pack_zh = {}
    for base in (PACK, COMMON / 'kubejs' / 'assets'):
        for q in base.rglob('lang/zh_cn.json'):
            try:
                d = json.loads(q.read_text(encoding='utf-8'))
            except Exception:
                continue
            for k, v in d.items():
                if isinstance(v, str):
                    pack_zh.setdefault(k, v)
    n = 0
    for rec in snap.values():
        zh = pack_zh.get(rec.get('key'))
        if zh and zh != rec.get('zh'):
            rec['zh'] = zh
            n += 1
        tm = rec.get('tmpl')
        if tm:
            m = re.match(r'^entity\.([a-z0-9_-]+)\.', rec.get('key', ''))
            tz = pack_zh.get('entity.%s.name' % m.group(1)) if m else None
            if tz and tz != tm.get('zh'):
                tm['zh'] = tz
                n += 1
    if n:
        print('  译文以资源包为准刷新了 %d 条' % n)
    return snap


if __name__ == '__main__':
    if len(sys.argv) > 2 and sys.argv[1] == '--scan':
        data = scan(sys.argv[2])
    else:
        if not SNAPSHOT.exists():
            # 快照不在就现扫：ATM_PACK_ROOT 指向的整合包实例就是权威来源
            root = os.environ.get('ATM_PACK_ROOT')
            if not root or not (Path(root) / 'mods').is_dir():
                sys.exit('缺少快照 %s；设好 ATM_PACK_ROOT 或跑 --scan <实例目录>' % SNAPSHOT)
            data = scan(root)
        else:
            data = json.loads(SNAPSHOT.read_text(encoding='utf-8'))
            # 快照缓存的是**扫 jar 很慢**的那部分（哪些实体、英文名叫什么）。
            # 译文不能跟着缓存：缓存住的话，改了资源包却不删快照，产物纹丝不动
            # ——2026-07-27 实测就这么被坑过（tempad 的「时空门」改成「时门」不生效）。
            refresh_zh(data)
    build(data)
