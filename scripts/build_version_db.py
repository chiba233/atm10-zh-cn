#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# atm10-zh-cn — All the Mods 10 简体中文汉化补丁「绿油油版」
# Copyright (C) 2026 星野夢華 (Hoshino Yumeka)
# SPDX-License-Identifier: GPL-3.0-or-later
"""为某个 ATM10 版本建 VaultPatcher 的**专属**数据库。

## 为什么要一版一份

VaultPatcher 靠字符串精确匹配替换硬编码文本，而且失配是**静默**的——对不上就是不替换，
玩家看到英文，日志一个字都没有。模组在整合包版本之间升级会带来两类破坏：

1. **类改名 / 搬家**：整块补丁失效。实测 7.2 里就有 6 处
   （`ToolbarPanel` 变成了内部类、RFTools 的 `GuiTools` 搬进了 mcjtylib……）
2. **文案改写**：单条 key 失效。industrialization_overdrive 1.11.2→1.12.1 就换了措辞。

所以不能拿一份模块文件同时发给 7.0/7.1/7.2 —— 那等于对老版本闭着眼睛发。
这里对着**该版本真实的 jar** 逐条核验，产出这一版专属的：

- 每个 target_class 在这一版的**实际位置**（搬了家就自动找回来）
- 每条 key 在这一版是否存在（exact / substring / missing）
- 每个模块命中的 jar **精确文件名**（带版本号，作为门控与追溯依据）

打包时按这份数据库生成版本专属的模块：搬了家的类改成该版真实位置、
这一版不存在的 key 剔掉，并附覆盖率报告。

## 类搬家了怎么自动找回

先按声明的全限定名找；找不到就在全部 jar 里找**同简单类名**的候选，
取常量池里命中本块 key 最多的那个。命中 0 条的不算数——宁可报「找不到」，
也不要张冠李戴把补丁打到别的类上。

## 证据必须锚到字节

这份库的全部合法性来自「对着该版本真实的 jar 逐条核验」。所以 `jars.json` 记的是
每个 jar 的 **sha256**，能拿到 `mods.provenance.json` 时还会一并记下 CurseForge 的
`fileID`（不可变，重传会换新 ID）。目录里出现 manifest 之外的 jar 就直接拒绝建库。

## 加了新模块之后怎么补老版本

`gen_vaultpatcher.py` 要求**每个模块在每一版都有记录**——没有记录就等于没对着那一版的
jar 核过，此时把模块发下去是闭着眼睛发。所以新增一个带 target_class 的模块，五个版本
的库全都过期了。

但老版本的 `jars.json` 是**冻结的字节基线**，不该因为加了个模块就整份重写。
`--only-missing` 就是为此：只算库里还没有的那几个模块，并入现有库；`jars.json`
一个字不改，改为拿它**核对**下载回来的这批 jar（`verify`，对不上当场红）。

用法:
    python3 scripts/build_version_db.py 7.1 <该版本的mods目录>
    python3 scripts/build_version_db.py 7.1 <mods目录> --verify        # 只核字节
    python3 scripts/build_version_db.py 7.1 <mods目录> --only-missing  # 只补缺的模块
"""
import hashlib
import json
import sys
import io
import zipfile
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'scripts'))
from check_vaultpatcher_strings import utf8_pool          # noqa: E402

from paths import SRC

MODULES = SRC / 'vaultpatcher' / 'modules'


def build_index(mods_dir):
    by_path, by_simple = {}, defaultdict(list)
    for j in sorted(Path(mods_dir).glob('*.jar')):
        try:
            with zipfile.ZipFile(j) as z:
                names = [n for n in z.namelist() if n.endswith('.class')]
                # 库常常以 jar-in-jar 的形式塞在 META-INF/jarjar/ 里（NeoForge 的常规做法）。
                # 只扫外层会漏掉一整批类——例如 Create 的配置界面 catnip 就在
                # ponder-*.jar 里面，不往里挖就会把我们指向它的模块判成「目标类找不到」。
                for inner in [n for n in z.namelist()
                              if n.startswith('META-INF/jarjar/') and n.endswith('.jar')]:
                    try:
                        with zipfile.ZipFile(io.BytesIO(z.read(inner))) as iz:
                            names += [n for n in iz.namelist() if n.endswith('.class')]
                    except Exception:                              # noqa: BLE001
                        pass
        except Exception:
            continue
        for n in names:
            by_path.setdefault(n, j)
            last = n.rsplit('/', 1)[-1][:-6]
            by_simple[last].append(n)
            # 内部类要同时按最内层名建索引：声明写的是 `….item.Builder`，
            # 而它在新版里是 `….item.ItemDescription$Builder`，只按整段名查会漏。
            if '$' in last:
                by_simple[last.rsplit('$', 1)[-1]].append(n)
    return by_path, by_simple


