#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# atm10-zh-cn — All the Mods 10 简体中文汉化补丁「绿油油版」
# Copyright (C) 2026 星野夢華 (Hoshino Yumeka)
# SPDX-License-Identifier: GPL-3.0-or-later
"""给随包分发的 VaultPatcher 打两处性能补丁 —— 现拉源、现打、现编、现塞进 jar。

## 为什么

VaultPatcher 只要存在**任意一个** dynamic 模块，就会把
`DynamicReplaceUtils.__mappingString` 注入进这三处（拿真 `Font.class` 喂它的
`VPMinecraftTransformer` 实测过，不是读代码猜的）：

    net.minecraft.client.gui.Font#renderText(String,…)
    net.minecraft.network.chat.contents.PlainTextContents$LiteralContents#<init>(String)
    net.minecraft.network.chat.FormattedText#of(String[,Style])

也就是**游戏每帧画的每一个字符串**都要走一次。而那个方法在开头无条件
`Thread.getStackTrace()`，又对整张替换表做线性 `String.equals`。
GraalVM 21 上实测单次 18.3us（栈遍历 9.4us + 1085 对线性扫 10.2us）。
玩家机器的 spark 采样里它占 Render thread 的 3.45%~9.09%，随玩家装的 HUD 模组增长，
`StackTraceElement.initStackTraceElements` 一度是自身耗时第一名。

补丁只做两件事，都不改行为：栈遍历改成命中之后再取；dyn 模式补一张哈希表做精确查表。
打完实测 18,339ns → 348ns，且 1085 个键的命中/未命中/边界值输出摘要与官方 jar
逐字节相同（`594ab0f8…`）。

## 为什么不走别的路

- **没有配置开关**：`VaultPatcherConfig` 只有 `enableClassPatch` / `loadAllModules`，
  关不掉 dynamic。
- **`vaultpatcher/patch/` 够不着**：那条路是 NeoForge 的 `SimpleClassProcessor`，
  只作用于走 NeoForge 类加载管线的类；VaultPatcher 自己的类由它自己的
  transformation service 加载，不在管线里。
- **删 dynamic 模块能让注入彻底消失**，但要丢 1085 条译文（建筑风格名 828、模组列表名 111）。
- **等上游没用**：1.5.3 的 `DynamicReplaceUtils.java` 与 1.5.2 blob sha 完全相同。

## 闸

全程 fail-closed，任何一步对不上就退出，绝不「跳过」——跳过等于悄悄发一个慢 jar：

1. jar 的 sha256 必须等于 manifest 里钉的（上游换版就当场炸，由人重新核补丁还适不适用）
2. 拉下来的每个源文件 sha256 必须对上
3. 每处 `find` 在原文里**必须命中且只命中一次**
4. 编译产物只允许替换 manifest 里列的那 3 个条目，条目总数必须对上
5. 除这 3 个 + 新增的 `MODIFIED.txt` 外，其余条目必须逐字节不变

## GPL-3.0

VaultPatcher 是 GPL-3.0，本仓库同许可。分发改过的版本要保留许可、注明已修改、
提供对应源码。`src/mods/vaultpatcher/*.json` 加上 manifest 里钉死的 ref/sha256
就是完整的对应源码；本脚本另往 jar 根写一份 `MODIFIED.txt` 说明改了什么。

用法:
    python3 scripts/patch_vaultpatcher.py <出货树>        # 一般是 build/common
"""
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import urllib.request
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from paths import BUILD, SRC                                       # noqa: E402

SPEC = SRC / 'mods' / 'vaultpatcher'
CACHE = BUILD / 'vpcache'
UA = {'User-Agent': 'atm10-zh-cn/1.0 (+https://github.com/chiba233/atm10-zh-cn)'}


def sha256(b):
    return hashlib.sha256(b).hexdigest()


def fetch(url, want, name):
    """按 sha256 取一份东西，缓存在 build/vpcache/<sha256>。哈希对不上就退出。"""
    CACHE.mkdir(parents=True, exist_ok=True)
    c = CACHE / want
    if c.exists() and sha256(c.read_bytes()) == want:
        return c.read_bytes()
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=180) as r:
        data = r.read()
    got = sha256(data)
    if got != want:
        sys.exit('❌ %s 哈希对不上——**不要用这个文件**\n'
                 '   期望 %s\n   实得 %s\n   地址 %s\n'
                 '   要么上游把同一个地址的内容换了，要么下载被人动了手脚。'
                 % (name, want, got, url))
    c.write_bytes(data)
    return data


def apply_edits(text, spec, name):
    """按 src/upstream 那套 {find, replace} 定点替换。命中数不为 1 就退出。"""
    for i, ed in enumerate(spec['edits']):
        find, repl = ''.join(ed['find']), ''.join(ed['replace'])
        n = text.count(find)
        if n != 1:
            sys.exit('❌ %s 第 %d 处补丁命中 %d 次（应为 1）——上游这一段变了，\n'
                     '   补丁不再适用。**不要硬打**，请重新核对：\n%s'
                     % (name, i + 1, n, find[:300]))
        text = text.replace(find, repl)
    return text


