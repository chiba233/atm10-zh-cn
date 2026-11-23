#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# atm10-zh-cn — All the Mods 10 简体中文汉化补丁「绿油油版」
# Copyright (C) 2026 星野夢華 (Hoshino Yumeka)
# SPDX-License-Identifier: GPL-3.0-or-later
"""KubeJS 的类过滤表是硬约束：脚本里 `Java.loadClass` 一个被禁的类，运行时当场抛异常。

## 为什么要这道闸

`hanhua_update_check.js` 在 vr16-beta4 与 vr16 里发了出去，一次都没工作过：

    const $System = Java.loadClass('java.lang.System')      // ← 这一行必抛
    const $HttpClient = Java.loadClass('java.net.http.HttpClient')

KubeJS 自带的 `kubejs.classfilter.txt` 里写着 `- java.lang`（白名单里没有 `System`）
与 `- java.net`。这两行在任何机器上都 100% 抛异常，可它们躺在事件回调里，
外面又套着 `catch {}`，于是表现成「进游戏什么都没发生」，既不报错也不留日志，
跟「已经是最新版所以没提示」完全无法区分。加载阶段全绿（`18/18 … 0 errors`），
CI 全绿，只有真去读 KubeJS 的字节码才看得出来。

静态可判定的东西就不该靠玩家反馈发现。

## 判定语义（照抄 ClassFilter 的字节码，不是猜的）

    isAllowed0(name):
        name in denyStrong   → 拒绝      # 精确匹配优先
        name in allowStrong  → 放行
        任一 denyWeak 前缀 startsWith(name) → 拒绝
        否则 → 放行                       # 默认放行

`- x` 同时进 denyStrong 与 denyWeak，`+ x` 同时进 allowStrong 与 allowWeak。
所以 `- java.lang` + `+ java.lang.Integer` = 「整个包禁掉，只放行这几个具体类」。

那张表不抄进仓库：不同 KubeJS 版本的表不一样，抄一份进来就是又一个会
悄悄过期的上游副本。这里从目标整合包自己那个 kubejs jar 里现读。

## fail-closed

拿不到 jar、读不到表、树里一个脚本都没有、一条 `Java.loadClass` 都没扫到、
或者参数不是字符串字面量（静态判不了），全部当红，不许「没发现问题所以通过」。

用法:
    python3 scripts/compliance/check_kubejs_classfilter.py <mods 目录> <出货树>...
"""
import os
import re
import sys
import zipfile
from pathlib import Path

FILTER_MEMBER = 'kubejs.classfilter.txt'
# 只认 `Java.loadClass(...)`：KubeJS 里其余取类的路子（Platform、各 mod 的绑定）
# 不过这张表。参数一律要求是单个字符串字面量，别的形状静态判不了 → 直接红。
CALL = re.compile(r'Java\.loadClass\s*\(([^)]*)\)')
LITERAL = re.compile(r"""^\s*(['"])(?P<name>[A-Za-z_$][\w.$]*)\1\s*$""")


def die(msg):
    raise SystemExit('❌ KubeJS 类过滤检查没跑成：%s' % msg)


def load_filter(mods):
    """从目标整合包的 kubejs jar 里现读那张表。"""
    if not mods.is_dir():
        die('找不到 mods 目录 %s（CI 应传 $ATM_PACK_ROOT/mods）' % mods)
    jars = sorted(mods.glob('kubejs-*.jar'))
    if not jars:
        die('%s 下没有 kubejs-*.jar' % mods)
    jar = jars[-1]
    try:
        with zipfile.ZipFile(jar) as z:
            raw = z.read(FILTER_MEMBER).decode('utf-8')
    except KeyError:
        die('%s 里没有 %s——KubeJS 换实现了，这道闸要跟着改' % (jar.name, FILTER_MEMBER))
    except zipfile.BadZipFile:
        die('%s 不是有效的 jar' % jar.name)

    deny, allow = [], []
    for line in raw.splitlines():
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        target = deny if line[0] == '-' else allow if line[0] == '+' else None
        if target is None:
            die('%s 第一列既不是 + 也不是 -：%r' % (FILTER_MEMBER, line[:40]))
        entry = line[1:].strip()
        if entry:
            target.append(entry)
    if not deny:
        die('%s 里一条 - 规则都没有，表读空了' % jar.name)
    return jar.name, set(deny), set(allow), deny


def allowed(name, deny_strong, allow_strong, deny_weak):
    if name in deny_strong:
        return False
    if name in allow_strong:
        return True
    return not any(name.startswith(w) for w in deny_weak)


def main():
    args = [a for a in sys.argv[1:]]
    if not args:
        raise SystemExit(__doc__.strip().splitlines()[-1])
    mods = Path(args[0])
    trees = [Path(t) for t in args[1:]] or [Path(os.environ.get('ATM_TREE', 'build/common'))]

    jar_name, deny_strong, allow_strong, deny_weak = load_filter(mods)

    scripts = []
    for tree in trees:
        if not tree.is_dir():
            die('出货树 %s 不存在' % tree)
        scripts += sorted((tree / 'kubejs').rglob('*.js'))
    if not scripts:
        die('出货树里一个 kubejs/**/*.js 都没有')

    seen, bad = 0, []
    for path in scripts:
        for i, line in enumerate(path.read_text(encoding='utf-8', errors='replace').splitlines(), 1):
            for arg in CALL.findall(line):
                seen += 1
                m = LITERAL.match(arg)
                if not m:
                    bad.append((path, i, arg.strip()[:40], '参数不是字符串字面量，静态判不了'))
                    continue
                name = m.group('name')
                if not allowed(name, deny_strong, allow_strong, deny_weak):
                    bad.append((path, i, name, '被 %s 的过滤表拒绝，运行时必抛' % jar_name))
    if not seen:
        die('全树一条 Java.loadClass 都没扫到——正则或出货树不对')

    if bad:
        print('❌ KubeJS 会拒绝这些类，脚本运行时当场抛异常：')
        for path, line, name, why in bad:
            print('   %s:%d  %s  ← %s' % (path, line, name, why))
        print('\n   过滤表来自 %s。放行的替代品：整合包类路径上的 org.apache.http.*'
              '（HttpGet 收字符串 URL）、org.apache.commons.lang3.*、java.util.concurrent.*。' % jar_name)
        return 1

    print('✅ KubeJS 类过滤：%d 个脚本里 %d 条 Java.loadClass 全部放行（表来自 %s）'
          % (len(scripts), seen, jar_name))
    return 0


if __name__ == '__main__':
    sys.exit(main())
