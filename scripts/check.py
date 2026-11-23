# -*- coding: utf-8 -*-
# atm10-zh-cn — All the Mods 10 简体中文汉化补丁「绿油油版」
# Copyright (C) 2026 星野夢華 (Hoshino Yumeka)
# SPDX-License-Identifier: GPL-3.0-or-later
"""发版前校验：`src/rules/*.json` 规则的解释器。

这里只提供检查器（`@checker('kind')`），按每条规则的 `kind` 分派。加同类规则只改 JSON，
加新检查器才改这里。废弃译名、豁免白名单这类会持续累积的数据都放在 JSON 里。
每条规则必须写 `why`，多数规则来自真实问题。

用法:
    python3 scripts/check.py [出货树]        # 缺省 build/common
"""
import json
import os
import re
import sys
from pathlib import Path

from paths import COMMON, SRC

ROOT = Path(__file__).resolve().parent.parent
RULES_DIR = SRC / 'rules'

# 查出货树（含全部生成物），默认 build/common。build_dist.sh 会传入每个版本合成好的树。
TREE = Path(sys.argv[1]) if len(sys.argv) > 1 else COMMON
PACK_DIR = TREE / 'resourcepacks' / 'ATM10汉化包'

CJK = re.compile(r'[一-鿿]')
CHECKERS = {}

# 有几条检查的前提是生成物（要读 mod jar）。没有 jar 的环境里只打一行提示。
# 生成之后的环节传 GATE_STRICT=1：这时前提不在说明生成器没产出，必须失败。
STRICT = (os.environ.get('GATE_STRICT') or '').strip() not in ('', '0')


def absent(what, hint):
    """前提缺失时的统一出口。

    返回该 yield 出去的话（strict 下），或 None（非 strict，只打一行 ℹ️）。
    调用方一律写成 `m = absent(...); if m: yield m; return`。
    """
    if STRICT:
        return ('%s没跑成：%s。设置了 GATE_STRICT，前提应已生成，'
                '缺失说明生成环节出了问题' % (what, hint))
    print('ℹ️ 跳过%s：%s' % (what, hint))
    return None


def checker(kind):
    def deco(fn):
        CHECKERS[kind] = fn
        return fn
    return deco


def need(rule, *fields):
    for f in fields:
        if f not in rule:
            raise KeyError('规则 %s 缺字段 %s' % (rule.get('id', '?'), f))
    return [rule[f] for f in fields]


def files(pattern):
    """出货树里 glob 命中的文件。"""
    return sorted(p for p in TREE.glob(pattern) if p.is_file())


def rel(p):
    try:
        return p.relative_to(TREE).as_posix()
    except ValueError:
        return p.relative_to(ROOT).as_posix()


# ────────────────────────────── 通用检查器 ──────────────────────────────

@checker('json_parses')
def _json_parses(rule):
    g, = need(rule, 'glob')
    hit = files(g)
    if not hit:
        yield 'glob %r 一个文件都没命中（规则失效了，比不加还危险）' % g
    for p in hit:
        try:
            json.loads(p.read_text(encoding='utf-8'))
        except Exception as e:
            yield '%s: JSON 解析失败: %s' % (rel(p), e)


@checker('no_files')
def _no_files(rule):
    """出货树里不许存在匹配该 glob 的文件（用来拦「本该删掉却还在生成」的产物）。"""
    g, = need(rule, 'glob')
    hit = files(g)
    for p in hit:
        yield '不该出现的文件 %s：%s' % (rel(p), rule['why'])


@checker('vp_no_single_word_keys')
def _vp_no_single_word(rule):
    """配置界面模块里不许出现单个词的键：这类词多半同时是枚举值。

    RFTools 把 `Ignored` / `Off` 这类界面词同时当枚举名反查，译了会抛异常（见
    vp-enum-protocol-values）。配置界面下拉框的值和条目标签一模一样，无法区分，整类不译。
    """
    mods, = need(rule, 'modules')
    for mod in mods:
        f = ROOT / 'src' / 'vaultpatcher' / 'modules' / mod
        if not f.is_file():
            continue
        doc = json.loads(f.read_text(encoding='utf-8'))
        for blk in doc[1:]:
            for pair in blk.get('pairs', []):
                if len(pair['key'].split()) < 2:
                    yield '%s 出现单词键 %r：%s' % (mod, pair['key'], rule['why'])


