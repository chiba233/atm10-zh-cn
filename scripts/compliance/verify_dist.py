#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# atm10-zh-cn — All the Mods 10 简体中文汉化补丁「绿油油版」
# Copyright (C) 2026 星野夢華 (Hoshino Yumeka)
# SPDX-License-Identifier: GPL-3.0-or-later
"""打包后解开 zip 逐项清点内容，是发版前的最后一项检查。

汉化产物在构建时生成，生成器少产出或没运行时，打出的包结构完整但没有汉化，上传、发版都不会报错。
`build_dist.sh` 开头只查文件是否存在，0 字节的 lang、全透明的横幅、只剩 3 条键的资源包都能通过。
所以这里查数量：每一项都按实测值设下限，低于下限说明这一环生成失败。

用法:
    python3 scripts/verify_dist.py dist/atm10-zh_cn-client-r12-atm7.2.zip
    python3 scripts/verify_dist.py dist/*.zip
"""
import hashlib
import io
import json
import re
import sys
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # scripts/ 下的公共模块

import toolchain

# 客户端包的下限，取实测值的九成左右：容得下上游增删的正常波动，拦得住整块丢失。
# 去掉 7.0/7.1/7.2 三版都不存在的 236 个模组的 lang 后：lang 362 个文件、17.7 万键，导览书 1683 个。
CLIENT_MIN = {
    'lang_files':   330,    # 实测 362 个 lang/*.json
    'lang_keys': 160000,    # 实测 17.7 万条
    'banners':      190,    # 实测 200 张
    'buttons':       14,    # 14 张主菜单按钮
    'vp_modules':   140,    # 152 个 VaultPatcher 模块
    'quest_delta':   30,    # 34 个任务书 delta
    'gui_files':     20,    # 24 个 RFTools .gui
    # 导览书文件数。CI 实测 1269 个 = 生成的 987 个 + src/ 里静态的 325 个（两者有少量重叠）。
    # 不要用开发机上玩过的实例做基准，那里装了官方包以外的 mod，书更多。
    # 下限 1200 容得下上游增删，拦得住整块丢失。97 个书本文件被误删时数字降到 1172，其中有
    # 27 篇 Ars Nouveau 图鉴页和 12 篇 Just Dire Things 页。所以这个数不许为了让 CI
    # 变绿而下调：它掉下去，先查是不是删错了东西。
    'book_files':  1200,
}
SERVER_MIN = {
    'vp_modules':    10,
    'quest_delta':   30,
}


def inner_pack(z):
    """客户端包里那个资源包 zip"""
    for n in z.namelist():
        if '/resourcepacks/' in n and n.endswith('.zip'):
            return n, zipfile.ZipFile(io.BytesIO(z.read(n)))
    return None, None


