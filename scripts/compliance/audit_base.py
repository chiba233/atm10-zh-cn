#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# All the Mods 10 简体中文汉化补丁 · 绿油油版
# Copyright (C) 2026 星野夢華 (Hoshino Yumeka)
# SPDX-License-Identifier: GPL-3.0-or-later
"""底本残留核验：出货包里还有多少东西和 BBSMC 的底本一样。

LICENSE 第三节写明，在取得底本授权之前，合规路径之一是「移除全部底本成分，
改由各模组自带官方中文、CFPA 社区翻译与本项目自译构成，并逐条核验无底本残留」。
这个脚本就是那个「逐条核验」。

判定分两层：

文件层  出货包里任何一个文件与底本逐字节相同，都是直接搬运，没有辩解余地。

字符串层  译文与底本一字不差时，不能一概算作残留，同一条 key，模组自带
中文与 CFPA 社区翻译也可能就是那个译法，底本本身就收录了这两者（其说明文件
自陈包含 CFPA 社区翻译）。所以要三方比对：

    我们的译文 == 底本 == 模组自带中文   → 官方译法，不算残留
    我们的译文 == 底本 == CFPA          → 社区译法，不算残留
    我们的译文 == 底本，且两者都没有     → 底本残留
        其中：模组自带 / CFPA 对这条 key 另有译文 → 可直接替换
              二者都没有这条 key                 → 只能自译

用法:
    python3 scripts/audit_base.py --base <底本目录> --tree build/common \\
        --mods <整合包的 mods 目录> [--cfpa <CFPA 资源包 zip>]
"""
import hashlib
import json
import re
import sys
import zipfile
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # scripts/ 下的公共模块

ROOT = Path(__file__).resolve().parent.parent.parent
SNBT = re.compile(r'^\s*([\w.\-]+):\s*"(.*)"\s*$')


def sha(b):
    return hashlib.sha256(b).hexdigest()


def base_files(base):
    """底本里的全部文件：散装文件 + 资源包 zip 里的条目。"""
    out = {}
    for p in Path(base).rglob('*'):
        if not p.is_file():
            continue
        rel = p.relative_to(base).as_posix()
        if p.suffix == '.zip':
            try:
                z = zipfile.ZipFile(p)
            except Exception:                              # noqa: BLE001
                continue
            for n in z.namelist():
                if not n.endswith('/'):
                    out['%s!%s' % (rel, n)] = sha(z.read(n))
            continue
        out[rel] = sha(p.read_bytes())
    return out


def lang_of_dir(root):
    """一棵树里的全部 `assets/<ns>/lang/zh_cn.json`。"""
    out = {}
    for p in Path(root).rglob('lang/zh_cn.json'):
        s = p.as_posix()
        if '/assets/' not in s:
            continue
        ns = s.split('/assets/')[1].split('/')[0]
        try:
            out.setdefault(ns, {}).update(
                json.loads(p.read_text(encoding='utf-8-sig')))
        except Exception:                                  # noqa: BLE001
            pass
    return out


def lang_of_zip(path, prefix=''):
    out = {}
    z = zipfile.ZipFile(path)
    for n in z.namelist():
        if not n.endswith('/lang/zh_cn.json') or '/assets/' not in '/' + n:
            continue
        ns = ('/' + n).split('/assets/')[1].split('/')[0]
        try:
            out.setdefault(ns, {}).update(
                json.loads(z.read(n).decode('utf-8-sig')))
        except Exception:                                  # noqa: BLE001
            pass
    return out


def lang_of_jars(mods):
    out = {}
    for j in sorted(Path(mods).glob('*.jar')):
        try:
            z = zipfile.ZipFile(j)
        except Exception:                                  # noqa: BLE001
            continue
        for n in z.namelist():
            if n.startswith('assets/') and n.endswith('/lang/zh_cn.json'):
                try:
                    out.setdefault(n.split('/')[1], {}).update(
                        json.loads(z.read(n).decode('utf-8-sig')))
                except Exception:                          # noqa: BLE001
                    pass
    return out


def base_lang(base):
    out = {}
    for p in Path(base).rglob('*.zip'):
        for ns, kv in lang_of_zip(p).items():
            out.setdefault(ns, {}).update(kv)
    for ns, kv in lang_of_dir(base).items():
        out.setdefault(ns, {}).update(kv)
    return out


