#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# atm10-zh-cn — All the Mods 10 简体中文汉化补丁「绿油油版」
# Copyright (C) 2026 星野夢華 (Hoshino Yumeka)
# SPDX-License-Identifier: GPL-3.0-or-later
"""产出某个整合包版本的 VaultPatcher 模块。

模块头部里的 `mods` / `desc` 写的是**带版本号的 jar 文件名**，例如
`OctoLib-NEOFORGE-0.6.2+1.21.jar`。整合包换一个版本，一大半模组的 jar 版本号就变了，
所以这两个字段**不可能有一份通用的**：手写死在仓库里，等于三个包里有两个是错的。
实测把 7.2 那份原样拿去比对：7.1 只有 116/152 对得上，7.0 只有 83/152。

所以仓库里的 `src/vaultpatcher/modules/*.json` 只留人写的那部分
（`name` / `authors` / `dynamic` / `i18n` + `target_class` + `pairs`），
`mods` 与 `desc` 由本脚本按 `versions/db/<版本>/vaultpatcher.json` 现填——
那份数据库是拿**该版真实字节码**逐块解出来的，记着每个目标类实际由哪个 jar 提供。

（`mods` 在 VaultPatcher 里只用于 debug 输出，真正的匹配靠 `target_class` +
常量池里的字符串。但它是发出去给人看的东西，写错就是错。）

用法:
    python3 scripts/gen_vaultpatcher.py <整合包版本> <输出目录>
"""
import json
import sys
from pathlib import Path

from paths import ROOT, SRC

MODULES = SRC / 'vaultpatcher' / 'modules'

# 这些模块留在 src/ 备查，但不随包发行（对应的上游类已改名或该组文本已由别处覆盖，
# 发出去只会增加加载体积与排查噪音）。出货侧另有闸复核包里确实没有它们。
SRC_ONLY = {'blockui_legacy_labels.json'}

# ── 显示层动态替换是**全局**开销，不是「只在目标类里」 ──────────────────────
#
# 读 vaultpatcher 1.5.2 的字节码（sha256 034b53b7…，javap 逐条看）得到的事实：
#
#   VPNeoForgeMinecraftClassProcessor.targets() = {
#       net.minecraft.network.chat.contents.PlainTextContents$LiteralContents,
#       net.minecraft.client.gui.Font,
#       net.minecraft.network.chat.FormattedText }
#
# VaultPatcher 往这三个类里注了 DynamicReplaceUtils.__mappingString。
#
# ⚠️ 别把它说成「每渲染一个字符串都要调一次」——那个说法**已被推翻**：注入是按方法名
# 命中第一个就跳出循环的，1.21.1 的 Font 里 String 重载排在 FormattedCharSequence
# 重载前面，所以 Component 文本渲染那条路（drawInBatch → renderText(FormattedCharSequence…)）
# 很可能压根没被注入，只有裸 String 绘制与字面量 Component 构造会走。
# 这条结论来自 2026-07-30 的对抗验证，我**没有自己复现过**，别拿它当既定事实往外写。
# 能站住的只有：调用点在这几个类上，且每次调用要付下面 1-3 的代价。
#
# 而那个方法：
#
#   1. `Utils.needStacktrace` 为真就先 `Thread.currentThread().getStackTrace()`；
#      该开关 = 「任何一个 dynamic 块写了 target_class」（VaultPatcher._init 里
#      的 anyMatch(ti -> !ti.getTargetClassInfo().getDynamicName().isEmpty())）。
#   2. 然后遍历**所有** dynamic 模块的表；`Pairs.getValue` 在 dyn 模式下是
#      对 pairsSet 的**线性 String.equals 扫描**，不是哈希查表。
#   3. target_class 只在**命中之后**才拿栈回溯去校验。所以它不省任何开销，
#      它只防误替换。
#
# 实测（拿仓库里三个版本的真实表直接调 DynamicReplaceUtils.__mappingString，
# 栈深 40，语料 64 条真实界面串，200k 次取均值）：
#
#     一个 dynamic 模块都不装                  0.1 µs / 串
#     vr13（481 对，0 个 @）                  13.1 µs / 串
#     vr14-beta2（1375 对，其中 502 个 @）     69.9 µs / 串   ← 5.3 倍
#     vr14-beta2 只把 @ 前缀去掉（对数不变）    18.2 µs / 串
#
# 那 5 倍几乎全来自 `@`：值以 @ 开头 = 该块进「非完整匹配」模式，于是任何
# **没被精确命中**的字符串都要在这块里对每个 @ 对做一次 String.replace。
# 而精确匹配路径本来就会把 @ 前缀吃掉（MatchUtils.matchPairs 第 46 字节起），
# 所以对「整串就是这个键」的对子，@ 一点额外作用都没有——只有键是长串里的一小段
# 时才多覆盖一点。拿全局帧率换那点覆盖不成立：性能是 P0，漏翻只是 issue。
#
# 因此出货侧一律把 @ 摊平成精确匹配，并给 dynamic 总对数上预算闸。
#
# 2026-08-15：1300 这个数是**打性能补丁之前**定的——当时的成本模型是
# 「1085 对线性 String.equals 要 10.2 µs」，对数直接线性推高每串开销。
# patch_vaultpatcher.py 之后精确匹配走的是哈希查表（实测 18,339ns → 348ns），
# 对数已经不在那条曲线上，真正贵的只剩下面 MAX_FRAGMENT_PAIRS 管的子串路径。
# 所以这个数**可以**放宽——但现在没有东西需要那份余量：本来要靠它容纳的那批
# 材料名，查下来是正常的 lang 键，资源包直接就能盖，根本不该走 VaultPatcher。
# 于是维持 1300 不动（当前 1172 对）。留着这段是为了记住「1300 背后的成本模型
# 已经不成立」，下次真有非 VaultPatcher 不可的东西撑爆它时，不用重新量一遍。
MAX_DYNAMIC_PAIRS = 1300