def pool_of(by_path, cls_path, cache):
    """该类 + 其内部类的常量池字符串"""
    if cls_path in cache:
        return cache[cls_path]
    jar = by_path.get(cls_path)
    if jar is None:
        cache[cls_path] = (None, [])
        return cache[cls_path]
    base = cls_path[:-6]
    out = []
    with zipfile.ZipFile(jar) as z:
        for n in [cls_path] + [p for p in by_path
                               if p.startswith(base + '$') and by_path[p] == jar]:
            try:
                out += utf8_pool(z.read(n))
            except Exception:
                pass
    cache[cls_path] = (jar.name, out)
    return cache[cls_path]


def resolve(declared, keys, by_path, by_simple, cache):
    """声明的类在这一版的实际位置；搬家了就按 key 命中数找回"""
    p = declared.replace('.', '/') + '.class'
    if p in by_path:
        jar, pool = pool_of(by_path, p, cache)
        return declared, jar, pool, 'declared'
    tail = declared.split('.')[-1]
    cands = list(dict.fromkeys(by_simple.get(tail, []) +
                               by_simple.get(tail.rsplit('$', 1)[-1], [])))
    best = None
    for cand in cands:
        jar, pool = pool_of(by_path, cand, cache)
        blob = '\n'.join(pool)
        hit = sum(1 for k in keys if k in blob)
        if hit and (best is None or hit > best[0]):
            best = (hit, cand[:-6].replace('/', '.'), jar, pool)
    if best:
        return best[1], best[2], best[3], 'moved'
    return None, None, [], 'not_found'


def jar_records(mods_dir):
    """这一版**实际被核验的那批 jar** 的字节指纹。

    只记文件名是记了个寂寞：CurseForge 同名重传、本机换过的 jar、下坏的文件，
    记录都长得一模一样，而整套 vaultpatcher.json 的合法性全建立在
    「对着该版真实的 jar 逐条核验」这句话上。没有哈希，这句话没有证据。

    （这不是假想：7.2 的库原本就是拿本机实例建的，里面躺着自制的 ysm 桩 mod
    和换过版本的 cc-tweaked，只看文件名完全看不出来。）
    """
    out = {}
    for j in sorted(Path(mods_dir).glob('*.jar')):
        b = j.read_bytes()
        out[j.name] = {'sha256': hashlib.sha256(b).hexdigest(), 'size': len(b)}
    return out


def load_provenance(mods_dir):
    """fetch_pack 下载时留下的 fileID ↔ sha256 对照表，有就用。"""
    d = Path(mods_dir)
    for cand in (d / 'mods.provenance.json', d.parent / 'mods.provenance.json'):
        if cand.is_file():
            try:
                return json.loads(cand.read_text(encoding='utf-8'))
            except Exception:
                return {}
    return {}


