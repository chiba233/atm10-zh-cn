#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# atm10-zh-cn — All the Mods 10 简体中文汉化补丁「绿油油版」
# Copyright (C) 2026 星野夢華 (Hoshino Yumeka)
# SPDX-License-Identifier: GPL-3.0-or-later
"""给出货树里所有带补丁版本号的文件填上这次发布的版本。

源码里这些文件是模板，写着 ``@@PATCHVER@@``：

    kubejs/client_scripts/hanhua_update_check.js   游戏内更新提示，比对 GitHub 最新 tag
    kubejs/client_scripts/hanhua_pack_check.js     资源包生效自检，比对下面那个探针键
    resourcepacks/<包名>/assets/atm10zhcn/lang/zh_cn.json
                                                   探针键 atm10zhcn.pack.version

后两者必须由同一次替换填同一个值：自检脚本正是拿自己的版本号去比对资源包里
读到的探针值，两边不一致就会当成「玩家启用着旧版本的资源包」报给玩家。分成两个
脚本各填各的，早晚会因为漏调一个而让所有正常用户天天看到误报。

这个逻辑独立于 build_dist.sh，避免 shell 里内嵌难测的 Python，也让漏复制文件、
占位符数量异常等情况立即失败而不是静默产出一个填了一半的包。

用法:
    python3 scripts/gen_hanhua_update_check.py <补丁版本号> <出货树>
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from paths import PACK_NAME                                     # noqa: E402


PLACEHOLDER = '@@PATCHVER@@'
TARGETS = [
    Path('kubejs/client_scripts/hanhua_update_check.js'),
    Path('kubejs/client_scripts/hanhua_pack_check.js'),
    Path('resourcepacks') / PACK_NAME / 'assets/atm10zhcn/lang/zh_cn.json',
]


def main(version, tree):
    root = Path(tree)
    for rel in TARGETS:
        target = root / rel
        if not target.is_file():
            sys.exit('❌ 出货树里缺少 %s：先确认 assemble.py 已复制它。' % target)
        text = target.read_text(encoding='utf-8')
        count = text.count(PLACEHOLDER)
        if count != 1:
            sys.exit('❌ %s 中应恰有一个 %s，实际有 %d 个。'
                     % (target, PLACEHOLDER, count))
        target.write_text(text.replace(PLACEHOLDER, version), encoding='utf-8')
    print('补丁版本 %s：已填入 %d 个文件' % (version, len(TARGETS)))


if __name__ == '__main__':
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    main(sys.argv[1], sys.argv[2])