def vp_pairs(root):
    out = {}
    for p in (Path(root) / 'vaultpatcher' / 'modules').glob('*.json'):
        try:
            d = json.loads(p.read_text(encoding='utf-8-sig'))
        except Exception:                                  # noqa: BLE001
            continue
        for blk in d if isinstance(d, list) else []:
            for pr in (blk.get('pairs') or []):
                if isinstance(pr, dict) and 'key' in pr and 'value' in pr:
                    out[pr['key']] = pr['value']
    return out


def snbt_pairs(root, sub='config/ftbquests'):
    out = {}
    for p in (Path(root) / sub).rglob('*.snbt'):
        for line in p.read_text(encoding='utf-8', errors='replace').splitlines():
            m = SNBT.match(line)
            if m:
                out[m.group(1)] = m.group(2)
    return out


def main(base, tree, mods=None, cfpa=None):
    bfiles = base_files(base)
    byhash = set(bfiles.values())
    ours = {p.relative_to(tree).as_posix(): sha(p.read_bytes())
            for p in Path(tree).rglob('*') if p.is_file()}
    hits = sorted(k for k, h in ours.items() if h in byhash)
    print('=== 文件层：出货包 %d 个文件，与底本逐字节相同 %d 个' % (len(ours), len(hits)))
    for d, c in Counter('/'.join(k.split('/')[:5]) for k in hits).most_common(15):
        print('   %-62s %d' % (d, c))

    ol = lang_of_jars(mods) if mods else {}
    cl = lang_of_zip(cfpa) if cfpa else {}
    bl, ul = base_lang(base), lang_of_dir(tree)
    cat = Counter()
    fixable, selftrans = defaultdict(list), defaultdict(list)
    for ns, kv in ul.items():
        B, O, C = bl.get(ns, {}), ol.get(ns, {}), cl.get(ns, {})
        for k, v in kv.items():
            if k not in B:
                cat['我们独有']
                cat['我们独有'] += 1
            elif v != B[k]:
                cat['与底本不同'] += 1
            elif O.get(k) == v:
                cat['同底本，但也等于模组自带中文'] += 1
            elif C.get(k) == v:
                cat['同底本，但也等于 CFPA'] += 1
            elif k in O:
                cat['残留·可换成模组自带译文'] += 1
                fixable[ns].append([k, v, O[k], 'official'])
            elif k in C:
                cat['残留·可换成 CFPA 译文'] += 1
                fixable[ns].append([k, v, C[k], 'cfpa'])
            else:
                cat['残留·只能自译'] += 1
                selftrans[ns].append([k, v])
    total = sum(cat.values())
    print('\n=== 字符串层：出货包 %d 条译文' % total)
    for k, c in cat.most_common():
        print('   %-34s %7d  %5.1f%%' % (k, c, c / max(1, total) * 100))

    bvp, ovp = vp_pairs(base), vp_pairs(tree)
    vp_same = [k for k in set(bvp) & set(ovp) if bvp[k] == ovp[k]]
    bq, oq = snbt_pairs(base), snbt_pairs(tree)
    q_same = [k for k in set(bq) & set(oq) if bq[k] == oq[k]]
    print('\n=== 其余两块')
    print('   VaultPatcher 替换对：我们 %d 对，与底本译文相同 %d 对' % (len(ovp), len(vp_same)))
    print('   任务书条目：我们 %d 条，与底本译文相同 %d 条' % (len(oq), len(q_same)))

    out = {
        'file_level': hits,
        'lang_fixable': fixable,
        'lang_selftrans': selftrans,
        'vaultpatcher_same': sorted(vp_same),
        'quests_same': sorted(q_same),
        'summary': dict(cat),
    }
    (ROOT / 'versions' / 'base_residue.json').write_text(
        json.dumps(out, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    print('\n清单写进 versions/base_residue.json')
    return len(hits) + len(vp_same) + len(q_same) + sum(len(v) for v in fixable.values()) \
        + sum(len(v) for v in selftrans.values())


if __name__ == '__main__':
    a = sys.argv[1:]

    def arg(name, default=None):
        return a[a.index(name) + 1] if name in a else default

    if '--base' not in a or '--tree' not in a:
        sys.exit(__doc__)
    n = main(arg('--base'), arg('--tree'), arg('--mods'), arg('--cfpa'))
    print('\n残留合计 %d 处' % n)
    sys.exit(1 if n else 0)