# 片段键（`'[Default: '` 这种带首尾空格的）才配用 `@`，而且要单独成块。上限卡死，
# 因为子串替换是「每次替换调用 × 该块全部对数」的开销。
MAX_FRAGMENT_PAIRS = 16

# 因上面这条预算而暂不随包发行的模块（文件留在 src/，一个字没删）。
# 配置界面那两块合计 3495 对，实测会把每串成本从 17 µs 推到 64 µs。
# **r14 正式版发过这两个文件**（拿 vr14 的发布产物解包比对过；vr14-beta2 里确实没有，
# 只看 beta 会得出相反的错结论）。安装器只覆盖不删除，所以停发的同时必须清理旧文件——
# 见 installer/install.{sh,ps1} 的 clean_legacy_config_ui / Clear-LegacyConfigUI。
PERF_HOLD = {
    'config_ui_generated.json': '3174 对，dynamic 全局扫表，代价见上方实测',
    'catnip_config_ui.json': '321 对，同上；与 config_ui_generated 是同一批界面',
}


def wants_substring(key, value):
    """这一对要不要保留子串模式（`@`）。两种算：

    1. **键带首尾空格**：`'[Default: '`、`'Farthest '` 这种，它是拼出来的长串里的
       一段，不可能与整串相等——摊平等于静默丢译文。自动识别，不用标注。
    2. **值写 `@@`**：显式声明「我确实需要子串替换，知道代价」。给的是
       「`Caledonia` 出现在 `Caledonia Roads` 里」这类键本身没空格、但确实只能靠
       子串命中的情况。出货时 `@@` 收敛成一个 `@`。

    两种都会被关进独立的片段块（见 flatten_at），并受 MAX_FRAGMENT_PAIRS 约束——
    子串替换是「每次替换调用 × 该块全部对数」的开销，能用精确匹配就别用它。
    """
    return key != key.strip() or str(value).startswith('@@')


