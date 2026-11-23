#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# atm10-zh-cn — All the Mods 10 简体中文汉化补丁「绿油油版」
# Copyright (C) 2026 星野夢華 (Hoshino Yumeka)
# SPDX-License-Identifier: GPL-3.0-or-later
"""任务书语言：把本包的覆盖打进 ATM 的章节文件，按原文件名出货。

`ftbquestslangsplitter` 1.0.5 的合并顺序不是文件名字母序：

    // lang/<locale>/ 这一层
    Files.list(dir).sorted(Comparator.comparingInt(p -> isDirectory(p) ? 1 : 0))
    // chapters/ 里面
    Files.list(chapters).forEach(...)            // ← 没有排序

第一层只保证文件排在目录前面，第二层不排序。`Files.list` 不保证顺序：NTFS / APFS 按名字返回，
ext4 按哈希序返回，所以同一个键在两个文件里时，Linux 上哪份生效是随机的，zz_ 前缀不起作用。

本包 1249 条覆盖里有 923 条与 ATM 自带的中文同键（分布在 62 个章节文件）。在服务器或客户端
第一次启动之前装包，两批文件都未合并，会有随机一批覆盖退回上游原文。启动过一次再装包看不到
这个问题：ATM 的文件已改名成 `.snbt_merged`。

所以一个键只放在一份文件里：把覆盖打进上游的章节文件，用原文件名出货，安装时覆盖 ATM 的同名文件。

  - 全新实例：上游那份被替换，目录里只有一份，直接生效。
  - 启动过的实例：上游那份是 `.snbt_merged`（不再读取），本包这份是唯一未合并的，后合并的生效。

上游没有的键（在任何上游文件里都找不到）放在 `chapters/hanhua_additions.snbt`，不与任何文件同键。

用原文件名出货时必须写整份文件：只写本包那几条会覆盖掉上游同名文件的全部内容（只有 2 个键的
aether.snbt 覆盖过上游 167 个键）。所以写出的是「上游全文 + 本包覆盖」。

用法:
    python3 scripts/gen_quest_lang_patches.py <上游目录> <出货树> [整合包版本]
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from paths import ROOT                                              # noqa: E402

LANG = 'config/ftbquests/quests/lang/zh_cn'
DELTA_PREFIX = 'zz_hanhua_'
ADDITIONS = 'chapters/hanhua_additions.snbt'
# 上游文件的缩进不统一（同一个 chapters/ 里有 tab 也有 4 空格），所以按「行首空白 + 键 + 冒号」
# 匹配，缩进原样保留，只换值，不改排版。
KEY = re.compile(r'^[\t ]+([A-Za-z0-9_.]+):')


class SnbtShapeError(Exception):
    """delta 文件的块结构损坏。

    单独定义异常，让 check.py 复用同一个解析器：生成阶段遇到它就退出，校验阶段把它变成一条带规则号
    的报错继续检查。两份解析器结论不同时会漏判：按行 sort 把多行数组打散成 513 个游离的 `""`，
    按行正则匹配不上就放过。
    """


def blocks(path):
    """把一个 .snbt 语言文件切成 [(键, 该键占的原始行)]，多行数组整块保留。"""
    lines = path.read_text(encoding='utf-8').split('\n')
    if not (lines and lines[0] == '{' and lines[-2:] == ['}', '']):
        raise SnbtShapeError('%s 不是预期的 snbt 语言文件（首行 { 尾行 }）' % path)
    body, out, i = lines[1:-2], [], 0
    while i < len(body):
        if not body[i].strip():          # 空行归给上一个键，输出时原样带回去
            if out:
                out[-1][1].append(body[i])
                i += 1
                continue
            raise SnbtShapeError('%s 开头就是空行' % path)
        m = KEY.match(body[i])
        if not m:
            raise SnbtShapeError('%s 第 %d 行不属于任何键: %r'
                                 % (path, i + 2, body[i][:60]))
        blk = [body[i]]
        if body[i].rstrip().endswith('['):          # 多行数组：吃到单独的 ]
            start = i
            i += 1
            while i < len(body) and body[i].strip() != ']':
                blk.append(body[i])
                i += 1
            if i >= len(body):
                # 数组到文件尾都没闭合，报出是哪个键
                raise SnbtShapeError('%s 第 %d 行的键 %s 起了个多行数组，直到文件尾都没闭合'
                                     % (path, start + 2, m.group(1)))
            blk.append(body[i])
        i += 1
        out.append((m.group(1), blk))
    return out


def write(path, pairs):
    path.parent.mkdir(parents=True, exist_ok=True)
    body = '\n'.join('\n'.join(b) for _, b in pairs)
    path.write_text('{\n' + body + '\n}\n', encoding='utf-8')


def collect_delta(tree, mc):
    """本包的覆盖：出货树里的 zz_hanhua_*.snbt，外加该版专属覆盖（优先级最高）。"""
    srcs = sorted((tree / LANG).rglob(DELTA_PREFIX + '*.snbt'))
    if not srcs:
        raise SystemExit('❌ 出货树里一个 %s*.snbt 都没有，先运行 assemble.py' % DELTA_PREFIX)
    ver = ROOT / 'versions' / str(mc) / 'quest_overrides.snbt' if mc else None
    delta, owner = {}, {}
    for p in srcs + ([ver] if ver and ver.is_file() else []):
        per_version = ver is not None and p == ver
        for k, blk in blocks(p):
            if k in delta and not per_version:
                # 两个 delta 文件定义同一个键，又会依赖合并顺序，check.py 也检查这一条
                raise SystemExit('❌ 覆盖键 %s 在 %s 与 %s 里都定义了' % (k, owner[k], p.name))
            delta[k], owner[k] = blk, p.name
    return srcs, delta, ver


def main():
    if len(sys.argv) < 3:
        raise SystemExit(__doc__.strip().splitlines()[-1])
    uproot, tree = Path(sys.argv[1]), Path(sys.argv[2])
    mc = sys.argv[3] if len(sys.argv) > 3 else None

    upstream_dir = uproot / LANG
    if not upstream_dir.is_dir():
        raise SystemExit('❌ 上游目录里没有 %s：%s' % (LANG, uproot))

    srcs, delta, ver = collect_delta(tree, mc)

    # 上游每个键属于哪个文件（上游自己不会跨文件重键，重了说明这里的前提不成立）
    up_files = sorted(upstream_dir.glob('*.snbt')) + sorted((upstream_dir / 'chapters').glob('*.snbt'))
    if not up_files:
        raise SystemExit('❌ 上游 %s 下一个 .snbt 都没有' % LANG)
    up_pairs, home = {}, {}
    for p in up_files:
        rel = p.relative_to(upstream_dir).as_posix()
        up_pairs[rel] = blocks(p)
        for k, _ in up_pairs[rel]:
            if k in home:
                raise SystemExit('❌ 上游自己重键：%s 同时在 %s 与 %s' % (k, home[k], rel))
            home[k] = rel

    # 打补丁：上游全文加本包覆盖，位置不变
    placed, touched = set(), []
    for rel, pairs in up_pairs.items():
        hits = [k for k, _ in pairs if k in delta]
        if not hits:
            continue
        write(tree / LANG / rel, [(k, delta[k] if k in delta else blk) for k, blk in pairs])
        placed.update(hits)
        touched.append((rel, len(hits)))

    # 上游没有的键放进单独一个文件，不与任何文件同键
    extra = sorted(k for k in delta if k not in placed)
    if extra:
        write(tree / LANG / ADDITIONS, [(k, delta[k]) for k in extra])

    # 覆盖已经打进上游文件，delta 文件不能再带键出货，否则同一个键又有两份。安装器只覆盖不删除，
    # 老版本装过的 zz_hanhua_*.snbt 会留在玩家硬盘上，内容没变时 splitter 不改名，仍是未合并状态，
    # 会与新的上游文件争同一个键。所以按原名发一个空文件覆盖它。src/ 有保护清单（只增不删），
    # 这批文件名只会增加，空文件集合覆盖所有发过的文件名。
    for p in srcs:
        p.write_text('{\n}\n', encoding='utf-8')
        # r13 及更早用过 `_<章节名>.snbt` 这个命名，这些文件同样只覆盖不删除、可能未合并、会争键，
        # 而且名字与现在发的不同，不会被 payload 覆盖，所以同样发一个同名空文件。
        legacy = p.with_name('_' + p.name[len(DELTA_PREFIX):])
        if legacy.name != p.name:
            legacy.write_text('{\n}\n', encoding='utf-8')

    # ── 自检 ──────────────────────────────────────────────────────────────
    if len(placed) + len(extra) != len(delta):
        raise SystemExit('❌ 覆盖键 %d 条，落位 %d + %d 条，对不上'
                         % (len(delta), len(placed), len(extra)))
    seen = {}
    for p in sorted((tree / LANG).rglob('*.snbt')):
        rel = p.relative_to(tree / LANG).as_posix()
        got = [k for k, _ in blocks(p)]
        if len(got) != len(set(got)):
            raise SystemExit('❌ %s 内部有重复键' % rel)
        if rel in up_pairs and len(got) != len(up_pairs[rel]):
            raise SystemExit('❌ %s 的键数从 %d 变成了 %d，上游内容丢失了'
                             % (rel, len(up_pairs[rel]), len(got)))
        for k in got:
            if k in seen:
                raise SystemExit('❌ 出货树里 %s 同时出现在 %s 与 %s（又回到靠顺序了）'
                                 % (k, seen[k], rel))
            seen[k] = rel
    for k in delta:
        if k not in seen:
            raise SystemExit('❌ 覆盖键 %s 没出现在出货树里' % k)

    print('✅ 任务书语言：%d 条覆盖打进上游 %d 个文件%s，上游没有的 %d 条进 %s'
          % (len(placed), len(touched),
             '（含 %s 专属 %d 条）' % (mc, len(blocks(ver))) if ver and ver.is_file() else '',
             len(extra), ADDITIONS))


if __name__ == '__main__':
    try:
        main()
    except SnbtShapeError as e:
        # 生成阶段块结构损坏就退出，报一行说明，不打印堆栈。
        raise SystemExit('❌ %s' % e)
