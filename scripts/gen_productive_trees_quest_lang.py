#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# atm10-zh-cn — All the Mods 10 简体中文汉化补丁「绿油油版」
# Copyright (C) 2026 0xyk3r
# Copyright (C) 2026 星野夢華 (Hoshino Yumeka)
# SPDX-License-Identifier: GPL-3.0-or-later
"""给资源树育种结构填入中文，生成任务书副标题。

任务书副标题是「甲 + 乙」形式的育种公式，名字必须与 JEI 物品名逐字一致，否则玩家搜不到。
改了树名，公式也要跟着变，所以由脚本生成。

只读结构，不读 jar。结构由 ``scripts/scan_productive_trees.py`` 在版本入库时扫描一次，存成
``versions/db/<版本>/productive_trees.json``（与 jars.json、keybinds.json 一样是该版基线）。
已发布版本的章节与配方不会再变，所以这个脚本：

* 不读整合包、不读 jar、不联网。
* 只做「词根 → 中文」，输入是基线与 ``src/`` 里的树名 lang。
* 改译名后重新运行即可，不用重新扫描。

产物由 ``generate_all.sh`` 写进出货树，不入 src/：路径登记在 ``assemble.py`` 的 FORBIDDEN_IN_SRC 里，
提交进 src/ 会失败。

出货的育种公式只有一份（按最新版基线生成），所以对其余版本也要成立。``--verify-versions``
给每个在册版本各生成一遍，要求结果逐字一致。这里只检查一致性，不检查数量：数量随 ATM 更新变化。
这项检查只读几份 JSON，放在 ci.yml 里。不一致时会列出版本与键，那时再按
``versions/<版本>/quest_overrides.snbt`` 拆成该版专属覆盖。

    python3 scripts/gen_productive_trees_quest_lang.py --version 7.3 --out <出货树里的 snbt>
    python3 scripts/gen_productive_trees_quest_lang.py --version 7.3      # 预览到 stdout
    python3 scripts/gen_productive_trees_quest_lang.py --verify-versions
"""
import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / 'src'
ZH_LANG = SRC / 'pack' / 'assets' / 'productivetrees' / 'lang' / 'zh_cn.json'
DELTA_ROOT = SRC / 'config' / 'ftbquests' / 'quests' / 'lang' / 'zh_cn'
SCALAR = re.compile(r'^[\t ]+([A-Za-z0-9_.]+):\s*(.+)$')

# 原版树的名字不由本生成器决定，写成任务书里现有的中文。它们属于 minecraft: 命名空间，
# 不能借育种公式改原版译名。
VANILLA_PARENTS = {
    'minecraft:acacia_leaves': '相思木',
    'minecraft:birch_leaves': '白桦',
    'minecraft:cherry_leaves': '樱花木',
    'minecraft:dark_oak_leaves': '深色橡木',
    'minecraft:flowering_azalea_leaves': '开花杜鹃',
    'minecraft:jungle_leaves': '丛林木',
    'minecraft:mangrove_leaves': '红树林',
    'minecraft:oak_leaves': '橡木',
    'minecraft:spruce_leaves': '云杉',
}


class DataError(Exception):
    """数据不是预期的形状。一律当失败，不许降级继续。"""


# ── 词根 → 中文 ─────────────────────────────────────────────────────────────

def sapling_name(item_id, zh, bare):
    """取树苗中文名。``bare`` 时去掉「树苗」两个字，公式里写的是树名。"""
    if not item_id.startswith('productivetrees:') or not item_id.endswith('_sapling'):
        raise DataError('不是 Productive Trees 树苗：%s' % item_id)
    key = 'block.productivetrees.%s' % item_id.split(':', 1)[1]
    value = zh.get(key)
    if not isinstance(value, str) or not value.strip():
        raise DataError('中文语言文件缺少有效的 %s' % key)
    if not bare:
        return value
    if value == '树苗' or not value.endswith('树苗'):
        raise DataError('%s 必须严格以「树苗」结尾，实际是 %r' % (key, value))
    return value[:-2]


