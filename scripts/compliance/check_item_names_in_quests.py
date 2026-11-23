#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# atm10-zh-cn — All the Mods 10 简体中文汉化补丁「绿油油版」
# Copyright (C) 2026 星野夢華 (Hoshino Yumeka)
# SPDX-License-Identifier: GPL-3.0-or-later
"""任务书里提到某件物品时，必须用玩家在 JEI 里搜得到的名字。

例如任务书写「XP 果冻豆」「XP 固化机」「空灵魂宝石」「挡光玻璃」，物品名是「经验果冻宝宝」
「经验固化器」「灵魂宝石（空）」「遮光玻璃」。check_bee_names_in_quests.py 只查 productivebees，
这里查 NAMESPACES 里的模组。

Industrial Foregoing 的无限工具档位（差 / 普通 / 罕见 / 稀有 / 史诗 / 传说 / 神器）不是物品名，
整个命名空间放进物品名扫描会让 Plastic、Speed 等常用词误报。这类术语按「目标任务键 → jar 语言键」
精确绑定，参照值从最终生效的语言表取，任务键或参照键消失都失败。

## 判定

英文原文出现某件物品的英文名，中文里就必须出现它的中文名。英文名取模组 jar 的 `en_us.json`，
中文名取出货树里实际生效的那份（`resourcepacks/ATM10汉化包/assets/<ns>/lang/zh_cn.json` 优先，
没有才用 jar 自带的）。

- 最长匹配优先：命中 `Soul Gem` 时，同一处也命中了包含它的更长名字（`Empty Soul Gem`），这次不算。
- 命中处前面紧跟大写词的不算独立提及，例如 `Wither Skeleton Skull` 里的 `Skeleton Skull`（长名是
  原版物品，不在表里）、`Glass Divination Rod` 里的 `Divination Rod`。`the cheapest Divination Rod`
  前一个词是小写，照常判断。一段文字里所有命中都被挡掉，才算没有提及。
- 区分大小写：正文里 `call down a falling star` 不是 Relics 的遗物 `Falling Star`。上游把物品名
  写成小写时会漏判，漏判好过误报。
- 一个英文名对应多件东西时（`Rotten Egg` 在 mob_grinding_utils 和 iceandfire 里各有一件），命中
  任意一个中文名就算通过。候选中文名和「更长的名字」都取全包所有模组的并集，`NAMESPACES` 只决定
  哪些模组的名字要强制检查。

按 jar 内容找 jar：`occultism*.jar` 在 ATM10 里匹配到两个文件，其中一个没有 `assets/`，按文件名
排序取最后一个会拿到空的那个。这里扫描所有 jar，取真正有这个命名空间 lang 的那个，一个都没有就失败。

拿不到 jar、读不到英文表、找不到中文表、上游英文任务书目录不在、某个模组一对名字都配不上、
绑定的任务键或语言键消失、两棵树一个键都对不上，都按失败处理。

用法:
    python3 scripts/compliance/check_item_names_in_quests.py <mods 目录> <上游树> <出货树>
"""
import json
import re
import sys
import zipfile
from pathlib import Path

# 纳入检查的命名空间。加模组前先运行一遍，报出的必须全是真错误，否则说明该模组的名字表
# 不适合当判据（例如物品名是常用词）。
NAMESPACES = ('mob_grinding_utils', 'occultism', 'relics')

# 不能全局扫的界面术语：限定到具体任务键，再从 jar 英文和最终生效中文里动态取值。
# keys 的顺序也是任务正文应使用的顺序。
QUEST_LANG_BINDINGS = {
    'quest.41E8550FC36ABCA5.quest_desc': {
        'label': 'Industrial Foregoing 无限工具档位',
        'namespace': 'industrialforegoing',
        'keys': tuple('text.industrialforegoing.tooltip.infinitydrill.%s' % tier for tier in (
            'poor', 'common', 'uncommon', 'rare', 'epic', 'legendary', 'artifact')),
    },
}

PACK_ZH = 'resourcepacks/ATM10汉化包/assets/%s/lang/zh_cn.json'
EN_QUESTS = 'config/ftbquests/quests/lang/en_us'
ZH_QUESTS = 'config/ftbquests/quests/lang/zh_cn'
NAME_KEY = ('item.', 'block.', 'fluid.', 'entity.')
KEY = re.compile(r'^[\t ]+([A-Za-z0-9_.]+):\s*(.*)$')
# 太短的英文名（Bee、Jar、Egg 之类）拿去全文搜必然满地假阳性，判不了就不判。
MIN_LEN = 6


def die(msg):
    print('❌ %s' % msg)
    sys.exit(1)


def load_json(z, name):
    try:
        return json.loads(z.read(name), strict=False)   # 少数 mod 的 lang 里有裸控制符
    except Exception:
        return None


def pack_zh(tree):
    """我们资源包里每个命名空间的 zh_cn（盖过模组自带）。"""
    out = {}
    for p in sorted(Path(tree).glob(PACK_ZH % '*')):
        try:
            out[p.parts[-3]] = json.loads(p.read_text(encoding='utf-8'))
        except Exception as e:
            die('%s 解析失败：%s' % (p, e))
    return out


