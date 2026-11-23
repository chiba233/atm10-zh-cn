#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# atm10-zh-cn — All the Mods 10 简体中文汉化补丁「绿油油版」
# Copyright (C) 2026 星野夢華 (Hoshino Yumeka)
# SPDX-License-Identifier: GPL-3.0-or-later
"""验保护闸自己会不会红。

一道从来没被触发过的闸，和没有这道闸是一回事。这里在临时目录里建一个
玩具 git 仓库，把 protect.py 拿过去，逐个造出它应该拦下的局面，
再确认它确实退出 1。哪一条拦不住，这个脚本就红。

用法:
    python3 scripts/test_protect.py
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # scripts/ 下的公共模块

SELF = Path(__file__).resolve().parent / 'protect.py'


def sh(*a, **kw):
    return subprocess.run(a, capture_output=True, text=True, **kw)


def run(repo, *args, base=None, break_git=False, extra_env=None):
    env = dict(os.environ)
    env.pop('PROTECT_REQUIRE_GIT', None)      # 别让外面的流水线环境影响用例
    if base:
        env['PROTECT_BASE'] = base
    if extra_env:
        env.update(extra_env)
    if break_git:
        # 造一个必定退 128 的假 git 顶在 PATH 前面，模拟出货容器里那种
        # `detected dubious ownership`，真出过这个事故。
        shim = Path(repo) / '.shim'
        shim.mkdir(exist_ok=True)
        (shim / 'git').write_text('#!/bin/sh\nexit 128\n')
        (shim / 'git').chmod(0o755)
        env['PATH'] = '%s:%s' % (shim, env.get('PATH', ''))
    return subprocess.run([sys.executable, 'scripts/compliance/protect.py', *args],
                          cwd=repo, capture_output=True, text=True, env=env)


def setup(tmp):
    """玩具仓库：src/ 下三个汉化文件，已收进保护清单并提交。"""
    repo = Path(tmp) / 'toy'
    (repo / 'scripts' / 'compliance').mkdir(parents=True)
    (repo / 'src' / 'pack').mkdir(parents=True)
    shutil.copy(SELF, repo / 'scripts' / 'compliance' / 'protect.py')
    for n in ('a', 'b', 'c'):
        (repo / 'src' / 'pack' / ('%s.json' % n)).write_text('{"k":"译文"}\n',
                                                             encoding='utf-8')
    sh('git', 'init', '-q', '-b', 'main', cwd=repo)
    sh('git', 'config', 'user.email', 't@t', cwd=repo)
    sh('git', 'config', 'user.name', 't', cwd=repo)
    sh('git', 'add', '-A', cwd=repo)
    sh('git', 'commit', '-q', '--no-gpg-sign', '-m', 'init', cwd=repo)
    run(repo, '--update')
    sh('git', 'add', '-A', cwd=repo)
    sh('git', 'commit', '-q', '--no-gpg-sign', '-m', 'manifest', cwd=repo)
    return repo


CASES = []


def case(name):
    def deco(fn):
        CASES.append((name, fn))
        return fn
    return deco


@case('干净状态应当通过')
def t_clean(repo):
    return run(repo, '--check').returncode == 0


@case('删掉一个受保护的汉化文件 → 必须红')
def t_delete(repo):
    (repo / 'src' / 'pack' / 'b.json').unlink()
    r = run(repo, '--check')
    return r.returncode == 1 and 'src/pack/b.json' in r.stdout


@case('把文件清空（留个空壳）→ 必须红')
def t_empty(repo):
    (repo / 'src' / 'pack' / 'b.json').write_text('', encoding='utf-8')
    r = run(repo, '--check')
    return r.returncode == 1 and '是空的' in r.stdout


@case('新增汉化没收进清单 → 必须红')
def t_uncovered(repo):
    (repo / 'src' / 'pack' / 'd.json').write_text('{"k":"新"}\n', encoding='utf-8')
    sh('git', 'add', '-A', cwd=repo)
    r = run(repo, '--check')
    return r.returncode == 1 and 'src/pack/d.json' in r.stdout


@case('删文件的同时把它从清单里抹掉（洗白）→ 必须红')
def t_launder(repo):
    (repo / 'src' / 'pack' / 'b.json').unlink()
    m = repo / 'src' / 'protected.json'
    d = json.loads(m.read_text(encoding='utf-8'))
    d['protected'] = [p for p in d['protected'] if p != 'src/pack/b.json']
    m.write_text(json.dumps(d, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    sh('git', 'add', '-A', cwd=repo)
    r = run(repo, '--check', base='HEAD')
    return r.returncode == 1 and '被改短' in r.stdout


@case('放行但不写理由 → 必须红')
def t_released_no_why(repo):
    (repo / 'src' / 'pack' / 'b.json').unlink()
    m = repo / 'src' / 'protected.json'
    d = json.loads(m.read_text(encoding='utf-8'))
    d['protected'] = [p for p in d['protected'] if p != 'src/pack/b.json']
    d['released'] = [{'path': 'src/pack/b.json'}]
    m.write_text(json.dumps(d, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    sh('git', 'add', '-A', cwd=repo)
    r = run(repo, '--check', base='HEAD')
    return r.returncode == 1 and 'approved' in r.stdout


@case('放行且写明谁批的、为什么 → 放过')
def t_released_ok(repo):
    (repo / 'src' / 'pack' / 'b.json').unlink()
    m = repo / 'src' / 'protected.json'
    d = json.loads(m.read_text(encoding='utf-8'))
    d['protected'] = [p for p in d['protected'] if p != 'src/pack/b.json']
    d['released'] = [{'path': 'src/pack/b.json', 'approved': '用户',
                      'date': '2026-07-27', 'why': '用户在对话里点名要删'}]
    m.write_text(json.dumps(d, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    sh('git', 'add', '-A', cwd=repo)
    return run(repo, '--check', base='HEAD').returncode == 0


@case('git 用不了时不许崩，干净状态照样放过')
def t_nogit_clean(repo):
    r = run(repo, '--check', break_git=True)
    return r.returncode == 0 and 'Traceback' not in r.stderr


@case('git 用不了时**仍然**要拦下删除（那条不依赖 git）')
def t_nogit_delete(repo):
    (repo / 'src' / 'pack' / 'b.json').unlink()
    r = run(repo, '--check', break_git=True)
    return (r.returncode == 1 and 'src/pack/b.json' in r.stdout
            and 'Traceback' not in r.stderr)


@case('声明了 PROTECT_REQUIRE_GIT 而 git 用不了 → 必须红')
def t_require_git(repo):
    # build.yml 的容器镜像里没有 git，checkout 就退化成 REST API 下 tarball，
    # 压根不建 .git 目录。于是「新增必须登记」和「清单不许变短」两条在出货流水线里
    # 一次都没跑过，而闸退 0。流水线一律传这个变量，让「闸没跑成」变成红。
    r = run(repo, '--check', break_git=True, extra_env={'PROTECT_REQUIRE_GIT': '1'})
    return r.returncode == 1 and '没跑成' in r.stdout and 'Traceback' not in r.stderr


@case('base 指向克隆里没有的提交 → 必须红（不许静默跳过）')
def t_base_missing(repo):
    # 上面那条 t_launder 传的是 base='HEAD'，在完整仓库里永远解析得出来，
    # 所以它从没走过「base 取不到」这条分支。而 CI 里恰恰常常取不到：
    # ci.yml 曾用 fetch-depth: 2 而 github.event.before 在三笔之外，
    # build.yml 的 checkout 连 fetch-depth 都没写（默认 1）。
    # 那时闸打一行 ℹ️ 然后退 0，洗白式改动正好能从这里整个漏过去。
    r = run(repo, '--check', base='0123456789abcdef0123456789abcdef01234567')
    return r.returncode == 1 and '没跑成' in r.stdout


@case('base 是全零 sha（新建分支首次 push）→ 放过')
def t_base_zero(repo):
    # github.event.before 在这种 push 上就是全零，确实没有可比的上一版。
    r = run(repo, '--check', base='0' * 40)
    return r.returncode == 0 and '全零' in r.stdout


@case('真·浅克隆里拿不到 HEAD~1 → 必须红')
def t_shallow_clone(repo):
    shallow = repo.parent / 'shallow'
    sh('git', 'clone', '--quiet', '--depth=1', 'file://%s' % repo, str(shallow))
    if not (shallow / 'src' / 'protected.json').is_file():
        return False                                  # 克隆没成，测试本身失效
    r = run(shallow, '--check')                        # 不传 base，回落 HEAD~1
    return r.returncode == 1 and '没跑成' in r.stdout


@case('--update 只会加，不会把消失的文件从清单里抹掉')
def t_update_never_removes(repo):
    (repo / 'src' / 'pack' / 'b.json').unlink()
    sh('git', 'add', '-A', cwd=repo)
    run(repo, '--update')
    d = json.loads((repo / 'src' / 'protected.json').read_text(encoding='utf-8'))
    return 'src/pack/b.json' in d['protected'] and run(repo, '--check').returncode == 1


def main():
    fail = 0
    for name, fn in CASES:
        tmp = tempfile.mkdtemp()
        try:
            ok = fn(setup(tmp))
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
        print('%s %s' % ('✅' if ok else '❌', name))
        fail += 0 if ok else 1
    print('\n%d/%d 条通过' % (len(CASES) - fail, len(CASES)))
    return 1 if fail else 0


if __name__ == '__main__':
    sys.exit(main())
