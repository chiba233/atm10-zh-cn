#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# atm10-zh-cn — All the Mods 10 简体中文汉化补丁「绿油油版」
# Copyright (C) 2026 星野夢華 (Hoshino Yumeka)
# SPDX-License-Identifier: GPL-3.0-or-later
"""补上任务书**引用了、整合包里却没有**的章节配图。

ATM10 8.0 把机械动力章节的任务连线改成一根根「传动杆」贴图，引用
`atm:textures/questpics/create/create_shaft.png` 共 27 处——而这张图整合包里
从来没有过：7.0/7.1/7.2/7.3/8.0 五个版本的 `questpics/create/` 都只有那 11 张，
干净的 8.0 实例全盘 find 也没有，create 系 jar 里也没有。缺失纹理在游戏里
就是那片品红黑格，把整章的连线画成一团花（不装本包同样如此，7.0–7.3 不受影响）。

成因在上游，但玩家看到的是「我装了这个包，任务书是花的」，所以补。
资源包的加载顺序排在 KubeJS 之后（见 gen_quest_banners.py 顶部），同路径放一张
就生效；而这张在任何包里都不存在，也就谈不上覆盖谁。

**画，不搬**：仓库不放上游字节（见 CONTRIBUTING「版权红线」），何况这张上游
压根没有。画成 7.3 里那种细连线的样子——那是玩家在旧版看惯的形态，
比凭空造一根传动杆更不容易出戏。形状按章节里的实际用法定：27 处引用的宽高比
集中在 4:1，另有 ±45° / ±60° / 70° / 90° 旋转，所以画成横向、上下对称、
两端齐平（旋转拼接时接缝不显）。

**顺带当闸用**：跑完核一遍该版本章节引用的每一张 questpic 是否都拿得到，
拿不到又不在本脚本表里的，当场红——上游再丢图，下一次构建就会说出来，
而不是等玩家截图。

用法:
    python3 scripts/gen_missing_questpics.py
    ATM_PACK_ROOT=<整合包目录> python3 scripts/gen_missing_questpics.py
"""
import os
import re
import sys
from pathlib import Path

try:
    from PIL import Image, ImageDraw
except ImportError:                                      # noqa: BLE001
    sys.exit('需要 Pillow：python3 -m pip install Pillow')

sys.path.insert(0, str(Path(__file__).resolve().parent))
from paths import PACK                                   # noqa: E402

OUT = PACK / 'assets' / 'atm' / 'textures' / 'questpics'
INST = Path(os.environ.get(
    'ATM_PACK_ROOT',
    '/Users/yumeka/Documents/minecraft/.minecraft/versions/All the Mods 10'))
SRC = INST / 'kubejs' / 'assets' / 'atm' / 'textures' / 'questpics'
CHAPTERS = INST / 'config' / 'ftbquests' / 'quests' / 'chapters'

# 7.3 里那条连线呈现出来的淡灰粉。FTB Quests 自己的 dependency.png 是纯白、
# 靠代码染色，照它的像素画只会得到一根白条，所以取的是**显示后的**颜色。
LINE = (198, 184, 184, 255)
EDGE = (150, 139, 139, 255)


def draw_link(w=512, h=128):
    """一段横向连线：两端齐平，便于按任意角度旋转后首尾相接。"""
    im = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    half = max(3, h // 12)                 # 线宽约为图高的 1/6
    mid = h // 2
    d.rectangle([0, mid - half, w - 1, mid + half], fill=LINE)
    d.rectangle([0, mid - half, w - 1, mid - half + 1], fill=EDGE)
    d.rectangle([0, mid + half - 1, w - 1, mid + half], fill=EDGE)
    return im


# 缺哪张、画成什么样。加一项就是加一行，不用动逻辑。
MISSING = {
    'create/create_shaft.png': draw_link,
}


def referenced():
    """该版本的章节文件里每个 questpic 引用了几次（路径 → 次数）。"""
    if not CHAPTERS.is_dir():
        sys.exit('❌ 找不到章节目录 %s（本脚本要对着整合包实例跑）' % CHAPTERS)
    out = {}
    for p in sorted(CHAPTERS.glob('*.snbt')):
        for m in re.findall(r'questpics/([a-z0-9_/-]+\.png)',
                            p.read_text(encoding='utf-8')):
            out[m] = out.get(m, 0) + 1
    return out


def on_disk():
    """上游实际有的图，按**小写**路径索引。

    章节里的引用一律小写（资源路径必须小写），而上游的目录名不一定：ATM 把
    现代工业化那三张放在 `ModernIndustrialization/` 下，章节却写
    `modernindustrialization/`。Windows / macOS 的文件系统不区分大小写，
    这三张照样显示；Linux 上找不到。这是上游 7.0 就有的老毛病，不是我们引入的，
    也不该让构建红——闸要判的是「这个引用有没有对应的图」，有，只是大小写没对齐。
    """
    got = {}
    if SRC.is_dir():
        for p in SRC.rglob('*.png'):
            got[str(p.relative_to(SRC)).replace(os.sep, '/').lower()] = p
    return got


def main():
    used = referenced()
    got = on_disk()
    for rel, fn in sorted(MISSING.items()):
        if rel in got:
            # 上游把图补回来了。继续画就成了「拿我们的图盖掉上游的」——那是另一回事，
            # 必须有人重新裁决，不许静默发生。
            sys.exit('❌ %s 上游已经有了（%s），去掉 MISSING 里的这一条。'
                     % (rel, got[rel].name))
        t = OUT / rel
        t.parent.mkdir(parents=True, exist_ok=True)
        fn().save(t)
        print('  现画 %s（本版章节引用 %d 处）' % (rel, used.get(rel, 0)))
    # 大小写没对齐的：上游有这张图，只是目录名大小写与引用不一致。说出来但不红。
    odd = sorted(u for u in used
                 if u in got
                 and str(got[u].relative_to(SRC)).replace(os.sep, '/') != u)
    for u in odd:
        print('  ⚠️ %s 上游实际叫 %s，只有大小写不同（Linux 上找不到，'
              '这是上游的老毛病，我们不改）'
              % (u, str(got[u].relative_to(SRC)).replace(os.sep, '/')))
    lost = sorted(u for u in used if u not in got and u not in MISSING)
    if lost:
        sys.exit('❌ 章节引用了这些配图，整合包里没有、本脚本也没画：\n   %s\n'
                 '   上游又丢图了。补进 MISSING，或者去问上游，别让它这样发出去。'
                 % '\n   '.join(lost))
    print('✅ 缺图补齐：本版章节引用的 %d 张配图全部拿得到' % len(used))


if __name__ == '__main__':
    main()