@checker('vp_no_key_prefix')
def _vp_no_key_prefix(rule):
    """键不许以这些前缀开头：以它们开头的是路径片段，不是界面文字。

    issue #3：structurize 建筑棒的类别路径（如 `craftsmanship/luxury`）同时用作面包屑、
    按钮 ID 和 `currentBluePrintMappingAtDepthCache` 的 Map 键，楼层行还会把 `路径:序号`
    存进隐藏 Text 控件再读回来查表。167 条 `/luxury → /豪华` 子串替换改写了 458 条路径
    里的 277 条，查表落空，`handleBlueprintCategory` 里 NPE 闪退。

    按钮上显示的是路径最后一段，用精确键就能译，所以以 `/` 开头的键一律不许有。
    """
    prefixes, = need(rule, 'prefixes')
    mods = sorted((ROOT / 'src' / 'vaultpatcher' / 'modules').glob('*.json'))
    if not mods:
        yield 'src/vaultpatcher/modules 下一个模块都没有（规则失效了，比不加还危险）'
    for f in mods:
        try:
            doc = json.loads(f.read_text(encoding='utf-8'))
        except Exception:                                          # noqa: BLE001
            continue
        if not isinstance(doc, list):
            continue
        for blk in doc[1:]:
            for pair in blk.get('pairs', []):
                k = pair.get('key', '')
                if any(k.startswith(p) for p in prefixes):
                    yield '%s 的键 %r 是路径片段：%s' % (f.name, k, rule['why'])


@checker('vp_forbidden_keys')
def _vp_forbidden_keys(rule):
    """有些字符串是行为标志，译了功能就坏，只能点名禁译。

    blockui 的 Alignment 用 `tag.contains("horizontal")` 判断对齐。'top horizontal' 译成
    '顶部水平' 后整个 blockui 的对齐失效，文字一律左对齐，上游的 textalign 也不生效。
    """
    keys, = need(rule, 'keys')
    ban = set(keys)
    for f in sorted((ROOT / 'src' / 'vaultpatcher' / 'modules').glob('*.json')):
        try:
            doc = json.loads(f.read_text(encoding='utf-8'))
        except Exception:                                          # noqa: BLE001
            continue
        if not isinstance(doc, list):
            continue
        for blk in doc[1:]:
            for pair in blk.get('pairs', []):
                if pair.get('key') in ban:
                    yield '%s 译了 %r：%s' % (f.name, pair['key'], rule['why'])


@checker('xml_parses')
def _xml_parses(rule):
    """出货的界面 XML 必须能解析。

    windowtownhall.xml 里同一个 <button> 有两个 textoffset 时，blockui 报
    「Can't parse xml at: …」，玩家右键市政厅就崩溃。XML 要等玩家打开界面才报错，所以在这里检查。
    """
    import xml.etree.ElementTree as ET
    g, = need(rule, 'glob')
    hit = files(g)
    if not hit:
        # 这些 XML 由 gen_literal_books.py 用 mod jar 生成，只运行 assemble.py 时没有。
        # 有 jar 却一个都没命中才是问题，所以按是否装过书来区分。
        base = TREE / 'resourcepacks' / 'ATM10汉化包' / 'assets'
        if not any((base / ns / 'gui').is_dir() for ns in ('minecolonies', 'structurize')):
            # 不接 GATE_STRICT：本包从 aafe85f 起不发界面 XML，0 个是预期状态。
            # 这条检查留着，将来再发 XML 时仍然有效。
            print('ℹ️ 跳过界面 XML 解析检查：本版不发界面 XML（见 aafe85f）')
            return
        yield 'glob %r 一个文件都没命中（规则失效了，比不加还危险）' % g
    for p in hit:
        try:
            ET.fromstring(p.read_bytes())
        except Exception as e:
            yield '%s: XML 解析失败: %s。%s' % (rel(p), e, rule['why'])


