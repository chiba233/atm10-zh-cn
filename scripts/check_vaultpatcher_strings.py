#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# atm10-zh-cn — All the Mods 10 简体中文汉化补丁「绿油油版」
# Copyright (C) 2026 星野夢華 (Hoshino Yumeka)
# SPDX-License-Identifier: GPL-3.0-or-later
"""VaultPatcher 模块的 key 是否真的还在目标模组的字节码里。

## 为什么必须机械查

VaultPatcher 靠字符串精确匹配替换硬编码文本：`key` 对不上就是不替换，
玩家看到英文，日志里一个字都没有。模组升个小版本把某句话改了，
这条补丁就静默失效，这是本项目最难自查的一类问题。

模块里的 `mods` 字段帮不上忙：反编译 vaultpatcher.jar 确认 `getInfoMods()`
只被丢进 `debugInfo(...)` 打日志，不参与任何过滤，纯注释。所以这里不看它，
改为按 target_class 反查它在哪个 jar 里，再去那个 class 的常量池找字符串。

## 判定

- 命中：key 与常量池里某条 UTF-8 完全相等
- 子串命中：key 是某条常量的一部分。这是正常的，`makeConcatWithConstants`
  把 `"Energy: " + x + " FE"` 编译成一条 recipe 常量 `"Energy: \\u0001 FE"`，
  而我们的 key 是其中一段。VaultPatcher 自己也是按 \\u0001 切开再逐段匹配的。
- 找不到：那句话在这个版本的模组里已经不存在了 → 该条补丁必然不生效

内部类（`Foo$1`）一并扫，字符串常常落在 lambda / 匿名类里。

用法:
    python3 scripts/check_vaultpatcher_strings.py <mods目录> [--json 输出.json]
    python3 scripts/check_vaultpatcher_strings.py --help
"""
import json
import re
import struct
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
from paths import SRC

MODULES = SRC / 'vaultpatcher' / 'modules'


def utf8_pool(data):
    """从 .class 字节里取出常量池中全部 CONSTANT_Utf8。

    只解析常量池就够了，不必读完整个 class 结构。各 tag 的长度是固定的，
    照 JVM 规范跳过即可。tag 5/6（Long/Double）占两个槽位，是经典的坑。
    """
    if data[:4] != b'\xca\xfe\xba\xbe':
        return []
    n = struct.unpack_from('>H', data, 8)[0]
    out, i, idx = [], 10, 1
    SKIP = {7: 2, 8: 2, 16: 2, 19: 2, 20: 2, 15: 3, 3: 4, 4: 4, 9: 4, 10: 4,
            11: 4, 12: 4, 17: 4, 18: 4, 5: 8, 6: 8}
    while idx < n:
        tag = data[i]
        i += 1
        if tag == 1:
            ln = struct.unpack_from('>H', data, i)[0]
            out.append(data[i + 2:i + 2 + ln].decode('utf-8', 'replace'))
            i += 2 + ln
        else:
            i += SKIP.get(tag, 2)
        idx += 2 if tag in (5, 6) else 1
    return out


def index_jars(mods_dir):
    """class 路径 → jar 文件。用来按 target_class 反查它属于哪个模组。"""
    idx = {}
    for j in sorted(Path(mods_dir).glob('*.jar')):
        try:
            with zipfile.ZipFile(j) as z:
                for n in z.namelist():
                    if n.endswith('.class'):
                        idx.setdefault(n, j)
        except Exception:
            continue
    return idx


def strings_of(idx, dotted):
    """某个类（含其内部类）常量池里的全部字符串。类不存在返回 None"""
    base = dotted.replace('.', '/')
    main = base + '.class'
    if main not in idx:
        return None, None
    jar = idx[main]
    names = [main]
    pre = base + '$'
    names += [n for n in idx if n.startswith(pre) and idx[n] == jar]
    out = []
    with zipfile.ZipFile(jar) as z:
        for n in names:
            try:
                out += utf8_pool(z.read(n))
            except Exception:
                pass
    return jar.name, out


def main(mods_dir, out_json=None):
    idx = index_jars(mods_dir)
    print('索引了 %d 个 class（来自 %s）' % (len(idx), mods_dir))
    exact = sub = miss = 0
    noclass, noglobal = [], []
    bad = []
    for p in sorted(MODULES.glob('*.json')):
        try:
            blocks = json.loads(p.read_text(encoding='utf-8'))
        except Exception as e:
            print('  ⚠️ %s 解析失败: %s' % (p.name, e))
            continue
        for blk in blocks:
            if not isinstance(blk, dict) or 'pairs' not in blk:
                continue
            tcs = blk.get('target_class') or []
            if not tcs:                       # 全局替换：无从定位 jar，跳过
                noglobal.append(p.name)
                continue
            pool = []
            found_any = False
            for tc in tcs:
                jar, s = strings_of(idx, tc)
                if s is None:
                    continue
                found_any = True
                pool += s
            if not found_any:
                noclass.append((p.name, tcs[0]))
                continue
            joined = '\n'.join(pool)
            ps = set(pool)
            for pair in blk.get('pairs', []):
                k = pair.get('key', '')
                if not k:
                    continue
                if k in ps:
                    exact += 1
                elif k in joined:
                    sub += 1
                else:
                    miss += 1
                    bad.append({'module': p.name, 'class': tcs[0], 'key': k})
    tot = exact + sub + miss
    print()
    print('可核对的 key 共 %d 条' % tot)
    print('  ✅ 常量池里完全相等 : %d' % exact)
    print('  ✅ 是某条常量的一部分（字符串拼接，正常）: %d' % sub)
    print('  ❌ 在这个版本的模组里找不到          : %d' % miss)
    print()
    print('无法核对：%d 个块是全局替换（没有 target_class）；'
          '%d 个块的 target_class 在这批 jar 里不存在' % (len(noglobal), len(noclass)))
    for n, c in noclass[:10]:
        print('    类不存在  %-38s %s' % (n, c))
    if bad:
        print()
        print('=== 失效的补丁（这些文本在游戏里必然还是英文）===')
        for b in bad[:40]:
            print('  %-34s %s' % (b['module'][:34], repr(b['key'])[:70]))
        if len(bad) > 40:
            print('  ……另有 %d 条' % (len(bad) - 40))
    if out_json:
        Path(out_json).write_text(json.dumps(
            {'exact': exact, 'substring': sub, 'miss': miss,
             'missing': bad, 'no_target_class': noglobal,
             'class_not_found': noclass}, ensure_ascii=False, indent=1),
            encoding='utf-8')
        print('\n明细写入', out_json)
    return miss


if __name__ == '__main__':
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    if not args or '--help' in sys.argv:
        sys.exit(__doc__)
    oj = None
    if '--json' in sys.argv:
        oj = sys.argv[sys.argv.index('--json') + 1]
    main(args[0], oj)
