#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# atm10-zh-cn — All the Mods 10 简体中文汉化补丁「绿油油版」
# Copyright (C) 2026 星野夢華 (Hoshino Yumeka)
# SPDX-License-Identifier: GPL-3.0-or-later
"""根源经典教程书的正文：构建时按行宽预切，在断点插 ASCII 空格。

## 为什么要这么干

RootsClassic 1.5.7 的 `ResearchPage.makeLines(String)` 是自己写的折行，字节码
翻回来是这样：

    for (int i = 0; i < s.length(); i++) {
        sb.append(s.charAt(i));
        if (s.charAt(i) == 32) {          // ← 只认 ASCII 空格
            words.add(sb.toString());     //   在这里切词，空格算进前一个词
            sb = new StringBuilder();
        }
    }
    for (String w : words) {
        width += font.width(w);
        if (width > 160) { lines.add(cur); cur = w; width = font.width(w); }
        else cur += w;
    }

英文靠单词间的空格切得开；**中文一个 ASCII 空格都没有，整段就是一个「词」**，
永远大于 160，于是整条画成一行冲出书页。这不是漏翻，是模组的折行算法碰上中文
就失效——跟 CC 终端画不出汉字、blockui 不认 textalign 是同一类：病在上游，
但只有我们能绕。

## 绕法

唯一的杠杆是往中文里插 ASCII 空格。关键在于**空格落在行尾就是看不见的**：
`makeLines` 把空格算进它前面那个词，而那个词正是该行最后一个。所以只要把每段
预切成一个个「刚好一行宽」的块、块之间插一个空格，模组照着切出来的行就跟我们
算的一模一样，视觉上没有任何多余空隙。

要让这条成立，必须保证**每一行连同行尾那个空格 ≤ 160px**：模组是先加宽度再判
`> 160`，等于 160 不会换行。所以行内容的预算是 160 − 空格(6) = 154。

## 宽度怎么来的

正文实测只用到三类字符，取值都往大了算（宁可行排不满，不可能溢出）：

  - CJK 与全角标点  9px    unifont 的全角字形，MC 里 advance 固定 9
  - ASCII           6px    原版位图字体里最宽的也就 6
  - 其余            9px    保守

本包自带的那几个字形 provider（CJK 标点 / 二字线 / 省略号）在这 81 条正文里
**一个都没用到**（跑 rcchars 核过），所以不必去算它们的 advance。将来正文里
真出现了，`WIDE` 这条按 9 估仍然偏小的话会溢出——所以下面的自检把每一行都
重新按模组的算法量一遍，量出来超 160 就直接报错，不会静默发出去。

用法:
    python3 scripts/gen_rootsclassic_wrap.py
"""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from paths import PACK, ROOT, need_common                          # noqa: E402

LANG = 'assets/rootsclassic/lang/zh_cn.json'
KEY = re.compile(r'\.page\d+info$')

MOD_LIMIT = 160          # ResearchPage.makeLines 里的常数

# 160 是从下面这几份 jar 的字节码里**逐份**读出来的（sipush 160，紧跟着 if_icmple）。
# 模组一升级这个数就可能变，而变了之后这里算出来的行宽全是错的、还不会有人发现。
# 所以把它钉到版本库已经记着的那些 jar 上：出现没登记过的 jar 就红，逼人回去重读一次
# 字节码再往这里加。**不许只因为「又升了一版」就把新 sha 填进来**——填之前必须真读。
JAR_PREFIX = 'rootsclassic'
VERIFIED_JARS = {
    # fileID: sha256
    7886347: '9407e843601bf5998c8f24b608f70a510b3727d2f3b8bef9753348a3147ba83d',
    8860609: '29d8a909126a93947197ab4b7b8c0bfa779b0f0eeeb0068423254ffb9631c7dc',
}
SPACE = 6                # ASCII 空格按 ASCII 上限算，同样是往大了估
BUDGET = MOD_LIMIT - SPACE

# 行首禁则：这些收尾标点不许出现在行首（中文排版的避头尾）
NO_LINE_START = '、。，；：？！）〕》」』】…‥·%》”’'


def adv(ch):
    return 6 if ord(ch) < 128 else 9


def width(s):
    return sum(adv(c) for c in s)


def wrap(s):
    """把一段正文切成若干行，每行内容宽度 ≤ BUDGET。"""
    lines, cur, w = [], '', 0
    for ch in s:
        cw = adv(ch)
        if w + cw > BUDGET and cur:
            lines.append(cur)
            cur, w = '', 0
        cur += ch
        w += cw
    if cur:
        lines.append(cur)

    # 避头尾：行首是收尾标点时，把上一行末尾那个字挪下来（只往窄了挪，不会撑破预算）
    for i in range(1, len(lines)):
        while (lines[i] and lines[i][0] in NO_LINE_START
               and len(lines[i - 1]) > 1
               and width(lines[i - 1][-1]) + width(lines[i]) <= BUDGET):
            lines[i] = lines[i - 1][-1] + lines[i]
            lines[i - 1] = lines[i - 1][:-1]

    # 断点正好落在原有空格上时，那个空格直接当分隔用，不再多插一个
    return [x.strip(' ') for x in lines if x.strip(' ')]


