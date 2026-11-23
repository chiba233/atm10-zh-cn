#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# atm10-zh-cn — All the Mods 10 简体中文汉化补丁「绿油油版」
# Copyright (C) 2026 星野夢華 (Hoshino Yumeka)
# SPDX-License-Identifier: GPL-3.0-or-later
"""模组自己把英文画进贴图的那几张图，擦掉英文重写中文。

## 为什么需要这个

语言文件只能管「从 lang 键取出来渲染」的文字。有些模组把字直接画进 PNG，
资源包唯一的办法是放一张同路径的图盖过去。主菜单按钮（gen_menu_buttons.py）
和任务书章节横幅（gen_quest_banners.py）已经这么做了，这个脚本是同一套办法
用在模组贴图上。

## 现在收了哪些

逐张核过 minecolonies（222 张）、structurize（84 张）、blockui（6 张）、
stylecolonies / Byzantine（0 张）的 GUI 贴图，只有一张图里有可读的英文：

    minecolonies  gui/guide/background.png   960×540   左上角「Quick Guide」

同一张图里那本速查手册的示意图上还有一些小字，但它是刻意画糊的草图（原图就
认不出写了什么），不属于要汉化的文字。其余四个浅色气泡框是空的，里面的字是
运行时按 lang 键画上去的，早就是中文。

## 常量怎么来的（逐像素量的，不是估的）

对 `background.png` 在 x[0..320] y[20..140] 区间扫「亮度和 > 300」的像素：

- 文字包围盒 **x[72..274] y[64..91]**，字高 28px。再往外三像素的环带里
  最亮的像素只有 66~78（纯背景），说明矩形外确实没有文字。
- 字色取区域内最常见的实心色：**(246, 246, 246)**。
- 背景不是纯色，是一层径向暗角渐变（文字左侧 (8,7,5)、右侧 (14,12,8)、
  上下 (20,17,12)）。所以不能像主菜单按钮那样填一个色，否则会留下一块死板的补丁。
  这里改成逐列在矩形上下两行之间线性插值，暗角在竖直方向是平滑的，
  插出来的过渡看不出接缝。

源图的 sha1 一并钉在表里：MineColonies 哪天挪了这行字，构建会直接报错，
而不是照着旧坐标把图擦花。
"""
import hashlib
import io
import os
import sys
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
import books                                                   # noqa: E402
from gen_menu_buttons import render, save_png                    # noqa: E402
from paths import PACK                                          # noqa: E402

TEXTURES = {
    'assets/minecolonies/textures/gui/guide/background.png': {
        'sha1': '9880fc64ca90695452ee4e3bdd9797ad389ecf90',
        'text': '快速指南',
        'box': (68, 58, 282, 97),       # 擦除矩形（含四周留白，见 docstring）
        'left': 72,                     # 与英文原文同一个左边距
        'bottom': 91,                   # 文字底边
        'height': 28,                   # 目标字高 = 原文字高
        'color': (246, 246, 246, 255),
    },
}
PROBE = 3          # 矩形外侧探测环带的宽度
BRIGHT = 300       # 「这是字不是背景」的亮度和阈值


def mods_dir(argv):
    if argv:
        return argv[0]
    root = os.environ.get('ATM_PACK_ROOT')
    if not root:
        sys.exit('❌ 给个 mods 目录，或设 ATM_PACK_ROOT 指向整合包。')
    return os.path.join(root, 'mods')


def assert_box_clean(im, box, rel):
    """矩形外一圈必须是纯背景，否则说明上游挪了字，坐标不能再用。"""
    px = im.load()
    x0, y0, x1, y1 = box
    band = [(x, y) for y in range(max(0, y0 - PROBE), min(im.height, y1 + PROBE + 1))
            for x in range(max(0, x0 - PROBE), min(im.width, x1 + PROBE + 1))
            if not (x0 <= x <= x1 and y0 <= y <= y1)]
    worst = max((sum(px[x, y][:3]), x, y) for x, y in band)
    if worst[0] > BRIGHT:
        sys.exit('❌ %s: 擦除矩形 %s 外侧 %d 像素内发现亮像素 %d（%d,%d）——'
                 '上游大概挪了这行字，重新量坐标，别照旧的擦。'
                 % (rel, box, PROBE, worst[0], worst[1], worst[2]))


def erase(im, box):
    """逐列在矩形上下两行之间线性插值，抹掉文字又保住暗角渐变。"""
    px = im.load()
    x0, y0, x1, y1 = box
    top, bot = y0 - 1, y1 + 1
    span = bot - top
    for x in range(x0, x1 + 1):
        a, b = px[x, top], px[x, bot]
        for y in range(y0, y1 + 1):
            t = (y - top) / span
            px[x, y] = tuple(round(a[i] + (b[i] - a[i]) * t) for i in range(4))


def main(argv, check_only=False):
    jars = books.Jars(mods_dir(argv))
    n = 0
    for rel, spec in sorted(TEXTURES.items()):
        raw = jars.read(rel)
        if raw is None:
            sys.exit('❌ 在 mods 里找不到 %s' % rel)
        got = hashlib.sha1(raw).hexdigest()
        if got != spec['sha1']:
            sys.exit('❌ %s 的源图变了（记的是 %s，实际 %s）——'
                     '坐标是按旧图量的，重新量过再改这里。' % (rel, spec['sha1'], got))
        im = Image.open(io.BytesIO(raw)).convert('RGBA')
        assert_box_clean(im, spec['box'], rel)
        glyph = render(spec['text'], spec['color'], spec['height'])
        x, y = spec['left'], spec['bottom'] - glyph.height + 1
        x0, y0, x1, y1 = spec['box']
        if x < x0 or x + glyph.width > x1 or y < y0 or y + glyph.height > y1 + 1:
            sys.exit('❌ %s: 中文 x[%d..%d] y[%d..%d] 越出擦除矩形 %s'
                     % (rel, x, x + glyph.width, y, y + glyph.height, spec['box']))
        out = PACK / rel
        if not check_only:
            erase(im, spec['box'])
            im.alpha_composite(glyph, (x, y))
            out.parent.mkdir(parents=True, exist_ok=True)
            save_png(im, out)
        print('  %-58s %s  字高=%d 宽=%d  x[%d..%d] y[%d..%d]'
              % (rel.split('textures/')[1], spec['text'], glyph.height, glyph.width,
                 x, x + glyph.width, y, y + glyph.height))
        n += 1
    print(('校验通过' if check_only else '已重绘') + ' %d 张模组贴图' % n)


if __name__ == '__main__':
    args = [a for a in sys.argv[1:] if a != '--check']
    main(args, check_only='--check' in sys.argv[1:])