@checker('json_assert')
def _json_assert(rule):
    f, path, want = need(rule, 'file', 'path', 'equals')
    p = TREE / f
    if not p.is_file():
        yield '缺少 %s' % f
        return
    cur = json.loads(p.read_text(encoding='utf-8'))
    for step in path:
        cur = cur.get(step) if isinstance(cur, dict) else None
    if cur != want:
        yield '%s 的 %s 必须是 %r，实为 %r：%s' % (f, '.'.join(path), want, cur, rule['why'])


@checker('file_absent')
def _file_absent(rule):
    p, = need(rule, 'path')
    if (TREE / p).exists():
        yield '%s 不应存在：%s' % (p, rule['why'])


@checker('filename_prefix')
def _filename_prefix(rule):
    g, pre = need(rule, 'glob', 'prefix')
    msg = rule.get('message', '{path} 缺少前缀 {prefix}')
    # scope=repo 时 glob 相对仓库根，用来查 src/ 里的源文件命名（出货树里的文件名可能沿用上游原名）
    hit = (sorted(p for p in ROOT.glob(g) if p.is_file())
           if rule.get('scope') == 'repo' else files(g))
    if not hit:
        # glob 一个文件都没命中，说明源文件被挪走或删了，必须报错，否则检查静默失效。
        yield 'glob %r 一个文件都没命中（规则失效了，比不加还危险）' % g
    for p in hit:
        if not p.name.startswith(pre):
            yield msg.format(path=rel(p), prefix=pre)


@checker('js_no_duplicate_decl')
def _js_no_duplicate_decl(rule):
    """同一批 KubeJS 脚本之间不许有重名的顶层声明。

    client_scripts 共用一个全局作用域。两个文件都写 `const $Component = Java.loadClass(...)` 时，
    第二个抛 `TypeError: redeclaration of const $Component`，整批客户端脚本都失效。

    按顶格（第 0 列）声明检测，会把 IIFE 里的名字也算进来，宁可多报。
    """
    g, = need(rule, 'glob')
    hit = files(g)
    if len(hit) < 2:
        m = absent('「客户端脚本不许重名声明」', '%r 只命中 %d 个文件，凑不出两两比较'
                   % (g, len(hit)))
        if m:
            yield m
        return
    decl = re.compile(r'^(?:const|let|var|function)\s+([A-Za-z_$][\w$]*)')
    seen = {}
    for p in hit:
        for ln in p.read_text(encoding='utf-8').splitlines():
            m = decl.match(ln)          # 顶格才算：match 而不是 search
            if not m:
                continue
            name = m.group(1)
            if name in seen and seen[name] != rel(p):
                yield ('%s 与 %s 都在顶层声明了 %s。KubeJS 客户端脚本共用一个作用域，'
                       '第二个会抛 redeclaration，整批脚本加载失败'
                       % (seen[name], rel(p), name))
            seen.setdefault(name, rel(p))


@checker('js_no_const_inside_block')
def _js_no_const_inside_block(rule):
    """`try {}` / `if {}` / `for {}` 这类普通块内部不许 `const`，只许赋值。

    KubeJS 的 Rhino 把块里的 const 提升成函数作用域的 var，执行到声明时抛
    `TypeError: redeclaration of var <名字>`。加载阶段不报错，写在事件回调里就是进游戏没有效果。

    函数体与回调体顶层的 const 是安全的，上游几十处都这样写。所以只拦最内层 `{` 不是
    函数或箭头函数开的那种。
    """
    g, = need(rule, 'glob')
    hit = files(g)
    if not hit:
        m = absent('「块里不许 const」', '%r 一个文件都没命中' % g)
        if m:
            yield m
        return
    decl = re.compile(r'^[\t ]*const\s+([\w$]+)')
    # 这一行开出来的块算不算「函数体」：箭头、function、以及 `get x() {` 这类方法。
    funcish = re.compile(r'=>|\bfunction\b')
    for p in hit:
        stack = []                      # 每层一个布尔：True = 函数体
        for i, raw in enumerate(p.read_text(encoding='utf-8').splitlines(), 1):
            ln = raw.split('//')[0]     # 注释里的花括号不算（本文件注释里就有 `try {}`）
            m = decl.match(raw)
            if m and stack and not stack[-1]:
                yield ('%s:%d 在块内部 `const %s`，KubeJS 的 Rhino 执行到这里会抛 '
                       'redeclaration of var。'
                       '把声明提到函数体顶层，块里只赋值' % (rel(p), i, m.group(1)))
            kind = bool(funcish.search(ln))
            for ch in ln:
                if ch == '{':
                    stack.append(kind)
                elif ch == '}' and stack:
                    stack.pop()