def make_lines(s):
    """照抄 ResearchPage.makeLines，用来自检我们插的空格确实切出预期的行。"""
    words, sb = [], ''
    for ch in s:
        sb += ch
        if ch == ' ':
            words.append(sb)
            sb = ''
    words.append(sb)
    out, cur, w = [], '', 0
    for wd in words:
        w += width(wd)
        if w > MOD_LIMIT:
            out.append(cur)
            cur, w = wd, width(wd)
        else:
            cur += wd
    out.append(cur)
    return out


def check_jar_pinned():
    """确认各版本记的 RootsClassic 还是当初读出 160 的那一份。"""
    seen = {}
    for p in sorted((ROOT / 'versions' / 'db').glob('*/jars.json')):
        jars = json.loads(p.read_text(encoding='utf-8')).get('jars') or {}
        for name, meta in jars.items():
            if name.lower().startswith(JAR_PREFIX):
                seen[p.parent.name] = (name, meta.get('sha256'), meta.get('fileID'))
    if not seen:
        raise SystemExit('❌ versions/db/*/jars.json 里找不到 %s——没法确认 makeLines '
                         '的行宽常数还是不是 %d' % (JAR_PREFIX, MOD_LIMIT))
    bad = {v: s for v, s in seen.items()
           if VERIFIED_JARS.get(s[2]) != s[1]}
    if bad:
        raise SystemExit(
            '❌ RootsClassic 换了一份没登记过的 jar，%d 这个行宽常数必须重新从字节码里'
            '读一遍\n'
            '   （javap -c elucent/rootsclassic/research/ResearchPage.class，'
            '看 makeLines 里 if_icmple 前面那个 sipush）\n'
            '   读出来确实还是 %d，才把它加进 VERIFIED_JARS；不是就改 MOD_LIMIT。\n'
            '   已登记：%s\n   没登记：%s'
            % (MOD_LIMIT, MOD_LIMIT,
               '、'.join('fileID %d' % f for f in sorted(VERIFIED_JARS)),
               '；'.join('%s→%s' % (v, s) for v, s in sorted(bad.items()))))
    return seen


def main():
    need_common()
    pinned = check_jar_pinned()
    p = PACK / LANG
    if not p.is_file():
        raise SystemExit('❌ 出货树里没有 %s——先跑 assemble.py' % LANG)
    d = json.loads(p.read_text(encoding='utf-8'))

    done = skipped = 0
    widest = 0
    most = ('', 0)
    for k, v in d.items():
        if not KEY.search(k) or not isinstance(v, str):
            continue
        # 已经切得开就不动。这一条同时管两件事：短到本来就不满一行的，
        # 以及**已经跑过一遍的**——否则重复跑会一层层往里加空格。
        if all(width(ln) <= MOD_LIMIT for ln in make_lines(v)):
            skipped += 1
            continue
        lines = wrap(v)
        out = ' '.join(lines)
        got = make_lines(out)                      # 自检①：模组会切成我们算的那些行
        # 行尾那个空格模组是算进词里的，会跟着留在行末——屏幕上看不见，比对时去掉
        if [x.rstrip(' ') for x in got] != lines:
            raise SystemExit('❌ %s：模组切出来的行与预期不一致\n  预期 %r\n  实际 %r'
                             % (k, lines, got))
        for ln in got:                             # 自检②：每行不许超（行尾空格已含在里面）
            if width(ln) > MOD_LIMIT:
                raise SystemExit('❌ %s：这一行 %dpx，超过 %dpx —— %r'
                                 % (k, width(ln), MOD_LIMIT, ln))
        widest = max(widest, max(width(x) for x in got))
        if len(got) > most[1]:
            most = (k, len(got))
        d[k] = out
        done += 1

    p.write_text(json.dumps(d, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    tail = ('｜最宽的一行 %dpx/%dpx｜最多的一条 %d 行（%s）'
            % (widest, MOD_LIMIT, most[1], most[0].split('.')[-2])) if done else ''
    print('根源经典教程书折行：改写 %d 条（%d 条无需处理：短到不满一行，或已经切得开）%s'
          '｜行宽常数已对 %d 个版本的 jar 核过'
          % (done, skipped, tail, len(pinned)))


if __name__ == '__main__':
    main()
