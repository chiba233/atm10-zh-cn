#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# atm10-zh-cn — All the Mods 10 简体中文汉化补丁「绿油油版」
# Copyright (C) 2026 星野夢華 (Hoshino Yumeka)
# SPDX-License-Identifier: GPL-3.0-or-later
"""去掉任务书中文里那些从英文原文带过来的半角空格。

## 为什么

FTB Quests 在空格处断行：MC 的 `StringSplitter` 一旦在本行见过空格，行宽溢出时
就回退到那个空格断开。于是中文段落里任何一个半角空格都是潜在的断行点，而且断出来
的是半截空行，比按字符硬断难看得多：

    你开始时有 3 个基本形态          → 断成「你开始时有」/「3 个基本形态」
    这些生物会失去全部 AI，          → 断成「……会失去全部」/「AI，基本就和……」
    护符碎片来自 Reliquary，         → 断成「护符碎片来自」/「Reliquary，可以……」

issue #10 报了 11 条、issue #11 又报了 9 条，全是同一个成因、几千处。逐条存覆盖的话
delta 会暴涨，上游一改还得重新对齐。所以放在构建时统一处理，上游怎么改都自动跟上。

## 判据：空格两侧都必须是「词」，且至少一侧是中文

    左右都是中文                        → 删    「均受 保留」→「均受保留」
    一侧中文、另一侧字母或数字            → 删    「失去全部 AI，」→「失去全部AI，」
    任一侧是标点或符号                   → 留

「词」= 汉字，或字母/数字（`0.5%` 这种以 `%` 收尾的数值也算，`%` 前是数字即可）。
颜色码在判定时透明，`&a` 这类，以及 `&#RRGGBB` 十六进制色码。

两条例外，都留空格：

* 序号：数字紧跟 `.` 时是列表标记（`1. 放在副手 2. 必须`），删了会粘成
  `1.放在副手2.必须`。
* 命令：`/` 开头的那一串是让玩家照抄的（`输入 /kubejs hand 来查找`），
  两侧都不动，免得中文被抄进命令里。

## 这条判据是第二版，第一版把符号两侧的空格吃掉了

第一版只看「空格一侧是不是中文」，不管另一侧是什么，于是成对符号被单边吃掉：

    &8原油&r -> &#D2CD2D硫酸轻燃油    → &8原油&r-> &#D2CD2D硫酸轻燃油
    9 粒 → 1 锭                       → 9粒→ 1锭
    按 Shift + 左键                   → 按Shift +左键
    干尸 - 生成于沙漠                 → 干尸-生成于沙漠

`&#RRGGBB` 不在当时的颜色码正则里，是箭头那条的直接病根：`->` 右边隔着
`&#D2CD2D` 是中文、左边不是，于是只删了左边那个空格。对抗审计在 2290 个删除点里
分出 460 个箭头/运算符、293 个列表短横、73 个序号、56 个冒号后，都是这么来的。

## 治不了的那一半

中文标点落在行首（「……什么颜色」/「、几支纱」）。MC 的换行器没有禁则处理，删空格
反而会让行填得更满、更容易撞上。这是引擎限制，只能靠改写句子回避，不在本脚本职责内。

用法:
    python3 scripts/gen_quest_space_fix.py <出货树>
"""
import re
import sys
from pathlib import Path

LANG = 'config/ftbquests/quests/lang/zh_cn'
# 汉字（含扩展 A）+ 中文标点 + 全角符号 + 中文文本里常用的那几个西文区标点
CJK = ('—‘’“”…'
       '　-〿㐀-䶿一-鿿＀-￯')
CJK_RE = re.compile('[%s]' % CJK)
# 颜色码：&a 这类，以及 &#RRGGBB 十六进制。判定时透明。
COLOR = re.compile(r'(?:&#[0-9a-fA-F]{6}|&[0-9a-fk-orA-FK-OR])+')
WORD = re.compile(r'[0-9A-Za-z]')
RUN = re.compile(r'[0-9A-Za-z]+')


