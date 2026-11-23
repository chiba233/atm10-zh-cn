#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# atm10-zh-cn — All the Mods 10 简体中文汉化补丁「绿油油版」
# Copyright (C) 2026 0xyk3r
# Copyright (C) 2026 星野夢華 (Hoshino Yumeka)
# SPDX-License-Identifier: GPL-3.0-or-later
"""扫出某版整合包的资源树育种结构，写成该版基线。

任务书里「甲 + 乙」那种育种公式，名字必须与 JEI 物品名逐字一致，手写必漂，
改了树名不会有人记得回来改公式。所以公式不手写，从数据推。

但推的那一步不该每次构建都做：它要读整合包章节 + Productive Trees 的 jar，
而这两样对一个已发布的整合包版本来说是不会变的。仓库对这类东西的一贯做法是
「新版本入库时扫一次，算成基线，人过目后提交」，`versions/db/<版本>/` 下的
jars.json / keybinds.json / lang_baseline_local.json 都是这么来的。这里照办：

    versions/db/<版本>/productive_trees.json

基线里只有结构，没有一个中文：哪个任务对应哪棵树、它的父本是哪几棵。
译名是我们自己的东西，放 src/，改译名不必重扫。这样构建期只做「词根 → 中文」，
不下 jar、不联网。

字段：

    subtitles: {任务ID: {kind: pollination, left: [词根…], right: [词根…]}}
               {任务ID: {kind: mutation,    source: 词根}}
               left/right 里 `minecraft:` 开头的是原版树，原样留着
    titles:    {任务ID: 词根}      仅当英文标题 == 该树苗官方英文名

    python3 scripts/scan_productive_trees.py 7.3 <整合包目录>
    python3 scripts/scan_productive_trees.py 7.3 <整合包目录> --jar <指定 jar>
"""
import argparse
import json
import re
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CHAPTER = Path('config/ftbquests/quests/chapters/productive_trees.snbt')
EN_QUEST = Path('config/ftbquests/quests/lang/en_us/chapters/productive_trees.snbt')
JAR_PREFIX = 'productivetrees'
TREES_JSON = 'data/productivetrees/trees.json'
EN_LANG = 'assets/productivetrees/lang/en_us.json'
POLLINATION = re.compile(r'data/productivetrees/recipe/pollination/[^/]+\.json')
SCALAR = re.compile(r'^[\t ]+([A-Za-z0-9_.]+):\s*(.+)$')
QUEST_ID = re.compile(r'[0-9A-F]{16}')
ITEM_ID = re.compile(r'[a-z0-9_.-]+:[a-z0-9_./-]+')


class DataError(Exception):
    """数据不是预期的形状。一律当失败，不许降级继续。"""


def parse_quest_tasks(text):
    """返回 ``quest id -> 该任务 tasks 里的 item id``，不读 rewards。

    FTB Quests 的 SNBT 不是 JSON，``tasks: [{`` 还经常挤在同一行，正则读不了。
    这里按字符维护容器路径：只在 ``quests`` 的直接子对象里认任务，只在该任务的
    ``tasks`` 里认物品，奖励里也会出现树苗，认进来会把「产出」和「奖励」搞混。
    """
    out, stack = {}, []
    pending = current = None
    i, n = 0, len(text)
    while i < n:
        c = text[i]
        if c == '"':
            j = i + 1
            while j < n and not (text[j] == '"' and text[j - 1] != '\\'):
                j += 1
            if j >= n:
                raise DataError('任务章节里有未闭合的字符串（偏移 %d）' % i)
            value, path = text[i + 1:j], [k for _, k in stack]
            if current and pending == 'id' and len(stack) == current[0] \
                    and current[1] is None and QUEST_ID.fullmatch(value):
                current[1] = value
            if current and 'tasks' in path[current[0] - 1:] \
                    and pending in ('item', 'id') and ITEM_ID.fullmatch(value):
                current[2].append(value)
            pending, i = None, j + 1
            continue
        if c in '{[':
            stack.append((c, pending))
            if pending is None and c == '{' and current is None \
                    and len(stack) >= 2 and stack[-2][1] == 'quests':
                current = [len(stack), None, []]
            pending, i = None, i + 1
            continue
        if c in '}]':
            if current and c == '}' and len(stack) == current[0]:
                if current[1]:
                    if current[1] in out:
                        raise DataError('任务章节里重复的 quest id：%s' % current[1])
                    out[current[1]] = tuple(dict.fromkeys(current[2]))
                current = None
            if stack:
                stack.pop()
            pending, i = None, i + 1
            continue
        m = re.match(r'([A-Za-z_][A-Za-z0-9_]*)\s*:', text[i:])
        if m:
            pending, i = m.group(1), i + m.end()
            continue
        i += 1
    if current or stack:
        raise DataError('任务章节的括号没闭合')
    if not out:
        raise DataError('任务章节里一个 quest id 都没读到')
    return out