def parent_name(item_id, zh):
    if item_id in VANILLA_PARENTS:
        return VANILLA_PARENTS[item_id]
    if item_id.startswith('productivetrees:') and item_id.endswith('_leaves'):
        stem = item_id.split(':', 1)[1][:-len('_leaves')]
        return sapling_name('productivetrees:%s_sapling' % stem, zh, True)
    raise DataError('授粉配方出现未知父本：%s' % item_id)


def baseline_path(version):
    return ROOT / 'versions' / 'db' / version / 'productive_trees.json'


def load_baseline(version):
    p = baseline_path(version)
    if not p.is_file():
        raise DataError('缺 %s，该版还没扫描过育种结构，先运行\n'
                        '   python3 scripts/scan_productive_trees.py %s <该版整合包目录>'
                        % (p, version))
    d = json.loads(p.read_text(encoding='utf-8'))
    if not isinstance(d.get('subtitles'), dict) or not isinstance(d.get('titles'), dict):
        raise DataError('%s 不是预期的育种结构基线' % p)
    if not d['subtitles']:
        raise DataError('%s 里一条育种公式都没有' % p)
    return d


def render_values(baseline, zh):
    """基线 + 中文 → ``{任务语言键: 中文}``。"""
    out = {}
    for quest, spec in sorted(baseline['subtitles'].items()):
        key = 'quest.%s.quest_subtitle' % quest
        kind = spec.get('kind')
        if kind == 'pollination':
            left = '/'.join(parent_name(i, zh) for i in spec['left'])
            right = '/'.join(parent_name(i, zh) for i in spec['right'])
            out[key] = '%s + %s' % (left, right)
        elif kind == 'mutation':
            out[key] = '%s + 运气' % sapling_name(spec['source'], zh, True)
        else:
            raise DataError('任务 %s 的育种类型不认识：%r' % (quest, kind))
    for quest, target in sorted(baseline['titles'].items()):
        out['quest.%s.title' % quest] = sapling_name(target, zh, False)
    return out


def render(values):
    lines = ['{']
    lines += ['\t%s: %s' % (k, json.dumps(v, ensure_ascii=False))
              for k, v in sorted(values.items())]
    lines.append('}')
    return '\n'.join(lines) + '\n'


# ── 与手写 delta 的边界 ──────────────────────────────────────────────────────

def delta_scalars(path):
    out = {}
    for no, line in enumerate(Path(path).read_text(encoding='utf-8').splitlines(), 1):
        m = SCALAR.match(line)
        if not m or not m.group(2).startswith('"'):
            continue
        key, raw = m.groups()
        try:
            value = json.loads(raw)
        except Exception as e:                                   # noqa: BLE001
            raise DataError('%s 第 %d 行的 %s 解析失败：%s' % (path, no, key, e)) from e
        if isinstance(value, str):
            if key in out:
                raise DataError('%s 内部重复键：%s' % (path, key))
            out[key] = value
    return out


def ownership_issues(values, delta_root=DELTA_ROOT):
    """生成器负责的键，不许同时出现在 src/ 里的手写 delta 中。

    两处定义同一个键，最后由合并顺序决定哪份生效。这里不判断哪份对，要求先把键移交出去。
    生成物在出货树、不在 delta_root 下，不用排除自己。
    """
    owners = {}
    for path in sorted(Path(delta_root).rglob('zz_hanhua_*.snbt')):
        for key in delta_scalars(path):
            if key in owners:
                raise DataError('手写 delta 重复键：%s 同时在 %s 与 %s'
                                % (key, owners[key], path))
            owners[key] = path
    return ['生成键 %s 仍由手写文件 %s 持有，需先移交' % (k, owners[k])
            for k in sorted(set(values) & set(owners))]


