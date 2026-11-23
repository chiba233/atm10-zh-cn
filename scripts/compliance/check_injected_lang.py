#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# atm10-zh-cn — All the Mods 10 简体中文汉化补丁「绿油油版」
# Copyright (C) 2026 星野夢華 (Hoshino Yumeka)
# SPDX-License-Identifier: GPL-3.0-or-later
"""查 ATM 注入的语言文件，那才是玩家实际看到的那一份。

## 为什么需要这个

ATM 通过 `kubejs/assets/<命名空间>/lang/zh_cn.json` 注入自己的译名，**它压过
我们的资源包**。后果是：我们在 `src/pack/assets/…` 里写的译名，只要 ATM 也注入了
同一个键，就根本不生效。

2026-07-28 实测这件事的代价：ATM 注入 1992 个键，其中 **536 个我们也译了但写得
不一样**，那 536 条全是死的。用户当面纠正「高级机械外壳是对的，进阶机器外壳是
错的」才暴露：我一直在看仓库，他在看游戏，看的不是同一份东西。更糟的是其中 26 个
键 ATM 注入的是英文，把我们的中文盖成了英文，玩家一直看着 `Depth: %d`、
`Press [Shift] for info`，而仓库里明明有译文。

要真正改变这些显示名，只能改 `src/upstream/kubejs/assets/<ns>/lang/zh_cn.json.json`
（对 ATM 那份的行级改写映射），改我们的资源包没有任何用。

## 这个脚本报两件事

1. 注入值仍是英文，玩家看得见的英文。除去专有名（Discord/Github）、
   缩写（LV/MV/HV/EV/SV）、译者注释（`_comment`）之外，都该补进上游映射。
2. 我们的译名与注入值不同，我们那份是死的。要么去上游映射改注入值，
   要么把我们那份改齐，别让仓库里存着两套名字。

## 两种运行模式

- 缺省（不带参数）：只报告，恒返回 0。给人手动跑、盯着输出自己判断用，
  `bare` 那条英文判定和 `KEEP_VALUES` 专有名单都可能有漏网之鱼，不该拿这种
  启发式规则直接拦构建，所以默认不改变退出码。
- `--strict`：只要①或②任意一类命中，就返回 1。这是留给接进 CI 的开关。
  2026-07-28 对抗审计第二轮指出：`main()` 结尾恒定 `return 0`，就算手动接进
  workflow 也拦不住任何东西，这份脚本本身就是当年发现「ATM 注入 536 个键
  盖掉我们译文、其中 26 个还是英文」那次事故的报告工具，如果它自己永远不会
  让构建变红，下一次同样的事故还是得靠玩家在游戏里当面纠正才能发现。

用法:
    python3 scripts/compliance/check_injected_lang.py [<实例目录>]              # 只报告
    python3 scripts/compliance/check_injected_lang.py [<实例目录>] --strict      # 报告 + 拦截
    # 缺省读 ATM_PACK_ROOT，再退到 build/packsrc/<最新版本>
"""
import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
CJK = re.compile('[一-鿿]')
WORD = re.compile(r'[A-Za-z]{2,}')
# 有意保留英文的：平台专有名、电压等级缩写（科技模组通例，且参与机器外壳名拼接）
KEEP_VALUES = {'Discord', 'Github', 'GitHub', 'Reddit', 'CurseForge', 'Modrinth',
               'LV', 'MV', 'HV', 'EV', 'SV', 'KubeJS', 'NeoForge', 'FE'}


def instance_dir(argv):
    if argv:
        return Path(argv[0])
    env = os.environ.get('ATM_PACK_ROOT')
    if env:
        return Path(env)
    cand = sorted((ROOT / 'build' / 'packsrc').glob('[0-9]*'))
    if cand:
        return cand[-1]
    sys.exit('❌ 找不到整合包目录。给个参数，或设 ATM_PACK_ROOT。')


def main(argv):
    strict = '--strict' in argv
    argv = [a for a in argv if a != '--strict']    # 剩下的才可能是实例目录路径
    inj = instance_dir(argv) / 'kubejs' / 'assets'
    if not inj.is_dir():
        print('（%s 不存在，跳过）' % inj)
        return 0
    english, shadowed = [], []
    n_ns = n_key = 0
    for d in sorted(inj.iterdir()):
        f = d / 'lang' / 'zh_cn.json'
        if not f.is_file():
            continue
        try:
            atm = json.loads(f.read_text(encoding='utf-8-sig'))
        except Exception:                                          # noqa: BLE001
            continue
        n_ns += 1
        n_key += len(atm)
        p = ROOT / 'src' / 'pack' / 'assets' / d.name / 'lang' / 'zh_cn.json'
        ours = json.loads(p.read_text(encoding='utf-8-sig')) if p.is_file() else {}
        for k, v in atm.items():
            if not isinstance(v, str):
                continue
            if k.startswith('_') or '_comment' in k:
                continue
            bare = re.sub(r'[§&][0-9a-fk-orA-FK-OR]|%(?:\d+\$)?[a-zA-Z]|[\d\s\W_]', '', v)
            if bare and not CJK.search(v) and WORD.search(v) and v.strip() not in KEEP_VALUES:
                english.append((d.name, k, v))
            if k in ours and str(ours[k]) != str(v):
                shadowed.append((d.name, k, v, ours[k]))
    print('ATM 注入：%d 个命名空间、%d 个键' % (n_ns, n_key))
    print('① 注入值仍是英文（玩家看得见）：%d 条' % len(english))
    for ns, k, v in english[:20]:
        print('     %-24s %-44s %r' % (ns, k[-44:], v[:36]))
    print('② 我们的译名与注入值不同（我们那份不生效）：%d 条' % len(shadowed))
    for ns, k, v, o in shadowed[:20]:
        print('     %-20s %-38s 注入=%-14r 我们=%r' % (ns, k[-38:], v[:14], o[:14]))
    if english or shadowed:
        print('\n要改注入值，改 src/upstream/kubejs/assets/<ns>/lang/zh_cn.json.json，'
              '改我们的资源包没有用。')
    if strict and (english or shadowed):
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