def flatten_at(doc, name, stats):
    """把 dynamic 模块里的 `@值` 摊平成精确匹配，并统计对数。

    例外：`is_fragment` 的键留着 `@`，并集中到该 target_class 的**独立块**里。
    因为「非完整匹配」是**按块**触发的——一块里只要有一个 `@`，任何没被精确命中的
    字符串都要把这块的整张表过一遍。把 4 条片段单独关进一块，子串扫描就只跑 4 次
    而不是跟着 966 条一起跑；译文保住，开销可以忽略。

    只动出货副本，src/ 里的原文件不碰。返回新的块列表。
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
            sys.exit('❌ %s 的 %s 在该版数据库里没有记录——数据库过期了，重建它。'
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
            # 该版本里一个目标类都找不到：模块留着无害（匹配靠 target_class），
            # 但不能瞎填一个不存在的 jar 名。
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
    # 出货侧的硬闸：@ 一个都不许留，总对数不许超预算。
    for f in sorted(out.glob('*.json')):
        doc = json.loads(f.read_text(encoding='utf-8'))
        if not doc[0].get('dynamic'):
            continue
        for b in doc[1:]:
            prs = b.get('pairs') or []
            at = [x for x in prs if str(x.get('value', '')).startswith('@')]
            if not at:
                continue
            # 「非完整匹配」按块触发：块里只要有一个 @，这块的整张表都会被逐串扫。
            # 所以 @ 只许待在**整块都是片段键**的小块里。
            if len(at) != len(prs):
                sys.exit('❌ %s 有个块混着 %d 个 @ 和 %d 个精确对——@ 会让整块进'
                         '非完整匹配模式，逐串扫全块。把 @ 单独成块。'
                         % (f.name, len(at), len(prs) - len(at)))
            # 出货副本里已经不带 @@ 了，所以这里只能反查 src/ 的原始值来放行显式声明。
            src_path = MODULES / f.name
            if not src_path.is_file():
                sys.exit('❌ 出货树里有个 src/ 里不存在的模块 %s，而它还带着 @。'
                         '这多半是脏 build/ 的残留——先清干净再构建。' % f.name)
            src_doc = json.loads(src_path.read_text(encoding='utf-8'))
            explicit = {x['key'] for b2 in src_doc[1:] for x in (b2.get('pairs') or [])
                        if str(x.get('value', '')).startswith('@@')}
            bad = [x['key'] for x in at
                   if x['key'] == x['key'].strip() and x['key'] not in explicit]
            if bad:
                sys.exit('❌ %s 里 %r 用了 @ 但键没有首尾空格，也没写 @@ 显式声明。'
                         '整串就是这个键时精确匹配已经够用，@ 只会白花钱；'
                         '确实需要子串替换就把值写成 @@译文。' % (f.name, bad[0]))
            if len(at) > MAX_FRAGMENT_PAIRS:
                sys.exit('❌ %s 的片段块有 %d 条，超过上限 %d——子串替换是逐串开销，'
                         '别往这里堆。' % (f.name, len(at), MAX_FRAGMENT_PAIRS))
    # 这道闸以前只写在注释里（「出货侧另有闸复核包里确实没有它们」），实际并不存在：
    # src/rules/vaultpatcher.json 的 no_files 只 glob 了 blockui_legacy_labels.json，
    # verify_dist 的 vp_modules 是**下限**，漏进来照样过。而「漏回出货树」正是 r14
    # 那次掉帧事故的形状——停发的模块必须真的不在包里。
    # 单一真源：名单在这里，但拦它的闸在 src/rules/vaultpatcher.json 里（check.py 跑出货树）。
    # 两处不同步的话，往名单里加第三个模块时「出货侧有闸」就会静默变成假话——
    # 所以这里反过来查一遍：名单里每个名字都必须被某条 no_files 规则的 glob 盖住。
    import fnmatch
    rules = json.loads((ROOT / 'src' / 'rules' / 'vaultpatcher.json').read_text(encoding='utf-8'))
    globs = [r['glob'] for r in rules if r.get('kind') == 'no_files' and 'glob' in r]
    for hold in sorted(set(SRC_ONLY) | set(PERF_HOLD)):   # 别用 n：那是上面的模块计数
        target = 'vaultpatcher/modules/%s' % hold
        if not any(fnmatch.fnmatch(target, gl) for gl in globs):
            sys.exit('❌ %s 在不出货名单里，却没有任何 no_files 规则拦它。\n'
                     '   往 src/rules/vaultpatcher.json 补一条，否则「出货侧有闸」是假话。' % hold)
    leaked = sorted(n for n in list(SRC_ONLY) + list(PERF_HOLD) if (out / n).exists())
    if leaked:
        sys.exit('❌ 这些模块本不该出货，却出现在出货树里：%s\n'
                 '   （SRC_ONLY / PERF_HOLD 名单见本脚本顶部；多半是脏 build/ 残留）'
                 % '、'.join(leaked))
    if stats['pairs'] > MAX_DYNAMIC_PAIRS:
        top = '、'.join('%s %d 对' % r for r in sorted(stats['mods'], key=lambda r: -r[1])[:4])
        sys.exit('❌ dynamic 模块合计 %d 对，超过预算 %d 对。\n'
                 '   这张表是**每次替换调用**都要线性扫一遍的（见本脚本顶部实测），\n'
                 '   超预算就是全局掉帧。最大的几个：%s\n'
                 '   要么把它挪进 PERF_HOLD，要么先量过再改预算。'
                 % (stats['pairs'], MAX_DYNAMIC_PAIRS, top))
    # VaultPatcher 主配置里的 modules / mods 就是模块清单本身，可推导 → 现填。
    # 手维护的那份此刻已经漏了 6 个（我们自己加的 *_zh 模块全没进去）：
    # `load_all_modules` 为真时无害，一旦有人关掉它，这 6 个模块就静默失效。
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

    print('VaultPatcher 模块：%d 个（ATM10 %s 的 jar 名现填），主配置清单 %d 条'
          % (n, ver, len(names)))
    print('  dynamic 表合计 %d 对 / 预算 %d 对；摊平 @ 前缀 %d 个，去重 %d 对，'
          '片段键保留 @ 并单独成块 %d 条'
          % (stats['pairs'], MAX_DYNAMIC_PAIRS, stats['at'], stats['dedup'], stats['frag']))
    if PERF_HOLD:
        print('  因预算暂不出货 %d 个：%s'
              % (len(PERF_HOLD), '；'.join('%s（%s）' % kv for kv in sorted(PERF_HOLD.items()))))
    if nojar:
        print('  该版本里找不到目标类的 %d 个：%s' % (len(nojar), '、'.join(nojar)))


if __name__ == '__main__':
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    main(sys.argv[1], sys.argv[2])