def existing_values(path):
    """读回上一轮的生成物。格式不对就拒绝覆盖，说明有人手改过它。"""
    lines = Path(path).read_text(encoding='utf-8').splitlines()
    if len(lines) < 2 or lines[0] != '{' or lines[-1] != '}':
        raise DataError('%s 不是预期的纯生成 SNBT' % path)
    out = {}
    for no, line in enumerate(lines[1:-1], 2):
        m = SCALAR.match(line)
        if not m:
            raise DataError('%s 第 %d 行不是单行标量，拒绝覆盖' % (path, no))
        key, raw = m.groups()
        try:
            value = json.loads(raw)
        except Exception as e:                                   # noqa: BLE001
            raise DataError('%s 第 %d 行解析失败：%s' % (path, no, e)) from e
        if not isinstance(value, str) or key in out:
            raise DataError('%s 第 %d 行不是唯一字符串键，拒绝覆盖' % (path, no))
        out[key] = value
    return out


# ── 版本 ────────────────────────────────────────────────────────────────────

def declared_versions():
    out = sorted((p.name for p in (ROOT / 'versions').iterdir()
                  if p.is_dir() and p.name[:1].isdigit()),
                 key=lambda s: [int(x) for x in s.split('.')])
    if not out:
        raise DataError('versions/ 下一个整合包版本都没有')
    return out


def verify_versions(versions, zh):
    """各版本各套一遍中文，结果必须逐字一致。返回共同结果。"""
    results = {v: render_values(load_baseline(v), zh) for v in versions}
    base = versions[0]
    for v in versions[1:]:
        a, b = results[base], results[v]
        if a == b:
            continue
        diff = sorted(set(a) ^ set(b)) + sorted(k for k in set(a) & set(b) if a[k] != b[k])
        raise DataError(
            'ATM10 %s 与 %s 的育种公式不一致，%d 个键分叉：%s\n'
            '   一份共用的生成物已经描述不了所有版本了。把分叉的那版拆成\n'
            '   versions/<版本>/quest_overrides.snbt 的专属覆盖。'
            % (base, v, len(diff), '、'.join(diff[:12]) + ('…' if len(diff) > 12 else '')))
    return results[base]


# ── 入口 ────────────────────────────────────────────────────────────────────

def parse_args(argv):
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument('--version', help='用哪个版本的基线生成，默认最新的在册版本')
    p.add_argument('--out', type=Path,
                   help='写到出货树里的这个路径，不给就只输出到 stdout')
    p.add_argument('--verify-versions', action='store_true',
                   help='检查：在册各版本各生成一遍中文，结果必须逐字一致')
    p.add_argument('--only', nargs='+', metavar='版本',
                   help='配合 --verify-versions，只查这几个版本，默认全部')
    p.add_argument('--lang', type=Path, default=ZH_LANG, help='本包的树名中文 lang')
    return p.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    try:
        zh = json.loads(Path(args.lang).read_text(encoding='utf-8-sig'))

        if args.verify_versions:
            if args.version or args.out:
                raise DataError('--verify-versions 是纯检查，不接受 --version / --out')
            versions = args.only or declared_versions()
            values = verify_versions(versions, zh)
            note = '%d 个版本一致（%s）' % (len(versions), '、'.join(versions))
            target = None
        else:
            version = args.version or declared_versions()[-1]
            values = render_values(load_baseline(version), zh)
            note, target = '取 %s 的基线' % version, args.out

        # 生成物不进 src/，但它负责的键不许同时出现在 src/ 里的手写 delta 中，
        # 否则又由合并顺序决定哪份生效。
        issues = ownership_issues(values)
        if issues:
            raise DataError('任务键所有权没就绪：\n   ' + '\n   '.join(issues))

        text = render(values)
        if target is not None:
            if SRC.resolve() in target.resolve().parents:
                raise DataError('拒绝写进 src/：%s。生成物只写出货树' % target)
            if target.is_file():
                foreign = sorted(set(existing_values(target)) - set(values))
                if foreign:
                    raise DataError('%s 里有本生成器不管理的键，拒绝删除：%s'
                                    % (target, '、'.join(foreign)))
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(text, encoding='utf-8')
            note += '，已写入 %s' % target
        elif not args.verify_versions:
            sys.stdout.write(text)

        subtitles = sum(1 for k in values if k.endswith('.quest_subtitle'))
        print('✅ 资源树育种公式：%d 条副标题 + %d 条标题，%s'
              % (subtitles, len(values) - subtitles, note), file=sys.stderr)
        return 0
    except DataError as e:
        print('❌ %s' % e, file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