@checker('lang_value_forbidden')
def _lang_value_forbidden(rule):
    """lang 文件里，键匹配 key_regex 的条目，值不许匹配 value_regex。

    issue #8：tooltip 不断行，值里的 `\\n` 按 U+000A 查字形，unifont 画成写着「LF」的方框。
    上游 en_us 里就有这些换行，升版重导上游译文时容易带回来。
    """
    g, kre, vre = need(rule, 'glob', 'key_regex', 'value_regex')
    msg = rule.get('message', '{key}: 值里不许出现 {value_regex}')
    krx, vrx = re.compile(kre), re.compile(vre)
    hit = files(g)
    if not hit:
        yield 'glob %r 一个文件都没命中（规则失效了，比不加还危险）' % g
    for p in hit:
        doc = json.loads(p.read_text(encoding='utf-8'))
        watched = [k for k in doc if krx.search(k)]
        if not watched:
            # 键被上游改名或文件被换掉时规则不再匹配，必须报错，否则看起来和「查过了没问题」一样。
            yield '%s: key_regex %r 一个键都没匹配到（规则失效了，比不加还危险）' % (rel(p), kre)
        for k in watched:
            if vrx.search(doc[k]):
                yield '%s: %s' % (rel(p), msg.format(key=k, value_regex=vre))


@checker('forbidden_text')
def _forbidden_text(rule):
    terms, = need(rule, 'terms')
    msg = rule.get('message', '含禁用词 "{term}"')
    allow = tuple(rule.get('allow_paths', []))
    skip_dirs = set(rule.get('skip_dirs', []))
    skip_suf = tuple(rule.get('skip_suffixes', []))
    base = ROOT if rule.get('scope') == 'repo' else TREE
    for p in base.rglob('*'):
        if not p.is_file() or skip_dirs & set(p.parts):
            continue
        r = p.relative_to(base).as_posix()
        if allow and r.endswith(allow):
            continue
        if p.suffix in skip_suf:
            continue
        try:
            txt = p.read_text(encoding='utf-8')
        except Exception:
            continue
        for t in terms:
            if t in txt:
                yield '%s: %s' % (r, msg.format(term=t))


# ─────────────────────────── VaultPatcher 检查器 ───────────────────────────

def vp_modules():
    out = []
    for p in sorted((TREE / 'vaultpatcher' / 'modules').glob('*.json')):
        try:
            out.append((p, json.loads(p.read_text(encoding='utf-8'))))
        except Exception:
            out.append((p, None))
    return out


def vp_pairs(only_risky=False):
    """产出 (文件名, target_class, 原文, 译文)。

    `only_risky`：只要可能命中 McJtyLib 枚举常量池的块，无 target_class 的
    全局替换，或定向到 mcjty.* 的非 client 类（枚举/协议类所在地）。
    定向到具体 GUI/Screen 类的同名显示标签（形状卡的 Solid）是安全的。
    """
    for p, mod in vp_modules():
        if not isinstance(mod, list):
            continue
        for blk in mod:
            if not isinstance(blk, dict):
                continue
            tcs = blk.get('target_class') or []
            if only_risky:
                risky = (not tcs) or any(
                    c.startswith('mcjty.') and '.client.' not in c for c in tcs)
                if not risky:
                    continue
            for pair in blk.get('pairs', []):
                yield p.name, tcs, pair.get('key', ''), pair.get('value', '')


@checker('vp_shape')
def _vp_shape(rule):
    for p, mod in vp_modules():
        if mod is None:
            yield '%s: JSON 解析失败' % p.name
        elif not isinstance(mod, list):
            yield '%s: 顶层必须是数组' % p.name
        else:
            for blk in mod:
                if not isinstance(blk, dict):
                    yield '%s: 模块元素必须是对象' % p.name


@checker('vp_pair_key_in')
def _vp_pair_key_in(rule):
    vals, = need(rule, 'values')
    vals = set(vals)
    msg = rule.get('message', '禁止替换 {key}')
    for name, tcs, k, v in vp_pairs(rule.get('only_risky_blocks', False)):
        if k.strip() in vals:
            where = '全局替换' if not tcs else '定向 %s' % tcs
            yield '%s: %s' % (name, msg.format(key=repr(k), value=repr(v), where=where))


