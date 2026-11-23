#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# atm10-zh-cn — All the Mods 10 简体中文汉化补丁「绿油油版」
# Copyright (C) 2026 星野夢華 (Hoshino Yumeka)
# SPDX-License-Identifier: GPL-3.0-or-later
"""资源包自检的探针键必须与自检脚本严丝合缝。

## 为什么要这道闸

`hanhua_pack_check.js` 的判据是：拿脚本里写的键名去查语言表，查不到就告诉玩家
「你没启用汉化资源包」，查到但值与脚本里的版本号不一致就告诉玩家「你启用的是旧
版本的包」。这条链子上任何一环对不上，后果都是给配置完全正常的玩家每次进游戏
弹一次红字，比不做这个功能还糟。

而这四种对不上，全都是静态可判定的：

    1. 资源包里压根没有那个 lang 文件（改了目录、漏进出货树）
    2. 键名与脚本里的 PROBE_KEY 不一致（改了一边忘了另一边）
    3. 值与脚本里的 PACK_VERSION 不一致（版本号没被同一次替换填上）
    4. 命名空间目录与脚本里的 PROBE_NAMESPACE 不一致（顺序自检认不出自己）

静态可判定的东西就不该靠玩家反馈发现。

## fail-closed

出货树不存在、文件缺失、JSON 读不通、脚本里的常量抽不出来、还残留着
`@@PATCHVER@@`，一律红。不许「没发现问题所以通过」。

用法:
    python3 scripts/compliance/check_pack_probe.py <出货树>
"""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from paths import PACK_NAME                                     # noqa: E402


SCRIPT_REL = Path('kubejs/client_scripts/hanhua_pack_check.js')
PLACEHOLDER = '@@PATCHVER@@'
# 脚本里这三个常量是判据的全部输入，逐个抽出来跟资源包对账
CONSTS = ('PROBE_KEY', 'PROBE_NAMESPACE', 'PACK_VERSION')


def die(msg):
    raise SystemExit('❌ 资源包探针检查没跑成：%s' % msg)


def read_consts(path):
    text = path.read_text(encoding='utf-8')
    out = {}
    for name in CONSTS:
        found = re.findall(r"^\s*const\s+%s\s*=\s*'([^']*)'\s*$" % name, text, re.M)
        if len(found) != 1:
            die('%s 里 const %s 应恰有一处，实际 %d 处' % (path, name, len(found)))
        out[name] = found[0]
    return out


def main(tree):
    root = Path(tree)
    if not root.is_dir():
        die('出货树 %s 不存在' % root)

    script = root / SCRIPT_REL
    if not script.is_file():
        die('出货树里缺少 %s' % script)
    consts = read_consts(script)

    if consts['PACK_VERSION'] == PLACEHOLDER:
        die('%s 里的 PACK_VERSION 还是占位符——gen_hanhua_update_check.py 没跑过'
            % SCRIPT_REL)

    lang = (root / 'resourcepacks' / PACK_NAME / 'assets'
            / consts['PROBE_NAMESPACE'] / 'lang' / 'zh_cn.json')
    if not lang.is_file():
        die('资源包里缺少探针文件 %s（脚本的 PROBE_NAMESPACE 是 %r）'
            % (lang, consts['PROBE_NAMESPACE']))
    try:
        data = json.loads(lang.read_text(encoding='utf-8'))
    except ValueError as exc:
        die('%s 不是有效的 JSON：%s' % (lang, exc))
    if not isinstance(data, dict):
        die('%s 的顶层不是对象' % lang)

    key = consts['PROBE_KEY']
    if key not in data:
        die('探针文件里没有键 %r，实际有 %r' % (key, sorted(data)))
    value = data[key]
    if value == PLACEHOLDER:
        die('探针值还是占位符——gen_hanhua_update_check.py 没填资源包这一份')
    if value != consts['PACK_VERSION']:
        die('探针值与脚本对不上：资源包里是 %r，脚本里的 PACK_VERSION 是 %r。'
            '两者必须由同一次替换填同一个值，否则玩家会被误报「启用着旧版本的包」'
            % (value, consts['PACK_VERSION']))

    print('✅ 资源包探针：%s = %r，与 %s 一致'
          % (key, value, SCRIPT_REL.name))
    return 0


if __name__ == '__main__':
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    sys.exit(main(sys.argv[1]))
