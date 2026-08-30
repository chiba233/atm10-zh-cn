#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# atm10-zh-cn — All the Mods 10 简体中文汉化补丁「绿油油版」
# Copyright (C) 2026 星野夢華 (Hoshino Yumeka)
# SPDX-License-Identifier: GPL-3.0-or-later
"""任务书章节横幅上的艺术字（烤进 PNG，语言文件够不着）。

ATM 的任务书每章顶上挂一张标题图，文字直接画在 PNG 里。原图在整合包自带的
`kubejs/assets/atm/textures/questpics/`，资源包的加载顺序排在 KubeJS 之后
（对着 ReloadableResourceManager 日志核过），所以本包放同路径的图即可覆盖。

## 写什么字：单一真源 = 该图所属章节的中文标题

每张标题图都只被一个章节引用（脚本启动时会重新核验），所以直接取那一章
已有的中文标题，不另造词。这样任务书侧边栏、章节标题、横幅三处永远一致。

## 怎么画：从原图采样，而不是逐张手调

这些是带渐变和描边的艺术字，一张张配色调不过来，也不可复现。做法是：

1. **描边色 / 内部像素的划分**：先用最小值滤波把不透明区**整体腐蚀掉描边的厚度**
   （原图描边普遍有 3~4 像素厚，只排除紧贴透明的那一圈远远不够——剩下几层黑描边
   会被当成材质采进去，中文笔画上就是一块块黑斑）。腐蚀掉的外圈取中位色作描边色，
   腐蚀后活下来的才算内部像素；
2. **默认只取颜色，不抠材质**：绝大多数标题字就是「单色 + 描边」，
   取原图的本色与描边色、自己干净地画就够了。硬去抠材质反而引入一串问题
   （描边被当材质→黑斑、两行时第二行套上暗部→像缺笔、细笔画腐蚀不动→整片黑）。
   只有**确实是材质字**的那几张（APOTHIC 裂纹石、UNDERGARDEN 长苔石、
   FIRE DRAGON 岩浆岩……）才走材质路径，名单写死在 TEXTURED 里。
   下面这段讲的就是那条材质路径：ATM 的标题字大多不是纯色——APOTHIC 是裂纹石头、
   UNDERGARDEN 是长苔石、EXTENDED AND ADVANCED AE 干脆是用方块贴图拼出来的立体字。
   只取一个颜色或一条竖向渐变，纹理和方块效果就全没了（"抠烂了"）。
   做法是按行提取原字内部（非描边）的像素序列，横向平铺成一张与画布同大的材质板，
   再用中文字形当遮罩去取色——中文看起来就像用同一种材料刻出来的。
   **只取最高的那一条文字带**：不少原图是两行且两行异色（APOTHIC 灰 / ENCHANTING 紫、
   DRACONIC / EVOLUTION、INDUSTRIAL FOREGOING 加一行小字副标），
   整块一起采会把「上灰下紫」当成渐变，映到一行中文上就是拦腰一道色带（斑纹）；
3. **描边宽度**：按图高的 4.5% 估，最少 2px；
4. 文字按 `min(可用宽/字宽, 可用高/字高)` 等比放到最大后居中，
   4 倍超采样渲染再缩回，边缘与原图同级顺滑。

**中文排几行，材质板就竖向重复几遍**：材质板是从原图**一行**英文取的竖向剖面
（上部高光、下部阴影）。中文若排两行而材质只拉伸一次，第二行就正好落在剖面的
下半段——整行套上字母底部的暗部阴影，看起来像被抠烂了。

**尺寸基准是原图的内容框，不是整块画布** —— 有些图（如 id_title 400×400）文字只占
中间一条，按整块画布铺满会让中文比原文大一圈，贴进任务书的固定框里就撑爆了。

## 带装饰的图：只换文字框

少数图除了文字还有别的东西（神秘学两侧站着两只怪、气动工艺右边有小图标、
暮色森林的字压在一条石砖带上）。整张重画会把这些一起抹掉，所以给它们单独标出
「只有英文字的那个框」（按百分比），只在框内替换；框外原样保留。
暮色森林那条石砖带被文字压着，抹掉会留个洞，所以从文字上方干净的砖行取一条
纹理平铺补上。

## 字形：逐图判定，不是全套一种字

原图 154 张的字体各不相同——有 MC 那种方块像素字（CHAPTER 2 / Mekanism / Powah）、
有粗衬线（The Aether / Bumblezone / Nature's Aura）、有粗黑无衬线（Create / Artifacts）、
也有细体（Deeper and Darker / Integrated Dynamics）。全用同一种字既不像原作也不好看。

判定是机械的，不靠人眼逐张点名：

- **是不是像素字**：把不透明遮罩按 k×k 方格对齐检查（k 从大到小试），
  若某个 k≥2 能让每个格子内部要么全实要么全空，说明原图是 1 倍点阵放大 k 倍来的，
  即像素字体 → 用 Minecraft 自己的 Unifont 点阵渲染，放大倍率对齐原图的 k。
- **笔画粗细**：量平均笔画宽度占字高的比例，据此在细黑 / 粗黑 / 粗宋之间选。
- 少数明显是衬线体的（天境 / 蜜蜂领域 / 自然灵气 / 遗物 / 神秘学 等）在 SERIF 表里点名，
  走宋体 Black。

## 点阵渲染细节

早期版本用系统黑体渲染，字形是平滑矢量，跟原图的像素英文完全不搭。
正解是用 **Minecraft 渲染中文时用的那套字**——GNU Unifont，16×16 点阵，
整合包 assets 里就有（`minecraft/font/unifont.zip`，随资源索引下载，无需外部字体）。

流程：按 Unifont 的 `.hex` 位图在 **1 倍尺度**拼出文字 → 按整数倍**最近邻**放大到目标框。
这样笔画边缘是硬像素块，和原图的像素英文同一套观感；描边也在 1 倍尺度做膨胀再一起放大，
所以描边同样是方块状，不会出现矢量字那种圆滑边。

## 例外：不动的图

- 4 张压根不是文字（木框、末影人图标、五芒星、气动工艺图标）
- 章节里那些非标题的插图（矿车、生物图鉴等）本来就没字

用法:
    python3 scripts/gen_quest_banners.py            # 重新生成
    python3 scripts/gen_quest_banners.py --check    # 只算尺寸不写文件
"""
import os
import re
import statistics
import sys
from pathlib import Path

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    sys.exit('需要 Pillow：python3 -m pip install Pillow')

import vanilla
from paths import PACK, SRC
ROOT = Path(__file__).resolve().parent.parent
OUT = PACK / 'assets' / 'atm' / 'textures' / 'questpics'
# 源图 / 任务书来自整合包本体。默认取本机实例，CI 上用 ATM_PACK_ROOT 指向
# 官方包解压出来的 overrides 目录，这样 Linux 上也能复现出同样的图。
INST = Path(os.environ.get(
    'ATM_PACK_ROOT',
    '/Users/yumeka/Documents/minecraft/.minecraft/versions/All the Mods 10'))
SRC = INST / 'kubejs' / 'assets' / 'atm' / 'textures' / 'questpics'
QUESTS = INST / 'config' / 'ftbquests' / 'quests'

MARGIN = 4    # 原图四周的透明边
LINE_GAP = 2  # 多行时的行距（1 倍尺度像素）

# ---------------------------------------------------------------- 字体
# 优先用仓库里 assets-src/fonts/<名字>.(ttf|otf|ttc)；没有就退回系统自带的。
# 想让某一类更贴原图，把对应字体丢进那个目录即可，不用改代码（见该目录的 README）。
FONTS_DIR = ROOT / 'assets-src' / 'fonts'
SYSTEM_FALLBACK = {
    'thin':  ('/System/Library/Fonts/Hiragino Sans GB.ttc', 0),   # 冬青黑 W3
    'bold':  ('/System/Library/Fonts/Hiragino Sans GB.ttc', 2),   # 冬青黑 W6
    'serif': ('/System/Library/Fonts/Songti.ttc', 0),             # 宋体 SC Black
    'deco':  ('/System/Library/Fonts/Songti.ttc', 0),
}



def save_png(im, path):
    """确定性写 PNG：参数一律显式给。

    Pillow 的默认压缩级别/optimize 策略换个版本就可能变，写出来的字节跟着变，
    于是产物哈希对不上而图其实一模一样——这种噪声会让「比 sha256」这件事失去意义。
    显式钉死之后，字节只剩下**栅格化**这一个变量，而它由 toolchain.lock.json
    里钉的 Pillow wheel（自带 freetype）决定。
    """
    im.save(path, format='PNG', optimize=False, compress_level=9)

def face_file(name):
    for ext in ('.ttf', '.otf', '.ttc'):
        p = FONTS_DIR / (name + ext)
        if p.exists():
            return str(p), 0
    return SYSTEM_FALLBACK.get(name, SYSTEM_FALLBACK['bold'])


