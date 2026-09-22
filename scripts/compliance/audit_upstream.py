#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# All the Mods 10 简体中文汉化补丁 · 绿油油版
# Copyright (C) 2026 星野夢華 (Hoshino Yumeka)
# SPDX-License-Identifier: GPL-3.0-or-later
"""版权审计：仓库里有没有上游的东西，出货包里又带了谁的东西。

这个仓库的规矩是「只放源不放产物」「不放上游拷贝」。规矩写在文档里没用，
得能机械地核——所以这个脚本干三件事：

1. **逐字节比对**：把整合包里每个 mod jar 的每个条目按 sha256 建索引，
   再拿仓库里 git 跟踪的每个文件去比。命中就是**原样搬运**，必须处理；
2. **同名不同容**：同名但字节不同的，多半是我们改过的衍生物（翻译过的书页、
   重绘过的示意图）——这类要人来判断「改动够不够大」，脚本只负责列出来；
3. **按命名空间归属**：出货包里每个 `assets/<namespace>/…` 属于哪个 mod、
   那个 mod 声明的是什么许可。ARR 的模组要单独拿许可，这张表就是清单。

许可信息从 Modrinth 取（有公开接口）。CurseForge 的项目接口对匿名请求一律 403，
取不到就记 `unknown`——**不猜**。

用法:
    python3 scripts/audit_upstream.py --mods <整合包的 mods 目录>
    python3 scripts/audit_upstream.py --mods … --licenses   # 顺便查许可
    python3 scripts/audit_upstream.py --mods … --tree <出货树>  # 核产物，非零即失败
    python3 scripts/audit_upstream.py --mods … --tree … --drop  # 顺手删掉
    python3 scripts/audit_upstream.py --mods … --tree … --drop --manifest <剔除清单>
"""
import hashlib
import json
import subprocess
import sys
import urllib.request
import zipfile
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # scripts/ 下的公共模块

ROOT = Path(__file__).resolve().parent.parent.parent
UA = 'atm10-zh-cn-audit/1.0 (+https://github.com/chiba233/atm10-zh-cn)'
MODRINTH = 'https://api.modrinth.com/v2'
# 这些目录按设计就含有上游原文（「原文 → 译文」映射），不算搬运，单独归类
QUOTING = ('src/books/', 'src/kubejs/', 'src/config/', 'src/vaultpatcher/')


def tracked():
    out = subprocess.run(['git', 'ls-files'], cwd=ROOT,
                         capture_output=True, text=True, check=True).stdout
    return [ROOT / f for f in out.split('\n') if f]


def index_jars(mods):
    """把每个 jar 的每个条目按 sha256 与文件名建索引。"""
    by_hash, by_name = {}, defaultdict(list)
    jars = sorted(Path(mods).glob('*.jar'))
    for j in jars:
        try:
            z = zipfile.ZipFile(j)
        except Exception:                                  # noqa: BLE001
            continue
        for n in z.namelist():
            if n.endswith('/'):
                continue
            try:
                b = z.read(n)
            except Exception:                              # noqa: BLE001
                continue
            by_hash.setdefault(hashlib.sha256(b).hexdigest(), (j.name, n))
            by_name[n.rsplit('/', 1)[-1]].append((j.name, n))
    return jars, by_hash, by_name


def namespaces(jars):
    """`assets/<namespace>/` 归谁。一个 jar 可能带好几个命名空间（jar-in-jar）。"""
    owner = {}
    for j in jars:
        try:
            z = zipfile.ZipFile(j)
        except Exception:                                  # noqa: BLE001
            continue
        for n in z.namelist():
            if n.startswith('assets/') and n.count('/') >= 2:
                owner.setdefault(n.split('/')[1], j.name)
    return owner


def modrinth_license(slug_or_id):
    try:
        req = urllib.request.Request('%s/project/%s' % (MODRINTH, slug_or_id),
                                     headers={'User-Agent': UA})
        d = json.loads(urllib.request.urlopen(req, timeout=30).read())
        lic = d.get('license') or {}
        return lic.get('id') or lic.get('name') or 'unknown', d.get('title')
    except Exception:                                      # noqa: BLE001
        return None, None


