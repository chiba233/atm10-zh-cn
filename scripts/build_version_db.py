#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# atm10-zh-cn — All the Mods 10 简体中文汉化补丁「绿油油版」
# Copyright (C) 2026 星野夢華 (Hoshino Yumeka)
# SPDX-License-Identifier: GPL-3.0-or-later
"""为某个 ATM10 版本建 VaultPatcher 的专属数据库。

VaultPatcher 按字符串精确匹配替换硬编码文本，匹配不上就不替换，玩家看到英文，日志里也没有记录。
模组在整合包版本之间升级会造成两类失效：

1. 类改名或移动位置：整块补丁失效。7.2 里有 6 处（`ToolbarPanel` 变成内部类，RFTools 的
   `GuiTools` 移进了 mcjtylib 等）。
2. 文案改写：单条 key 失效，例如 industrialization_overdrive 1.11.2→1.12.1。

所以按该版本实际的 jar 逐条核对，产出这一版专属的数据：

- 每个 target_class 在这一版的实际位置（移动过的自动找回）
- 每条 key 在这一版是否存在（exact / substring / missing）
- 每个模块命中的 jar 的完整文件名（带版本号，用于门控与追溯）

打包时据此生成版本专属的模块：移动过的类改成实际位置，不存在的 key 剔除，并附覆盖率报告。

类找回：先按声明的全限定名找，找不到就在全部 jar 里找同简单类名的候选，取常量池里命中本块 key
最多的那个。命中 0 条时报「找不到」，不把补丁打到别的类上。

`jars.json` 记录每个 jar 的 sha256，有 `mods.provenance.json` 时一并记录 CurseForge 的 `fileID`
（不可变，重传会换新 ID）。目录里有 manifest 之外的 jar 就拒绝建库。

新增一个带 target_class 的模块时，所有版本的库都会过期（`gen_vaultpatcher.py` 要求每个模块在每一版
都有记录）。老版本的 `jars.json` 是固定的字节基线，不重写：`--only-missing` 只计算库里还没有的模块，
并入现有库，同时用 `jars.json` 核对下载的 jar（`verify`，对不上就失败）。

用法:
    python3 scripts/build_version_db.py 7.1 <该版本的mods目录>
    python3 scripts/build_version_db.py 7.1 <mods目录> --verify        # 只核对字节
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
from fetch_pack import unregistered_missing               # noqa: E402

from paths import SRC

MODULES = SRC / 'vaultpatcher' / 'modules'


def build_index(mods_dir):
    by_path, by_simple = {}, defaultdict(list)
    for j in sorted(Path(mods_dir).glob('*.jar')):
        try:
            with zipfile.ZipFile(j) as z:
                names = [n for n in z.namelist() if n.endswith('.class')]
                # 库常以 jar-in-jar 形式放在 META-INF/jarjar/ 里（NeoForge 的常规做法），只扫外层会漏掉
                # 一批类。例如 Create 配置界面的 catnip 在 ponder-*.jar 里面，不往里找会判成目标类找不到。
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
            # 内部类同时按最内层名建索引：声明写的是 `….item.Builder`，
            # 新版里是 `….item.ItemDescription$Builder`，只按完整名查会漏。
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
    """声明的类在这一版的实际位置，移动过的按 key 命中数找回"""
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
    """这一版实际核对过的 jar 的字节指纹。

    只记文件名的话，CurseForge 同名重传、换过版本的 jar、下载损坏的文件，记录都一样，
    无法证明库是对着该版真实的 jar 核对出来的。例如用开发机上的实例建库时，里面有自制的
    ysm 桩 mod 和换过版本的 cc-tweaked，只看文件名看不出来。
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
    # 少下载的 jar 必须逐个登记才放行：残缺的集合会让 vaultpatcher.json 里的 "missing"
    # 分不清是这一版没有这个 key，还是没下载到 jar。判断与 fetch_pack 共用同一个函数。
    undeclared = unregistered_missing(ver, meta.get('missing_file_ids') or [])
    if undeclared:
        sys.exit('❌ 这份 %s 的 jar 没下全（%s/%s），且以下 fileID 没有登记原因：%s\n'
                 '   限速就重新运行 fetch_pack.py 补齐。确实 404 的就写进 '
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
            sys.exit('❌ %s 的字节与下载时记录的不一致，这份 jar 被改过' % name)
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
    """用仓库里记录的哈希核对一个 mods 目录。缓存命中也要核对，缓存同样可能是坏的。"""
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
        # 这一版的字节基线是固定的：增补时不重写 jars.json，而是用它核对这批 jar，
        # 少下、下坏、下错版本都会失败。
        verify(ver, mods_dir)
        todo = [p for p in todo if p.name not in db]
        if not todo:
            print('%s: 库里已有全部 %d 个模块，无需增补' % (ver, len(db)))
            return
        print('%s: 增补 %d 个模块：%s'
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
        # dynamic 模块（模块头 "dynamic": true）替换的是运行时拼出的字符串，例如 MineColonies 的
        # 风格名来自 jar 内 blueprints/*/pack.json，类常量池里没有。按常量匹配核对会全是 missing，
        # 打包时还会被当成不存在剔掉。所以只核对类是否存在（类没了仍要失败），key 一律记为 dynamic，
        # 不计入覆盖率。
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
        # 这几个数只覆盖这次增补的模块，不是全库覆盖率。
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
