#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# atm10-zh-cn — All the Mods 10 简体中文汉化补丁「绿油油版」
# Copyright (C) 2026 星野夢華 (Hoshino Yumeka)
# SPDX-License-Identifier: GPL-3.0-or-later
"""主菜单按钮图上的中文文字生成器。

ATM 的主菜单按钮把文字烤进了 PNG（996×234，FancyMenu 直接贴图），
语言文件够不着，只能重绘。本脚本负责「擦掉文字区、重新写中文」这一步。

## 为什么要有这个脚本

第一版是手工渲染的、没留脚本，字号字重要再调就无从下手。
现在把参数固化在这里：擦除矩形是常量，所以脚本可以反复跑而不会越擦越多
（不是去检测已有文字再擦，那样每跑一次都会啃掉一点边缘）。

## 常量怎么来的

对 14 张图逐像素量过：
- 文字区 x[280..900] y[50..143] 之内只有文字，矩形外一圈是纯背景色。
  左边的圆形图标止于 x≈250，下划线自 y≈146 起（akliz 是 153），都不在矩形内。
- 背景在该区域是纯色（灰态 #DFE0E1 / 高亮态 #CECFD1），所以直接填色即可抹掉。
- 文字为实心单色，取区域内最深的像素即该图的文字色（模组=橙、Akliz=红，其余近黑）。

字号与字重：原先字高约 49px、常规字重，在游戏内实际显示尺寸下偏小偏淡。
现为 Hiragino Sans GB **W6**（比原来粗一档）、字高 **62px**（+27%），底边仍锚在 y=132
（与下划线的间距不变）。

水平位置改为统一居中于下划线（x[236..888] 的中点 562）。第一版是逐图沿用英文原文的
中心，结果 2 字标签（选项/退出）与 4~5 字标签（单人游戏/租用服务器）中心相差近 60px。
字放大后这个错位更明显，故一并对齐。

用法:
    python3 scripts/gen_menu_buttons.py            # 重新生成 14 张
    python3 scripts/gen_menu_buttons.py --check    # 只校验尺寸/未越界，不写文件
"""
import os
import shutil
import sys
from pathlib import Path

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    sys.exit('需要 Pillow：python3 -m pip install Pillow')

from paths import COMMON
ROOT = Path(__file__).resolve().parent.parent
ASSETS = COMMON / 'config' / 'fancymenu' / 'assets'
# 按钮图是就地重绘的：擦掉文字区再写中文。所以必须先有整合包的原图。
# 成品不入 git（见 .gitignore），本地/CI 跑之前从整合包拷一份干净的过来。
PACK = Path(os.environ.get(
    'ATM_PACK_ROOT',
    '/Users/yumeka/Documents/minecraft/.minecraft/versions/All the Mods 10'))



def save_png(im, path):
    """确定性写 PNG：参数一律显式给。

    Pillow 的默认压缩级别/optimize 策略换个版本就可能变，写出来的字节跟着变，
    于是产物哈希对不上而图其实一模一样，这种噪声会让「比 sha256」这件事失去意义。
    显式钉死之后，字节只剩下栅格化这一个变量，而它由 toolchain.lock.json
    里钉的 Pillow wheel（自带 freetype）决定。
    """
    im.save(path, format='PNG', optimize=False, compress_level=9)

def ensure_sources():
    src = PACK / 'config' / 'fancymenu' / 'assets'
    if not src.is_dir():
        sys.exit('❌ 找不到整合包的按钮原图: %s\n'
                 '   请设 ATM_PACK_ROOT 指向整合包（或其 overrides 目录）' % src)
    ASSETS.mkdir(parents=True, exist_ok=True)
    n = 0
    for stem in list(BUTTONS) + BASE_STEMS:
        for variant in ('color', 'gray'):
            f = '%s_%s.png' % (stem, variant)
            if (src / f).exists():
                shutil.copy2(src / f, ASSETS / f)
                n += 1
    print('  已从整合包取回 %d 张按钮原图' % n)

# 字体按顺序找第一个存在的，一律取中粗那一档。
# 首选仓库里的 assets-src/fonts/bold.otf（思源黑体 Bold，OFL，跑 scripts/fetch_fonts.sh 取），
# 这样 Linux 上的 CI 也能生成出逐字节相同的结果。macOS 自带字体只作为没取字体时的兜底。
FONT_CANDIDATES = [
    (str(ROOT / 'assets-src' / 'fonts' / 'bold.otf'), 0),
    (str(ROOT / 'assets-src' / 'fonts' / 'bold.ttf'), 0),
    ('/System/Library/Fonts/Hiragino Sans GB.ttc', 2),   # 冬青黑体简体中文 W6
    ('/System/Library/Fonts/STHeiti Medium.ttc', 1),     # 黑体-简 Medium
    ('/System/Library/Fonts/PingFang.ttc', 4),           # 苹方-简 Medium（部分系统才有）
]
FONT, FONT_INDEX = next(((f, i) for f, i in FONT_CANDIDATES if Path(f).exists()),
                        (None, 0))
if FONT is None:
    sys.exit('找不到可用的中文字体，候选：%s' % [f for f, _ in FONT_CANDIDATES])
TARGET_H = 62             # 目标字高（原 49）
SS = 4                    # 超采样倍数，保证描边和原图一样顺滑