def collect(mods, tree):
    """扫全包，收物品名及任务键绑定的界面术语。"""
    ours = pack_zh(tree)
    names, enforced = {}, set()
    seen_ns = set()
    binding_values = {
        qkey: {key: set() for key in spec['keys']}
        for qkey, spec in QUEST_LANG_BINDINGS.items()
    }
    for jar in sorted(Path(mods).glob('*.jar')):
        try:
            z = zipfile.ZipFile(jar)
        except Exception:
            continue
        with z:
            for n in z.namelist():
                if not n.endswith('/lang/en_us.json'):
                    continue
                ns = n.split('/')[1]
                en = load_json(z, n)
                if not isinstance(en, dict):
                    continue
                zh = dict(load_json(z, n.replace('en_us', 'zh_cn')) or {})
                zh.update(ours.get(ns, {}))       # 我们的包盖在模组自带之上
                seen_ns.add(ns)
                for qkey, spec in QUEST_LANG_BINDINGS.items():
                    if ns != spec['namespace']:
                        continue
                    for key in spec['keys']:
                        e = en.get(key)
                        if not (isinstance(e, str) and e.strip()):
                            continue
                        c = zh.get(key)
                        if not (isinstance(c, str) and c.strip()):
                            die('%s 的参照键 %s 没有最终生效的中文值' % (spec['label'], key))
                        binding_values[qkey][key].add((e, c))
                for k, e in en.items():
                    # count==2 → 只要 item.<ns>.<id> 这种纯名字键，
                    # 把 .tooltip_1 / .jei.info 这类描述排掉
                    if not (k.startswith(NAME_KEY) and k.count('.') == 2):
                        continue
                    c = zh.get(k)
                    if not (isinstance(e, str) and len(e) >= MIN_LEN):
                        continue
                    if '%' in e or not WORD.match(e):
                        continue          # `%s Spawner` 这类格式串不是名字
                    if not (isinstance(c, str) and c.strip()):
                        continue
                    names.setdefault(e, set()).add(c)
                    if ns in NAMESPACES:
                        enforced.add(e)
    missing = [ns for ns in NAMESPACES if ns not in seen_ns]
    if missing:
        die('%s 里没有任何 jar 含这些命名空间的 en_us.json：%s，无法检查'
            % (mods, '、'.join(missing)))
    if not enforced:
        die('要检查的命名空间（%s）一对「英文名→中文名」都没配上，无法判断'
            % '、'.join(NAMESPACES))

    bindings = {}
    for qkey, spec in QUEST_LANG_BINDINGS.items():
        pairs = []
        for key in spec['keys']:
            got = binding_values[qkey][key]
            if not got:
                die('%s 里找不到 %s 的英文语言键 %s，术语参照已经失效'
                    % (mods, spec['label'], key))
            if len(got) != 1:
                die('%s 的语言键 %s 在 jar 中有互相冲突的值：%s'
                    % (spec['label'], key, sorted(got)))
            pairs.append(next(iter(got)))
        if len({e for e, _ in pairs}) != len(pairs):
            die('%s 的英文参照值发生重复，无法逐档核对：%s'
                % (spec['label'], [e for e, _ in pairs]))
        bindings[qkey] = (spec['label'], pairs)
    return names, enforced, bindings


def quest_text(root):
    """把一棵任务书语言树读成 键 -> 全文（多行数组拼成一串，只为查词）。"""
    out = {}
    for p in sorted(Path(root).rglob('*.snbt*')):
        cur = None
        for line in p.read_text(encoding='utf-8', errors='replace').split('\n'):
            m = KEY.match(line)
            if m:
                cur = m.group(1)
                out[cur] = out.get(cur, '') + m.group(2)
            elif cur:
                out[cur] = out.get(cur, '') + line
    return out


# 颜色码和转义换行会破坏词边界：`&8Wither` 里 `8` 和 `W` 都是 \w，`\bWither` 匹配不上，长名
# 匹配不到，短名 `Skeleton Skull` 就会误报。匹配前先换成空格（偏移会变，下面一律在规范化后的
# 文本上算）。非法颜色码也要去掉：ATM 的任务书里有 `&zRainbow Plating`，只按合法表处理的话
# `z` 会贴着 `Rainbow`，导致漏判。
NOISE = re.compile(r'[&§](?:#[0-9A-Fa-f]{6}|[0-9A-Za-z])|\\+n')
# 命中处前面紧跟的大写词，说明正文说的是一件更长名字的东西，不是本条。
LEADING_CAP = re.compile(r'[A-Z][a-zA-Z]*\s+$')


def norm(text):
    return NOISE.sub(' ', text)


WORD = re.compile(r'\w+')
SPACE = re.compile(r'[\s\u00a0]+')