def _skip_left(s, i):
    """从 i（不含）向左跳过颜色码，返回下一个有效字符的下标，没有则 -1。"""
    while i >= 0:
        for m in COLOR.finditer(s, 0, i + 1):
            if m.end() == i + 1:
                i = m.start() - 1
                break
        else:
            return i
    return -1


def _skip_right(s, i):
    """从 i（含）向右跳过颜色码，返回下一个有效字符的下标，没有则 len(s)。"""
    while i < len(s):
        m = COLOR.match(s, i)
        if not m:
            return i
        i = m.end()
    return len(s)


def _is_ordinal(s, i):
    """s[i] 所在的数字串紧跟一个 `.`，且 `.` 后面不是数字，那是列表序号。

    必须排掉小数：`0.5%` 的 `0` 后面也是 `.`，但那是数值，空格该删。
    """
    if not s[i].isdigit():
        return False
    j = i
    while j < len(s) and s[j].isdigit():
        j += 1
    if j >= len(s) or s[j] != '.':
        return False
    return not (j + 1 < len(s) and s[j + 1].isdigit())


def _in_command(s, i, limit=40):
    """s[i] 落在一条 `/xxx yyy` 命令里。

    命令可以有多个词（`/kubejs hand`），所以向左跨过字母数字与空格去找 `/`。
    遇到中文或别的标点就停，那说明已经出了命令的范围。
    """
    if i < 0 or i >= len(s):
        return False
    j, steps = i, 0
    while j > 0 and steps < limit:
        c = s[j - 1]
        if c == '/':
            # 真命令的 `/` 前面是空格或开头。`25MFE/t`、`8b/类型` 里的斜杠不算
            return j - 1 == 0 or s[j - 2] in ' "(（[【'
        if c.isalnum() or c in '_- ':
            j -= 1; steps += 1
            continue
        return False
    return False


def _wordish(s, i, side):
    """s[i] 是不是「词」的一端。side='L' 表示它在空格左边。

    数字/字母直接算。`0.5%` 这种以 % 收尾的数值，看 % 前面是不是数字。
    """
    if i < 0 or i >= len(s):
        return False
    c = s[i]
    if WORD.match(c):
        return True
    if side == 'L' and c == '%' and i > 0 and s[i - 1].isdigit():
        return True
    return False


def fix(text):
    out, i, n = [], 0, 0
    while i < len(text):
        if text[i] != ' ':
            out.append(text[i]); i += 1; continue
        j = i
        while j < len(text) and text[j] == ' ':
            j += 1
        li = _skip_left(text, i - 1)
        ri = _skip_right(text, j)
        lc = text[li] if li >= 0 else ''
        rc = text[ri] if ri < len(text) else ''
        l_cjk, r_cjk = bool(CJK_RE.match(lc)), bool(CJK_RE.match(rc))
        l_word, r_word = _wordish(text, li, 'L'), _wordish(text, ri, 'R')
        drop = (l_cjk or l_word) and (r_cjk or r_word) and (l_cjk or r_cjk)
        # 例外：列表序号、命令串
        if drop and ((r_cjk and _is_ordinal(text, ri)) or (l_word and _is_ordinal(text, li))
                     or (r_word and _is_ordinal(text, ri))):
            drop = False
        if drop and (_in_command(text, li) or _in_command(text, ri)):
            drop = False
        if drop:
            n += j - i
        else:
            out.append(text[i:j])
        i = j
    return ''.join(out), n


def main(argv):
    if len(argv) != 2:
        print('❌ 用法: gen_quest_space_fix.py <出货树>')
        return 1
    root = Path(argv[1]) / LANG
    if not root.is_dir():
        print('❌ %s 不在 —— 任务书语言树没摊出来，这一步等于没跑' % root)
        return 1
    files = sorted(p for p in root.rglob('*') if p.is_file())
    if not files:
        print('❌ %s 下一个文件都没有' % root)
        return 1
    total = touched = 0
    for p in files:
        s = p.read_text(encoding='utf-8')
        out, n = fix(s)
        if n:
            p.write_text(out, encoding='utf-8')
            touched += 1
            total += n
    print('✅ 任务书断行：%d 个文件、共去掉 %d 处紧挨中文的半角空格' % (touched, total))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
