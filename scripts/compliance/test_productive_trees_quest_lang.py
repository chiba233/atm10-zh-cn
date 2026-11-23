#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# atm10-zh-cn — All the Mods 10 简体中文汉化补丁「绿油油版」
# Copyright (C) 2026 0xyk3r
# Copyright (C) 2026 星野夢華 (Hoshino Yumeka)
# SPDX-License-Identifier: GPL-3.0-or-later
"""资源树育种公式：扫描器与生成器的反例测试。

每条复刻一种「本该红却可能悄悄放行」的情形。写了闸不等于有闸，
一道从没被触发过的闸和没有闸是一回事。

全部用合成 jar 与合成目录，不读真整合包也不联网：这套测试要能在 PR 阶段秒跑。

    python3 scripts/compliance/test_productive_trees_quest_lang.py
"""
import json
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / 'scripts'))

import gen_productive_trees_quest_lang as g                      # noqa: E402
import scan_productive_trees as s                                # noqa: E402

POLL, MUTATION, LOOT, MACHINE = (c * 16 for c in 'ABCD')

# 章节结构：四个任务。POLL / MUTATION 各产一棵树苗。LOOT 也产树苗，但它的英文
# 副标题是来源说明。MACHINE 压根不产树苗。
CHAPTER = '{\n\tquests: [\n' + '\n'.join(
    '\t\t{\n\t\t\tid: "%s"\n\t\t\ttasks: [{\n\t\t\t\tid: "%s"\n'
    '\t\t\t\titem: { count: 1, id: "%s" }\n\t\t\t\ttype: "item"\n\t\t\t}]\n\t\t}'
    % (q, str(i) * 16, item) for i, (q, item) in enumerate((
        (POLL, 'productivetrees:hybrid_sapling'),
        (MUTATION, 'productivetrees:mutated_sapling'),
        (LOOT, 'productivetrees:loot_sapling'),
        (MACHINE, 'productivetrees:sawmill'),
    ), 1)) + '\n\t]\n}\n'

QUEST_LANG = (
    '{\n'
    '\tquest.%s.quest_subtitle: "Parent + Oak/Other"\n'
    '\tquest.%s.title: "Hybrid Sapling"\n'
    '\tquest.%s.quest_subtitle: "Source + Luck"\n'
    '\tquest.%s.title: "Mutated Sapling"\n'
    '\tquest.%s.quest_subtitle: "Ancient City Chests"\n'
    '\tquest.%s.quest_subtitle: "I Wood too"\n'
    '\tquest.%s.title: "Sawmill"\n'
    '}\n' % (POLL, POLL, MUTATION, MUTATION, LOOT, MACHINE, MACHINE))

ZH = {
    'block.productivetrees.hybrid_sapling': '杂交树树苗',
    'block.productivetrees.mutated_sapling': '突变树树苗',
    'block.productivetrees.loot_sapling': '战利品树树苗',
    'block.productivetrees.parent_sapling': '亲本树苗',
    'block.productivetrees.other_sapling': '另一树树苗',
    'block.productivetrees.source_sapling': '源树树苗',
}


def make_jar(path, extra_tree=False):
    def poll(result, a, b):
        return {'type': 'productivetrees:tree_pollination', 'result': {'id': result},
                'leafA': [{'item': x} for x in a], 'leafB': [{'item': x} for x in b]}

    trees = {'source': {'mutation_info': {'target': 'productivetrees:mutated',
                                          'chance': 0.05}}}
    if extra_tree:
        trees['newcomer'] = {}
    with zipfile.ZipFile(path, 'w') as z:
        z.writestr('data/productivetrees/recipe/pollination/hybrid.json',
                   json.dumps(poll('productivetrees:hybrid_sapling',
                                   ['productivetrees:parent_leaves'],
                                   ['minecraft:oak_leaves',
                                    'productivetrees:other_leaves'])))
        z.writestr('data/productivetrees/recipe/pollination/loot.json',
                   json.dumps(poll('productivetrees:loot_sapling',
                                   ['productivetrees:parent_leaves'],
                                   ['minecraft:birch_leaves'])))
        z.writestr('data/productivetrees/trees.json', json.dumps(trees))
        z.writestr('assets/productivetrees/lang/en_us.json', json.dumps({
            'block.productivetrees.hybrid_sapling': 'Hybrid Sapling',
            'block.productivetrees.mutated_sapling': 'Mutated Sapling',
            'block.productivetrees.loot_sapling': 'Loot Sapling'}))