def scalar_lang(text):
    """任务语言文件里的单行标量。多行数组（描述）有意不读，本流程不碰描述。"""
    out = {}
    for no, line in enumerate(text.splitlines(), 1):
        m = SCALAR.match(line)
        if not m or not m.group(2).startswith('"'):
            continue
        key, raw = m.groups()
        try:
            value = json.loads(raw)
        except Exception as e:                                   # noqa: BLE001
            raise DataError('任务语言第 %d 行的 %s 不是合法字符串：%s' % (no, key, e)) from e
        if isinstance(value, str):
            if key in out:
                raise DataError('任务语言里重复的键：%s' % key)
            out[key] = value
    if not out:
        raise DataError('任务语言文件里一个标量键都没读到')
    return out


def _items(value, where):
    values = value if isinstance(value, list) else [value]
    if not values:
        raise DataError('%s 是空的配料数组' % where)
    out = []
    for one in values:
        if not isinstance(one, dict) or not ITEM_ID.fullmatch(str(one.get('item', ''))):
            raise DataError('%s 出现不支持的配料结构：%r' % (where, one))
        out.append(one['item'])
    return tuple(dict.fromkeys(out))


def mod_data(jar):
    """从 jar 里取：授粉配方、自突变、官方英文名。三者缺一都当失败。"""
    try:
        z = zipfile.ZipFile(jar)
    except Exception as e:                                       # noqa: BLE001
        raise DataError('%s 不是可读的 jar：%s' % (jar, e)) from e
    with z:
        def load(name):
            try:
                value = json.loads(z.read(name).decode('utf-8-sig'))
            except Exception as e:                               # noqa: BLE001
                raise DataError('%s 里的 %s 读不出来：%s' % (jar, name, e)) from e
            if not isinstance(value, dict):
                raise DataError('%s 里的 %s 根节点不是对象' % (jar, name))
            return value

        recipes = {}
        for name in sorted(n for n in z.namelist() if POLLINATION.fullmatch(n)):
            d = load(name)
            if d.get('type') != 'productivetrees:tree_pollination':
                raise DataError('%s 不是授粉配方' % name)
            result = d.get('result', {}).get('id') if isinstance(d.get('result'), dict) else None
            if not isinstance(result, str) or not result.startswith('productivetrees:') \
                    or not result.endswith('_sapling'):
                raise DataError('%s 的 result 不是树苗：%r' % (name, result))
            if result in recipes:
                raise DataError('多个授粉配方产出同一树苗：%s' % result)
            recipes[result] = (_items(d.get('leafA'), name + '.leafA'),
                               _items(d.get('leafB'), name + '.leafB'))

        mutations = {}
        for source, tree in load(TREES_JSON).items():
            info = tree.get('mutation_info') if isinstance(tree, dict) else None
            if not isinstance(info, dict):
                continue
            raw = info.get('target')
            if not isinstance(raw, str) or ':' not in raw:
                raise DataError('%s 的 mutation_info.target 非法：%r' % (source, raw))
            namespace, path = raw.split(':', 1)
            if namespace != 'productivetrees':
                raise DataError('%s 的突变目标不属于 Productive Trees：%s' % (source, raw))
            target = 'productivetrees:%s' % (path if path.endswith('_sapling')
                                             else path + '_sapling')
            if target in mutations:
                raise DataError('多个自突变来源指向同一树苗：%s' % target)
            mutations[target] = 'productivetrees:%s_sapling' % source

        english = load(EN_LANG)

    if not recipes:
        raise DataError('%s 里一个授粉配方都没读到' % jar)
    if not mutations:
        raise DataError('%s 里一个自突变都没读到' % jar)
    overlap = set(recipes) & set(mutations)
    if overlap:
        raise DataError('这些树苗同时有授粉与自突变来源：%s' % '、'.join(sorted(overlap)))
    return recipes, mutations, english


