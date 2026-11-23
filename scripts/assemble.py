#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# atm10-zh-cn — All the Mods 10 简体中文汉化补丁「绿油油版」
# Copyright (C) 2026 星野夢華 (Hoshino Yumeka)
# SPDX-License-Identifier: GPL-3.0-or-later
"""把 src/ 里的真源摊成一棵出货树（build/common/）。

仓库里不存在 `resourcepacks/`、`kubejs/`、`config/` 这些目录，它们是产物，
每次构建现摊。这样就不可能出现「仓库里躺着一份手改过、和生成器输出对不上的文件」。

摊完之后再跑生成器（横幅、奖杯名、按钮…），它们直接往这棵树里写。
版本专属的上游文件由 gen_upstream_patches.py 单独产到 build/upstream/<版本>/。

用法:
    python3 scripts/assemble.py
"""
import os
import shutil
import sys

import fetch_mods
import gen_vaultpatcher
import gen_vanilla_assets
from paths import COMMON, PACK, PACK_NAME, ROOT, SRC

# src 下的目录 → 出货树里的位置。
# vaultpatcher/ 不在这里：模块头部要写该版本真实的 jar 文件名，
# 由 gen_vaultpatcher.py 按 versions/db/<版本>/ 现填（见那个脚本的说明）。
# mods/ 不在：VaultPatcher 那个 jar 由 fetch_mods.py 按 src/mods.lock.json
# 的 sha256 现取，许可证正文也由它一并取下放在 jar 旁边。
LAYOUT = [
    ('pack', 'resourcepacks/' + PACK_NAME),
    ('config', 'config'),
    ('kubejs', 'kubejs'),
    # jar 与它的许可证正文放在一起进仓库、一起进包：MIT 的义务就是
    # 再分发时附版权声明与许可全文，放在同一个目录里最不会散
    ('optional-mods-pinyin', '可选mods-拼音搜索'),
]

# 这些路径是生成器的产物，绝不该出现在 src/ 里。出现了就说明有人把产物提交了。
FORBIDDEN_IN_SRC = [
    'pack/assets/atm/textures/questpics',
    'pack/assets/hanhua_trophies',
    'pack/assets/hanhua_wood_names',
    'kubejs/client_scripts/pb_hanhua_tooltip.js',
    'kubejs/server_scripts/pb_hanhua_cage_migrate.js',
    'config/fancymenu/assets',
    'pack/assets/minecraft/font/default.json',
    'pack/assets/minecraft/font/uniform.json',
    'pack/pack.mcmeta',
    # 任务书里的育种公式副标题：从 Productive Trees 的授粉配方现推，
    # 由 gen_productive_trees_quest_lang.py 写进出货树。
    'config/ftbquests/quests/lang/zh_cn/chapters/zz_hanhua_productive_trees_names.snbt',
]


def main():
    bad = [p for p in FORBIDDEN_IN_SRC if (SRC / p).exists()]
    if bad:
        sys.exit('❌ src/ 里出现了生成物，必须删掉（它们由 generate_all.sh 现产）：\n  '
                 + '\n  '.join('src/' + b for b in bad))

    if COMMON.exists():
        shutil.rmtree(COMMON)
    n = 0
    for name, dest in LAYOUT:
        s = SRC / name
        if not s.is_dir():
            sys.exit('❌ 缺 src/%s' % name)
        d = COMMON / dest
        d.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(s, d, ignore=shutil.ignore_patterns('.DS_Store'))
        n += sum(1 for _ in d.rglob('*') if _.is_file())
    # 不依赖 mod jar 的那两个生成器就地跑掉，保证「摊完就是一棵自洽的树」。
    # 否则只跑 assemble 的调用方（安装器测试、CI 快闸）会拿到一棵缺
    # vaultpatcher/ 和 pack.mcmeta 的树，报出来的错还完全看不出根因。
    newest = sorted((d.name for d in (ROOT / 'versions').iterdir()
                     if d.is_dir() and d.name[0].isdigit()),
                    key=lambda s: [int(x) for x in s.split('.')])[-1]
    gen_vaultpatcher.main(newest, COMMON)
    fetch_mods.main(COMMON)
    gen_vanilla_assets.main(os.environ.get('ATM_PACK_ROOT', ''), PACK)

    n = sum(1 for _ in COMMON.rglob('*') if _.is_file())
    print('已摊出货树: %s（%d 个文件）' % (COMMON, n))
    print('  资源包源目录: %s' % PACK)


if __name__ == '__main__':
    main()