def scan_one(tmp, quest_lang=QUEST_LANG, extra_tree=False):
    jar = tmp / ('pt-%s.jar' % extra_tree)
    make_jar(jar, extra_tree)
    return s.scan(CHAPTER, quest_lang, jar)


def put_baseline(tmp, version, data):
    d = tmp / 'versions' / 'db' / version
    d.mkdir(parents=True, exist_ok=True)
    (d / 'productive_trees.json').write_text(json.dumps(data, ensure_ascii=False),
                                             encoding='utf-8')
    (tmp / 'versions' / version).mkdir(parents=True, exist_ok=True)


def in_sandbox(tmp, fn):
    """把生成器的 ROOT 临时指进沙盒，跑完还原。"""
    saved = g.ROOT
    g.ROOT = tmp
    try:
        return fn()
    finally:
        g.ROOT = saved


CASES = []


def case(name):
    def deco(fn):
        CASES.append((name, fn))
        return fn
    return deco


# ── 扫描器 ──────────────────────────────────────────────────────────────────

@case('扫描器只收能被数据证明归它管的字段')
def t_scan_scope(tmp):
    d = scan_one(tmp)
    return (d['subtitles'].get(POLL, {}).get('kind') == 'pollination'
            and d['subtitles'].get(MUTATION, {}).get('kind') == 'mutation'
            # 来源说明、机器双关都归人写，一条都不许被收走
            and LOOT not in d['subtitles'] and MACHINE not in d['subtitles']
            # 标题只在「英文标题 == 官方英文名」时才收，Sawmill 不算
            and set(d['titles']) == {POLL, MUTATION}
            and MACHINE not in d['titles'])


@case('扫描器产出里一个中文都不许有')
def t_scan_no_chinese(tmp):
    blob = json.dumps(scan_one(tmp), ensure_ascii=False)
    return not any('一' <= c <= '鿿' for c in blob)


@case('章节 SNBT 括号没闭合 → 必须红')
def t_scan_broken_snbt(tmp):
    jar = tmp / 'pt.jar'
    make_jar(jar)
    try:
        s.scan(CHAPTER.replace('\n}\n', '\n'), QUEST_LANG, jar)
    except s.DataError as e:
        return '没闭合' in str(e)
    return False


@case('jar 里一个授粉配方都没有 → 必须红，不许产出空基线')
def t_scan_empty_jar(tmp):
    jar = tmp / 'empty.jar'
    with zipfile.ZipFile(jar, 'w') as z:
        z.writestr('data/productivetrees/trees.json', '{}')
        z.writestr('assets/productivetrees/lang/en_us.json', '{}')
    try:
        s.scan(CHAPTER, QUEST_LANG, jar)
    except s.DataError as e:
        return '一个授粉配方都没读到' in str(e)
    return False


# ── 生成器 ──────────────────────────────────────────────────────────────────

@case('基线 + 中文 → 公式，父本按 / 连接')
def t_render(tmp):
    v = g.render_values(scan_one(tmp), dict(ZH))
    return (v.get('quest.%s.quest_subtitle' % POLL) == '亲本 + 橡木/另一树'
            and v.get('quest.%s.quest_subtitle' % MUTATION) == '源树 + 运气'
            and v.get('quest.%s.title' % POLL) == '杂交树树苗'
            and v.get('quest.%s.title' % MUTATION) == '突变树树苗'
            and not any(k.endswith('.quest_desc') for k in v))


@case('树苗中文名不以「树苗」结尾 → 必须红')
def t_bad_suffix(tmp):
    zh = dict(ZH, **{'block.productivetrees.parent_sapling': '亲本'})
    try:
        g.render_values(scan_one(tmp), zh)
    except g.DataError as e:
        return '必须严格以「树苗」结尾' in str(e)
    return False