# 按「模组/目录」分组指定字面。原图每套标题图共用一种字体，所以按组指定即可，
# 不必逐张点名。pixel = 用 Minecraft 自带的 Unifont 点阵渲染。
FACE_BY_PREFIX = [
    # ---- 逐图点名（与同目录其余图不是一套字，必须排在目录规则前面）
    ('mystical_agriculture/title.png', 'bold'),   # 同目录别的是像素字，这张是模组官方 logo 的无衬线
    # ---- 方块像素字（MC 风的硬边字）
    ('mek/',                     'pixel'), ('cataclysm/',            'pixel'),
    ('powah/',                   'pixel'), ('twilight_forest_title', 'pixel'),
    ('deepndark/',               'pixel'), ('immersive/',            'pixel'),
    ('forbidden/forbidden_title_tier', 'pixel'), ('bumblezone/bumble_title_', 'pixel'),
    ('basicarmor/',              'pixel'), ('allthemodium/all_title', 'pixel'),
    ('chap2/atmstar_title1',     'pixel'), ('chap3/creative_chap4',  'pixel'),
    ('extremereactors/',         'pixel'), ('oritech/',              'pixel'),
    ('pylons/',                  'pixel'), ('apothic/enchant_',      'pixel'),
    ('pneumaticcraft/',          'pixel'), ('industrialforegoing/',  'pixel'),
    ('artifacts/',               'pixel'), ('id_title',              'pixel'),
    ('extended_advanced_ae/',    'pixel'), ('mystical_agriculture/', 'pixel'),
    ('undergarden/undergarden_biomes',    'pixel'),
    ('undergarden/undergarden_friendly',  'pixel'),
    ('undergarden/undergarden_hostile',   'pixel'),
    ('undergarden/undergarden_neutral',   'pixel'),
    ('undergarden/undergarden_tools',     'pixel'),
    ('undergarden/undergarden_vegetation','pixel'),
    ('chap2/atmstar_title2',     'pixel'), ('chap3/creative_creative', 'pixel'),
    ('ae2.png',                  'pixel'), ('allthemodium/all_allthemodium', 'pixel'),
    ('aurora/',                  'pixel'),   # 白字身 + 深描边的方框点阵字
    ('apothic/other_spawners',   'pixel'), ('apothic/spawn_eggs',    'pixel'),
    ('building_tips/',           'pixel'), ('eternal/starlight_',    'pixel'),
    ('furnaces/',                'pixel'), ('generator/',            'pixel'),
    ('gettingstarted/titleimage','pixel'), ('logistics/',            'pixel'),
    ('xycraft/',                 'pixel'),
    # ---- 粗衬线 / 装饰
    ('aether/',                  'serif'), ('bumblezone/bumble_title.png', 'serif'),
    ('apothic/apotheosis_gear',  'serif'), ('railcraft/railcraft',   'serif'),
    ('natures_aura/',            'serif'), ('occultism/',            'serif'),
    ('draconic/',                'serif'), ('undergarden/undergarden_title', 'serif'),
    ('relics/',                  'serif'), ('iron_spells/',          'serif'),
    ('apothic/gear_',            'serif'), ('chap3/creative_items',  'serif'),
    ('chap3/creative_star',      'serif'), ('iceandfire/',           'serif'),
    ('mahou/',                   'serif'), ('eternal/',              'serif'),
    ('neovitae/',                'serif'),
    # ---- 细体
    ('ars/',                     'thin'),  ('router/',               'thin'),
    # ---- 其余默认粗黑
]


def pick_face(rel):
    for pre, kind in FACE_BY_PREFIX:
        if rel.startswith(pre):
            return kind
    return 'bold'


