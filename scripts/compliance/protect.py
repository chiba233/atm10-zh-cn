#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# atm10-zh-cn — All the Mods 10 简体中文汉化补丁「绿油油版」
# Copyright (C) 2026 星野夢華 (Hoshino Yumeka)
# SPDX-License-Identifier: GPL-3.0-or-later
"""保护清单：src/ 下的文件只许加，不许删。

清单里的文件少一个，CI 就失败。要删文件，先在 `released` 里写明谁批准、理由和日期。
src/ 曾以「上游死重 / 游戏不读取 / 会回落到英文」为由误删 1033 个文件
（恢复提交 `6d37e00`、`72a5cc8`），所以用机械检查代替人工判断。

用法:
    python3 scripts/protect.py --check     # CI 用。少一个文件就退出 1
    python3 scripts/protect.py --update    # 新增汉化后运行，把新文件登记进清单
"""
import json
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # scripts/ 下的公共模块

ROOT = Path(__file__).resolve().parent.parent.parent
MANIFEST = ROOT / 'src' / 'protected.json'
# 保护整个 src/：这里没有生成物，不按类型挑，就不用争论哪个文件算汉化。
SCOPE = 'src/'

HEADER = ('src/ 下的文件只许加不许删。要删必须挪进 released 并写明谁批的、'
          '为什么，见 scripts/protect.py 顶部。')


MANIFEST_REL = 'src/protected.json'


def git(*args):
    """运行 git，失败返回 None。检查崩溃会被当成删了文件。

    容器里仓库 owner 与 uid 不同，git 报 `detected dubious ownership` 并退出 128，
    所以放开 safe.directory。「文件必须存在」不依赖 git，始终运行。
    """
    r = subprocess.run(['git', '-c', 'safe.directory=*',
                        '-c', 'core.quotepath=false', *args],
                       cwd=ROOT, capture_output=True, text=True)
    return r.stdout if r.returncode == 0 else None


def tracked():
    """git 跟踪的 src/ 文件，git 不可用时返回 None。

    清单自己也算在内。首次 --update 时它还没 git add，这里手动补上。
    """
    out = git('ls-files', SCOPE)
    if out is None:
        return None
    return sorted(set(p for p in out.splitlines() if p) | {MANIFEST_REL})


def load(text):
    d = json.loads(text)
    return d, set(d.get('protected') or []), {r['path'] for r in (d.get('released') or [])}


def read_manifest():
    if not MANIFEST.is_file():
        return {'_说明': HEADER, 'protected': [], 'released': []}, set(), set()
    return load(MANIFEST.read_text(encoding='utf-8'))


ABSENT = 'absent'      # 那个提交上还没有清单这个文件
BROKEN = 'broken'      # 有文件但解析不了


def at(rev):
    """某个提交上的清单，或 ABSENT（当时还没有清单，正常）/ BROKEN（解析失败，按失败处理）。"""
    out = git('show', '%s:%s' % (rev, MANIFEST_REL))
    if out is None:
        return ABSENT
    try:
        return load(out)
    except Exception:                                          # noqa: BLE001
        return BROKEN


def have(rev):
    return git('rev-parse', '--verify', '--quiet', rev + '^{commit}') is not None


def base_rev():
    """确定比较基准，返回 `(rev, 跳过理由)`。

    两者都是 None 表示取不到，调用方必须按失败处理。CI 是浅克隆，
    `github.event.before` 可能不在克隆里，所以先按需补取一次。
    """
    raw = (os.environ.get('PROTECT_BASE') or '').strip()
    if raw and set(raw) == {'0'}:
        # 新建分支首次 push 时 github.event.before 是全零
        return None, '上一版是全零 sha（新建分支的首次 push），没有可比的清单'
    rev = raw or 'HEAD~1'
    if have(rev):
        return rev, None
    # 只对像 sha 的值补取：HEAD~1 这种相对引用不能 fetch
    if len(rev) >= 7 and all(c in '0123456789abcdefABCDEF' for c in rev):
        git('fetch', '--quiet', '--depth=1', 'origin', rev)
        if have(rev):
            return rev, None
    return None, None


def update():
    d, prot, rel = read_manifest()
    now = tracked()
    if now is None:
        print('❌ git 不可用，列不出 src/ 下的文件，无法更新清单')
        return 1
    add = [p for p in now if p not in prot and p not in rel]
    d['_说明'] = HEADER
    d['protected'] = sorted(prot | set(add))
    d.setdefault('released', [])
    MANIFEST.write_text(json.dumps(d, ensure_ascii=False, indent=2) + '\n',
                        encoding='utf-8')
    print('保护清单：%d 个文件（新收 %d 个）' % (len(d['protected']), len(add)))
    for p in add[:20]:
        print('   + %s' % p)
    if len(add) > 20:
        print('   … 还有 %d 个' % (len(add) - 20))
    return 0


