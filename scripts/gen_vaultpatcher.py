#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# atm10-zh-cn — All the Mods 10 简体中文汉化补丁「绿油油版」
# Copyright (C) 2026 星野夢華 (Hoshino Yumeka)
# SPDX-License-Identifier: GPL-3.0-or-later
"""产出某个整合包版本的 VaultPatcher 模块。

模块头部的 `mods` / `desc` 写的是带版本号的 jar 文件名（如 `OctoLib-NEOFORGE-0.6.2+1.21.jar`），
各版本不同：拿 7.2 那份比对，7.1 只有 116/152 对得上，7.0 只有 83/152。

所以 `src/vaultpatcher/modules/*.json` 只存手写的部分（`name` / `authors` / `dynamic` / `i18n`
+ `target_class` + `pairs`），`mods` 与 `desc` 由本脚本按 `versions/db/<版本>/vaultpatcher.json`
填入，那份数据库按该版字节码记录每个目标类由哪个 jar 提供。`mods` 在 VaultPatcher 里只用于
debug 输出，匹配靠 `target_class` 与常量池字符串，但它会发给玩家，必须正确。

用法:
    python3 scripts/gen_vaultpatcher.py <整合包版本> <输出目录>
"""
import json
import sys
from pathlib import Path

from paths import ROOT, SRC

MODULES = SRC / 'vaultpatcher' / 'modules'

# 这些模块留在 src/ 备查，不随包发行：对应的上游类已改名，或该组文本已由别处覆盖。
SRC_ONLY = {'blockui_legacy_labels.json'}

# ── 显示层动态替换是全局开销 ────────────────────────────────────────────
#
# vaultpatcher 1.5.3-fix（sha256 d79668dd…）的字节码里：
#
#   VPNeoForgeMinecraftClassProcessor.targets() = {
#       net.minecraft.network.chat.contents.PlainTextContents$LiteralContents,
#       net.minecraft.client.gui.Font,
#       net.minecraft.network.chat.FormattedText }
#
# 这三个类被注入 DynamicReplaceUtils.__mappingString。注入按方法名命中第一个就停，1.21.1 的
# Font 里 String 重载排在 FormattedCharSequence 重载前面，所以 Component 文本渲染
# （drawInBatch → renderText(FormattedCharSequence…)）可能没被注入，只有裸 String 绘制与字面量
# Component 构造会走到。这一点来自对抗验证，没有复现过。确定的是每次调用的代价：
#
#   1. `Utils.needStacktrace` 为真时先 `Thread.currentThread().getStackTrace()`。只要有一个
#      dynamic 块写了 target_class，这个开关就为真（VaultPatcher._init 里的
#      anyMatch(ti -> !ti.getTargetClassInfo().getDynamicName().isEmpty())）。
#   2. 遍历所有 dynamic 模块的表。dyn 模式下 `Pairs.getValue` 是对 pairsSet 的线性
#      String.equals 扫描。
#   3. target_class 只在命中后用栈回溯校验，只防误替换，不省开销。
#
# 实测（三个版本的真实表直接调 DynamicReplaceUtils.__mappingString，栈深 40，
# 64 条真实界面串，200k 次取均值）：
#
#     不装 dynamic 模块                       0.1 µs / 串
#     vr13（481 对，0 个 @）                  13.1 µs / 串
#     vr14-beta2（1375 对，其中 502 个 @）     69.9 µs / 串   ← 5.3 倍
#     vr14-beta2 只去掉 @ 前缀（对数不变）     18.2 µs / 串
#
# 差距几乎全来自 `@`：值以 @ 开头时该块进入非完整匹配模式，没被精确命中的字符串都要对每个 @ 对
# 做一次 String.replace。精确匹配路径本来就会去掉 @ 前缀（MatchUtils.matchPairs 第 46 字节起），
# 对整串等于键的对子，@ 没有额外作用。性能是 P0，漏翻只是 issue，所以出货时把 @ 改成精确匹配，
# 并限制 dynamic 总对数。
#
# 1300 是打性能补丁之前按「1085 对线性 String.equals 要 10.2 µs」定的。patch_vaultpatcher.py
# 之后精确匹配走哈希查表（18,339ns → 348ns），对数不再线性推高开销，贵的只剩 MAX_FRAGMENT_PAIRS
# 管的子串路径。目前没有需要放宽的内容（当前 1172 对），所以保持 1300。
MAX_DYNAMIC_PAIRS = 1300