def ordered_terms(text, terms):
    """terms 是否都作为独立词按顺序出现。中文档位也必须是独立列表项。"""
    pos = 0
    for term in terms:
        m = re.search(r'(?<!\w)%s(?!\w)' % re.escape(term), text[pos:])
        if not m:
            return False
        pos += m.end()
    return True


def found_names(text, by_first):
    """正文里独立提到的所有名字。

    全包两万条名字乘八千段任务文本，逐条跑正则要几分钟，所以按首词建索引：只在每个单词的位置上，
    试以这个词开头的名字。

    最长匹配按出现位置算：`The cheapest Divination Rod, the Glass Divination Rod.` 里两个名字都出现了，
    只有被更长匹配的区间覆盖的那次出现不算。按整段算的话，短名会被长名吃掉而漏判。
    """
    spans = []
    for m in WORD.finditer(text):
        for name in by_first.get(m.group(0), ()):
            s = m.start()
            e = s + len(name)
            if not text.startswith(name, s):
                continue
            if e < len(text) and (text[e].isalnum() or text[e] == '_'):
                continue                      # 右边界：Piglin 不算命中 Piglins
            spans.append((s, e, name))
    hits = set()
    for s, e, name in spans:
        if any(s2 <= s and e2 >= e and e2 - s2 > e - s for s2, e2, _ in spans):
            continue                          # 这一次出现嵌在更长的名字里
        if LEADING_CAP.search(text[max(0, s - 40):s]):
            continue                          # 更长的名字不在表里（原版物品等）时的兜底
        hits.add(name)
    return hits


def mismatches(names, enforced, up, ours, common):
    by_first = {}
    for e in names:
        by_first.setdefault(WORD.match(e).group(0), []).append(e)
    bad = []
    for k in common:
        text, mine = norm(up[k]), ours[k]
        # 「更长的名字」要拿全包的名字表来排，只看被检查的那几个模组会漏
        for e in found_names(text, by_first):
            if e not in enforced:
                continue
            cs = names[e]
            # 比较时抹掉空白：物品名「16k 存储元件」与正文里的「16k存储元件」
            # 是同一个东西，不该因为一个空格判红
            if not any(SPACE.sub('', c) in SPACE.sub('', mine) for c in cs):
                bad.append((k, e, '／'.join(sorted(cs))))
    return bad


def binding_mismatches(bindings, up, ours):
    """限定任务内的术语序列必须跟最终生效的语言键逐项一致。"""
    bad = []
    for qkey, (label, pairs) in bindings.items():
        if qkey not in up:
            die('上游英文任务书里没有绑定键 %s（%s），任务可能改版，需重新核对'
                % (qkey, label))
        if qkey not in ours:
            die('出货中文任务书里没有绑定键 %s（%s），无法检查'
                % (qkey, label))
        en_terms = [e for e, _ in pairs]
        if not ordered_terms(norm(up[qkey]), en_terms):
            die('上游任务 %s 已不再按预期列出 %s：%s，需重新核对绑定'
                % (qkey, label, ' / '.join(en_terms)))
        zh_terms = [c for _, c in pairs]
        if not ordered_terms(norm(ours[qkey]), zh_terms):
            bad.append((qkey, label, zh_terms))
    return bad


def main(argv):
    if len(argv) != 4:
        die('用法: check_item_names_in_quests.py <mods 目录> <上游树> <出货树>')
    mods, uproot, tree = argv[1], Path(argv[2]), Path(argv[3])

    if not (uproot / EN_QUESTS).is_dir():
        die('上游树里没有 %s，取不到英文原文（树: %s）'
            % (EN_QUESTS, uproot))
    up = quest_text(uproot / EN_QUESTS)
    ours = quest_text(tree / ZH_QUESTS)
    if not up:
        die('%s 里一条任务文本都没读到' % (uproot / EN_QUESTS))
    if not ours:
        die('%s 里一条任务文本都没读到，出货树没有组装好' % (tree / ZH_QUESTS))
    common = [k for k in up if k in ours]
    if not common:
        die('英文与中文一个键都对不上，两棵树不是同一版')

    names, enforced, bindings = collect(mods, tree)
    bad = mismatches(names, enforced, up, ours, common)
    binding_bad = binding_mismatches(bindings, up, ours)

    if bad:
        print('❌ 任务书里的物品名跟游戏内物品名对不上（玩家照任务书去 JEI 搜会搜不到）：')
        for k, e, c in sorted(bad):
            print('   %-40s 英文 %-24s 中文应出现 %s' % (k, e, c))
    if binding_bad:
        print('❌ 任务书里的界面术语跟游戏内实际显示对不上：')
        for k, label, terms in binding_bad:
            print('   %-40s %s 应按顺序写作 %s' % (k, label, ' / '.join(terms)))
    if bad or binding_bad:
        return 1
    print('✅ %s：%d 条任务文本、%d 个物品名当参照，强制检查 %d 个（%s）及 %d 组界面术语，全部一致'
          % (tree, len(common), len(names), len(enforced), '、'.join(NAMESPACES), len(bindings)))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
