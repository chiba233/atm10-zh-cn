#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# atm10-zh-cn — All the Mods 10 简体中文汉化补丁「绿油油版」
# Copyright (C) 2026 星野夢華 (Hoshino Yumeka)
# SPDX-License-Identifier: GPL-3.0-or-later
"""全仓库统一的目录约定。

仓库里没有任何一棵出货用的目录树：`kubejs/`、`config/`、`resourcepacks/`、
`mods/` 全部是构建时现生成的，落在 `build/` 下（`.gitignore` 排除）。
仓库里只有 `src/`（手写的真源与映射）和 `scripts/`（生成器）。

    src/pack/            资源包内容（译文、本包独有资源）
    src/config/          本包独有的 config（任务书 delta、VaultPatcher 主配置…）
    src/kubejs/          本包独有的 KubeJS 脚本
    src/upstream/        上游文件的行级改写映射（见 gen_upstream_patches.py）
    src/vaultpatcher/    字节码替换表
    src/mods/            随包分发的 jar

    build/common/        出货树，版本中立部分（含全部生成物）
    build/upstream/<版本>/ 该版专属：套用映射后的上游 kubejs/ 与 config/
    build/snapshots/     生成器之间传递的中间快照
"""
import os
import sys
from pathlib import Path

# Windows runner 的 stdout 默认 cp1252，打不出中文，脚本会在 print 那一行直接崩，
# 而且崩在「干完活之后」，看起来像是活没干成。所有脚本都 import 这个模块，
# 所以放在这里一次性解决。
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / 'src'
BUILD = Path(os.environ.get('ATM_BUILD') or (ROOT / 'build'))

COMMON = BUILD / 'common'
UPSTREAM = BUILD / 'upstream'
SNAPSHOTS = BUILD / 'snapshots'

PACK_NAME = 'ATM10汉化包'
PACK = COMMON / 'resourcepacks' / PACK_NAME


def snapshot(name):
    SNAPSHOTS.mkdir(parents=True, exist_ok=True)
    return SNAPSHOTS / name


def need_common():
    if not PACK.is_dir():
        raise SystemExit('❌ 还没组装出货树。先跑: python3 scripts/assemble.py')
    return COMMON
