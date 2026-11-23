#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# atm10-zh-cn — All the Mods 10 简体中文汉化补丁「绿油油版」
# Copyright (C) 2026 星野夢華 (Hoshino Yumeka)
# SPDX-License-Identifier: GPL-3.0-or-later
"""Iron Jetpacks 的等级名不在 lang 里，在整合包的 config 里，漏一个就静默显示英文。

## 为什么要这道闸

游戏里显示「Vibranium能量电池」「Creative喷气背包」。乍看像是漏翻了两条，
其实是 17 个等级一条都没翻，木/石/铁那几个也是英文，只是不扎眼。

物品名的模板在 lang 里（`item.ironjetpacks.cell` = `%s能量电池`），但 `%s`
不来自 lang，来自整合包 `config/ironjetpacks/jetpacks/*.json` 里的 `name`。
照 `Jetpack#getDisplayName` 的字节码：

    String key = String.format("jetpack.%s.name", name.replaceAll(" ", "_"));
    if (Language.getInstance().has(key)) return Component.translatable(key);
    return Component.literal(displayName);   // 兜底＝把 name 首字母大写

也就是说 mod 留了正规注入点：只要 lang 里有 `jetpack.<name>.name` 就用它，
没有就悄悄回退成英文。回退是静默的，不报错、不留日志，跟「已经翻好了」
在任何自动检查里都长得一模一样。

而等级清单是整合包给的、随版本变：ATM 自己加了 allthemodium / vibranium /
unobtainium / creative 这几档。下个版本 ATM 再加一档，我们这边只会静默少一条。
所以这个清单不能手写死在仓库里，要拿目标版本的官方 config 现查。

## fail-closed

上游树没取到、jetpacks 目录不在、目录里一个 json 都没有、json 解析不了、
缺 `name` 字段、出货树里没有 ironjetpacks 的 lang，全部当红。
「没扫到东西所以通过」是这道闸最没用的失败形态。

`"disable": true` 的档位 mod 根本不注册，不需要译名，跳过。
但 `disable` 字段本身读不出来时按需要译名处理（宁可多要一条）。

用法:
    python3 scripts/compliance/check_jetpack_tiers.py <上游树> <出货树>...
"""
import json
import sys
from pathlib import Path

PACK_LANG = 'resourcepacks/ATM10汉化包/assets/ironjetpacks/lang/zh_cn.json'
CONFIG_DIR = 'config/ironjetpacks/jetpacks'


def die(msg):
    print('❌ %s' % msg)
    sys.exit(1)


def read_tiers(uproot):
    """从上游 config 读出这一版真实存在的等级名。"""
    d = uproot / CONFIG_DIR
    if not d.is_dir():
        die('上游树里没有 %s —— 上游文件没取到，等级清单无从谈起（树: %s）' % (CONFIG_DIR, uproot))
    jsons = sorted(d.glob('*.json'))
    if not jsons:
        die('%s 里一个 json 都没有 —— 取包取了个空目录，不算查过' % d)
    tiers = {}
    for p in jsons:
        try:
            data = json.loads(p.read_text(encoding='utf-8'))
        except Exception as e:
            die('%s 解析失败：%s' % (p, e))
        name = data.get('name')
        if not isinstance(name, str) or not name.strip():
            die('%s 缺 name 字段 —— 判不了它需要哪个 lang 键' % p)
        # 只有明确写了 true 才当停用。读不出来一律按「要译名」处理。
        if data.get('disable') is True:
            continue
        tiers[name] = p.name
    if not tiers:
        die('%s 里的档位全被 disable —— 不可能，多半是读错了字段' % d)
    return tiers


def check_tree(tree, tiers):
    """出货树里每个等级都得有 jetpack.<name>.name。"""
    lang = tree / PACK_LANG
    if not lang.is_file():
        die('%s 不在 —— 资源包没摊出来，这道闸等于没跑' % lang)
    try:
        data = json.loads(lang.read_text(encoding='utf-8'))
    except Exception as e:
        die('%s 解析失败：%s' % (lang, e))

    missing, empty = [], []
    for name, src in sorted(tiers.items()):
        key = 'jetpack.%s.name' % name.replace(' ', '_')
        if key not in data:
            missing.append((key, src))
        elif not str(data[key]).strip():
            empty.append(key)

    if missing or empty:
        print('❌ %s：Iron Jetpacks 等级名会静默回退成英文' % tree)
        for key, src in missing:
            print('   缺 %-34s （来自 %s/%s）' % (key, CONFIG_DIR, src))
        for key in empty:
            print('   空 %s' % key)
        print('   补进 src/pack/assets/ironjetpacks/lang/zh_cn.json 即可，'
              '译名跟对应材料的物品名保持一致')
        return False

    # 反向只报不拦：多余的键不会生效，但多半意味着上游删了档位。
    extra = sorted(k for k in data
                   if k.startswith('jetpack.') and k.endswith('.name')
                   and k[len('jetpack.'):-len('.name')].replace('_', ' ') not in tiers
                   and k[len('jetpack.'):-len('.name')] not in tiers)
    if extra:
        print('ℹ️ %s：这些等级键在上游 config 里已经没有对应档位了：%s'
              % (tree, '、'.join(extra)))
    print('✅ %s：Iron Jetpacks %d 个等级名全部有译' % (tree, len(tiers)))
    return True


def main(argv):
    if len(argv) < 3:
        die('用法: check_jetpack_tiers.py <上游树> <出货树>...')
    uproot = Path(argv[1])
    tiers = read_tiers(uproot)
    ok = True
    for t in argv[2:]:
        ok = check_tree(Path(t), tiers) and ok
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main(sys.argv))
