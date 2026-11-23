#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# atm10-zh-cn — All the Mods 10 简体中文汉化补丁「绿油油版」
# Copyright (C) 2026 星野夢華 (Hoshino Yumeka)
# SPDX-License-Identifier: GPL-3.0-or-later
"""任务书里提到某只蜜蜂时，必须用玩家在 JEI 里搜得到的名字。

例如任务正文写「倒在幽灵蜜蜂蛋上」，JEI 里那个物品叫「恶魂蜜蜂」，照任务书搜不到。同类还有正文里
留着英文原名 `BeeBee`、`KamikazBee`（物品名是「蜂蜂」「“神风特攻队”蜜蜂」），以及英文的
`Ghostly Bee or Shroombees` 在中文里漏掉了 Shroombees。

判定：英文原文出现某只蜜蜂的英文名，中文里就必须出现它的中文名。英文名取 productivebees 的
`en_us.json`，中文名取本包资源包的 `zh_cn.json`，按同一个键一一对应。

蜜脾、蜜脾块、刷怪蛋的名字由蜂名拼出，lang 里没有独立的键，也要检查（例如任务标题写
「凋亡蜜脾块」，游戏里叫「凋灵蜜蜂蜜脾块」）。拼法来自 `CombBlockItem` / `Honeycomb` 的字节码：
取 `entity.productivebees.<type>_bee` 的本地化名字，删掉字面量 `" Bee"`，填进 `%s Comb Block` /
`%s蜜脾块` 这类模板。中文名里没有 `" Bee"`，所以填进去的是整个蜂名，「凋灵蜜蜂蜜脾块」因此多了
「蜜蜂」两个字。模板从两张表的 `*_configurable` 键里取。

最长匹配优先：`Dragonsteel Bee` 按词边界也能匹配到 `Lightning Dragonsteel Bee` 里，会误报
「龙霆钢蜜蜂」。所以某条英文名命中时，同一段文字里还命中了包含它的更长名字，这条不算。

拿不到 jar、读不到两张表、上游英文任务书目录不在、一个任务条目都没对上，都按失败处理。

用法:
    python3 scripts/compliance/check_bee_names_in_quests.py <mods 目录> <上游树> <出货树>
"""
import json
import re
import sys
import zipfile
from pathlib import Path

EN_LANG = 'assets/productivebees/lang/en_us.json'
ZH_LANG = 'resourcepacks/ATM10汉化包/assets/productivebees/lang/zh_cn.json'
EN_QUESTS = 'config/ftbquests/quests/lang/en_us'
ZH_QUESTS = 'config/ftbquests/quests/lang/zh_cn'
KEY = re.compile(r'^[\t ]+([A-Za-z0-9_.]+):\s*(.*)$')
# 由蜂名拼出的几类名字的模板键（`%s Comb Block` / `%s蜜脾块` 这种）
DERIVED = ('block.productivebees.comb_configurable',
           'item.productivebees.honeycomb_configurable',
           'item.productivebees.spawn_egg_configurable')
# 太短的英文名（Bee、Egg 之类）全文搜索一定大量误报，不检查。
MIN_LEN = 6
WORD = re.compile(r'\w+')
# 颜色码和转义换行会破坏词边界：`&8Withered` 里 `8` 和 `W` 都是 \w，按单词切会切出 `8Withered`，
# 导致漏判。非法颜色码（ATM 任务书里有 `&z`）也要去掉。
NOISE = re.compile(r'[&§](?:#[0-9A-Fa-f]{6}|[0-9A-Za-z])|\\+n')


def die(msg):
    print('❌ %s' % msg)
    sys.exit(1)