def sapling_key(item_id):
    if not item_id.startswith('productivetrees:') or not item_id.endswith('_sapling'):
        raise DataError('不是 Productive Trees 树苗：%s' % item_id)
    return 'block.productivetrees.%s' % item_id.split(':', 1)[1]


def scan(chapter_text, quest_lang_text, jar):
    """产出该版基线：任务 → 育种结构。一个中文都不含。"""
    tasks = parse_quest_tasks(chapter_text)
    lang = scalar_lang(quest_lang_text)
    recipes, mutations, english = mod_data(jar)

    # 一个任务只认一个树苗产出。多个就说明这不是「种出某棵树」的节点。
    by_quest, by_target = {}, {}
    for quest, items in tasks.items():
        targets = tuple(dict.fromkeys(
            i for i in items
            if i.startswith('productivetrees:') and i.endswith('_sapling')))
        if targets:
            by_quest[quest] = targets
            for t in targets:
                by_target.setdefault(t, []).append(quest)

    subtitles, owned = {}, {}
    for target, source in sorted({**recipes, **mutations}.items()):
        quests = by_target.get(target, [])
        if not quests:
            continue
        if len(quests) != 1:
            raise DataError('%s 同时被多个任务作为目标：%s' % (target, '、'.join(quests)))
        quest = quests[0]
        if quest in owned:
            raise DataError('任务 %s 同时对应多个树苗结果' % quest)
        key = 'quest.%s.quest_subtitle' % quest
        if key not in lang:
            raise DataError('该由本流程管理的树木任务缺英文副标题：%s' % key)

        # 有配方 ≠ ATM 想把这个节点展示成育种公式。作者写成「Ancient City Chests」
        # 这类来源说明时，那条文案归人写，本流程让开。判据是英文副标题的形状。
        if lang[key].count(' + ') != 1:
            continue
        if target in recipes:
            left, right = recipes[target]
            subtitles[quest] = {'kind': 'pollination',
                                'left': list(left), 'right': list(right)}
        else:
            if not lang[key].endswith(' + Luck'):
                continue
            subtitles[quest] = {'kind': 'mutation', 'source': source}
        owned[quest] = target

    # 标题另判：只在「英文标题 == 该树苗官方英文名」时才算，这样
    # Productive Trees / Stripping / Sawing 这些人起的标题不会被吃掉。
    titles = {}
    for quest, targets in sorted(by_quest.items()):
        if len(targets) != 1:
            continue
        key = 'quest.%s.title' % quest
        if key in lang and lang[key] == english.get(sapling_key(targets[0])):
            titles[quest] = targets[0]

    if not subtitles:
        raise DataError('一个可生成的树木育种公式都没找到')
    return {'subtitles': dict(sorted(subtitles.items())),
            'titles': dict(sorted(titles.items()))}


def find_jar(mods):
    hit = sorted(Path(mods).glob(JAR_PREFIX + '*.jar'))
    if len(hit) != 1:
        raise DataError('%s 下以 %r 开头的 jar 应恰有一个，实际 %d 个'
                        % (mods, JAR_PREFIX, len(hit)))
    return hit[0]


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument('version', help='整合包版本，如 7.3')
    p.add_argument('pack_root', type=Path, help='该版整合包目录（要有 mods/）')
    p.add_argument('--jar', type=Path, help='指定 Productive Trees jar')
    p.add_argument('--out', type=Path, help='默认 versions/db/<版本>/productive_trees.json')
    args = p.parse_args(argv)
    try:
        chapter, quest_lang = args.pack_root / CHAPTER, args.pack_root / EN_QUEST
        for path, label in ((chapter, '任务章节'), (quest_lang, '英文任务语言')):
            if not path.is_file():
                raise DataError('%s不存在：%s' % (label, path))
        jar = args.jar or find_jar(args.pack_root / 'mods')
        data = scan(chapter.read_text(encoding='utf-8'),
                    quest_lang.read_text(encoding='utf-8'), jar)
        out = args.out or ROOT / 'versions' / 'db' / args.version / 'productive_trees.json'
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(data, ensure_ascii=False, indent=1) + '\n',
                       encoding='utf-8')
        print('✅ ATM10 %s 育种结构 → %s（副标题 %d、标题 %d，取自 %s）'
              % (args.version, out, len(data['subtitles']), len(data['titles']), jar.name))
        return 0
    except DataError as e:
        print('❌ %s' % e, file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
