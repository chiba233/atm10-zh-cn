#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# atm10-zh-cn — All the Mods 10 简体中文汉化补丁「绿油油版」
# Copyright (C) 2026 星野夢華 (Hoshino Yumeka)
# SPDX-License-Identifier: GPL-3.0-or-later
"""给每一条译文记下它翻译时对应的英文底本。

英文底本会变：模组作者改 en_us（措辞、单位、数值、参数顺序），ATM 改任务书正文。英文改了而中文
没跟上时，键和译文都还在，游戏不报错，玩家看到的是一句与实际行为不符的中文，比漏翻危险。
所以把每条译文对应的英文快照下来，版本升级时逐条 diff，英文变了的列为需复核。

覆盖范围：

- 资源包 lang：本包 `assets/<ns>/lang/zh_cn.json` 里的每个键，取该版本模组 jar 里
  `assets/<ns>/lang/en_us.json` 的对应英文
- 任务书：本包 delta 覆盖的每个键，取整合包 `quests/lang/en_us.snbt` 的对应英文

VaultPatcher 的底本是字节码里的字符串，由 `build_version_db.py` 逐条核对，不在这里。

用法:
    python3 scripts/build_en_baseline.py 7.2 <该版本mods目录> <该版本overrides目录>
"""
import hashlib
import io
import json
import os
import re
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
from paths import SRC

PACK = SRC / 'pack'
QDELTA = SRC / 'config' / 'ftbquests' / 'quests' / 'lang' / 'zh_cn'


def lang_in(z, out):
    """把一个 zip 里的全部 assets/<ns>/lang/en_us.json 并进 out。"""
    for n in z.namelist():
        m = re.fullmatch(r'assets/([^/]+)/lang/en_us\.json', n)
        if not m:
            continue
        try:
            d = json.loads(z.read(n).decode('utf-8-sig'))
        except Exception:
            continue
        if isinstance(d, dict):
            out.setdefault(m.group(1), {}).update(
                {k: v for k, v in d.items() if isinstance(v, str)})


def mod_en(mods_dir):
    """该版本全部模组的 en_us：{命名空间: {键: 英文}}

    必须扫描 `META-INF/jarjar/`：库模组多半以 jar-in-jar 形式放在别的 jar 里，`mods/` 下没有它们
    自己的文件，但游戏会加载并注册翻译键。只扫顶层 jar 会把这些命名空间判成整合包里没有，
    曾因此误删 6 个命名空间共 104 条译文（additionalentityattributes / cumulus_menus /
    nitrogen_internals / nuggets / olympus / spectrelib，分别在 allthearcanistgear、aether、
    ars_nouveau、tempad、comforts 里）。

    先扫顶层再扫 jar-in-jar：同名命名空间以顶层为准（顶层 jar 一定被加载，嵌套的可能因版本去重被替换）。
    """
    out, jij = {}, {}
    for j in sorted(Path(mods_dir).glob('*.jar')):
        try:
            z = zipfile.ZipFile(j)
        except Exception:
            continue
        lang_in(z, out)
        for n in z.namelist():
            if not (n.startswith('META-INF/jarjar/') and n.endswith('.jar')):
                continue
            try:
                lang_in(zipfile.ZipFile(io.BytesIO(z.read(n))), jij)
            except Exception:
                continue
    for ns, d in jij.items():
        for k, v in d.items():
            out.setdefault(ns, {}).setdefault(k, v)
    return out


# 一条 snbt 值里的字符串字面量。转义大体按 JSON 的规矩，所以逐个再 json.loads 一次。
_SNBT_STR = re.compile(r'"((?:[^"\\]|\\.)*)"')


def _unescape(s):
    """把字面量还原成文本。

    SNBT 允许 JSON 不认的转义，本包里有 4 处 `\\&`（转义颜色码的 &，让它显示为普通字符）。
    解不了的原样保留：这些值只用来比对与查漂移，保持原样不丢字。
    """
    try:
        return json.loads('"%s"' % s)
    except ValueError:
        return s