@checker('vp_pair_regex')
def _vp_pair_regex(rule):
    pat, = need(rule, 'key_regex')
    rx = re.compile(pat)
    msg = rule.get('message', '原文 {key} 不许被替换成 {value}')
    for name, _tcs, k, v in vp_pairs():
        if not rx.match(k):
            continue
        if rule.get('value_has_cjk') and not CJK.search(v):
            continue
        yield '%s: %s' % (name, msg.format(key=repr(k), value=repr(v)))


@checker('vp_server_global')
def _vp_server_global(rule):
    lst, = need(rule, 'list')
    names = [l.strip() for l in (ROOT / lst).read_text(encoding='utf-8').splitlines()
             if l.strip() and not l.startswith('#')]
    for name in names:
        p = TREE / 'vaultpatcher' / 'modules' / ('%s.json' % name)
        if not p.exists():
            yield '%s: 清单里的 %s.json 不存在' % (lst, name)
            continue
        for blk in json.loads(p.read_text(encoding='utf-8')):
            if isinstance(blk, dict) and 'pairs' in blk and not blk.get('target_class'):
                bad = [pr['key'] for pr in blk['pairs']
                       if not pr.get('key', '').startswith(' ')]
                if bad:
                    yield ('%s.json: 服务端模块含全局替换 %s'
                           '（会污染服务端数据，禁止入服务端清单）' % (name, bad))


@checker('vp_keybind_names')
def _vp_keybind_names(rule):
    g, = need(rule, 'data_glob')
    data = sorted(ROOT.glob(g))
    if not data:
        # 不看 GATE_STRICT，一律失败：前提 versions/db/*/keybinds.json 是入库数据，
        # 而 protect.py 只保护 src/。
        yield ('按键注册名检查没跑成：%s 一个都没命中。这些文件是入库的，'
               '不是生成物，缺了说明被删/被挪走了（跑 scan_keybinds.py 重建）' % g)
        return
    names = set()
    for p in data:
        d = json.loads(p.read_text(encoding='utf-8'))
        names |= set(d.get('names', {}))
        names |= set(d.get('name_atoms', {}))
    msg = rule.get('message', '原文 {key} 是按键注册名')
    for name, _tcs, k, v in vp_pairs():
        if k in names:
            yield '%s: %s' % (name, msg.format(key=repr(k), value=repr(v)))


@checker('vp_value_conflict')
def _vp_value_conflict(rule):
    """同一个类、同一条原文、同一种匹配模式，只许有一种译文。

    value 以 `@` 开头是子串替换，其余是全串匹配（见 compliance/check_minecolonies_paths.py），
    所以 `Fortress→要塞` 与 `Fortress→@要塞` 是两种模式，可以同时存在。同模式下有两句译文时，
    哪句生效取决于模块加载顺序与表内顺序，例如 rftoolsbase.json 与 rftoolsbase_filter_zh.json
    给 GuiFilterModule 的三条原文各写了一套（「忽略耐久值」与「忽略损伤值」）。
    """
    seen = {}
    total = 0
    for name, tcs, k, v in vp_pairs():
        total += 1
        sub = v.startswith('@')
        scope = tuple(sorted(tcs)) if tcs else ('<全局替换>',)
        seen.setdefault((scope, k, sub), {}).setdefault(v[1:] if sub else v, set()).add(name)
    if not total:
        yield 'vaultpatcher/modules 一条 pair 都没读到（规则失效了，比不加还危险）'
        return
    for (scope, k, sub), vs in sorted(seen.items(), key=lambda kv: (kv[0][1], kv[0][0])):
        if len(vs) < 2:
            continue
        where = ' / '.join('%r ← %s' % (t, ','.join(sorted(fs))) for t, fs in sorted(vs.items()))
        yield ('%s 的原文 %r（%s）有 %d 种译文：%s'
               % (scope[0], k, '子串替换' if sub else '全串匹配', len(vs), where))