# 只有片段键（如 `'[Default: '` 这种带首尾空格的）才用 `@`，而且单独成块。
# 子串替换的开销是「每次替换调用 × 该块全部对数」，所以上限要严。
MAX_FRAGMENT_PAIRS = 16

# 因上面的预算暂不随包发行的模块（文件留在 src/）。配置界面这两块共 3495 对，实测把每串成本
# 从 17 µs 推到 64 µs。r14 正式版发过这两个文件（按 vr14 的发布产物核对，vr14-beta2 里没有），
# 安装器只覆盖不删除，所以由 installer/install.{sh,ps1} 的 clean_legacy_config_ui /
# Clear-LegacyConfigUI 清理旧文件。
PERF_HOLD = {
    'config_ui_generated.json': '3174 对，dynamic 全局扫表，代价见上方实测',
    'catnip_config_ui.json': '321 对，同上，与 config_ui_generated 是同一批界面',
}


def wants_substring(key, value):
    """这一对是否保留子串模式（`@`）。两种情况保留：

    1. 键带首尾空格（如 `'[Default: '`、`'Farthest '`）：它是长串里的一段，不会与整串相等，
       改成精确匹配会丢译文。自动识别。
    2. 值写 `@@`：显式声明需要子串替换，例如 `Caledonia` 出现在 `Caledonia Roads` 里。
       出货时 `@@` 收敛成一个 `@`。

    两种都放进独立的片段块（见 flatten_at），受 MAX_FRAGMENT_PAIRS 约束。
    """
    return key != key.strip() or str(value).startswith('@@')


def flatten_at(doc, name, stats):
    """把 dynamic 模块里的 `@值` 改成精确匹配，并统计对数。

    `is_fragment` 的键保留 `@`，集中到该 target_class 的独立块里：非完整匹配按块触发，
    块里有一个 `@`，没被精确命中的字符串就要扫一遍整张表。4 条片段单独成块，
    子串扫描只跑 4 次，不用跟着 966 条一起跑。

    只改出货副本，不碰 src/ 的原文件。返回新的块列表。
    """
    if not doc[0].get('dynamic'):
        return doc[1:]
    out = []
    for b in doc[1:]:
        pairs, frags, seen = [], [], set()
        for x in b.get('pairs') or []:
            k, v = x.get('key'), x.get('value', '')
            if not k:
                continue
            if isinstance(v, str) and v.startswith('@'):
                if wants_substring(k, v):           # 只有这两种才值得付子串扫描的钱
                    y = dict(x)
                    y['value'] = v[1:] if v.startswith('@@') else v   # @@ 收敛成 @
                    frags.append(y)
                    stats['frag'] += 1
                    continue
                v = v[1:]
                stats['at'] += 1
            if (k, v) in seen:                      # 摊平后可能撞成同一对
                stats['dedup'] += 1
                continue
            seen.add((k, v))
            y = dict(x)
            y['value'] = v
            pairs.append(y)
        stats['pairs'] += len(pairs) + len(frags)
        nb = dict(b)
        if 'pairs' in nb:
            nb['pairs'] = pairs
        out.append(nb)
        if frags:
            fb = dict(b)
            fb['pairs'] = frags
            out.append(fb)                          # 同一个 target_class，独立成块
    stats['mods'].append((name, sum(len(b.get('pairs') or []) for b in out)))
    return out



