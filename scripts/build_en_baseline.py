#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# atm10-zh-cn — All the Mods 10 简体中文汉化补丁「绿油油版」
# Copyright (C) 2026 星野夢華 (Hoshino Yumeka)
# SPDX-License-Identifier: GPL-3.0-or-later
"""给**每一条译文**记下它翻译时对着的英文底本。

## 为什么必须有

本包一共翻了十几万条文本，但直到现在只有 VaultPatcher 那一千多条有硬校验。
其余的全靠「当初翻的时候是对的」。问题是底本会变：

- 模组作者改一句 en_us（措辞、单位、数值、参数顺序）
- ATM 制作组改一段任务书正文

英文一改，我们的中文就**悄悄变成错的**——键还在、译文还在、游戏不报错、
玩家看到的是一句和实际行为对不上的中文。这比漏翻危险得多。

所以：把每条译文当时对应的英文原文快照下来，版本升级时逐条 diff。
底本变了而译文没跟着变的，一律列进「需复核」。

## 覆盖哪些

- **资源包 lang**：本包 `assets/<ns>/lang/zh_cn.json` 里的每个键，
  取该版本模组 jar 里 `assets/<ns>/lang/en_us.json` 的对应英文
- **任务书**：本包 delta 覆盖的每个键，取整合包 `quests/lang/en_us.snbt` 的对应英文

VaultPatcher 不在这里——它的底本是字节码里的字符串，由
`build_version_db.py` 逐条核验，机制不同。

用法:
    python3 scripts/build_en_baseline.py 7.2 <该版本mods目录> <该版本overrides目录>
"""
import hashlib
import io
import json
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

    **必须下钻 `META-INF/jarjar/`**。库模组多半是 jar-in-jar 塞在别人肚子里发的，
    `mods/` 下没有它们自己的文件，但游戏照样加载、照样注册翻译键。只扫顶层 jar
    会把这些命名空间判成「整合包里没有」——曾经据此裁掉过 6 个真实存在的命名空间
    共 104 条译文（additionalentityattributes / cumulus_menus / nitrogen_internals /
    nuggets / olympus / spectrelib，分别住在 allthearcanistgear、aether、ars_nouveau、
    tempad、comforts 里）。底本是一堆判断的依据，它瞎一块，下游就跟着错一片。

    顶层先扫、JiJ 后补：同名命名空间以顶层那份为准（顶层 jar 一定被加载，
    嵌套的那份可能因版本去重被换掉）。
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

    SNBT 允许 JSON 不认的转义——本包里有 4 处 `\\&`（转义颜色码的 & ，让它按普通
    字符显示）。这种解不了的原样留着：这些值只用来互相比对与查漂移，保持原形不丢字，
    比为了「解析成功」去猜它是什么意思安全。
    """
    try:
        return json.loads('"%s"' % s)
    except ValueError:
        return s


def snbt_pairs(text, where=''):
    """snbt 取值。数组常常跨多行（quest_desc 一段一行），必须按方括号配平续读，
    不能只用单行正则——早先那版对整合包的英文文件一条都没取到。

    **SNBT 的数组元素之间没有逗号**，所以跨行的值 `json.loads` 必然失败。早先那版
    在失败处 `except: pass`，于是每一条多行 quest_desc 都被静默丢掉：整合包 8922 个
    任务书键里有 716 个对它是隐形的，本包自己的 delta 也有 225 个。后果不是少几行日志——
    `quest_baseline.json` 靠它建，`check_en_drift.py` 又靠那份基线，于是「上游把多行正文
    改了」这类漂移**一次都报不出来**。ATM 在 8.1 里把「12 个耀光下界书架」改成 13 个，
    就是这么漏过去的（见 CHANGELOG R25）。

    解析不出来一律抛错，不许再吞：一个取值器安静地少给几百个键，比它报错难查得多。
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
                    # 以引号开头却读不出来 = 取值器跟不上写法了，必须红。
                    # 不以引号开头的（false、数字、{…}）是章节文件里的结构字段，
                    # 不是译文，跳过；本函数只负责取字符串。
                    raise SystemExit(
                        '❌ %s 里的 %s 以引号开头却取不出值，取值器该改了：%r'
                        % (where or 'snbt', k, v[:120]))
                out[k] = _unescape(mm.group(1))
        i += 1
    return out


def quest_en(ov_dir):
    """整合包的英文任务书。全新包里英文是**拆开的** `lang/en_us/**.snbt`，
    没有合并后的 en_us.snbt（那是 ftbquestslangsplitter 进游戏后才生成的）。"""
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
    # 分两份存，因为两者的性价比完全不同：
    #
    # - **任务书**（932 条）是 ATM 制作组自己写的正文，正是最需要盯住的那部分，
    #   而且量小，原文直接入库，任何人 clone 下来就能查漂移。
    # - **模组 lang**（13.8 万条）光键名就 7MB，三个版本进 git 会把仓库撑大一倍，
    #   而且它随时能从整合包重新生成。所以不入库，本地留一份指纹 + 全文即可。
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


if __name__ == '__main__':
    if len(sys.argv) < 4:
        sys.exit(__doc__)
    main(sys.argv[1], sys.argv[2], sys.argv[3])