@checker('term_binding')
def _term_binding(rule):
    """英文词与中文词双向绑定：原文出现其一，译文就必须出现其二，反之亦然。

    用来拦两个相似名字被对调，单看一条译文是通顺的。例如 Extended（AE2扩展，mcmod 作
    ME扩展样板供应器）被译成「拓充」，Expanded（ExpandedAE，jar 自带中文作拓充样板供应器）
    被译成「拓展」。
    """
    terms, = need(rule, 'terms')
    scope = rule.get('files')            # 文件名清单。缺省 = 全表
    hits = {t['en']: 0 for t in terms}
    total = 0
    for name, _tcs, k, v in vp_pairs():
        if scope and name not in scope:
            continue
        total += 1
        for t in terms:
            in_en = t['en'].lower() in k.lower()
            in_zh = t['zh'] in v
            if in_en:
                hits[t['en']] += 1
            if in_en and not in_zh:
                yield ('%s: 原文含 %r，译文 %r 里却没有 %r' % (name, t['en'], v, t['zh']))
            elif in_zh and not in_en:
                yield ('%s: 译文含 %r，原文 %r 里却没有 %r' % (name, t['zh'], k, t['en']))
    if not total:
        yield ('files %r 一条 pair 都没读到（规则失效了，比不加还危险）'
               % (scope if scope else 'vaultpatcher/modules/*.json',))
        return
    for e, c in sorted(hits.items()):
        if not c:
            yield ('原文里一次都没出现过 %r：上游改了措辞，或这些 pair 被挪走了，'
                   '这条绑定已不起作用' % e)


# ─────────────────────────────── 资源包检查器 ───────────────────────────────

@checker('tiered_family')
def _tiered_family(rule):
    """同一族的 N 档：词干必须完全相同，档位后缀写法必须全表统一。

    AllTheCompressed 有 1796 条这样的键（`_1x`..`_9x` 九档一族），出现过「1x荒古石」
    「荒古石 6x」「三重压缩荒古石」混用，词干也会不一致（振动合金块与脉冲合金块）。
    键名带档位号，词干和后缀都能推导出来。
    """
    g, kr, tpl = need(rule, 'glob', 'key_regex', 'value_template')
    rx = re.compile(kr)
    hit = files(g)
    if not hit:
        yield 'glob %r 一个文件都没命中（规则失效了，比不加还危险）' % g
        return
    total = 0
    for p in hit:
        try:
            d = json.loads(p.read_text(encoding='utf-8'))
        except Exception as e:
            yield '%s: JSON 解析失败: %s' % (rel(p), e)
            continue
        fam = {}
        for k, v in sorted(d.items()):
            m = rx.match(k)
            if not m:
                continue
            total += 1
            fam.setdefault(m.group('stem'), []).append((k, m.group('tier'), v))
        for stem, items in sorted(fam.items()):
            roots = {}
            for k, tier, v in items:
                tail = tpl.format(tier=tier)
                if not v.endswith(tail):
                    yield ('%s: %s 的译文 %r 不是「词干+%r」的写法'
                           % (rel(p), k, v, tail))
                    continue
                roots.setdefault(v[:-len(tail)], []).append(k)
            if len(roots) > 1:
                yield ('%s: %s 这一族 %d 档的词干不一致：%s'
                       % (rel(p), stem, len(items),
                          '、'.join('%r(%s)' % (r, ks[0].rsplit('.', 1)[-1])
                                    for r, ks in sorted(roots.items()))))
    if not total:
        yield 'key_regex %r 一个键都没命中（规则失效了，比不加还危险）' % kr


@checker('gui_choice_ascii')
def _gui_choice_ascii(rule):
    g, = need(rule, 'glob')
    msg = rule.get('message', "choice('{value}') 必须保持英文")
    hit = files(g)
    if not hit:
        # glob 一个文件都没命中，说明源文件被挪走或删了，必须报错，否则检查静默失效。
        yield 'glob %r 一个文件都没命中（规则失效了，比不加还危险）' % g
    for p in hit:
        text = p.read_text(encoding='utf-8', errors='replace')
        for m in re.finditer(r"choice\(\s*'([^']*)'", text):
            if CJK.search(m.group(1)):
                yield '%s: %s' % (rel(p), msg.format(value=m.group(1)))


