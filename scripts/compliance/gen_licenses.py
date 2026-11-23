#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# atm10-zh-cn — All the Mods 10 简体中文汉化补丁「绿油油版」
# Copyright (C) 2026 星野夢華 (Hoshino Yumeka)
# SPDX-License-Identifier: GPL-3.0-or-later
"""把各家模组自己的许可声明抓下来，生成随包分发的第三方许可清单。

不靠我复述，也不靠第三方网站：每个 mod jar 的 `META-INF/neoforge.mods.toml`
（Fabric 是 `fabric.mod.json`）里就写着 `license = "..."`，那是作者自己的声明，
和 jar 一起签在字节里。有些 jar 还随带许可证全文（`LICENSE`、`LICENSE.txt`），
那份也一并抓出来，MIT、Apache-2.0、BSD 这类的唯一实质义务就是再分发时
附上版权声明与许可全文。

产出两样：

    versions/licenses.json      每个 jar 的 modId / 名称 / 许可声明 / 有没有带
                                许可全文 / 全文的 sha256（入库，可复核）
    THIRD-PARTY-LICENSES.md     随包分发的清单：我们给哪些模组出了译文、
                                那些模组各自是什么许可（构建时生成）
    licenses/<modid>.txt        jar 里自带的许可全文，随包分发

用法:
    python3 scripts/gen_licenses.py <mods 目录> [<出货树>]
"""
import hashlib
import json
import re
import sys
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # scripts/ 下的公共模块

ROOT = Path(__file__).resolve().parent.parent.parent
OUT = ROOT / 'versions' / 'licenses.json'
# jar 里带的许可全文长这些名字
LIC_NAMES = re.compile(r'(^|/)(LICENSE|LICENCE|COPYING|NOTICE)(\.(txt|md))?$', re.I)


def toml_field(text, key):
    m = re.search(r'^\s*%s\s*=\s*"([^"]*)"' % key, text, re.M)
    return m.group(1) if m else None


def read_jar(path):
    """从一个 jar 里抠出：modId、显示名、作者、许可声明、随带的许可全文。"""
    try:
        z = zipfile.ZipFile(path)
    except Exception:                                      # noqa: BLE001
        return None
    names = z.namelist()
    info = {'jar': path.name, 'namespaces': sorted(
        {n.split('/')[1] for n in names
         if n.startswith('assets/') and n.count('/') >= 2})}

    for meta in ('META-INF/neoforge.mods.toml', 'META-INF/mods.toml'):
        if meta in names:
            t = z.read(meta).decode('utf-8', errors='replace')
            info.update({
                'loader': 'neoforge' if 'neoforge' in meta else 'forge',
                'modid': toml_field(t, 'modId'),
                'name': toml_field(t, 'displayName'),
                'authors': toml_field(t, 'authors'),
                'url': toml_field(t, 'displayURL'),
                'license': toml_field(t, 'license'),
            })
            break
    else:
        if 'fabric.mod.json' in names:
            try:
                d = json.loads(z.read('fabric.mod.json').decode('utf-8-sig'))
            except Exception:                              # noqa: BLE001
                d = {}
            lic = d.get('license')
            info.update({
                'loader': 'fabric', 'modid': d.get('id'), 'name': d.get('name'),
                'authors': ', '.join(str(a) for a in (d.get('authors') or [])),
                'url': (d.get('contact') or {}).get('homepage'),
                'license': lic if isinstance(lic, str) else
                (', '.join(lic) if isinstance(lic, list) else None),
            })

    texts = {}
    for n in names:
        if LIC_NAMES.search(n) and not n.endswith('/'):
            b = z.read(n)
            if 20 < len(b) < (256 << 10):
                texts[n] = b
    if texts:
        # 一个 jar 里可能有好几份（jar-in-jar），取最长的那份当主许可全文
        main = max(texts.items(), key=lambda kv: len(kv[1]))
        info['license_text_entry'] = main[0]
        info['license_text_sha256'] = hashlib.sha256(main[1]).hexdigest()
        info['_text'] = main[1]
    return info


def main(mods_dir, tree=None):
    rows = []
    for p in sorted(Path(mods_dir).glob('*.jar')):
        r = read_jar(p)
        if r:
            rows.append(r)
    data = [{k: v for k, v in r.items() if k != '_text'} for r in rows]
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(data, ensure_ascii=False, indent=1) + '\n',
                   encoding='utf-8')
    declared = sum(1 for r in data if r.get('license'))
    withtext = sum(1 for r in data if r.get('license_text_sha256'))
    print('%d 个 jar：%d 个写明了许可，%d 个随带许可全文 → %s'
          % (len(data), declared, withtext, OUT.relative_to(ROOT)))
    if not tree:
        return 0

    tree = Path(tree)
    # 我们给哪些命名空间出了译文，只列这些，没碰过的不列
    pack = tree / 'resourcepacks'
    ours = set()
    for p in pack.rglob('*'):
        if p.is_file():
            parts = p.relative_to(pack).as_posix().split('/')
            if 'assets' in parts:
                i = parts.index('assets')
                if len(parts) > i + 1:
                    ours.add(parts[i + 1])

    lic_dir = tree / 'licenses'
    lic_dir.mkdir(parents=True, exist_ok=True)
    lines = ['# 第三方许可清单',
             '',
             '本汉化包为下列模组提供了中文译文。译文是**衍生作品**，其权利受各模组',
             '自身许可证约束。下表的「许可」一栏抄自各模组 jar 内 `mods.toml` /',
             '`fabric.mod.json` 里作者自己的声明，不是本项目的判断。',
             '',
             '随 jar 分发的许可证全文放在 `licenses/` 下（文件名即 modId）。',
             '',
             '| 模组 | modId | 许可 | 全文 |',
             '|---|---|---|---|']
    n_txt = 0
    for r in sorted(rows, key=lambda r: (r.get('name') or r['jar']).lower()):
        if not (set(r.get('namespaces') or []) & ours):
            continue
        txt = ''
        if r.get('_text') and r.get('modid'):
            f = lic_dir / ('%s.txt' % r['modid'])
            f.write_bytes(r['_text'])
            txt = '`licenses/%s.txt`' % r['modid']
            n_txt += 1
        lines.append('| %s | `%s` | %s | %s |'
                     % (r.get('name') or r['jar'], r.get('modid') or '?',
                        r.get('license') or '**未声明**（默认保留所有权利）', txt))
    (tree / 'THIRD-PARTY-LICENSES.md').write_text(
        '\n'.join(lines) + '\n', encoding='utf-8')
    print('随包清单：%d 行、%d 份许可全文 → THIRD-PARTY-LICENSES.md'
          % (len(lines) - 10, n_txt))
    return 0


if __name__ == '__main__':
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    sys.exit(main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None))