def write_jars(ver, mods_dir):
    recs = jar_records(mods_dir)
    meta = load_provenance(mods_dir)
    prov = meta.get('jars') or {}
    # 少下的 jar 必须**逐个被显式登记**才放行。放宽门控是不行的：残缺的集合会让
    # vaultpatcher.json 里的 "missing" 变成假判定——不是这一版没有这个 key，
    # 只是我们没看到那个 jar。登记之后这条边界摆在明面上。
    known = {}
    kf = ROOT / 'versions' / ver / 'unobtainable.json'
    if kf.is_file():
        known = json.loads(kf.read_text(encoding='utf-8')).get('files') or {}
    undeclared = [i for i in (meta.get('missing_file_ids') or [])
                  if str(i) not in known]
    if undeclared:
        sys.exit('❌ 这份 %s 的 jar 没下全（%s/%s），且以下 fileID 没有登记原因：%s\n'
                 '   限速就重跑 fetch_pack.py 补齐；真的 404 了就写进 '
                 'versions/%s/unobtainable.json 说明情况。\n'
                 '   拿残缺集合建库会得出「这一版没有这个 key」的假结论。'
                 % (ver, meta.get('got'), meta.get('expected'), undeclared[:8], ver))
    if meta.get('missing_file_ids'):
        print('  ⚠️ 这一版有 %d 个 jar 已在 CurseForge 上取不到（已登记）：%s'
              % (len(meta['missing_file_ids']), meta['missing_file_ids']))
    stray = sorted(set(recs) - set(prov)) if prov else []
    for name, r in recs.items():
        pr = prov.get(name)
        if not pr:
            continue
        if pr.get('sha256') != r['sha256']:
            sys.exit('❌ %s 的字节与下载时记的对不上——这份 jar 被动过' % name)
        r['projectID'], r['fileID'] = pr.get('projectID'), pr.get('fileID')
    if stray:
        sys.exit('❌ %d 个 jar 不在这一版的官方 manifest 里，这不是一份干净的 %s：\n   %s\n'
                 '   拿本机实例建库会把自制/替换过的 jar 当成官方的记进去。'
                 % (len(stray), ver, '\n   '.join(stray[:10])))
    out = ROOT / 'versions' / 'db' / ver
    out.mkdir(parents=True, exist_ok=True)
    (out / 'jars.json').write_text(json.dumps(
        {'version': ver, 'count': len(recs),
         'provenance': 'curseforge' if prov else 'unverified',
         'manifest_expected': meta.get('expected'),
         'unobtainable': meta.get('missing_file_ids') or [],
         'jars': recs}, ensure_ascii=False, indent=1, sort_keys=True) + '\n',
        encoding='utf-8')
    print('  jars.json: %d 个 jar 的 sha256%s'
          % (len(recs), '（含 CurseForge fileID）' if prov else '（**出处未核**）'))
    return recs


def verify(ver, mods_dir):
    """拿仓库里记的哈希核对一个 mods 目录。缓存命中也要核——缓存同样可能是坏的。"""
    f = ROOT / 'versions' / 'db' / ver / 'jars.json'
    if not f.is_file():
        sys.exit('❌ versions/db/%s/jars.json 不存在' % ver)
    want = json.loads(f.read_text(encoding='utf-8'))
    if isinstance(want, list):
        sys.exit('❌ versions/db/%s/jars.json 还是旧的「只有文件名」格式，没有字节可核。'
                 '\n   重跑 build_version_db.py 生成带 sha256 的版本。' % ver)
    have = jar_records(mods_dir)
    bad = [n for n in sorted(set(have) & set(want['jars']))
           if have[n]['sha256'] != want['jars'][n]['sha256']]
    miss = sorted(set(want['jars']) - set(have))
    extra = sorted(set(have) - set(want['jars']))
    for label, lst in (('内容对不上', bad), ('缺少', miss), ('多出', extra)):
        for x in lst[:8]:
            print('  ❌ %s: %s' % (label, x))
        if len(lst) > 8:
            print('  ❌ %s: …还有 %d 个' % (label, len(lst) - 8))
    if bad or miss or extra:
        sys.exit('❌ %s 的 mods 目录与 versions/db/%s/jars.json 不一致' % (ver, ver))
    print('✅ %d 个 jar 逐字节与 versions/db/%s/jars.json 一致' % (len(have), ver))