@checker('format_safety')
def _format_safety(rule):
    snap, = need(rule, 'snapshot')
    f = ROOT / snap
    if not f.exists():
        m = absent('占位符检查', '还没有 %s（gen_format_snapshot.py 要读 mod jar 才能产出）' % snap)
        if m:
            yield m
        return
    up = json.loads(f.read_text(encoding='utf-8'))
    allow = set(rule.get('allow', {}))
    TOK = re.compile(r'%(?:(\d+)\$)?(\d+)?(?:\.(\d+))?([a-zA-Z%])')
    TRAIL = re.compile(r'(?<!%)%$')
    SECT_OK = set('0123456789abcdefklmnorABCDEFKLMNOR')

    def profile(s):
        prof, seq = {}, 0
        for m in TOK.finditer(s):
            if m.group(4) == '%':
                continue
            if m.group(1):
                idx = int(m.group(1))
            else:
                seq += 1
                idx = seq
            prof.setdefault(idx, m.group(4))
        return prof

    def bad_sect(s):
        return {m.group(1) for m in re.finditer('§(.)', s) if m.group(1) not in SECT_OK}

    lang = list(PACK_DIR.rglob('lang/zh_cn.json'))
    lang += list((TREE / 'kubejs' / 'assets').rglob('lang/zh_cn.json'))
    for p in lang:
        r = rel(p)
        try:
            d = json.loads(p.read_text(encoding='utf-8'))
        except Exception:
            continue                       # json_parses 那条已经报过了
        for k, zh in d.items():
            if not isinstance(zh, str) or k == '_comment' or k in allow:
                continue
            en = up.get(k)
            if en is None:
                continue
            pe, pz = profile(en), profile(zh)
            extra = sorted(set(pz) - set(pe))
            if extra:
                yield ('%s: %s 译文多出英文没有的占位符 %s（运行时参数不足会抛 '
                       'TranslatableFormatException）\n      en=%r\n      zh=%r'
                       % (r, k, extra, en, zh))
            down = sorted(i for i in set(pe) & set(pz) if pe[i] == 's' and pz[i] != 's')
            if down:
                yield ('%s: %s 第 %s 个参数把 %%s 降级成了 %%%s（类型对不上，必炸）'
                       '\n      en=%r\n      zh=%r' % (r, k, down, pz[down[0]], en, zh))
            if TRAIL.search(zh) and not TRAIL.search(en):
                yield '%s: %s 译文以裸 %% 结尾（MC 会当非法格式抛异常）\n      zh=%r' % (r, k, zh)
            new_sect = bad_sect(zh) - bad_sect(en)
            if new_sect:
                yield ('%s: %s 非法 § 颜色码 %s（§ 后面那个字会被渲染器吞掉）'
                       '\n      zh=%r' % (r, k, sorted(new_sect), zh))


@checker('pb_single_source')
def _pb_single_source(rule):
    lang, script = need(rule, 'lang', 'script')
    lp, sp = TREE / lang, TREE / script
    if not lp.is_file():
        yield '缺少 %s' % lang
        return
    pack = json.loads(lp.read_text(encoding='utf-8'))
    if not sp.exists():
        m = absent('蜂名漂移检查', '%s 是生成物，尚未生成' % script)
        if m:
            yield m
        return
    m = re.search(r'const PB_ID2ZH = (\{.*?\});', sp.read_text(encoding='utf-8'), re.S)
    if not m:
        yield '%s: 缺 PB_ID2ZH（必须由 gen_pb_hanhua.py 生成）' % script
        return
    for base, zh in json.loads(m.group(1)).items():
        expect = pack.get('entity.productivebees.%s_bee' % base,
                          pack.get('entity.productivebees.%s' % base))
        if expect is not None and expect != zh:
            yield ('蜂名漂移: %s 脚本=%r 资源包=%r'
                   '（真源是资源包，请重跑 gen_pb_hanhua.py）' % (base, zh, expect))


# ─────────────────────────────── 任务书检查器 ───────────────────────────────