# 擦除矩形（常量，见模块 docstring）：其内只有文字，其外是纯背景
BOX = (280, 50, 900, 143)
BASELINE_BOTTOM = 132     # 文字底边锚点，保持与下划线的间距不变
CENTER_X = 562            # 下划线 x[236..888] 的中点，所有按钮统一居中于此

BUTTONS = {
    'singleplayer': '单人游戏',
    'multiplayer':  '多人游戏',
    'options':      '选项',
    'exit':         '退出',
    'mods':         '模组',
    'language':     '语言',
    'akliz':        '租用服务器',
}
# GitHub / Reddit / Discord 等品牌按钮保持英文，不在此列

# 本包自己加的两个按钮（首页最下方）：整合包里没有这两张原图，拿 ATM 自己的
# GitHub 按钮当底稿，它左边的图标就是 GitHub logo，而这两个按钮也正是跳 GitHub，
# 语义对得上，视觉也与首页其余按钮完全一致。只擦文字区、图标原样保留。
NEW_BUTTONS = {
    'hanhua_home':   ('github', '汉化包主页'),
    'hanhua_issues': ('github', '问题反馈'),
}
BASE_STEMS = sorted({b for b, _ in NEW_BUTTONS.values()})


def text_color(im):
    """区域内最深的实心像素 = 该图的文字色（模组橙 / Akliz 红 / 其余近黑）"""
    px = im.load()
    best, col = 10 ** 9, None
    for y in range(BOX[1], BOX[3] + 1):
        for x in range(BOX[0], BOX[2] + 1):
            r, g, b, a = px[x, y]
            if a > 200 and r + g + b < best:
                best, col = r + g + b, (r, g, b, 255)
    return col


def render(word, color, target_h=TARGET_H):
    """把词渲染成一张紧贴文字的 RGBA 图（超采样后缩回）

    target_h 缺省是主菜单按钮的字高。gen_mod_textures.py 拿它按各自原图的字高复用。
    """
    # 先按目标字高反推字号：CJK 字面高度约为字号的 0.86
    size = int(round(target_h / 0.86))
    for _ in range(8):                       # 迭代校正到刚好 TARGET_H
        f = ImageFont.truetype(FONT, size * SS, index=FONT_INDEX)
        tmp = Image.new('RGBA', (size * SS * (len(word) + 2), size * SS * 3), (0, 0, 0, 0))
        ImageDraw.Draw(tmp).text((size * SS, size * SS), word, font=f, fill=color)
        bb = tmp.getbbox()
        h = (bb[3] - bb[1]) / SS
        if abs(h - target_h) < 0.6:
            break
        size = max(1, int(round(size * target_h / h)))
    glyph = tmp.crop(bb)
    return glyph.resize((max(1, round(glyph.width / SS)), max(1, round(glyph.height / SS))),
                        Image.LANCZOS)


def main(check_only=False):
    if not check_only:
        ensure_sources()
    n = 0
    for stem, word in sorted(BUTTONS.items()):
        for variant in ('color', 'gray'):
            p = ASSETS / f'{stem}_{variant}.png'
            if not p.exists():
                print(f'  跳过（不存在）: {p.name}')
                continue
            im = Image.open(p).convert('RGBA')
            bg = im.getpixel((930, 60))           # 文字区右侧空白，纯背景
            col = text_color(im)
            glyph = render(word, col)
            x = int(round(CENTER_X - glyph.width / 2))
            y = BASELINE_BOTTOM - glyph.height + 1
            if x < BOX[0] or x + glyph.width > BOX[2] or y < BOX[1]:
                sys.exit(f'❌ {p.name}: 文字 x[{x}..{x + glyph.width}] y[{y}..] 越出擦除矩形 {BOX}')
            if not check_only:
                ImageDraw.Draw(im).rectangle(BOX, fill=bg)
                im.alpha_composite(glyph, (x, y))
                save_png(im, p)
            print('  %-24s %s  字高=%d 宽=%d  x[%d..%d] y[%d..%d] 色=%s'
                  % (p.name, word, glyph.height, glyph.width,
                     x, x + glyph.width, y, y + glyph.height, col[:3]))
            n += 1
    for stem, (base, word) in sorted(NEW_BUTTONS.items()):
        for variant in ('color', 'gray'):
            src = ASSETS / f'{base}_{variant}.png'
            if not src.exists():
                sys.exit(f'❌ 缺底稿 {src.name}（本包新增按钮拿它重绘）')
            im = Image.open(src).convert('RGBA')
            bg = im.getpixel((930, 60))
            col = text_color(im)
            glyph = render(word, col)
            x = int(round(CENTER_X - glyph.width / 2))
            y = BASELINE_BOTTOM - glyph.height + 1
            if x < BOX[0] or x + glyph.width > BOX[2] or y < BOX[1]:
                sys.exit(f'❌ {stem}_{variant}: 文字越出擦除矩形 {BOX}')
            if not check_only:
                ImageDraw.Draw(im).rectangle(BOX, fill=bg)
                im.alpha_composite(glyph, (x, y))
                save_png(im, ASSETS / f'{stem}_{variant}.png')
            print('  %-24s %s  字高=%d 宽=%d  （底稿 %s_%s）'
                  % (f'{stem}_{variant}.png', word, glyph.height, glyph.width, base, variant))
            n += 1
    print(('校验通过' if check_only else '已生成') + f' {n} 张')


if __name__ == '__main__':
    main(check_only='--check' in sys.argv)