def snbt_pairs(text, where=''):
    """snbt 取值。数组常跨多行（quest_desc 一段一行），要按方括号配平继续读。

    SNBT 数组元素之间没有逗号，跨行的值用 `json.loads` 一定失败。失败时跳过的话，多行
    quest_desc 都会丢失：整合包 8922 个任务书键里有 716 个读不到，本包 delta 有 225 个。
    `quest_baseline.json` 和 `check_en_drift.py` 都依赖这里，多行正文的漂移就报不出来，
    例如 ATM 在 8.1 里把「12 个耀光下界书架」改成 13 个（见 CHANGELOG R25）。

    解析失败一律抛错。
    """
    out = {}
    lines = text.split('\n')
    i = 0
    while i < len(lines):
        m = re.match(r'^\t([A-Za-z0-9_.]+):\s*(.*)$', lines[i])
        if m:
            k, v = m.group(1), m.group(2)
            bal = v.count('[') - v.count(']')
            while bal > 0 and i + 1 < len(lines):
                i += 1
                v += '\n' + lines[i]
                bal += lines[i].count('[') - lines[i].count(']')
            if v.lstrip().startswith('['):
                # 数组：逐个取字符串字面量，段与段之间按换行接起来
                out[k] = '\n'.join(_unescape(s) for s in _SNBT_STR.findall(v))
            elif v.lstrip().startswith('"'):
                mm = _SNBT_STR.match(v.lstrip())
                if mm is None:
                    # 以引号开头却读不出来，说明取值器跟不上写法，必须失败。
                    # 不以引号开头的（false、数字、{…}）是章节文件的结构字段，不是译文，跳过。
                    raise SystemExit(
                        '❌ %s 里的 %s 以引号开头却取不出值，取值器该改了：%r'
                        % (where or 'snbt', k, v[:120]))
                out[k] = _unescape(mm.group(1))
        i += 1
    return out


def quest_en(ov_dir):
    """整合包的英文任务书。全新的包里英文是拆开的 `lang/en_us/**.snbt`，
    合并后的 en_us.snbt 要进游戏后由 ftbquestslangsplitter 生成。"""
    src = {}
    d = Path(ov_dir) / 'config/ftbquests/quests/lang'
    one = d / 'en_us.snbt'
    if one.exists():
        src.update(snbt_pairs(one.read_text(encoding='utf-8')))
    sub = d / 'en_us'
    if sub.is_dir():
        for f in sorted(sub.rglob('*.snbt')):
            src.update(snbt_pairs(f.read_text(encoding='utf-8')))
    return src


def quest_baseline(ov_dir):
    """只算任务书底本：本包 delta 覆盖的每个键，取该版官方 en_us 的对应英文。"""
    qsrc = quest_en(ov_dir)
    out = {}
    for f in sorted(QDELTA.rglob('*.snbt')):
        for k in snbt_pairs(f.read_text(encoding='utf-8'), str(f)):
            if k in qsrc:
                out[k] = qsrc[k]
    return out


def dump_quest(ver, base):
    p = ROOT / 'versions' / 'db' / ver / 'quest_baseline.json'
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(base, ensure_ascii=False, indent=0, sort_keys=True) + '\n',
                 encoding='utf-8')
    return p