def check(path):
    z = zipfile.ZipFile(path)
    names = z.namelist()
    is_client = any('/resourcepacks/' in n for n in names)
    bad = []
    got = {}

    got['vp_modules'] = sum(1 for n in names if '/vaultpatcher/modules/' in n and n.endswith('.json'))
    got['quest_delta'] = sum(1 for n in names
                             if '/quests/lang/zh_cn' in n and n.endswith('.snbt'))

    if is_client:
        pname, pz = inner_pack(z)
        if pz is None:
            return ['没有资源包 zip'], {}, True
        pn = pz.namelist()
        lang = [n for n in pn if re.fullmatch(r'assets/[^/]+/lang/zh_cn\.json', n)]
        got['lang_files'] = len(lang)
        keys = 0
        for n in lang:
            try:
                keys += len(json.loads(pz.read(n).decode('utf-8-sig')))
            except Exception:
                bad.append('%s 不是合法 JSON' % n)
        got['lang_keys'] = keys
        got['banners'] = sum(1 for n in pn if '/questpics/' in n and n.endswith('.png'))
        got['gui_files'] = sum(1 for n in pn if n.endswith('.gui'))
        got['book_files'] = sum(1 for n in pn if 'patchouli_books' in n
                                or 'ae2guide' in n or 'oracle-index' in n)
        got['buttons'] = sum(1 for n in names
                             if '/config/fancymenu/assets/' in n and n.endswith('.png'))
        # 资源包描述里的版本号要和文件名对得上
        try:
            desc = json.loads(pz.read('pack.mcmeta'))['pack']['description']
        except Exception:
            desc = ''
            bad.append('pack.mcmeta 读不出来')
        mc = re.search(r'-atm([0-9.]+)\.zip$', str(path))
        if mc and mc.group(1) not in desc:
            bad.append('pack.mcmeta 描述 %r 与文件名里的 atm%s 对不上' % (desc, mc.group(1)))
        if '@@' in desc:
            bad.append('pack.mcmeta 里的占位符没被替换: %r' % desc)
        if mc and ('汉化包-%s.zip' % mc.group(1)) not in pname:
            bad.append('资源包文件名 %r 与 atm%s 对不上' % (pname, mc.group(1)))

    # 说明文档必须在包里，并且叫这个名字：多数人从别处拿到 zip，不会去看 GitHub 上的 README。
    README = '请安装前务必看我.md'
    if README not in [n.rsplit('/', 1)[-1] for n in names]:
        bad.append('包里没有「%s」，从别处拿到 zip 的玩家看不到说明' % README)

    # 占位符必须已被打包脚本填掉。查包里全部文本文件，不只查安装器：SERVER.md 写死过
    # 「适用于 ATM10 7.2 专用服务器」，7.0 / 7.1 的包里也印着 7.2。
    TEXT = ('.sh', '.ps1', '.bat', '.md', '.txt', '.json', '.snbt', '.js', '.mcmeta', '.url')
    # 这几份项目文档原样分发，正文会提到占位符本身（CHANGELOG 讲到这套机制），不算漏填。
    # 「请安装前务必看我.md」不在名单里：客户端那份是 README 原样复制（没有占位符），
    # 服务端那份由 SERVER.md 填入版本号生成，必须检查。
    VERBATIM = ('CHANGELOG.md', 'CONTRIBUTING.md', 'LICENSE', '致谢与技术说明.md')
    for n in names:
        if not n.endswith(TEXT) or n.rsplit('/', 1)[-1] in VERBATIM:
            continue
        body = z.read(n).decode('utf-8', 'replace')
        m = re.search(r'@@[A-Z_]+@@', body)
        if m:
            bad.append('%s 里还有未替换的占位符 %s' % (n, m.group(0)))

    for k, lo in (CLIENT_MIN if is_client else SERVER_MIN).items():
        v = got.get(k, 0)
        if v < lo:
            bad.append('%s 只有 %d，低于下限 %d，这一环多半没有生成' % (k, v, lo))
    return bad, got, is_client


def zip_digest(path):
    """zip 内容的确定性指纹，只计入路径与文件内容。

    zip 头里有时间戳和压缩器版本，同样的内容换个时间打包就是另一个哈希，所以不对整个 zip 取 sha256。
    """
    h = hashlib.sha256()
    with zipfile.ZipFile(path) as z:
        for n in sorted(x.filename for x in z.infolist() if not x.is_dir()):
            h.update(n.encode())
            h.update(b'\0')
            h.update(hashlib.sha256(z.read(n)).digest())
    return h.hexdigest()


def check_reproducible(paths):
    """标准工具链下，产物内容指纹必须与仓库记录的一致。

    src/toolchain.lock.json 固定了镜像、Pillow 与字体，产物字节可以比对。只在标准环境里比对，
    其他环境也能构建，只是跳过这一节并说明已跳过。
    """
    ok, _env, diff, _missing = toolchain.status()
    print('\n工具链: %s' % toolchain.stamp())
    if not ok:
        print('ℹ️ 不是标准构建环境，跳过产物字节比对（%s）' % ' / '.join(diff[:2]))
        return []
    rec = Path(__file__).resolve().parent.parent / 'versions' / 'dist.sha256'
    have = json.loads(rec.read_text(encoding='utf-8')) if rec.is_file() else {}
    bad, news = [], {}
    for p in paths:
        name = re.sub(r'-[rvR][^-]*-', '-<版本>-', Path(p).name)
        d = zip_digest(p)
        if name not in have:
            news[name] = d
        elif have[name] != d:
            bad.append('%s 的内容指纹与 versions/dist.sha256 不符\n'
                       '       记录 %s\n       实得 %s' % (name, have[name], d))
    if news:
        print('ℹ️ versions/dist.sha256 里还没记这几项，核对无误后写进去：')
        for k, v in sorted(news.items()):
            print('     %s  %s' % (v, k))
    return bad


def main(paths):
    fail = 0
    for p in paths:
        bad, got, is_client = check(p)
        tag = '客户端' if is_client else '服务端'
        if bad:
            fail += 1
            print('❌ %s [%s]' % (p, tag))
            for b in bad:
                print('     ', b)
        else:
            print('✅ %s [%s]  %s' % (p, tag,
                  '  '.join('%s=%s' % (k, v) for k, v in sorted(got.items()))))
    repro = check_reproducible(paths)
    for b in repro:
        print('  ❌ ', b)
    if fail or repro:
        sys.exit('\n❌ %d 个包没通过内容核验，不要发布' % (fail + len(repro)))
    print('\n全部通过内容核验')


if __name__ == '__main__':
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    main(sys.argv[1:])
