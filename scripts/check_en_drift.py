#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# atm10-zh-cn — All the Mods 10 简体中文汉化补丁「绿油油版」
# Copyright (C) 2026 星野夢華 (Hoshino Yumeka)
# SPDX-License-Identifier: GPL-3.0-or-later
"""两个整合包版本之间的英文底本漂移：上游改了哪些文案。

## 为什么要它

公共内容是照着某一个版本的英文写的。上游升版时改了正文，我们的中文还停在旧描述，
玩家读到的是一段通顺但描述错误行为的中文，比漏翻危险得多，因为看不出来。
`versions/README.md` 记的 7.1→7.2 那五条就是这么找出来的。

列出不等于要改译文：半数是拼写修正（Ingrediant→Ingredient 之类），中文不用动。
只有行为 / 数值真的变了，才写进 `versions/<版本>/quest_overrides.snbt` 分叉。

这个脚本只报告，不设闸：它退出码永远是 0。要不要跟、怎么跟，是人的判断。
（一个只会打印的东西不该有能力拦住构建。）

用法:
    python3 scripts/check_en_drift.py 7.2 7.3
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PREVIEW = 90


def load(ver, name, required=True):
    """required=False 时文件不在就返回 None，给那些故意不入库的底本用。

    `lang_baseline_local.json` 被 .gitignore 排除（十几万条键，且随时可从 jar 重建），
    所以在 CI 上通常只有「刚生成的那一版」有、上一版没有。任务书底本是入库的，
    两版都在，那才是这个脚本的主要判据。
    """
    f = ROOT / 'versions' / 'db' / ver / (name + '.json')
    if not f.is_file():
        if not required:
            return None
        sys.exit('❌ 没有 %s\n   先跑: python3 scripts/build_en_baseline.py %s <该版mods目录> <该版overrides目录>'
                 % (f.relative_to(ROOT), ver))
    return json.loads(f.read_text(encoding='utf-8'))


def clip(s):
    s = ' '.join(str(s).split())
    return s if len(s) <= PREVIEW else s[:PREVIEW] + '…'


def report(title, a, b):
    added = sorted(set(b) - set(a))
    removed = sorted(set(a) - set(b))
    changed = sorted(k for k in set(a) & set(b) if a[k] != b[k])
    print('\n── %s：新增 %d，消失 %d，改动 %d（旧 %d 键 → 新 %d 键）'
          % (title, len(added), len(removed), len(changed), len(a), len(b)))
    for k in changed:
        print('   ~ %s' % k)
        print('       旧 %s' % clip(a[k]))
        print('       新 %s' % clip(b[k]))
    for k in added:
        print('   + %s  %s' % (k, clip(b[k])))
    for k in removed:
        print('   - %s  （上游删了这一条）' % k)
    return added, removed, changed


def main(old, new):
    print('英文底本漂移：ATM10 %s → %s' % (old, new))

    qa, qb = load(old, 'quest_baseline'), load(new, 'quest_baseline')
    _, _, qchanged = report('任务书（我们已有覆盖的那批键）', qa, qb)

    # 资源包 lang 有十几万条，逐条打印没法看。只报「我们译过的命名空间里改了多少」。
    # 这份底本不入库（.gitignore 排除），所以经常只有一边有，那就跳过并说清楚，
    # 不要因为一份可再生的本地产物缺席就把整份报告废掉。
    ra, rb = load(old, 'lang_baseline_local', False), load(new, 'lang_baseline_local', False)
    if ra is None or rb is None:
        miss = ' 与 '.join(v for v, r in ((old, ra), (new, rb)) if r is None)
        print('\n── 资源包 lang：跳过（%s 的 lang_baseline_local.json 不在本地）' % miss)
        print('   它被 .gitignore 排除，只在跑过 build_en_baseline.py 的机器上存在。')
        print('   要看这部分，对两个版本各跑一次 build_en_baseline.py 再重跑本脚本。')
        print('\n结论：任务书 %d 条的英文变了（资源包 lang 未比对）。' % len(qchanged))
        return 0
    la, lb = ra['lang'], rb['lang']
    lchanged = sorted(k for k in set(la) & set(lb) if la[k] != lb[k])
    ladded = sorted(set(lb) - set(la))
    lgone = sorted(set(la) - set(lb))
    print('\n── 资源包 lang：新增 %d，消失 %d，改动 %d（旧 %d 键 → 新 %d 键）'
          % (len(ladded), len(lgone), len(lchanged), len(la), len(lb)))
    for k in lchanged[:40]:
        print('   ~ %s' % k)
        print('       旧 %s' % clip(la[k]))
        print('       新 %s' % clip(lb[k]))
    if len(lchanged) > 40:
        print('   …还有 %d 条改动没列（全量看 versions/db/*/lang_baseline_local.json）'
              % (len(lchanged) - 40))

    print('\n结论：任务书 %d 条、资源包 lang %d 条的英文变了。'
          % (len(qchanged), len(lchanged)))
    print('逐条看是**拼写修正**还是**行为/数值变了**——只有后者需要在'
          ' versions/%s/quest_overrides.snbt 里分叉，前者中文原样不动。' % new)
    return 0        # 只报告，永远不拦构建


if __name__ == '__main__':
    if len(sys.argv) != 3:
        raise SystemExit(__doc__.strip().splitlines()[-1])
    sys.exit(main(sys.argv[1], sys.argv[2]))