def main(ver, mods_dir, ov_dir):
    en = mod_en(mods_dir)
    base = {'lang': {}, 'quest': {}}

    miss_ns, miss_key = set(), 0
    for p in sorted(PACK.rglob('lang/zh_cn.json')):
        ns = p.parts[-3]
        try:
            zh = json.loads(p.read_text(encoding='utf-8'))
        except Exception:
            continue
        src = en.get(ns)
        if src is None:
            miss_ns.add(ns)
            continue
        for k in zh:
            if k in src:
                base['lang']['%s/%s' % (ns, k)] = src[k]
            else:
                miss_key += 1

    qsrc = quest_en(ov_dir)
    for f in sorted(QDELTA.rglob('*.snbt')):
        for k in snbt_pairs(f.read_text(encoding='utf-8')):
            if k in qsrc:
                base['quest'][k] = qsrc[k]

    out = ROOT / 'versions' / 'db' / ver
    out.mkdir(parents=True, exist_ok=True)
    # 分两份存：
    #
    # - 任务书（932 条）是 ATM 写的正文，最需要盯住，量也小，原文入库，clone 下来就能查漂移。
    # - 模组 lang（13.8 万条）键名就有 7MB，三个版本入库会让仓库大一倍，而且随时能从整合包
    #   重新生成，所以不入库，只保留一份指纹与全文。
    (out / 'quest_baseline.json').write_text(
        json.dumps(base['quest'], ensure_ascii=False, indent=0, sort_keys=True) + '\n',
        encoding='utf-8')
    (out / 'lang_baseline_local.json').write_text(
        json.dumps({'lang': base['lang'],
                    'digest': {k: hashlib.sha1(v.encode('utf-8')).hexdigest()[:12]
                               for k, v in base['lang'].items()}},
                   ensure_ascii=False, indent=0, sort_keys=True) + '\n',
        encoding='utf-8')
    print('%s 底本快照：' % ver)
    print('  资源包 lang  %6d 条有英文底本（%d 条键在该版模组里不存在、%d 个命名空间无 en_us）'
          % (len(base['lang']), miss_key, len(miss_ns)))
    print('  任务书       %6d 条有英文底本（本包 delta 共 %d 键）'
          % (len(base['quest']),
             sum(len(snbt_pairs(f.read_text(encoding='utf-8')))
                 for f in QDELTA.rglob('*.snbt'))))
    print('  写入 versions/db/%s/en_baseline.json' % ver)


def check_quest(ver, ov_dir, write):
    """任务书基线必须与「用当前取值器，对着该版官方文件」算出的结果一致。

    取值器读不了多行数组时，八千多个键里七百多个被丢掉，入库的基线不完整，`check_en_drift.py`
    报不出多行正文的漂移（ATM 把「12 个耀光下界书架」改成 13 个就这样漏了一版）。基线错了，
    依赖它的漂移检测不会报错，只能用当前取值器重算一遍来核对。

    `write=True` 时写回重算结果（供 CI 产出 artifact），仍然失败，等人提交：基线只由 CI 生成，
    由人核对，不用开发机下载的文件入库。
    """
    now = quest_baseline(ov_dir)
    f = ROOT / 'versions' / 'db' / ver / 'quest_baseline.json'
    old = json.loads(f.read_text(encoding='utf-8')) if f.is_file() else None
    if old == now:
        print('  ✅ ATM10 %s 的任务书底本与现在算出来的一致（%d 键）' % (ver, len(now)))
        return True
    if old is None:
        print('  ⚠️ ATM10 %s 还没有任务书底本' % ver)
    else:
        添 = sorted(set(now) - set(old)); 删 = sorted(set(old) - set(now))
        改 = [k for k in set(old) & set(now) if old[k] != now[k]]
        print('  ❌ ATM10 %s 的任务书底本过期：现值 %d 键，入库的 %d 键'
              '（多 %d、少 %d、内容不同 %d）'
              % (ver, len(now), len(old), len(添), len(删), len(改)))
        for k in (添[:3] + 删[:3] + 改[:3]):
            print('       %s' % k)
    if write:
        dump_quest(ver, now)
        print('     已重算 versions/db/%s/quest_baseline.json，人工核对后提交' % ver)
    return False


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == '--check-quest':
        if len(sys.argv) != 4:
            sys.exit('用法: %s --check-quest <版本> <该版官方文件目录>' % sys.argv[0])
        sys.exit(0 if check_quest(sys.argv[2], sys.argv[3],
                                  os.environ.get('BASELINE_WRITE') == '1') else 1)
    if len(sys.argv) < 4:
        sys.exit(__doc__)
    main(sys.argv[1], sys.argv[2], sys.argv[3])