@checker('snbt_blocks_parse')
def _snbt_blocks_parse(rule):
    """delta 文件必须能被生成器的块解析器完整读通。

    按行 sort 会把 129 个多行数组打散成 513 个游离的 `\t\t""`，按行正则匹配不上就会放过。
    这里直接 import 生成器用的解析器：两份解析器结论不同时，检查会通过而生成阶段失败。
    """
    from gen_quest_lang_patches import SnbtShapeError, blocks

    g, = need(rule, 'glob')
    # 只查结构，不查有没有键：gen_quest_lang_patches.py 会按原名发 `{\n}` 空文件覆盖玩家
    # 硬盘上的旧 delta（安装器只覆盖不删除），生成之后 35 个 delta 都是空的。
    hit = files(g)
    if not hit:
        yield 'glob %r 一个文件都没命中（规则失效了，比不加还危险）' % g
        return
    for p in hit:
        try:
            blocks(p)
        except SnbtShapeError as e:
            yield '%s' % e


@checker('snbt_no_dup_keys')
def _snbt_no_dup_keys(rule):
    g, = need(rule, 'glob')
    # 上游文件缩进不统一（同一个 chapters/ 里有 tab 也有 4 空格），只认 tab 会漏掉整个文件的键
    KEY = re.compile(r'^[\t ]+([A-Za-z0-9_.]+):\s*(.*)$')
    seen = {}
    hit = files(g)
    if not hit:
        # 一个文件都没命中，说明任务书 delta 目录被挪走、改名或生成步骤漏跑，必须报错。
        yield 'glob %r 一个文件都没命中（规则失效了，比不加还危险）' % g
    for p in hit:
        lines = p.read_text(encoding='utf-8').split('\n')
        i = 0
        while i < len(lines):
            m = KEY.match(lines[i])
            if m:
                k, rest = m.group(1), m.group(2)
                bal = rest.count('[') - rest.count(']')
                while bal > 0 and i + 1 < len(lines):        # 跨行数组
                    i += 1
                    bal += lines[i].count('[') - lines[i].count(']')
                if k in seen:
                    yield ('任务书 delta 重复键 %s：%s 与 %s 都定义了'
                           '（哪份生效取决于合并顺序，必须只保留一份）'
                           % (k, seen[k], p.name))
                seen[k] = p.name
            i += 1


# ─────────────────────────────── 解释器 ───────────────────────────────

def load_rules():
    if not RULES_DIR.is_dir():
        sys.exit('❌ 规则目录不存在: %s' % RULES_DIR)
    rules = []
    for f in sorted(RULES_DIR.glob('*.json')):
        try:
            got = json.loads(f.read_text(encoding='utf-8'))
        except Exception as e:
            sys.exit('❌ 规则文件 %s 解析失败: %s' % (f.name, e))
        if not isinstance(got, list):
            sys.exit('❌ 规则文件 %s 顶层必须是数组' % f.name)
        for r in got:
            r['_file'] = f.name
            rules.append(r)
    ids = [r.get('id') for r in rules]
    dup = sorted({i for i in ids if ids.count(i) > 1})
    if dup:
        sys.exit('❌ 规则 id 重复: %s' % dup)
    for r in rules:
        for k in ('id', 'kind', 'why'):
            if not r.get(k):
                sys.exit('❌ %s 里有规则缺 %s 字段: %r' % (r['_file'], k, r))
        if r['kind'] not in CHECKERS:
            # 认不出的 kind 必须失败，否则拼错一个字母规则就静默失效
            sys.exit('❌ 规则 %s 的 kind %r 没有对应的检查器。已有: %s'
                     % (r['id'], r['kind'], ' '.join(sorted(CHECKERS))))
    return rules


def main():
    if not TREE.is_dir():
        sys.exit('❌ 出货树不存在: %s\n'
                 '   先跑: python3 scripts/assemble.py && ./scripts/generate_all.sh' % TREE)
    rules = load_rules()
    errors = []
    for r in rules:
        try:
            errors += ['[%s] %s' % (r['id'], e) for e in CHECKERS[r['kind']](r)]
        except Exception as e:
            errors.append('[%s] 检查器自身出错: %r' % (r['id'], e))
    if errors:
        print('❌ 校验失败，共 %d 处：' % len(errors))
        for e in errors:
            print('  -', e)
        sys.exit(1)
    print('✅ %d 条规则全部通过：%s'
          % (len(rules), ' '.join(r['id'] for r in rules)))


if __name__ == '__main__':
    main()