def main(mods, want_licenses=False):
    jars, by_hash, by_name = index_jars(mods)
    print('索引了 %d 个 jar 的全部条目' % len(jars))

    exact, samename, ours = [], [], []
    for p in tracked():
        rel = p.relative_to(ROOT).as_posix()
        if rel.startswith(('.git', 'scripts/', '.github/')) or not p.is_file():
            continue
        b = p.read_bytes()
        # 空文件、`{}` 这种到处都是，哈希撞上不说明任何问题
        if len(b.strip()) < 24:
            continue
        h = hashlib.sha256(b).hexdigest()
        if h in by_hash:
            exact.append((rel, by_hash[h]))
        elif p.name in by_name:
            samename.append((rel, by_name[p.name][0]))
        else:
            ours.append(rel)

    print('\n=== 1. 逐字节与上游相同（原样搬运，必须处理）：%d 个' % len(exact))
    for rel, (j, n) in exact:
        print('   %s\n       ← %s ! %s' % (rel, j, n))

    print('\n=== 2. 同名但内容不同（衍生物，需人判断）：%d 个' % len(samename))
    per = defaultdict(int)
    for rel, _ in samename:
        per['/'.join(rel.split('/')[:3])] += 1
    for d, c in sorted(per.items(), key=lambda x: -x[1]):
        print('   %-58s %d 个' % (d, c))

    quoting = [r for r in ours if r.startswith(QUOTING)]
    print('\n=== 3. 上游没有同名文件：%d 个（其中 %d 个在「原文→译文」映射目录下，'
          '按设计就含上游原文）' % (len(ours), len(quoting)))

    ns = namespaces(jars)
    used = defaultdict(int)
    for p in tracked():
        rel = p.relative_to(ROOT).as_posix()
        parts = rel.split('/')
        if 'assets' in parts:
            i = parts.index('assets')
            if len(parts) > i + 1:
                used[parts[i + 1]] += 1
    print('\n=== 4. 我们给 %d 个命名空间出了内容' % len(used))
    rows = []
    for name, cnt in sorted(used.items(), key=lambda x: -x[1]):
        jar = ns.get(name, '(不在这个整合包里)')
        lic = ''
        if want_licenses:
            lid, _title = modrinth_license(name)
            lic = lid or 'unknown'
        rows.append((name, cnt, jar, lic))
        print('   %-26s %4d 个文件  %-46s %s' % (name, cnt, jar[:46], lic))

    (ROOT / 'versions' / 'audit.json').write_text(json.dumps({
        'exact_copies': [{'file': r, 'jar': j, 'entry': n} for r, (j, n) in exact],
        'same_name': [{'file': r, 'jar': j} for r, (j, _n) in samename],
        'namespaces': [{'namespace': a, 'files': b, 'jar': c, 'license': d}
                       for a, b, c, d in rows],
    }, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    print('\n结果写进 versions/audit.json')
    return len(exact)


def audit_tree(mods, tree, drop=False, manifest=None):
    """核**产物**：出货树里不许有任何与已装模组逐字节相同的文件。

    这条闸挡两种东西：上游自带的中文被我们原样搬进包里；以及别人写的译文
    （整合包里的附属模组会给别的模组的书塞自己的 zh_cn）被当成我们的发出去。
    两种都是再分发别人的作品，而且都毫无必要——Patchouli 与 AE2 导览按文件
    回落，缺了那一页玩家看到的东西一模一样。

    `--drop` 时命中即删——这是既定行为，不改；generate_all.sh 靠这条闸的退出码
    继续往下跑（见下面 return），改成非零会直接断构建。但 2026-07-28 对抗审计
    第二轮指出：删除动作本身是**静默**的——退出码恒为 0，CI 日志里翻不出「这次
    构建到底删了什么」，误删了也没人知道。所以删除照旧，只是现在会把删了什么、
    删了几个、来自哪些模组，用 ⚠️ 摆到日志里最显眼的地方。

    `manifest` 给后续版本文件层留下路径与内容哈希；只有清单与 `src/pack/` 公共源
    同时吻合，文件层才可恢复一份已经实质修改过的新版页面。
    """
    _jars, by_hash, _by_name = index_jars(mods)
    hits = []
    for p in sorted(Path(tree).rglob('*')):
        if not p.is_file():
            continue
        b = p.read_bytes()
        if len(b.strip()) < 24:
            continue
        h = hashlib.sha256(b).hexdigest()
        if h in by_hash:
            hits.append((p, h, by_hash[h]))
    dropped = []
    for p, _h, (j, n) in hits:
        tag = '⚠️ 已删除' if drop else '  命中'
        print('   %s %s\n       ← %s ! %s' % (tag, p.relative_to(tree), j, n))
        if drop:
            p.unlink()
            dropped.append((p, j))
    if manifest is not None:
        if not drop:
            raise SystemExit('❌ --manifest 只可与 --drop 一起使用。')
        manifest = Path(manifest)
        manifest.parent.mkdir(parents=True, exist_ok=True)
        manifest.write_text(json.dumps({
            'files': {
                p.relative_to(tree).as_posix(): {
                    'sha256': h,
                    'jar': j,
                    'entry': n,
                }
                for p, h, (j, n) in hits
            },
        }, ensure_ascii=False, indent=1, sort_keys=True) + '\n', encoding='utf-8')
        print('版权闸剔除清单：%d 个文件 -> %s' % (len(hits), manifest))
    print('出货树里与已装模组逐字节相同的文件：%d 个%s'
          % (len(hits), '（已删）' if drop and hits else ''))
    if drop and dropped:
        per_jar = defaultdict(int)
        for _p, j in dropped:
            per_jar[j] += 1
        print('\n⚠️ ⚠️ ⚠️ 本次构建静默删除了 %d 个文件（不会让构建失败，退出码仍是 0）⚠️ ⚠️ ⚠️'
              % len(dropped))
        print('⚠️ 汇总——来自哪些模组：')
        for j, c in sorted(per_jar.items(), key=lambda x: -x[1]):
            print('   ⚠️   %-46s %d 个' % (j, c))
    return 0 if (drop or not hits) else len(hits)


if __name__ == '__main__':
    a = sys.argv[1:]
    if '--mods' not in a:
        sys.exit(__doc__)
    mods = a[a.index('--mods') + 1]
    if '--tree' in a:
        mf = a[a.index('--manifest') + 1] if '--manifest' in a else None
        sys.exit(1 if audit_tree(mods, a[a.index('--tree') + 1], '--drop' in a, mf) else 0)
    sys.exit(1 if main(mods, '--licenses' in a) else 0)