def dyn_table(tree):
    """把出货树里全部 dynamic 模块摊成 [{t: 目标类, p: [[key, value], …]}, …]。

    一个 target_class 生成一条 TranslationInfo（`VaultPatcherModule.read` 就是这么做的），
    多个 target_class 共享同一份 pairs。
    """
    out = []
    for f in sorted((tree / 'vaultpatcher' / 'modules').glob('*.json')):
        d = json.loads(f.read_text(encoding='utf-8'))
        if isinstance(d, dict):
            d = [d]
        hdr = d[0] if d and 'dynamic' in d[0] else {}
        if not hdr.get('dynamic'):
            continue
        for m in d:
            if 'pairs' not in m:
                continue
            tc = m.get('target_class') or ['']
            if isinstance(tc, str):
                tc = [tc]
            pl = [[p.get('key', p.get('k', '')), p.get('value', p.get('v', ''))]
                  for p in (m['pairs'] or [])]
            for t in tc:
                out.append({'t': t, 'p': pl})
    return out


def equivalence_gate(man, tree, official, patched, work):
    """官方 jar 与补丁 jar 对同一张表的输出摘要必须逐字节相同。

    只证「只改了三个 class」不够——改坏了行为同样只改这三个 class。这道闸跑的是
    真实的 1085 对表：命中路径（从与 target_class 同名的调用方发起）、未命中路径、
    以及空串/空白/未知串这几个边界值，把全部输出拼起来取 sha256 比对。
    """
    table = dyn_table(tree)
    if not table:
        sys.exit('❌ 出货树里一个 dynamic 模块都没有——等价闸没有输入，'
                 '不能当作「通过」。请检查 assemble.py 是否摊了 vaultpatcher/modules/。')
    tf = work / 'dyn_table.json'
    tf.write_text(json.dumps(table, ensure_ascii=False), encoding='utf-8')

    cp = [str(CACHE / d['sha256'])
          for k, d in list(man['deps'].items()) + list(man['verify']['deps'].items())
          if not k.startswith('_')]
    for name, d in man['verify']['deps'].items():
        if not name.startswith('_'):
            fetch(d['url'], d['sha256'], name)

    digests = {}
    for tag, j in (('官方', official), ('补丁', patched)):
        out = work / ('vcls-' + tag)
        out.mkdir()
        srcs = [str(p) for p in sorted((SPEC / 'verify').rglob('*.java'))]
        r = subprocess.run(['javac', '-nowarn', '-encoding', 'UTF-8',
                            '-cp', ':'.join([str(j)] + cp), '-d', str(out)] + srcs,
                           capture_output=True, text=True)
        if r.returncode != 0:
            sys.exit('❌ 等价闸的对拍程序编译失败（%s）：\n%s\n%s' % (tag, r.stdout, r.stderr))
        r = subprocess.run(['java', '-cp', ':'.join([str(j)] + cp + [str(out)]),
                            'Verify', str(tf)], capture_output=True, text=True)
        if r.returncode != 0:
            sys.exit('❌ 等价闸的对拍程序跑失败（%s）：\n%s\n%s' % (tag, r.stdout, r.stderr))
        digests[tag] = r.stdout.strip()
        print('  等价对拍 %s jar：%s' % (tag, digests[tag]))

    if digests['官方'] != digests['补丁']:
        sys.exit('❌ **补丁改变了行为** —— 两个 jar 的输出摘要不同：\n'
                 '   官方 %s\n   补丁 %s\n'
                 '   这个包绝不能发。请回去核对 src/mods/vaultpatcher/*.json。'
                 % (digests['官方'], digests['补丁']))
    print('  等价闸：两个 jar 输出逐字节相同 ✅')