def main(ver, out_dir):
    db_path = ROOT / 'versions' / 'db' / ver / 'vaultpatcher.json'
    if not db_path.is_file():
        sys.exit('❌ 没有 %s\n'
                 '   先跑: python3 scripts/build_version_db.py %s <该版 mods 目录>'
                 % (db_path, ver))
    db = json.loads(db_path.read_text(encoding='utf-8'))
    out = Path(out_dir) / 'vaultpatcher' / 'modules'
    out.mkdir(parents=True, exist_ok=True)

    n = 0
    nojar = []
    stats = {'pairs': 0, 'at': 0, 'dedup': 0, 'frag': 0, 'mods': []}
    for p in sorted(MODULES.glob('*.json')):
        if p.name in SRC_ONLY or p.name in PERF_HOLD:
            continue
        doc = json.loads(p.read_text(encoding='utf-8'))
        entry = db.get(p.name)
        if entry is None:
            sys.exit('❌ %s 的 %s 在该版数据库里没有记录，数据库过期了，重建它。'
                     % (ver, p.name))
        # 该版里，这个模块的目标类实际由哪些 jar 提供
        jars = []
        for b in entry['blocks']:
            for j in b.get('jars') or []:
                if j not in jars:
                    jars.append(j)
        head = dict(doc[0])
        if jars:
            head['desc'] = '%s 硬编码文本汉化' % '、'.join(jars)
            head['mods'] = ', '.join(jars)
        else:
            # 该版本里找不到目标类：模块保留（匹配靠 target_class，不生效也无害），但不填不存在的 jar 名。
            head['desc'] = '硬编码文本汉化（ATM10 %s 里未找到目标类）' % ver
            head['mods'] = ''
            nojar.append(p.name)
        # 字段顺序照 VaultPatcher 自带样例：name, desc, authors, mods, dynamic, i18n
        ordered = {}
        for k in ('name', 'desc', 'authors', 'mods', 'dynamic', 'i18n'):
            if k in head:
                ordered[k] = head[k]
        for k in head:
            ordered.setdefault(k, head[k])
        blocks = flatten_at(doc, p.name, stats)
        (out / p.name).write_text(
            json.dumps([ordered] + blocks, ensure_ascii=False, indent=2) + '\n',
            encoding='utf-8')
        n += 1
    # 出货侧检查：不许有 @，总对数不许超预算。
    for f in sorted(out.glob('*.json')):
        doc = json.loads(f.read_text(encoding='utf-8'))
        if not doc[0].get('dynamic'):
            continue
        for b in doc[1:]:
            prs = b.get('pairs') or []
            at = [x for x in prs if str(x.get('value', '')).startswith('@')]
            if not at:
                continue
            # 非完整匹配按块触发，块里有一个 @，整张表都会被逐串扫描。
            # 所以 @ 只能放在全是片段键的小块里。
            if len(at) != len(prs):
                sys.exit('❌ %s 有个块混着 %d 个 @ 和 %d 个精确对。@ 会让整块进入'
                         '非完整匹配模式，逐串扫描全块。把 @ 单独成块。'
                         % (f.name, len(at), len(prs) - len(at)))
            # 出货副本里已经没有 @@，所以反查 src/ 的原始值来放行显式声明。
            src_path = MODULES / f.name
            if not src_path.is_file():
                sys.exit('❌ 出货树里有个 src/ 里不存在的模块 %s，而它还带着 @。'
                         '多半是 build/ 里的旧文件，清理后再构建。' % f.name)
            src_doc = json.loads(src_path.read_text(encoding='utf-8'))
            explicit = {x['key'] for b2 in src_doc[1:] for x in (b2.get('pairs') or [])
                        if str(x.get('value', '')).startswith('@@')}
            bad = [x['key'] for x in at
                   if x['key'] == x['key'].strip() and x['key'] not in explicit]
            if bad:
                sys.exit('❌ %s 里 %r 用了 @ 但键没有首尾空格，也没写 @@ 显式声明。'
                         '整串就是这个键时精确匹配就够了，@ 只会增加开销。'
                         '确实需要子串替换，就把值写成 @@译文。' % (f.name, bad[0]))
            if len(at) > MAX_FRAGMENT_PAIRS:
                sys.exit('❌ %s 的片段块有 %d 条，超过上限 %d。'
                         '子串替换是逐串开销，不要再往这里加。' % (f.name, len(at), MAX_FRAGMENT_PAIRS))
    # 停发的模块必须真的不在包里，r14 掉帧就是停发模块漏回出货树造成的。拦它的规则在
    # src/rules/vaultpatcher.json（check.py 查出货树），名单在这里，所以反过来核对：
    # 名单里每个名字都必须被某条 no_files 规则的 glob 覆盖。
    import fnmatch
    rules = json.loads((ROOT / 'src' / 'rules' / 'vaultpatcher.json').read_text(encoding='utf-8'))
    globs = [r['glob'] for r in rules if r.get('kind') == 'no_files' and 'glob' in r]
    for hold in sorted(set(SRC_ONLY) | set(PERF_HOLD)):   # 别用 n：那是上面的模块计数
        target = 'vaultpatcher/modules/%s' % hold
        if not any(fnmatch.fnmatch(target, gl) for gl in globs):
            sys.exit('❌ %s 在不出货名单里，却没有任何 no_files 规则拦它。\n'
                     '   在 src/rules/vaultpatcher.json 补一条 no_files 规则。' % hold)
    leaked = sorted(n for n in list(SRC_ONLY) + list(PERF_HOLD) if (out / n).exists())
    if leaked:
        sys.exit('❌ 这些模块本不该出货，却出现在出货树里：%s\n'
                 '   （SRC_ONLY / PERF_HOLD 名单见本脚本顶部，多半是 build/ 里的旧文件）'
                 % '、'.join(leaked))
    if stats['pairs'] > MAX_DYNAMIC_PAIRS:
        top = '、'.join('%s %d 对' % r for r in sorted(stats['mods'], key=lambda r: -r[1])[:4])
        sys.exit('❌ dynamic 模块合计 %d 对，超过预算 %d 对。\n'
                 '   每次替换调用都要线性扫描这张表（见本脚本顶部实测），\n'
                 '   超预算就是全局掉帧。最大的几个：%s\n'
                 '   要么把它挪进 PERF_HOLD，要么先量过再改预算。'
                 % (stats['pairs'], MAX_DYNAMIC_PAIRS, top))
    # VaultPatcher 主配置里的 modules / mods 就是模块清单，按模块自动填入。手维护时漏过 6 个
    # *_zh 模块：`load_all_modules` 为真时没有影响，关掉它这 6 个模块就静默失效。
    cfg_src = SRC / 'config' / 'vaultpatcher_asm' / 'config.json'
    cfg = json.loads(cfg_src.read_text(encoding='utf-8'))
    names = sorted(p.stem for p in MODULES.glob('*.json')
                   if p.name not in SRC_ONLY and p.name not in PERF_HOLD)
    cfg_out = {'modules': names, 'mods': names}
    cfg_out.update(cfg)
    cfg_path = Path(out_dir) / 'config' / 'vaultpatcher_asm' / 'config.json'
    cfg_path.parent.mkdir(parents=True, exist_ok=True)
    cfg_path.write_text(json.dumps(cfg_out, ensure_ascii=False, indent=2) + '\n',
                        encoding='utf-8')

    print('VaultPatcher 模块：%d 个（按 ATM10 %s 的 jar 名填入），主配置清单 %d 条'
          % (n, ver, len(names)))
    print('  dynamic 表合计 %d 对 / 预算 %d 对，摊平 @ 前缀 %d 个，去重 %d 对，'
          '片段键保留 @ 并单独成块 %d 条'
          % (stats['pairs'], MAX_DYNAMIC_PAIRS, stats['at'], stats['dedup'], stats['frag']))
    if PERF_HOLD:
        print('  因预算暂不出货 %d 个：%s'
              % (len(PERF_HOLD), '、'.join('%s（%s）' % kv for kv in sorted(PERF_HOLD.items()))))
    if nojar:
        print('  该版本里找不到目标类的 %d 个：%s' % (len(nojar), '、'.join(nojar)))


if __name__ == '__main__':
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    main(sys.argv[1], sys.argv[2])