def bee_names(mods, tree):
    jars = sorted(Path(mods).glob('productivebees*.jar'))
    if not jars:
        die('%s 里没有 productivebees 的 jar，英文名表取不到，无法检查' % mods)
    try:
        with zipfile.ZipFile(jars[-1]) as z:
            en = json.loads(z.read(EN_LANG))
    except Exception as e:
        die('%s 里读不出 %s：%s' % (jars[-1].name, EN_LANG, e))
    zp = Path(tree) / ZH_LANG
    if not zp.is_file():
        die('%s 不存在，资源包没有组装出来' % zp)
    try:
        zh = json.loads(zp.read_text(encoding='utf-8'))
    except Exception as e:
        die('%s 解析失败：%s' % (zp, e))

    # 一个英文名可能对应多只蜜蜂：上游把 chaos_bee 和 chaotic_bee 都叫 "Chaos Bee"，中文分别是
    # 混沌蜜蜂、混沌锭蜜蜂。静态判断不出正文说的是哪一只，命中任意一个中文名就算通过。
    # 蜜脾、蜜脾块、刷怪蛋的名字模板从两张表里取
    tmpl = []
    for k in DERIVED:
        if isinstance(en.get(k), str) and isinstance(zh.get(k), str) \
                and '%s' in en[k] and '%s' in zh[k]:
            tmpl.append((en[k], zh[k]))
    if not tmpl:
        die('%s 这几个模板键一个都没配上，无法判断蜜脾、刷怪蛋这类拼出来的名字'
            % '、'.join(DERIVED))

    byname = {}
    for k in en:
        if not (k.startswith('entity.productivebees.') and k in zh):
            continue
        e, c = en[k], zh[k]
        if not (isinstance(e, str) and len(e) >= MIN_LEN):
            continue
        if not (isinstance(c, str) and c.strip()):
            continue
        byname.setdefault(e, set()).add(c)
        # 拼法：本地化蜂名删掉字面量 " Bee" 再填进模板。中文名里没有 " Bee"，填的是整个蜂名。
        stem_en = e[:-4] if e.endswith(' Bee') else e   # 跟 CombBlockItem 的 endsWith 判定一致
        for te, tz in tmpl:
            byname.setdefault(te % stem_en, set()).add(tz % c)
    pairs = sorted((e, frozenset(cs)) for e, cs in byname.items())
    if not pairs:
        die('一对「英文名→中文名」都没配上，两张表对不上')
    return pairs


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


def main(argv):
    if len(argv) != 4:
        die('用法: check_bee_names_in_quests.py <mods 目录> <上游树> <出货树>')
    mods, uproot, tree = argv[1], Path(argv[2]), Path(argv[3])
    pairs = bee_names(mods, tree)

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

    # 加上蜜脾、蜜脾块、刷怪蛋后名字表是原来的三倍，逐条跑正则要几分钟，所以按首词建索引：
    # 只在正文里每个单词的位置上，试以这个词开头的名字。
    by_first = {}
    for e, cs in pairs:
        m = WORD.match(e)
        if m:
            by_first.setdefault(m.group(0).lower(), []).append((e, cs))

    hits = []
    for k in common:
        text, mine = NOISE.sub(' ', up[k]), ours[k]
        found = []
        for m in WORD.finditer(text):
            for e, cs in by_first.get(m.group(0).lower(), ()):
                end = m.start() + len(e)
                if text[m.start():end].lower() != e.lower():
                    continue
                if end < len(text) and (text[end].isalnum() or text[end] == '_'):
                    continue                  # 右边界，别把 Bees 当成 Bee
                found.append((e, cs))
        for e, cs in found:
            # 最长匹配优先：短名落在长名里不算命中
            if any(len(e2) > len(e) and e.lower() in e2.lower() for e2, _ in found):
                continue
            if not any(c in mine for c in cs):
                hits.append((k, e, '／'.join(sorted(cs))))

    if hits:
        print('❌ 任务书里的蜜蜂名跟物品名对不上（玩家照任务书去 JEI 搜会搜不到）：')
        for k, e, c in sorted(hits):
            print('   %-42s 英文 %-24s 中文应出现 %s' % (k, e, c))
        return 1
    print('✅ %s：%d 条任务文本对过 %d 个蜜蜂名，全部与物品名一致'
          % (tree, len(common), len(pairs)))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