def main(ver, mods_dir, only_missing=False):
    out = ROOT / 'versions' / 'db' / ver
    db = {}
    todo = sorted(MODULES.glob('*.json'))
    if only_missing:
        f = out / 'vaultpatcher.json'
        if not f.is_file():
            sys.exit('❌ versions/db/%s/vaultpatcher.json 不存在，没有可增补的库。\n'
                     '   去掉 --only-missing 整份重建。' % ver)
        db = json.loads(f.read_text(encoding='utf-8'))
        # 这一版的字节基线是冻结的：增补不重写 jars.json，改为拿它核对这批 jar。
        # 少下 / 下坏 / 拿错版本都会当场红，而不是悄悄写出一份「这一版没有这个 key」。
        verify(ver, mods_dir)
        todo = [p for p in todo if p.name not in db]
        if not todo:
            print('%s: 库里已有全部 %d 个模块，无需增补' % (ver, len(db)))
            return
        print('%s: 增补 %d 个模块 —— %s'
              % (ver, len(todo), '、'.join(p.name for p in todo)))
    else:
        write_jars(ver, mods_dir)
    by_path, by_simple = build_index(mods_dir)
    cache = {}
    print('%s: 索引 %d 个 class' % (ver, len(by_path)))
    stat = defaultdict(int)
    for f in todo:
        try:
            blocks = json.loads(f.read_text(encoding='utf-8'))
        except Exception as e:
            sys.exit('❌ %s 解析失败: %s' % (f.name, e))
        rec = {'blocks': []}
        # dynamic 模块（模块头 "dynamic": true）替换的是**运行时**才拼出来的字符串
        # ——比如 MineColonies 的风格名来自 jar 内 blueprints/*/pack.json，类常量池里
        # 根本没有它。拿「常量匹配」去核这类 key，结果必然是一片 missing，覆盖率被拖垮，
        # 打包时还会把它们当「这一版不存在」剔掉，等于这个模块白写。
        # 所以只核**类在不在**（类没了照样要红），key 一律记 dynamic，不计入覆盖率。
        dyn = any(isinstance(b, dict) and b.get('dynamic') for b in blocks)
        for bi, blk in enumerate(blocks):
            if not isinstance(blk, dict) or 'pairs' not in blk:
                continue
            keys = [p['key'] for p in blk['pairs'] if p.get('key')]
            tcs = blk.get('target_class') or []
            if not tcs:
                stat['global_block'] += 1
                rec['blocks'].append({'i': bi, 'global': True})
                continue
            classes, jars, pool = {}, [], []
            for tc in tcs:
                actual, jar, pl, how = resolve(tc, keys, by_path, by_simple, cache)
                classes[tc] = {'actual': actual, 'jar': jar, 'how': how}
                stat['class_' + how] += 1
                if jar and jar not in jars:
                    jars.append(jar)
                pool += pl
            ps, blob = set(pool), '\n'.join(pool)
            kv = {}
            for k in keys:
                if dyn:
                    kv[k] = 'dynamic'
                    continue
                s = 'exact' if k in ps else ('substring' if k in blob else 'missing')
                kv[k] = s
                stat['key_' + s] += 1
            rec['blocks'].append({'i': bi, 'classes': classes, 'jars': jars, 'keys': kv})
        if rec['blocks']:
            db[f.name] = rec
    out.mkdir(parents=True, exist_ok=True)
    (out / 'vaultpatcher.json').write_text(
        json.dumps(db, ensure_ascii=False, indent=1, sort_keys=True) + '\n', encoding='utf-8')
    tot = stat['key_exact'] + stat['key_substring'] + stat['key_missing']
    if only_missing:
        # 说清楚这几个数只覆盖这次增补的那几个模块，别被当成全库覆盖率读。
        print('  （以下只统计本次增补的 %d 个模块）' % len(todo))
    print('  target_class: 原位 %d / 搬家已找回 %d / 找不到 %d'
          % (stat['class_declared'], stat['class_moved'], stat['class_not_found']))
    print('  key: 命中 %d + 子串 %d = %d，缺 %d  → 覆盖率 %.1f%%'
          % (stat['key_exact'], stat['key_substring'],
             stat['key_exact'] + stat['key_substring'], stat['key_missing'],
             100 * (tot - stat['key_missing']) / max(1, tot)))
    print('  写入 versions/db/%s/' % ver)


if __name__ == '__main__':
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    a = [x for x in sys.argv[1:] if not x.startswith('--')]
    if '--verify' in sys.argv:
        verify(a[0], a[1])
    else:
        main(a[0], a[1], only_missing='--only-missing' in sys.argv)