def main(tree):
    tree = Path(tree)
    man = json.loads((SPEC / 'manifest.json').read_text(encoding='utf-8'))

    jar = tree / man['jar']['path']
    if not jar.is_file():
        sys.exit('❌ 没有 %s——fetch_mods.py 没跑？' % jar)
    got = sha256(jar.read_bytes())
    if got != man['jar']['sha256']:
        sys.exit('❌ %s 不是补丁写的那一版\n   期望 %s\n   实得 %s\n'
                 '   VaultPatcher 升级了就必须重新核对 src/mods/vaultpatcher/*.json\n'
                 '   还适不适用——**不许照旧打**。' % (jar, man['jar']['sha256'], got))

    java = shutil.which('javac')
    if not java:
        sys.exit('❌ 找不到 javac。本步骤要编译两个 java 文件（见本脚本 docstring）。\n'
                 '   装一个 JDK %d+，或者明确决定不发补丁版——但**不能悄悄跳过**：\n'
                 '   跳过等于发一个每帧多花几毫秒的 jar，而没人会发现。'
                 % man['release']['target'])

    work = Path(tempfile.mkdtemp(prefix='vp-'))
    try:
        # 1) 拉上游源、核哈希、打补丁
        srcdir = work / 'src'
        for name, want in man['upstream']['sources'].items():
            spec = json.loads((SPEC / (name + '.json')).read_text(encoding='utf-8'))
            raw = fetch(man['upstream']['raw'] + spec['src'], want, name).decode('utf-8')
            out = srcdir / spec['src'].split('src/main/java/', 1)[1]
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(apply_edits(raw, spec, name), encoding='utf-8')
            print('  打补丁 %-26s %d 处' % (name, len(spec['edits'])))

        # 2) 拉编译依赖
        cp = [str(jar)]
        for name, d in man['deps'].items():
            if name.startswith('_'):
                continue
            fetch(d['url'], d['sha256'], name)
            cp.append(str(CACHE / d['sha256']))

        # 3) 编译
        classes = work / 'classes'
        classes.mkdir()
        cmd = ['javac', '-nowarn', '-encoding', 'UTF-8',
               '--release', str(man['release']['target']),
               '-cp', ':'.join(cp), '-d', str(classes)] + \
              [str(p) for p in sorted(srcdir.rglob('*.java'))]
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode != 0:
            sys.exit('❌ 编译失败：\n%s\n%s' % (r.stdout, r.stderr))

        # 4) 换进 jar：保持条目顺序，时间戳钉死 1980（可复现）
        want_entries = set(man['replace_entries']['entries'])
        built = {str(p.relative_to(classes)): p.read_bytes()
                 for p in classes.rglob('*.class')}
        missing = want_entries - set(built)
        extra = set(built) - want_entries
        if missing or extra:
            sys.exit('❌ 编译产物与 manifest 对不上\n   少了: %s\n   多了: %s'
                     % (sorted(missing), sorted(extra)))

        # class 版本必须与被替换的那一个一致。编高了同一个 jar 里版本参差，老 JVM 直接
        # 加载不了；而 --release 写错在只有低版本 JDK 的构建容器上才会暴露（CI 上炸过一次）。
        src_zip0 = zipfile.ZipFile(jar)
        with src_zip0:
            for name, data in built.items():
                a = int.from_bytes(src_zip0.read(name)[6:8], 'big')
                b = int.from_bytes(data[6:8], 'big')
                if a != b:
                    sys.exit('❌ %s 编出来是 class 版本 %d，jar 里原本是 %d\n'
                             '   manifest 的 release.target 要对齐**jar 里原有的 class 版本**，'
                             '不是对齐运行时。' % (name, b, a))

        note = ('本 jar 由 atm10-zh-cn 修改过（GPL-3.0 第 5 条）。\n\n'
                '基线：VaultPatcher %s（sha256 %s）\n'
                '改动：%s\n\n'
                '改动内容与理由见 src/mods/vaultpatcher/ 下的 manifest.json 与两个补丁映射，\n'
                '构建脚本 scripts/patch_vaultpatcher.py。\n'
                '仓库：https://github.com/chiba233/atm10-zh-cn\n'
                % (man['upstream']['ref'], man['jar']['sha256'],
                   '、'.join(sorted(n for n in man['upstream']['sources']))))

        src_zip = zipfile.ZipFile(jar)
        out_path = work / 'patched.jar'
        with src_zip, zipfile.ZipFile(out_path, 'w', zipfile.ZIP_DEFLATED) as dst:
            for info in src_zip.infolist():
                data = built.get(info.filename) or src_zip.read(info.filename)
                ni = zipfile.ZipInfo(info.filename, date_time=(1980, 1, 1, 0, 0, 0))
                ni.compress_type = info.compress_type
                ni.external_attr = info.external_attr
                dst.writestr(ni, data)
            ni = zipfile.ZipInfo('MODIFIED.txt', date_time=(1980, 1, 1, 0, 0, 0))
            dst.writestr(ni, note.encode('utf-8'))

        # 5) 闸：除这 3 个 class + MODIFIED.txt 外，其余必须逐字节不变
        a, b = zipfile.ZipFile(jar), zipfile.ZipFile(out_path)
        with a, b:
            na, nb = {i.filename for i in a.infolist()}, {i.filename for i in b.infolist()}
            if nb - na != {'MODIFIED.txt'} or na - nb:
                sys.exit('❌ jar 条目集合变了：新增 %s，删除 %s'
                         % (sorted(nb - na - {'MODIFIED.txt'}), sorted(na - nb)))
            changed = {n for n in na if a.read(n) != b.read(n)}
            if changed != want_entries:
                sys.exit('❌ 变动的条目不是预期的那三个\n   实际变动: %s\n   预期: %s'
                         % (sorted(changed), sorted(want_entries)))
            total = man['replace_entries']['total_entries']
            if len(na) != total:
                sys.exit('❌ jar 条目数 %d ≠ manifest 记的 %d' % (len(na), total))

        # 6) 等价闸：拿本包真实的替换表，两个 jar 各跑一遍，输出摘要必须一样
        equivalence_gate(man, tree, jar, out_path, work)

        shutil.move(str(out_path), str(jar))
        print('  已替换 %d 个 class + 写入 MODIFIED.txt，其余 %d 个条目逐字节未动'
              % (len(want_entries), len(na) - len(want_entries)))
        print('VaultPatcher 性能补丁：完成')
    finally:
        shutil.rmtree(work, ignore_errors=True)


if __name__ == '__main__':
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(sys.argv[1])