def check():
    d, prot, rel = read_manifest()
    if not prot:
        print('❌ src/protected.json 是空的或不存在，先运行 --update')
        return 1
    bad = []

    # 1. 清单里的文件必须还在，且不是空壳
    gone = [p for p in sorted(prot) if not (ROOT / p).is_file()]
    empty = [p for p in sorted(prot)
             if (ROOT / p).is_file() and (ROOT / p).stat().st_size == 0]
    if gone:
        bad.append(('这些文件在保护清单里，但已经从仓库消失', gone))
    if empty:
        bad.append(('这些文件还在，但是空的', empty))

    # 2. src/ 下新加的文件必须登记进清单
    now = tracked()
    if now is None:
        # 开发环境里降级放过。流水线传 PROTECT_REQUIRE_GIT=1，这里必须失败：没有 git 时
        # 第 2、3 条都不运行，而同时删文件和清单条目只有第 3 条拦得住。
        # 容器里没装 git 时，checkout 下载的是 tarball，没有 .git。
        if (os.environ.get('PROTECT_REQUIRE_GIT') or '').strip() not in ('', '0'):
            bad.append(('git 不可用，「新增必须登记」与「清单不许变短」两条没跑成。'
                        '设置了 PROTECT_REQUIRE_GIT，按失败处理。'
                        '常见原因：容器里没装 git，checkout 下载的是 tarball，'
                        '没有 .git 目录', ['git ls-files %s 失败' % SCOPE]))
        else:
            print('ℹ️ git 不可用（如容器里的 ownership 问题），跳过「新增必须登记」'
                  '与「清单不许变短」，「文件必须存在」已检查')
    else:
        miss = [p for p in now if p not in prot and p not in rel]
        if miss:
            bad.append(('这些文件在 src/ 里但不在保护清单里，运行 --update 登记', miss))

    # 3. 清单不许变短：上一版清单里的路径必须仍在 protected 或 released 里。
    #    取不到 base 必须失败，否则浅克隆下这条不运行，同时删文件和清单条目的改动会被放过。
    #    git 完全不可用的情况在第 2 条处理。
    if now is not None:
        rev, skip_why = base_rev()
        if rev:
            prev = at(rev)
            if prev is ABSENT:
                print('ℹ️ %s 上还没有 %s，跳过「清单不许变短」这一条' % (rev, MANIFEST_REL))
            elif prev is BROKEN:
                bad.append(('上一版的保护清单解析失败，无法比对', [rev]))
            else:
                _, pprot, prel = prev
                lost = sorted((pprot | prel) - (prot | rel))
                if lost:
                    bad.append(('保护清单被改短了：这些路径上一版还在，现在 protected 和 released 里都没有',
                                lost))
        elif skip_why:
            print('ℹ️ %s，跳过「清单不许变短」这一条' % skip_why)
        else:
            bad.append((
                '取不到用来比对的上一版，「清单不许变短」这条没跑成，按失败处理。'
                '克隆里没有这个提交，--depth=1 补取也失败。'
                'CI 里请把 checkout 的 fetch-depth 设为 0',
                ['PROTECT_BASE=%s' % (os.environ.get('PROTECT_BASE') or '(未设，回落 HEAD~1)')]))

    # 4. released 每条都要写明谁批准、为什么。
    for r in (d.get('released') or []):
        if not str(r.get('why', '')).strip() or not str(r.get('approved', '')).strip():
            bad.append(('released 里这条没写 approved / why，不算有效放行',
                        [json.dumps(r, ensure_ascii=False)]))

    if not bad:
        print('✅ 保护清单：%d 个文件全部在位（另有 %d 个经批准放行）'
              % (len(prot), len(rel)))
        return 0
    for title, items in bad:
        print('\n❌ %s（%d 个）：' % (title, len(items)))
        for p in items[:30]:
            print('     %s' % p)
        if len(items) > 30:
            print('     … 还有 %d 个' % (len(items) - 30))
    print('\n' + '=' * 72)
    print('src/ 下的汉化只许加不许删。要删文件，先停下来问维护者。')
    print('获批后把路径挪进 src/protected.json 的 released，写上 approved 与 why。')
    print('=' * 72)
    return 1


if __name__ == '__main__':
    if '--update' in sys.argv:
        sys.exit(update())
    if '--check' in sys.argv:
        sys.exit(check())
    sys.exit(__doc__)