def pixel_scale(im):
    """原图是不是像素字？是就返回放大倍率 k，不是返回 1。

    判据一（硬）：像素字**没有抗锯齿**——alpha 只有 0 和 255 两种值。
    矢量渲染的标题字边缘一定有半透明过渡，这条一票否决。
    判据二：再找最大的 k，使得按 k×k 方格切开后几乎每格内部纯色。
    """
    a = im.getchannel('A')
    bb = a.getbbox()
    if not bb:
        return 1
    a = a.crop(bb)
    hist = a.histogram()
    tot = sum(hist)
    soft = tot - hist[0] - hist[255]
    if soft / max(1, tot) > 0.02:          # 有抗锯齿 → 矢量字
        return 1
    a = a.point(lambda v: 255 if v > 128 else 0)
    ap = a.load()
    W, H = a.size
    for k in range(8, 1, -1):
        if W // k < 4 or H // k < 4:
            continue
        bad = n = 0
        for by in range(H // k):
            for bx in range(W // k):
                v = {ap[bx * k + dx, by * k + dy] for dy in range(k) for dx in range(k)}
                n += 1
                if len(v) > 1:
                    bad += 1
        if n and bad / n < 0.02:
            return k
    return 1


def ink_density(im):
    """外接框内的着墨比例，用来选字重：粗体密、细体疏"""
    a = im.getchannel('A').point(lambda v: 255 if v > 128 else 0)
    bb = a.getbbox()
    if not bb:
        return 0.0
    a = a.crop(bb)
    return sum(1 for v in a.getdata() if v) / (a.size[0] * a.size[1])


def load_unifont():
    """Minecraft 自己用来渲染中文的 GNU Unifont（16×16 点阵），从游戏 assets 里取"""
    raw = vanilla.unifont_hex(INST)
    g = {}
    for line in raw.splitlines():
        cp, bits = line.split(':')
        w = len(bits) // 4                      # 8 或 16 像素宽
        g[int(cp, 16)] = (w, [int(bits[r * (w // 4):(r + 1) * (w // 4)], 16) for r in range(16)])
    return g


try:
    UNIFONT = load_unifont()
except Exception:
    # Unifont 只是没有像素字体时的兜底。CI 上没有 .minecraft 资源索引，
    # 但 assets-src/fonts/pixel-*.ttf 一定在（fetch_fonts.sh 取的），所以用不到它。
    UNIFONT = {}

# 点阵中文字面：优先用 assets-src/fonts/pixel-<设计尺寸>.ttf（缝合像素字体，OFL，
# 跑 scripts/fetch_fonts.sh 取），没有就退回 Unifont。两者都在**设计尺寸**上光栅化
# 成纯 0/1 点阵，再交给 render() 做整数倍最近邻放大，边缘始终是硬的，不会糊。
#
# 为什么不用 Unifont：它的汉字画在 16px 字框里、笔画只有 1px，放大后笔画相对字高
# 只占 1/16，配在原图那种粗壮的像素英文旁边显得又细又虚。12px 的汉字实际着墨高
# 11px，同样 1px 笔画占 1/11，放大倍率大了四成半，笔画跟着粗四成半，才压得住。
#
# 为什么要两档：放大倍率 k 只能取整数（取不整就不是硬边像素了），字框越高 k 的
# 台阶越粗。只用 12px 时有十几张图算出来的 k 比理论值差整整一档，字偏小。备一档
# 10px 兜着，既保住整数倍放大又不至于太小。
#
# 8px 那档下过又撤了：字框只有 7px，笔画多的字（斯、械、塔）笔画会粘在一起糊成
# 一团，撑得再满也没用。字号大小服从可读性，不为贴近原图英文的尺寸让路。
#
# 为什么是缝合像素字体而不是方舟像素字体：方舟的 zh_cn 12px 缺「旋热然聚嗡蟒骏」
# 这类常用字，10px/16px 更是只做了千把个常用字。缝合字体就是拿方舟 + Cubic 11 +
# Galmuri 拼起来补全覆盖的，8px/12px 对本包用到的字是零缺字。
#
# 缺字必须查字表判定，不能靠「渲染出来像不像豆腐块」反推——「口」这个字本身就长
# 那样。曾经漏查，「斯库拉」「植被」整个渲成了空框。
PIXEL_SIZES = (10, 12)


def pixel_face(size):
    p = FONTS_DIR / ('pixel-%d.ttf' % size)
    return p if p.exists() else None


def ttf_charset(path):
    """读 TTF 的 cmap 表，返回它真正有字形的码点集合"""
    import struct
    b = Path(path).read_bytes()
    n, = struct.unpack_from('>H', b, 4)
    cmap = next((o for t, _, o, _ in
                 (struct.unpack_from('>4sIII', b, 12 + 16 * i) for i in range(n))
                 if t == b'cmap'), None)
    if cmap is None:
        return set()
    out, nt = set(), struct.unpack_from('>H', b, cmap + 2)[0]
    for i in range(nt):
        o = cmap + struct.unpack_from('>HHI', b, cmap + 4 + 8 * i)[2]
        fmt, = struct.unpack_from('>H', b, o)
        if fmt == 4:
            segx2, = struct.unpack_from('>H', b, o + 6)
            seg = segx2 // 2
            ends = struct.unpack_from('>%dH' % seg, b, o + 14)
            starts = struct.unpack_from('>%dH' % seg, b, o + 16 + segx2)
            for s, e in zip(starts, ends):
                if s <= e < 0xFFFF:
                    out.update(range(s, e + 1))
        elif fmt == 12:
            ng, = struct.unpack_from('>I', b, o + 12)
            for j in range(ng):
                s, e, _ = struct.unpack_from('>III', b, o + 16 + 12 * j)
                out.update(range(s, e + 1))
    return out


PIXEL_CHARSET = {s: ttf_charset(pixel_face(s)) for s in PIXEL_SIZES if pixel_face(s)}


def hole_count(mask):
    """点阵里被笔画围起来的封闭内白个数。

    用来判定「笔画糊在一起了」：字框一小，「械」的两个口、「堆」的三横之间就会
    粘连，内白随之消失。数内白比数着墨比例灵——好的点阵字在小字框下会**简化**
    笔画而不是加粗，着墨比例看不出差别，内白却实打实少了。
    """
    h, w = len(mask), len(mask[0])
    seen = [[False] * w for _ in range(h)]
    stack = [(x, y) for y in range(h) for x in (0, w - 1) if not mask[y][x]]
    stack += [(x, y) for x in range(w) for y in (0, h - 1) if not mask[y][x]]
    for x, y in stack:
        seen[y][x] = True
    while stack:                                  # 先把与边界连通的背景涂掉
        x, y = stack.pop()
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            a, b = x + dx, y + dy
            if 0 <= a < w and 0 <= b < h and not mask[b][a] and not seen[b][a]:
                seen[b][a] = True
                stack.append((a, b))
    n = 0
    for y in range(h):                            # 剩下的背景连通块就是内白
        for x in range(w):
            if mask[y][x] or seen[y][x]:
                continue
            n += 1
            st = [(x, y)]
            seen[y][x] = True
            while st:
                a, b = st.pop()
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    c, d = a + dx, b + dy
                    if 0 <= c < w and 0 <= d < h and not mask[d][c] and not seen[d][c]:
                        seen[d][c] = True
                        st.append((c, d))
    return n


def pixel_candidates(text):
    """能完整写出这段文字的档位；一档都没有就退回 Unifont（None）"""
    need = {ord(c) for c in text if c != '\n'}
    ok = [s for s in PIXEL_SIZES if s in PIXEL_CHARSET and need <= PIXEL_CHARSET[s]]
    return ok or [None]

# 图 → 中文。取值来自「引用该图那一章的中文标题」，脚本会核验对得上。
# 少数几条与章节标题不同，原因写在行尾。
# 带装饰的图：(左, 上, 右, 下) 百分比 —— 只有英文字的那个框；框外原样保留。
# inpaint=True 表示框内是有底纹的（不能直接抹成透明），从 patch_from 那几行取纹理平铺。
BOXES = {
    # 两只怪的爪子和字的阴影连成一块，连通域切不开，硬校验只能豁免；成图逐张看过
    'occultism/occultism_title.png': dict(box=(16, 27, 73, 67), touching=True),   # 左右两只怪要留
    # 末尾的 T / D 和右边那个压力管图标在横向上挨着（字止于 91%，图标起于 90%），
    # 切不干净：框收到 82.7% 会把 T、D 两个英文字母留在图上，只能取 91.4% 让图标
    # 最左侧一小块跟着被擦掉。硬校验对它豁免。
    'pneumaticcraft/pnc_title.png':  dict(box=(0, 0, 91.4, 100), touching=True),
    'twilight_forest_title.png':     dict(box=(5, 18, 95, 72), patch_from=(86, 96)),  # 字压在石砖带上
    # 下面这些两端挂着装饰（方块、蜜蜂、剑、钻石、模组图标），只换中间那条文字。
    # 边界值不是目测拍的，是按连通域算出来的：先取不透明遮罩的 8 邻接连通域，
    # 文字是一组、两端装饰各是一组，框取文字那组的包围盒。目测过一版，
    # 结果把「悬赏板」左边那对剑和「食物与耕种」左边的装饰各啃掉一块，
    # 所以下面加了 check_boxes() 硬校验，边界切断任何连通域就直接报错退出。
    'ae2.png':                       dict(box=(0, 0, 78, 100)),   # 右边那个「2」是 logo 图案，留着当序号
    'basic_power/allthepower.png':   dict(box=(20, 0, 79, 100)),
    'bounty.png':                    dict(box=(31, 0, 68, 100)),
    'food_and_farming.png':          dict(box=(14, 0, 85, 100)),
    'tips_and_tricks.png':           dict(box=(16, 0, 82, 100)),
    # 这两张的装饰和文字在像素上是**连着**的（蜜蜂触角搭在字上、神秘农业整条黑底是
    # 一块），连通域切不开，硬校验对它们只能豁免。边界改从「有墨但没有字色」的
    # 列区间取（蜜蜂 19~24% 与 76~81% 两段只有触角没有字），并逐张看过成图。
    'bees/productive_bees.png':      dict(box=(24, 0, 76, 100), touching=True),
    'mystical_agriculture/title.png': dict(box=(21, 0, 81, 100), patch_from=(4, 14),
                                          touching=True),        # 底是不透明黑条
}


def check_boxes():
    """硬校验：擦除框的边界不许切断任何连通域。

    框写偏一点，两端的装饰就会被啃掉半个而人眼未必立刻发现（「悬赏板」左边那对剑
    就这么少了一把）。这里逐张核：凡是同时有像素在框内又有像素在框外的连通域，
    就说明边界从它身上穿过去了，直接报错。
    """
    for rel, cfg in sorted(BOXES.items()):
        # patch_from 的图底是整块不透明背景，框必然横切它——但框内会拿干净的
        # 背景条补回去，不算啃掉装饰，所以跳过。
        if cfg.get('touching') or 'patch_from' in cfg:
            continue
        im = Image.open(SRC / rel).convert('RGBA')
        w, h = im.size
        a = im.getchannel('A').load()
        x0, y0 = round(w * cfg['box'][0] / 100), round(h * cfg['box'][1] / 100)
        x1, y1 = round(w * cfg['box'][2] / 100), round(h * cfg['box'][3] / 100)
        seen = [[False] * w for _ in range(h)]
        for sy in range(h):
            for sx in range(w):
                if seen[sy][sx] or a[sx, sy] <= 40:
                    continue
                st, npx, ins, out = [(sx, sy)], 0, 0, 0
                seen[sy][sx] = True
                while st:
                    x, y = st.pop()
                    npx += 1
                    if x0 <= x < x1 and y0 <= y < y1:
                        ins += 1
                    else:
                        out += 1
                    for dy in (-1, 0, 1):
                        for dx in (-1, 0, 1):
                            p, q = x + dx, y + dy
                            if 0 <= p < w and 0 <= q < h and not seen[q][p] and a[p, q] > 40:
                                seen[q][p] = True
                                st.append((p, q))
                # 被切掉的是小的那半：装饰被啃 or 英文没擦干净，两种都不能要。
                # 留一点容差——有的图装饰的尖端和文字在像素上就是挨着的（悬赏板的剑尖
                # 压进文字第一列），差几个像素切不开，也确实看不出来。
                loss = min(ins, out)
                if npx >= 20 and loss:
                    if loss > max(64, npx * 0.01):
                        sys.exit('❌ %s 的擦除框切断了一个连通域（框内 %d / 框外 %d）'
                                 '——边界会把装饰啃掉半个，改 BOXES' % (rel, ins, out))
                    print('  ⚠ %s 擦除框边界擦掉了 %d 像素（在容差内）' % (rel, loss))

# ── 文字压在美术上的图：按描边抠字，美术原样留着 ──────────────────────────
#
# BOXES 那条路是「框内整块擦掉、框外保留」，前提是装饰在文字**两侧**。
# neovitae 不是：文字压在凤凰与圣杯上，两侧的 DNA 装饰又和文字同处一条带。
# 按框擦会把凤凰拦腰挖空，装饰也一起没。
#
# 可用的特征是**浅色描边只出现在文字上**——凤凰、圣杯、装饰都是纯深红，没有白边。
# 于是：取浅色遮罩 → 膨胀成闭合轮廓 → 从画布外围洪水填充 → 灌不到的就是字腹，
# 描边 ∪ 字腹 = 英文字。这张图抠出 10.5 万像素（占不透明区 56%），
# 凤凰、圣杯、血滴、两侧装饰、底部标尺全部完整。
#
#   light  判定「这是描边」的 RGB 下限
#   dense  判定「这一列/行属于字」的像素数下限，按图高取比例。装饰线很细，
#          用它把两端装饰排除在字的外接框之外——既不擦它们，也不让它们把
#          绘制框撑到满宽（撑宽了中文会被拉扁）
#   scale  中文相对英文外接框的高度比。CJK 字身撑满字面框，而英文有升降部，
#          取 1.0 会让中文比原文高出一截，把底部那条标尺压掉
WORDMARK = {
    'neovitae/neovitae.png': dict(light=(195, 185, 185), dense=0.04, scale=0.86),
}


def wordmark_split(im, rel, cfg):
    """按描边把压在美术上的英文字抠出来。

    → (只含英文字的子图, 该子图在原图里的位置, 已清掉英文字与投影的底图)

    每一步都 fail-closed：抠不出字就退出。静默返回空遮罩的话，产出的是一张
    只剩中文、美术全丢的图——而这种图不会有任何闸报错，只有玩家会看到。
    """
    from PIL import ImageChops, ImageDraw, ImageFilter
    W, H = im.size
    r, g, bl, a = im.split()
    lo = cfg['light']
    solid = a.point(lambda v: 255 if v >= 40 else 0)
    light = ImageChops.multiply(
        ImageChops.multiply(r.point(lambda v: 255 if v > lo[0] else 0),
                            g.point(lambda v: 255 if v > lo[1] else 0)),
        ImageChops.multiply(bl.point(lambda v: 255 if v > lo[2] else 0), solid))
    n_light = sum(light.point(lambda v: 1 if v else 0).getdata())
    if n_light < W * H * 0.004:
        sys.exit('❌ %s 的浅色描边只有 %d 像素，抠不出英文字——WORDMARK 的 light 阈值不对'
                 % (rel, n_light))

    # 膨胀成闭合轮廓，再从画布外围灌水：灌不到的封闭区域就是字腹。
    # 先加一圈透明边，保证 (0,0) 一定在字外——原图四角万一有墨，灌水会从内部起步。
    edge = light.filter(ImageFilter.MaxFilter(5))
    pad = Image.new('L', (W + 2, H + 2), 0)
    pad.paste(edge, (1, 1))
    ImageDraw.floodfill(pad, (0, 0), 128)
    outside = pad.crop((1, 1, W + 1, H + 1))
    word = ImageChops.lighter(edge, outside.point(lambda v: 255 if v == 0 else 0))
    if not word.getbbox():
        sys.exit('❌ %s 抠出来的英文字是空的' % rel)

    # 字的外接框只取「密集」的行列：装饰线很细，这样把它们排除在框外，
    # 既不会被擦掉，也不会把绘制框撑宽
    wp = word.load()
    thr = max(6, round(H * cfg['dense']))
    cols = [x for x in range(W) if sum(1 for y in range(H) if wp[x, y]) >= thr]
    rows = [y for y in range(H) if sum(1 for x in range(W) if wp[x, y]) >= thr]
    if not cols or not rows:
        sys.exit('❌ %s 抠出来的英文字不成片（dense 阈值 %d 太高）' % (rel, thr))
    bx0, by0, bx1, by1 = cols[0], rows[0], cols[-1] + 1, rows[-1] + 1

    # 清底：框内擦掉字；字外一圈的低饱和像素是原字的投影与描边余烬，一并清掉。
    # 美术是饱和的深红，按饱和度就能分开；清理只在框内做，框外一个像素不碰。
    near = word.filter(ImageFilter.MaxFilter(41))
    far = word.filter(ImageFilter.MaxFilter(81))
    base = im.copy()
    bp, np_, fp = base.load(), near.load(), far.load()
    for y in range(by0, by1):
        for x in range(bx0, bx1):
            if wp[x, y]:
                bp[x, y] = (0, 0, 0, 0)
                continue
            pr, pg, pb, pa = bp[x, y]
            if not pa:
                continue
            sat = max(pr, pg, pb) - min(pr, pg, pb)
            if (np_[x, y] and sat < 46) or (fp[x, y] and (sat < 26 or min(pr, pg, pb) > 170)):
                bp[x, y] = (0, 0, 0, 0)

    # 采样用的子图：框内只留字像素。按 scale 缩一档，让渲染尺寸跟着一起收
    sub = Image.new('RGBA', (bx1 - bx0, by1 - by0), (0, 0, 0, 0))
    sub.paste(im.crop((bx0, by0, bx1, by1)), (0, 0), word.crop((bx0, by0, bx1, by1)))
    k = cfg.get('scale', 1.0)
    if k != 1.0:
        sub = sub.resize((sub.width, max(1, round(sub.height * k))), Image.LANCZOS)
    at = (bx0, by0 + ((by1 - by0) - sub.height) // 2)
    return sub, at, base


# 少数图自动采样会采到底纹/装饰而不是字本身，颜色发灰看不清，这里直接给定
# （描边色, 填充色）。数值取自原图英文字的实际颜色。
STYLE = {
    'twilight_forest_title.png':  ((16, 40, 28), (86, 240, 190)),   # 字压在石砖上，采样会采到砖
    # 深红字面 + 奶白描边，而腐蚀量（图高 5%）比描边厚，外圈中位色被字面带偏成深红
    'neovitae/neovitae.png':      ((239, 226, 228), (150, 30, 47)),
    'ars/ars_nouveau_title.png':  ((58, 12, 78), (196, 96, 234)),   # 原字是发光紫，中位色偏暗
    'router/router_title.png':    ((54, 36, 18), (242, 222, 172)),  # 原字是米色，底纹拉灰了
    'occultism/occultism_title.png': ((28, 6, 34), (150, 40, 168)),
    'allthemodium/all_title.png': ((0, 0, 0), (236, 236, 236)),      # 原字自带上下两色调，会成一道横带
    'id_title.png':              ((22, 58, 68), (126, 238, 252)),
    'extended_advanced_ae/title.png': ((18, 18, 22), (198, 202, 210)),
    # 原字是浅灰石纹配深描边，但框里两行字之间的暗底会把采样拉黑，采出来正好反过来
    'pneumaticcraft/pnc_title.png': ((26, 26, 28), (176, 176, 178)),
    'immersive/immersive_title.png': ((28, 28, 30), (168, 168, 172)),  # 原字是深灰压深灰，采样出来看不清
    # 原图上下两行反色（APPLIED 深蓝底浅边 / ENERGISTICS 浅底深边），
    # 一起采会采成深蓝字，贴上去几乎看不见。取下面那行的配色
    'ae2.png':                       ((44, 44, 68), (232, 238, 250)),
    # 金描边 + 紫字身，但金边只占外圈一薄层，中位色会被黑影拉黑
    'eternal/starlight_armor.png':   ((248, 176, 0), (100, 76, 160)),
    'eternal/starlight_bosses.png':  ((248, 176, 0), (100, 76, 160)),
    'eternal/starlight_items.png':   ((248, 176, 0), (100, 76, 160)),
    'eternal/starlight_tools.png':   ((248, 176, 0), (100, 76, 160)),
    # 金描边 + 浅灰字身，自动采样把描边采成了浅灰，整块糊在一起看不出字
    'forbidden/forbidden_automatic.png': ((188, 140, 12), (178, 178, 178)),
    # create 那组 8 张横幅原图配色完全一致（字身 167,112,61 / 描边 60,60,60），
    # 但只有这一张的原文 "Rotational Power" 排了两行、图高 145px 而非 72~85px。
    # 两行之间那条暗底把采样拉偏，采出来主客颠倒：出货成了浅灰字身(210,218,218)
    # 配棕色描边，和同一页其余 7 张（字身 167,112,61 + 近黑描边）对不上。
    # 这里直接钉成与那 7 张一致的配色。同类失效见上面的 pneumaticcraft。
    'create/create_title_power.png': ((14, 14, 14), (167, 112, 61)),
}

# 只有这几张确实是「文字当遮罩、底下压材质图」，值得抠；其余一律取本色干净地画。
# 想给某张加材质，把路径加进来即可。
TEXTURED = {
    'apothic/logo.png',                      # 裂纹石头
    'apothic/spawners_title.png',
    'undergarden/undergarden_title.png',     # 长苔石
    'iceandfire/iaf_title_firedragon.png',   # 岩浆岩
    'iceandfire/iaf_title_icedragon.png',
    'relics/relics_title.png',
    'aether/aether_title.png',               # 金色云纹
    'building_tips/building.png',            # 裂纹石砖，砍成纯灰就认不出是「建造」那套字了
    'building_tips/building_building.png',
    'building_tips/building_tips.png',
    'building_tips/tips.png',
    'xycraft/xycraft.png',                   # 碎石纹
}

BANNERS = {
    'ae2.png':                                              '应用能源',    # 右边留着的「2」补成「应用能源2」
    'aether/aether_mobs.png':                               '生物',
    'aether/aether_queen.png':                              '武神女王',
    'aether/aether_slider.png':                             '滑行魔石',
    'aether/aether_spirit.png':                             '烈阳巨灵',
    'aether/aether_title.png':                              '天境',
    'aether/aether_tools.png':                              '工具',
    'allthemodium/all_allthemodium.png':                    'ATM',  # 该图是材料名，章节序号在 all_title
    'allthemodium/all_title.png':                           '第二章',      # 该图是章节序号，不是章名
    'apothic/apotheosis_gear.png':                          '神化装备',
    'apothic/logo.png':                                     '神化附魔',
    'apothic/other_spawners.png':                           '其他刷怪笼',
    'apothic/spawn_eggs.png':                               '刷怪蛋',
    'apothic/spawners_title.png':                           '神化刷怪笼',
    'ars/ars_nouveau_title.png':                            '新生魔艺',
    'artifacts/artifacts_belt.png':                         '腰带',
    'artifacts/artifacts_hands.png':                        '手饰',
    'artifacts/artifacts_head.png':                         '首饰',
    'artifacts/artifacts_necklace.png':                     '项链',
    'artifacts/artifacts_title.png':                        '奇异饰品',
    'artifacts/feet_olyfans.png':                           '足部',  # 饰品槽位名取 curios 的官方译法
    'aurora/aurora_title.png':                              '极光',  # 8.1 新增的章节；同目录的 aurora_ring 是纯图形
    'basic_power/allthepower.png':                          '基础能量',
    'basicarmor/armor_title.png':                           '基础护甲',
    'bees/productive_bees.png':                             '资源蜜蜂',
    'bounty.png':                                           '悬赏板',
    'building_tips/building.png':                           '建造',
    'building_tips/building_building.png':                  '建造',
    'building_tips/building_tips.png':                      '技巧',
    'building_tips/tips.png':                               '技巧',
    'bumblezone/bumble_title.png':                          '蜜蜂领域',
    'cataclysm/cataclysm_title.png':                        '灾变',
    'create/create_title.png':                              '机械动力',
    'deepndark/dnd_title.png':                              '幽邃黑暗',
    'draconic/draconic_title.png':                          '龙之进化',
    'eternal/starlight_armor.png':                          '护甲',
    'eternal/starlight_bosses.png':                         '首领',
    'eternal/starlight_items.png':                          '独特物品',
    'eternal/starlight_tools.png':                          '工具',
    'food_and_farming.png':                                 '食物与耕种',
    'forbidden/forbidden_automatic.png':                    '自动化锻炉',
    'forbidden/forbidden_title.png':                        '禁忌与奥秘',
    'forbidden/forbidden_title_clibano.png':                '炽炉',
    'forbidden/forbidden_title_relics.png':                 '遗物',
    'furnaces/iron_furnaces.png':                           '更多熔炉',
    'generator/generator_galore.png':                       '发电机盛会',
    'gettingstarted/titleimage1.png':                       '第一章',  # 该图是章节序号，不是章名
    'id_title.png':                                         '动态\n联合',   # 原图两行，画布 400x400，单行会缩得很小
    'immersive/immersive_title.png':                        '沉浸工程',
    'industrialforegoing/industrial_foregoing_title.png':   '工业先锋',
    'iron_spells/spells_title.png':                         '铁魔法',      # 章节标题仍夹英文，横幅用社区通用名
    'logistics/basic.png':                                  '基础',
    'logistics/integrated-.png':                            '动态联合',
    'logistics/logistics.png':                              '物流',
    'logistics/mekanism.png':                               '通用机械',
    'logistics/pipez.png':                                  '管道',
    'mek/mek_title.png':                                    '通用机械',
    'mystical_agriculture/title.png':                       '神秘农业',
    'natures_aura/natures_aura_title.png':                  '自然灵气',
    'neovitae/neovitae.png':                                '新血魔法',
    'occultism/occultism_title.png':                        '神秘学',
    'oritech/ori-addons.png':                               '附属',
    'oritech/ori-energy.png':                               '能源',
    'oritech/ori-logistics.png':                            '物流',
    'oritech/oritech-logo.png':                             '奥瑞科技',
    'pneumaticcraft/pnc_title.png':                         '气动工艺',
    'powah/text/generation_text.png':                       '发电',        # 章节内的分区标签
    'powah/text/storage_text.png':                          '储能',
    'powah/text/transfer_text.png':                         '传输',
    'powah/text/useful_items_text.png':                     '实用物品',
    'pylons/pylon_title.png':                               '实用塔',
    'railcraft/railcraft.png':                              '铁路工艺',
    'relics/relics_title.png':                              '遗物',
    'router/router_title.png':                              '模块化\n路由器',   # 原图就是两行，画布近正方，单行会缩得很小
    'theurgy/theurgy.png':                                  '神通术',
    'tips_and_tricks.png':                                  '技巧与窍门',
    'twilight_forest_title.png':                            '暮色森林',
    'undergarden/undergarden_title.png':                    '深暗之园',
    # ↓ 第二批：章节内的分区标签 / 生物名 / 阶级图等。生物与 Boss 名一律取模组 lang 的官方译名。
    # 纯图标（无文字）的不在此列：apothic/gear_{augment,gem,reforge,salvage,simple,smith}、
    # apothic/enchant_{deep,end,nether,ocean}（是书架插图）、chap3/creative_{crucible4,enchanter5,forge4}、
    # extremereactors/titleimage2；building_tips/building_title_* 是建筑师本人的 ID，属人名，不翻。
    'apothic/enchant_arcana.png': '阿卡那',
    'apothic/enchant_eterna.png': '位阶',
    'apothic/enchant_infusions.png': '灌注',
    'apothic/enchant_quanta.png': '量子化',
    'apothic/gear_sigils.png': '印记',
    'apothic/gear_tiers.png': '世界层级',
    'basicarmor/armor_colors.png': '纹饰颜色',
    'basicarmor/armor_trims.png': '盔甲纹饰',
    'bumblezone/bumble_title_armor.png': '护甲',
    'bumblezone/bumble_title_mobs.png': '生物',
    'bumblezone/bumble_title_progression.png': '进度',
    'bumblezone/bumble_title_special.png': '特殊',
    'bumblezone/bumble_title_structures.png': '结构',
    'bumblezone/bumble_title_tools.png': '工具',
    'cataclysm/cataclysm_title_guardian.png': '末影守卫',
    'cataclysm/cataclysm_title_habinger.png': '先驱者',
    'cataclysm/cataclysm_title_ignis.png': '焰魔',
    'cataclysm/cataclysm_title_items.png': '组合物品',
    'cataclysm/cataclysm_title_leviathan.png': '利维坦',
    'cataclysm/cataclysm_title_maledictus.png': '咒翼灵骸',
    'cataclysm/cataclysm_title_monstrosity.png': '下界合金巨兽',
    'cataclysm/cataclysm_title_remnant.png': '远古遗魂',
    'cataclysm/cataclysm_title_scylla.png': '斯库拉',
    'chap2/atmstar_title1.png': '第三章',
    'chap2/atmstar_title2.png': 'ATM之星',
    'chap3/creative_chap4.png': '第四章',
    'chap3/creative_creative.png': '创造',
    'chap3/creative_items.png': '创造物品',
    'chap3/creative_star.png': 'ATM之星自动化',
    'create/create_title_contrapt.png': '装置',
    'create/create_title_fluid.png': '流体物流',
    'create/create_title_item.png': '物品物流',
    'create/create_title_machines.png': '机器',
    'create/create_title_power.png': '旋转动力',
    'create/create_title_tool.png': '工具',
    'create/create_title_trains.png': '火车',
    'deepndark/dnd_biome.png': '生物群系',
    'deepndark/dnd_blocks.png': '方块',
    'deepndark/dnd_gear.png': '装备',
    'deepndark/dnd_mobs.png': '生物',
    'deepndark/dnd_plants.png': '植物',
    'eternal/starlight_title1.png': '永恒',
    'eternal/starlight_title2.png': '星光',
    'extended_advanced_ae/title.png': '拓展AE\n与高级AE',
    'extremereactors/title2.png': '极限反应堆',
    'forbidden/forbidden_title_tier1.png': '第一阶',
    'forbidden/forbidden_title_tier2.png': '第二阶',
    'forbidden/forbidden_title_tier3.png': '第三阶',
    'forbidden/forbidden_title_tier4.png': '第四阶',
    'forbidden/forbidden_title_tier5.png': '第五阶',
    'iceandfire/iaf_title_1.png': '冰',
    'iceandfire/iaf_title_2.png': '与',
    'iceandfire/iaf_title_3.png': '火',
    'iceandfire/iaf_title_amphithere.png': '翼蚺',
    'iceandfire/iaf_title_birds.png': '鸟类',
    'iceandfire/iaf_title_cockatrice.png': '鸡蛇',
    'iceandfire/iaf_title_cyclops.png': '独眼巨人',
    'iceandfire/iaf_title_firedragon.png': '火龙',
    'iceandfire/iaf_title_ghosts.png': '幽灵',
    'iceandfire/iaf_title_gorgon.png': '蛇发女妖',
    'iceandfire/iaf_title_hippocampus.png': '海马',
    'iceandfire/iaf_title_hippogryth.png': '骏鹰',
    'iceandfire/iaf_title_hydra.png': '九头蛇',
    'iceandfire/iaf_title_icedragon.png': '冰龙',
    'iceandfire/iaf_title_lightningdragon.png': '电龙',
    'iceandfire/iaf_title_pets.png': '宠物',
    'iceandfire/iaf_title_pixie.png': '小精灵',
    'iceandfire/iaf_title_serpent.png': '海蟒',
    'iceandfire/iaf_title_siren.png': '塞壬',
    'iceandfire/iaf_title_stymphalian.png': '铜羽泽鹗',
    'iceandfire/iaf_title_trolls.png': '食人妖',
    'iceandfire/iaf_title_worm.png': '死亡蠕虫',
    'immersive/immersive_title_log.png': '物流',
    'immersive/immersive_title_mac.png': '机器',
    'immersive/immersive_title_oad.png': '攻防',
    'immersive/immersive_title_sma.png': '小型机器',
    'immersive/immersive_title_tol.png': '工具',
    'immersive/immersive_title_upg.png': '升级',
    'immersive/immersive_title_wir.png': '布线',
    'mahou/mahou_bow.png': '武器投影之弓',
    'mahou/mahou_caliburn.png': '石中剑',
    'mahou/mahou_clarent.png': '克拉伦特',
    'mahou/mahou_disorientation.png': '次元扭曲魔杖',
    'mahou/mahou_emrys.png': '艾米雷斯',
    'mahou/mahou_explosion.png': '爆炸魔杖',
    'mahou/mahou_generation.png': '魔力生成',
    'mahou/mahou_keys.png': '赤之黑键',
    'mahou/mahou_morgan.png': '摩根',
    'mahou/mahou_nobu.png': '诺布',
    'mahou/mahou_replica.png': '暗夜之影',
    'mahou/mahou_tsukai.png': '魔法使',
    'mek/mek_title_1.png': '一级矿物处理',
    'mek/mek_title_2.png': '二级矿物处理',
    'mek/mek_title_3.png': '三级矿物处理',
    'mek/mek_title_4.png': '四级矿物处理',
    'mek/mek_title_advanced.png': '高级',
    'mek/mek_title_antimatter.png': '反物质',
    'mek/mek_title_basic.png': '基础',
    'mek/mek_title_boiler.png': '热力锅炉',
    'mek/mek_title_elite.png': '精英',
    'mek/mek_title_energy.png': '能量',
    'mek/mek_title_fission.png': '裂变反应堆',
    'mek/mek_title_fusion.png': '聚变反应堆',
    'mek/mek_title_logistics.png': '物流',
    'mek/mek_title_machines.png': '机器',
    'mek/mek_title_matrix.png': '感应矩阵',
    'mek/mek_title_mo.png': '更多机器',
    'mek/mek_title_module.png': '模块',
    'mek/mek_title_qio.png': 'QIO',
    'mek/mek_title_reactor.png': '通用机械反应堆',
    'mek/mek_title_sps.png': 'SPS',
    'mek/mek_title_suit.png': '通用装甲',
    'mek/mek_title_tools.png': '工具',
    'mek/mek_title_turbine.png': '涡轮',
    'mek/mek_title_ultimate.png': '终极',
    'mek/mek_title_upgrades.png': '升级',
    'mystical_agriculture/machines.png': '机器',
    'undergarden/undergarden_biomes.png': '生物群系',
    'undergarden/undergarden_friendly.png': '友好',
    'undergarden/undergarden_hostile.png': '敌对',
    'undergarden/undergarden_neutral.png': '中立',
    'undergarden/undergarden_tools.png': '工具与护甲',
    'undergarden/undergarden_vegetation.png': '植被',

    'xycraft/xycraft.png':                                  '晶工艺',}


def crop_box(im, rel):
    """→ (取样/绘制用的子图, 粘回原图的左上角坐标, 该图是否要保留框外内容)"""
    wm = WORDMARK.get(rel)
    if wm:
        sub, at, base = wordmark_split(im, rel, wm)
        # 这里返回的是**新** dict，不是 WORDMARK 里那个——往全局配置上挂
        # 每张图现算的底图，跑第二张时就会拿到上一张的底
        return sub, at, dict(wm, canvas=base)
    cfg = BOXES.get(rel)
    if cfg:
        x0, y0, x1, y1 = cfg['box']
        r = (round(im.width * x0 / 100), round(im.height * y0 / 100),
             round(im.width * x1 / 100), round(im.height * y1 / 100))
        return im.crop(r), (r[0], r[1]), cfg
    bb = im.getbbox() or (0, 0, im.width, im.height)   # 默认：原图内容框
    return im.crop(bb), (bb[0], bb[1]), None


def sample_style(im, rel=''):
    """从原图采出（描边色, 竖向渐变色表, 描边宽）"""
    from PIL import ImageFilter
    px = im.load()
    W, H = im.size
    if not im.getbbox():
        return (0, 0, 0), Image.new('RGB', (max(1, W), max(1, H)), (255, 255, 255)), 2, '空'
    # 描边厚度按图高估：原图描边普遍是字高的 4~5%
    def med(seq):
        return tuple(int(statistics.median(c[i] for c in seq)) for i in range(3))

    a = im.getchannel('A').point(lambda v: 255 if v > 200 else 0)
    ap = a.load()
    # 腐蚀量按图高 5% 起，若腐蚀后什么都不剩（像素字笔画本来就细）就**逐级减小**，
    # 而不是退回「完全不腐蚀」——那条兜底会把黑描边整个算进材质，
    # 中文笔画里就会出现莫名其妙的黑纹理（斯库拉就是这么烂的）。
    edge, inner = [], {}
    for ring in range(max(1, round(H * 0.05)), 0, -1):
        er = a.filter(ImageFilter.MinFilter(2 * ring + 1))
        ep = er.load()
        edge, inner = [], {}
        for y in range(H):
            for x in range(W):
                if not ap[x, y]:
                    continue
                (inner.setdefault(y, []) if ep[x, y] else edge).append(px[x, y][:3])
        if sum(len(v) for v in inner.values()) >= 40:
            break
    if not inner:      # 连 1 圈都腐蚀没了：整字就一两像素宽，取全部像素里最亮的一档当本色
        allpx = [px[x, y][:3] for y in range(H) for x in range(W) if ap[x, y]]
        allpx.sort(key=sum, reverse=True)
        inner = {0: allpx[:max(1, len(allpx) // 3)]}
        edge = allpx[-max(1, len(allpx) // 3):]
    # 描边色取腐蚀掉的外圈里**最深**的那一档，避免把渐变亮部当描边
    if edge:
        edge.sort(key=sum)
        outline = med(edge[:max(1, len(edge) // 3)])
    else:
        outline = (0, 0, 0)
    ys = sorted(inner)
    if not ys:
        return outline, Image.new('RGB', (W, H), (255, 255, 255)), max(2, round(H * 0.045)), '空'
    # 切成一条条连续的「有墨行」，只留最高的那条 —— 多行异色的原图（APOTHIC 灰 /
    # ENCHANTING 紫）整块一起用会让中文上下两截色
    peak = max(len(v) for v in inner.values())
    runs, cur = [], []
    for y in range(ys[0], ys[-1] + 1):
        if len(inner.get(y, ())) >= peak * 0.06:
            cur.append(y)
        elif cur:
            runs.append(cur); cur = []
    if cur:
        runs.append(cur)
    band = [y for y in (max(runs, key=len) if runs else ys) if y in inner]

    # 默认只取本色、自己干净地画。抠材质只对确实是材质字的那几张做——
    # 硬抠的收益远小于它带来的问题（描边混进材质→黑斑、两行时第二行套暗部→像缺笔）。
    pool = [c for y in band for c in inner[y]]
    if rel not in TEXTURED:
        return (outline, Image.new('RGB', (W, H), body_color(pool, outline)),
                max(2, round(H * 0.045)), '本色')

    # 材质板：每一行把该行原字内部的像素序列横向平铺满整宽，再纵向拉伸到画布高。
    # 这样石纹/苔藓/方块贴图都留得住，而不是塌成一个颜色。
    plate = Image.new('RGB', (W, len(band)))
    pp = plate.load()
    for j, y in enumerate(band):
        seq = inner[y]
        for x in range(W):
            pp[x, j] = seq[x % len(seq)]
    # 横向做一次窄窗平滑：平铺会把字母片段反复重复，直接用会看出周期性拖影
    from PIL import ImageFilter
    plate = plate.filter(ImageFilter.GaussianBlur(max(1, W / 240)))
    return outline, plate.resize((W, H), Image.LANCZOS), max(2, round(H * 0.045)), '材质'


def body_color(pool, outline, med=None):
    """字的本色。取中位色；若与描边色太接近就改取偏亮的四分位。

    气动工艺那张就是这么翻的：原字是浅灰配深描边，腐蚀后剩下的多是中间调，
    中位色几乎等于描边色，画出来整个字糊成一团深色，白字完全看不见。
    """
    if not pool:
        return (255, 255, 255)
    import statistics as _st
    m = tuple(int(_st.median(c[i] for c in pool)) for i in range(3))
    if sum(abs(m[i] - outline[i]) for i in range(3)) >= 90:
        return m
    bright = sorted(pool, key=sum)[int(len(pool) * 0.75):] or pool
    return tuple(int(_st.median(c[i] for c in bright)) for i in range(3))


def tile_plate(plate, text, gw, gh):
    """中文排几行，材质板就竖向重复几遍——否则第二行会套到字母底部的暗部阴影。

    另外：原图两行时，"最高的那条墨带"有时会把两行连着算成一条（下行的升部与
    上行的降部之间没断开），这样材质板里就含了「亮—暗—亮—暗」两轮。
    所以多行时只取材质板的上 55%（高光与本色所在），再重复，避免整行套上阴影。
    """
    n = text.count('\n') + 1
    if n > 1:
        plate = plate.crop((0, 0, plate.width, max(2, int(plate.height * 0.55))))
        stack = Image.new('RGB', (plate.width, plate.height * n))
        for i in range(n):
            stack.paste(plate, (0, i * plate.height))
        plate = stack
    return plate.resize((max(1, gw), max(1, gh)), Image.LANCZOS)


def render_vector(text, w, h, outline, plate, sw, face):
    """矢量字渲染：4 倍超采样，内部取材质、外圈上描边色"""
    path, idx = face_file(face)
    SS = 4
    aw, ah = w - 2 * MARGIN, h - 2 * MARGIN
    size = ah
    for _ in range(12):
        f = ImageFont.truetype(path, max(1, int(size)) * SS, index=idx)
        # 画布必须按文字的实际尺寸开。早先固定用 (w*SS*3, h*SS*3) 并从 (w*SS, h*SS)
        # 起笔，长文字会画出右边界被裁掉，getbbox 量到残缺字形，字号迭代跟着算错，
        # 输出就是缺角断笔的「抠烂」字。
        sp = int(round(size * SS * 0.12))
        tb = ImageDraw.Draw(Image.new('L', (1, 1))).multiline_textbbox(
            (0, 0), text, font=f, stroke_width=sw * SS, align='center', spacing=sp)
        # 画布留足余量再裁：textbbox 对多行的下伸部估得不准，余量小了第二行的
        # core（字身）会被画布底裁掉，而 allm（含描边）没被裁——渲染出来就是
        # 「下半行只剩一坨描边、字身没了」。余量给到半个字高，之后按 bbox 裁掉多余。
        pad = int(sw * SS) + int(size * SS * 0.5) + 8
        big = (int(tb[2] - tb[0]) + 2 * pad, int(tb[3] - tb[1]) + 2 * pad)
        allm = Image.new('L', big, 0)
        org = (pad - int(tb[0]), pad - int(tb[1]))
        ImageDraw.Draw(allm).text(org, text, font=f, fill=255,
                                  stroke_width=sw * SS, stroke_fill=255,
                                  align='center', spacing=sp)
        bb = allm.getbbox()
        tw, th = (bb[2] - bb[0]) / SS, (bb[3] - bb[1]) / SS
        k = min(aw / tw, ah / th)
        if abs(k - 1) < 0.01:
            break
        size = max(1, size * k)
    # core 必须用**同样的 stroke_width** 画（只是描边填 0），否则多行会错位：
    # PIL 算多行行距时是 line_spacing = 单行高 + stroke_width + spacing，
    # 带描边和不带描边算出来的第二行位置差约两倍描边宽 —— 第二行下半截 core 盖不到，
    # 渲染出来就只剩 allm 的描边色，看着像字被截掉一块。
    core = Image.new('L', big, 0)
    ImageDraw.Draw(core).text(org, text, font=f, fill=255, stroke_width=sw * SS,
                              stroke_fill=0, align='center', spacing=sp)
    allm, core = allm.crop(bb), core.crop(bb)
    gw, gh = max(1, round(allm.width / SS)), max(1, round(allm.height / SS))
    allm = allm.resize((gw, gh), Image.LANCZOS)
    core = core.resize((gw, gh), Image.LANCZOS)
    tex = tile_plate(plate, text, gw, gh).load()
    glyph = Image.new('RGBA', (gw, gh), (0, 0, 0, 0))
    ga, gc, gp = allm.load(), core.load(), glyph.load()
    for y in range(gh):
        for x in range(gw):
            a = ga[x, y]
            if not a:
                continue
            col = tex[x, y]
            t = gc[x, y] / 255
            gp[x, y] = (round(outline[0] + (col[0] - outline[0]) * t),
                        round(outline[1] + (col[1] - outline[1]) * t),
                        round(outline[2] + (col[2] - outline[2]) * t), a)
    return place(glyph, w, h)


def lum(c):
    return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]


MIN_CONTRAST = 96      # 描边与字身的明度差下限（0~255）


def boost_contrast(outline, plate):
    """保证描边与字身的明度差够大，不够就把描边推开。

    原图英文笔画粗、字内面积大，描边和字身接近一点也还看得清；中文笔画又细又密，
    同一套配色贴上去就糊成一坨（自动化锻炉的浅灰字配浅金描边、应用能源的深蓝配深蓝
    都是这么糊掉的）。所以不逐张调色，统一在这里加一道保底：明度差不到
    MIN_CONTRAST 就沿原描边色的方向把它压暗或提亮，色相不变，只动明暗。
    """
    sm = plate.resize((8, 8), Image.LANCZOS)
    px = list(sm.getdata())
    body = tuple(round(sum(c[i] for c in px) / len(px)) for i in range(3))
    lb, lo = lum(body), lum(outline)
    if abs(lb - lo) >= MIN_CONTRAST:
        return outline
    target = lb - MIN_CONTRAST if lb >= 128 else lb + MIN_CONTRAST
    target = min(255.0, max(0.0, target))
    if lo < 1:                                  # 原描边已经是纯黑，只能往亮里提
        return tuple(round(target) for _ in range(3))
    k = target / lo
    return tuple(min(255, max(0, round(v * k))) for v in outline)


def place(glyph, w, h):
    """硬性收口：字号迭代未必收敛，超出可用框就直接等比缩回去，绝不让画布裁掉笔画。"""
    aw, ah = w - 2 * MARGIN, h - 2 * MARGIN
    gw, gh = glyph.size
    if gw > aw or gh > ah:
        k = min(aw / gw, ah / gh)
        gw, gh = max(1, int(gw * k)), max(1, int(gh * k))
        glyph = glyph.resize((gw, gh), Image.LANCZOS)
    canvas = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    canvas.alpha_composite(glyph, ((w - gw) // 2, (h - gh) // 2))
    return canvas, gw, gh


def pixel_mask(text, size=None):
    """把文字排成 1 倍尺度的 0/1 点阵（无抗锯齿），供整数倍放大用。

    size 给定就用那一档方舟像素字体，整行交给 PIL 排（顺带拿到字距和比例宽度），
    在设计尺寸上出来的就是纯黑白；size=None 退回 Unifont 自己拼字。
    """
    if size is not None:
        f = ImageFont.truetype(str(pixel_face(size)), size)
        gap = max(1, round(size / 6))
        d0 = ImageDraw.Draw(Image.new('L', (1, 1)))
        tb = d0.multiline_textbbox((0, 0), text, font=f, align='center', spacing=gap)
        pad = size
        im = Image.new('L', (int(tb[2] - tb[0]) + 2 * pad, int(tb[3] - tb[1]) + 2 * pad), 0)
        ImageDraw.Draw(im).text((pad - tb[0], pad - tb[1]), text, font=f, fill=255,
                                align='center', spacing=gap)
        bb = im.getbbox()
        if bb:
            im = im.crop(bb)
        px = im.load()
        return [[1 if px[x, y] > 127 else 0 for x in range(im.width)]
                for y in range(im.height)]

    lines = text.split('\n')
    rows = []
    for ln in lines:
        gs = [UNIFONT.get(ord(c), (16, [0] * 16)) for c in ln]
        rows.append((sum(g[0] for g in gs), gs))
    W1 = max(r[0] for r in rows)
    H1 = len(rows) * 16 + (len(rows) - 1) * LINE_GAP
    core1 = [[0] * W1 for _ in range(H1)]
    for li, (lw, gs) in enumerate(rows):
        x0 = (W1 - lw) // 2
        y0 = li * (16 + LINE_GAP)
        for gw, bm in gs:
            for r in range(16):
                bits = bm[r]
                for c in range(gw):
                    if bits >> (gw - 1 - c) & 1:
                        core1[y0 + r][x0 + c] = 1
            x0 += gw
    return core1


def render(text, w, h, outline, plate, sw):
    """点阵排字，整数倍最近邻放大后按材质板上色"""
    # 描边：1 倍尺度上按切比雪夫距离膨胀 ow 圈，放大后就是方块状的粗描边
    aw, ah = w - 2 * MARGIN, h - 2 * MARGIN
    # 描边固定 1 圈（1 倍尺度）。放大 k 倍后描边就是 k 像素，与点阵字的 1px 笔画
    # 放大后同宽——早先按 sw 取 2 圈，k=8 时描边 16px 而笔画才 8px，字被描边吃掉，
    # 中间的本色几乎看不见（气动工艺就是这么糊掉的）。
    ow = 1
    # 逐档试字框，挑放大后填得最满的那档（见 PIXEL_SIZES 处的说明）
    best, holes0 = None, None
    for size in sorted(pixel_candidates(text), key=lambda s: -(s or 0)):
        c1 = pixel_mask(text, size)
        h1, w1 = len(c1), len(c1[0])
        kk = max(1, min(aw // (w1 + 2 * ow), ah // (h1 + 2 * ow)))
        fill = min(kk * (w1 + 2 * ow) / aw, kk * (h1 + 2 * ow) / ah)
        # 从大字框往小试。填充率差不多就用大的；小字框只有在**既明显撑得更满
        # （多 8 个百分点以上）又没把笔画糊到一起**时才换——可读性不给尺寸让路。
        if best is None:
            best, holes0 = (fill, c1, kk), hole_count(c1)
        elif fill > best[0] + 0.08 and hole_count(c1) >= holes0:
            best = (fill, c1, kk)
    _, core1, k = best
    H1, W1 = len(core1), len(core1[0])
    pad = ow
    AW, AH = W1 + 2 * pad, H1 + 2 * pad
    all1 = [[0] * AW for _ in range(AH)]
    for y in range(H1):
        for x in range(W1):
            if core1[y][x]:
                for dy in range(-ow, ow + 1):
                    for dx in range(-ow, ow + 1):
                        all1[y + pad + dy][x + pad + dx] = 1

    gw, gh = AW * k, AH * k
    tex = tile_plate(plate, text, gw, gh).load()
    glyph = Image.new('RGBA', (gw, gh), (0, 0, 0, 0))
    gp = glyph.load()
    for Y in range(gh):
        y1 = Y // k
        for X in range(gw):
            x1 = X // k
            if not all1[y1][x1]:
                continue
            inside = 0 <= y1 - pad < H1 and 0 <= x1 - pad < W1 and core1[y1 - pad][x1 - pad]
            gp[X, Y] = (tex[X, Y] + (255,)) if inside else (outline + (255,))
    return place(glyph, w, h)


def chapter_titles():
    """图 → 引用它的章节中文标题（用于核验译名没跑偏）"""
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from check_quest_item_names import parse_lang, strip
    # 整合包的中文任务书有两种形态：进过游戏的实例里是合并好的 zh_cn.snbt，
    # 刚解压的官方包里则还是拆开的 lang/zh_cn/**.snbt（合并是进游戏时才做的）。
    # 两种都要认，否则 CI 上对着官方包跑会直接找不到文件。
    zh = {}
    one = QUESTS / 'lang' / 'zh_cn.snbt'
    if one.exists():
        zh.update(parse_lang(str(one)))
    split = QUESTS / 'lang' / 'zh_cn'
    if split.is_dir():
        for p in sorted(split.rglob('*.snbt')):
            zh.update(parse_lang(str(p)))
    delta = SRC / 'config' / 'ftbquests' / 'quests' / 'lang' / 'zh_cn'
    for p in sorted(delta.rglob('*.snbt')):
        zh.update(parse_lang(str(p)))
    out = {}
    for p in sorted((QUESTS / 'chapters').glob('*.snbt')):
        src = p.read_text(encoding='utf-8')
        m = re.search(r'\bid: "([0-9A-F]{16})"', src)
        if not m:
            continue
        t = strip(zh.get('chapter.%s.title' % m.group(1), ''))
        for img in set(re.findall(r'questpics/([a-z0-9_/-]+)\.png', src)):
            out.setdefault(img + '.png', []).append(t)
    return out


def main(check_only=False):
    check_boxes()
    titles = chapter_titles()
    n = 0
    for rel, text in sorted(BANNERS.items()):
        src = SRC / rel
        if not src.exists():
            sys.exit('❌ 找不到原图 %s（本脚本要对着整合包实例跑）' % src)
        used = titles.get(rel, [])
        # 真正的风险形状：这张图**当章节标题用**（文案就是某个章节的标题），却被
        # 标题不同的两个章节共用——写死一个，另一个章节就顶着别人的标题。
        # 只是「被两个章节引用」不构成风险：内容横幅（如 gear_tiers 的「世界层级」）
        # 与章节标题无关，两处显示同一句话本来就对。
        # 2026-08-02：ATM10 7.3 改了 Apotheosis 系的章节结构，gear_tiers.png 同时被
        # 「神化装备」「神化附魔」引用，旧写法在这里必红——红的是闸太宽，不是内容有错。
        if len(set(used)) > 1 and text in used:
            sys.exit('❌ %s 的文案「%s」正是章节标题，而它被标题不同的多个章节共用 %s'
                     '——写死会让另一个章节顶着别人的标题' % (rel, text, used))
        im = Image.open(src).convert('RGBA')
        sub, at, cfg = crop_box(im, rel)
        outline, plate, sw, how = sample_style(sub, rel)
        if rel in STYLE:      # 少数原图字色与底纹太接近，采样出来看不清，直接给定
            outline = STYLE[rel][0]
            plate = Image.new('RGB', plate.size, STYLE[rel][1])
            how = '指定色'
        boosted = boost_contrast(outline, plate)
        if boosted != outline:
            outline, how = boosted, how + '+提对比'
        face = pick_face(rel)
        if face == 'pixel':
            img, gw, gh = render(text, sub.width, sub.height, outline, plate, sw)
        else:
            img, gw, gh = render_vector(text, sub.width, sub.height, outline, plate, sw, face)
        if cfg:
            # 保留框外的装饰：在原图上抠掉文字框，再把中文贴回去
            canvas = im.copy()
            if cfg.get('canvas') is not None:
                # 按描边抠字那条路：底图已经把英文字和投影清干净了，
                # 再按框整块擦会把压在字底下的美术一起挖掉
                canvas = cfg['canvas'].copy()
            elif 'patch_from' in cfg:    # 框内有底纹，取干净的几行平铺补上
                a, b = cfg['patch_from']
                ya, yb = round(im.height * a / 100), round(im.height * b / 100)
                strip = im.crop((at[0], ya, at[0] + sub.width, yb))
                sh = max(1, strip.height)
                for y in range(0, sub.height, sh):
                    # 最后一条要裁掉超出部分——原先整条贴，会溢出文字框下沿，
                    # 把框外本该原样保留的像素一起盖掉（暮色森林被盖掉了 5 万多个）
                    canvas.paste(strip.crop((0, 0, strip.width, min(sh, sub.height - y))),
                                 (at[0], at[1] + y))
            else:
                canvas.paste(Image.new('RGBA', sub.size, (0, 0, 0, 0)), at)
            canvas.alpha_composite(img, at)
            img = canvas
        else:
            canvas = Image.new('RGBA', im.size, (0, 0, 0, 0))
            canvas.alpha_composite(img, at)
            img = canvas
        if not check_only:
            dst = OUT / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            save_png(img, dst)
        # 被多个章节共用时把它们都列出来：只报第一个会让人以为另一个不存在。
        note = ('' if (not used or text in used)
                else '  ← 与章节标题「%s」不同' % '」「'.join(dict.fromkeys(used)))
        print('  %-48s %-7s %-5s %-10s %dx%d%s'
              % (rel, text, face, how, im.width, im.height, note))
        n += 1
    print(('校验通过' if check_only else '已生成') + ' %d 张 -> %s' % (n, OUT.relative_to(ROOT)))


if __name__ == '__main__':
    main(check_only='--check' in sys.argv)