@case('中文 lang 缺了某个父本 → 必须红，不许留空混过去')
def t_missing_zh(tmp):
    zh = {k: v for k, v in ZH.items() if k != 'block.productivetrees.other_sapling'}
    try:
        g.render_values(scan_one(tmp), zh)
    except g.DataError as e:
        return '缺少有效的' in str(e)
    return False


@case('渲染结果形状稳定，且只含生成键')
def t_render_shape(tmp):
    text = g.render(g.render_values(scan_one(tmp), dict(ZH)))
    return (text.startswith('{\n\tquest.') and text.endswith('\n}\n')
            and 'Ancient City' not in text and 'I Wood too' not in text)


@case('生成键还被手写 delta 攥着 → 三条都要报出来')
def t_ownership(tmp):
    values = g.render_values(scan_one(tmp), dict(ZH))
    root = tmp / 'delta'
    root.mkdir()
    (root / 'zz_hanhua_manual.snbt').write_text(
        '{\n\tquest.%s.title: "杂交树树苗"\n\tquest.%s.title: "突变树树苗"\n'
        '\tquest.%s.quest_subtitle: "旧公式"\n}\n' % (POLL, MUTATION, POLL),
        encoding='utf-8')
    issues = g.ownership_issues(values, root)
    return len(issues) == 3 and all('仍由手写文件' in i for i in issues)


@case('该版还没扫过基线 → 必须红，并给出扫法')
def t_no_baseline(tmp):
    (tmp / 'versions' / '7.9').mkdir(parents=True)
    try:
        in_sandbox(tmp, lambda: g.load_baseline('7.9'))
    except g.DataError as e:
        return 'scan_productive_trees.py' in str(e)
    return False


@case('两版模组版本不同但配方一致 → 应当通过')
def t_versions_agree(tmp):
    put_baseline(tmp, '7.0', scan_one(tmp, extra_tree=False))
    put_baseline(tmp, '7.9', scan_one(tmp, extra_tree=True))   # 多一棵树，配方没变
    values = in_sandbox(tmp, lambda: g.verify_versions(['7.0', '7.9'], dict(ZH)))
    return bool(values)


@case('某版公式分叉 → 必须红，并点名是哪版哪个键')
def t_versions_diverge(tmp):
    put_baseline(tmp, '7.0', scan_one(tmp))
    # 7.9 把那条副标题的 " + " 拆掉：该版不再认它是育种公式，于是分叉
    put_baseline(tmp, '7.9', scan_one(tmp, quest_lang=QUEST_LANG.replace(
        'Parent + Oak/Other', 'Parent and Oak/Other')))
    try:
        in_sandbox(tmp, lambda: g.verify_versions(['7.0', '7.9'], dict(ZH)))
    except g.DataError as e:
        return '7.9' in str(e) and 'quest.%s.quest_subtitle' % POLL in str(e)
    return False


@case('拒绝把生成物写进 src/')
def t_refuse_src(tmp):
    put_baseline(tmp, '7.9', scan_one(tmp))
    lang = tmp / 'zh_cn.json'
    lang.write_text(json.dumps(ZH, ensure_ascii=False), encoding='utf-8')
    out = g.SRC / 'config' / 'x.snbt'
    args = ['--version', '7.9', '--lang', str(lang), '--out', str(out)]
    rc = in_sandbox(tmp, lambda: g.main(args))
    if rc != 1 or out.exists():
        return False
    # 换个不在 src/ 下的落点，同样的参数必须成功，否则上面那个 1
    # 可能是别的原因（比如译名缺失），这道闸就等于没验到。
    ok_out = tmp / 'ok.snbt'
    args[-1] = str(ok_out)
    return in_sandbox(tmp, lambda: g.main(args)) == 0 and ok_out.is_file()


def main():
    fail = 0
    for name, fn in CASES:
        tmp = Path(tempfile.mkdtemp())
        try:
            ok = fn(tmp)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
        print('%s %s' % ('✅' if ok else '❌', name))
        fail += 0 if ok else 1
    print('\n%d/%d 条通过' % (len(CASES) - fail, len(CASES)))
    return 1 if fail else 0


if __name__ == '__main__':
    sys.exit(main())
