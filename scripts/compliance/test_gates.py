#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# atm10-zh-cn — All the Mods 10 简体中文汉化补丁「绿油油版」
# Copyright (C) 2026 星野夢華 (Hoshino Yumeka)
# SPDX-License-Identifier: GPL-3.0-or-later
"""闸的反例测试：造一批**故意违规**的样本，验每道闸真的会红。

## 为什么需要它

「写了闸」不等于「有闸」。2026-07-28 的对抗审计一次抓到三种假象：

- `check_gui_maps.py` / `check_dynamic_substrings.py` 写完了**从没接进任何流水线**；
- `vp-config-ui-no-single-word` 只查一个模块文件，另一份完全没保护；
- 好几个检查器在 glob 命中 0 个文件时**静默通过**，源文件被挪走闸就悄悄消失。

三种假象的共同点：跑一遍全绿，看起来一切正常。**只有拿反例去撞，才知道闸是不是实心的。**

## 反例长什么样

每条反例都复刻一次**真实事故**，而且都是「在游戏里绝不会生效」的假翻译——
它们只存在于临时目录里的夹具，跑完即弃：

| 反例 | 复刻的事故 |
|---|---|
| 模块里塞 `top horizontal` | 译了 blockui 的对齐标志串，整个 MineColonies/建筑棒对齐失效 |
| 配置模块塞单词键 `Sound` | 单词可能同时是枚举值，译了会被反查/写回配置 |
| 两条 `@` 子串键互为子串 | `String.replace` 顺序不定，长的那条被啃掉，翻出半中半英 |
| `class_patch: true` | 数据目录变成代码执行入口 |
| `vaultpatcher/patch/` 下留 `.class` | 旧补丁复活 → ClassFormatError 闪退 |
| 标识符样式的键 | 被拿去构造 ResourceLocation → 注册崩 |
| 以 `/` 开头的键 | 译了建筑棒的类别路径，查表落空 → NPE 闪退（issue #3） |

第二组反例撞的是另一种假象：**前提不在时静默放过**。检查的前提（生成物、入库的
数据文件、mod jar）缺失时打一行 ℹ️ 然后返回成功，退出码跟「查过了没问题」一样。
`protect.py` 就这么把两条闸关了整整一个版本。跑在生成之后的环节一律传
`GATE_STRICT=1`，让「闸没跑成」变成红；`ci.yml` 用 `--no-jars`，那边**不设**。

## 为什么不会进出货包

夹具全部在**临时目录**里现造现删，仓库里一个假翻译文件都不留；
`assemble.py` 只摊 `src/`，`scripts/` 与临时目录都不进出货树。
出货侧另有 `vp-no-stray-class-patch` 等闸兜底。

用法:
    python3 scripts/compliance/test_gates.py
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
CHECK = ROOT / 'scripts' / 'check.py'

# (名字, 怎么把违规注入到一棵临时出货树 / 临时模块目录, 期望报出的规则 id)
CASES = []


def case(name, rule_id):
    def deco(fn):
        CASES.append((name, fn, rule_id))
        return fn
    return deco


@case('译了 blockui 的对齐标志串', 'vp-blockui-alignment-tags')
def _c1(mods):
    p = mods / 'blockui.json'
    d = json.loads(p.read_text(encoding='utf-8'))
    d[1]['pairs'].append({'key': 'top horizontal', 'value': '顶部水平'})
    p.write_text(json.dumps(d, ensure_ascii=False), encoding='utf-8')


@case('配置界面模块出现单词键', 'vp-config-ui-no-single-word')
def _c2(mods):
    p = mods / 'catnip_config_ui.json'
    d = json.loads(p.read_text(encoding='utf-8'))
    d[1]['pairs'].append({'key': 'Sound', 'value': '音效'})
    p.write_text(json.dumps(d, ensure_ascii=False), encoding='utf-8')


@case('标识符样式的键被译', 'vp-identifier-not-translated')
def _c3(mods):
    p = mods / 'blockui.json'
    d = json.loads(p.read_text(encoding='utf-8'))
    d[1]['pairs'].append({'key': 'open_upgrade_screen', 'value': '打开升级界面'})
    p.write_text(json.dumps(d, ensure_ascii=False), encoding='utf-8')


@case('两条 @ 子串键互为子串', 'DYNSUB')
def _c4(mods):
    p = mods / 'minecolonies_styles.json'
    d = json.loads(p.read_text(encoding='utf-8'))
    d[1]['pairs'] += [{'key': 'Frontier', 'value': '@边疆'},
                      {'key': 'Farthest Frontier', 'value': '@最远边疆'}]
    p.write_text(json.dumps(d, ensure_ascii=False), encoding='utf-8')


@case('class_patch 被留开', 'vp-class-patch-off')
def _c5(mods):
    p = mods.parent.parent / 'config' / 'vaultpatcher_asm' / 'config.json'
    if not p.is_file():
        return
    d = json.loads(p.read_text(encoding='utf-8'))
    d['class_patch'] = True
    p.write_text(json.dumps(d, ensure_ascii=False), encoding='utf-8')


@case('路径片段被当界面文字译', 'vp-no-path-prefix-keys')
def _c7(mods):
    p = mods / 'minecolonies_styles.json'
    d = json.loads(p.read_text(encoding='utf-8'))
    d[1]['pairs'].append({'key': '/luxury', 'value': '@/豪华'})
    p.write_text(json.dumps(d, ensure_ascii=False), encoding='utf-8')


@case('停发的配置界面模块漏回出货树', 'vp-never-ship-config-ui')
def _c8(mods):
    # r14 那次事故的形状：模块本该被 PERF_HOLD 排除，却因为脏 build/ 或排除逻辑失效
    # 又回到了包里。它一进包，全局替换表就从 1086 对涨回 3396 对，掉帧照旧。
    (mods / 'config_ui_generated.json').write_text(
        json.dumps([{'name': 'x', 'dynamic': True, 'i18n': False},
                    {'target_class': ['net.createmod.catnip.config.ui.BaseConfigScreen'],
                     'pairs': [{'key': 'Advanced Capacity', 'value': '进阶容量'}]}],
                   ensure_ascii=False), encoding='utf-8')


@case('同一个任务键落在两份文件里', 'quest-delta-no-duplicate-keys')
def _c11(mods):
    # gen_quest_lang_patches.py 之后，出货树里一个任务键只许由一份文件持有：
    # splitter 在 chapters/ 里根本不排序（Files.list 直接 forEach），
    # 落在两份文件里就等于「谁生效看 ext4 的哈希序」。
    d = mods.parent.parent / 'config' / 'ftbquests' / 'quests' / 'lang' / 'zh_cn' / 'chapters'
    d.mkdir(parents=True, exist_ok=True)
    key = '\tquest.0000A88BB40B2149.quest_desc: ["闸探针"]\n'
    for n in ('aaa_gate_probe_one.snbt', 'aaa_gate_probe_two.snbt'):
        (d / n).write_text('{\n' + key + '}\n', encoding='utf-8')


@case('两个客户端脚本重名声明', 'client-scripts-no-duplicate-decl')
def _c10(mods):
    # 2026-08-01 实机事故的形状：KubeJS client_scripts 共用一个全局作用域，
    # 第二个 `const $Component` 抛 redeclaration，整批脚本一起加载失败。
    d = mods.parent.parent / 'kubejs' / 'client_scripts'
    d.mkdir(parents=True, exist_ok=True)
    for n in ('aaa_gate_probe_one.js', 'aaa_gate_probe_two.js'):
        (d / n).write_text("const $Component = Java.loadClass('net.minecraft.network.chat.Component')\n",
                           encoding='utf-8')


@case('try 块内部写 const', 'js-no-const-inside-block')
def _c12(mods):
    # 2026-08-01 实机事故的形状：KubeJS 的 Rhino 把块里的 const 提升成函数作用域的
    # var，执行到声明那句抛 redeclaration of var——加载阶段 0 errors，躺在事件回调里
    # 就表现成「进游戏什么都没发生」。前三句是对照：顶格、回调体顶层、块里的赋值，
    # 上游天天在用，一条都不许被拦。
    d = mods.parent.parent / 'kubejs' / 'client_scripts'
    d.mkdir(parents=True, exist_ok=True)
    (d / 'aaa_gate_probe_block.js').write_text(
        "const TopLevelIsFine = Java.loadClass('net.minecraft.network.chat.Component')\n"
        "ClientEvents.loggedIn(event => {\n"
        "  const CallbackTopIsFine = Java.loadClass('java.util.HashSet')\n"
        "  let assignedLater = null\n"
        "  try {\n"
        "    assignedLater = Java.loadClass('java.util.ArrayList')\n"
        "    const InsideTryIsFatal = Java.loadClass('org.apache.http.impl.client.HttpClients')\n"
        "  } catch (err) {}\n"
        "})\n", encoding='utf-8')


@case('同一个类的同一条原文有两句译文', 'vp-no-conflicting-values')
def _c13(mods):
    # 2026-08-07 的形状：rftoolsbase.json 与 rftoolsbase_filter_zh.json 对同一个
    # GuiFilterModule 的「Filter ignoring damage」各写了一句（「忽略耐久值」与
    # 「忽略损伤值」）。谁生效取决于模块加载顺序与表内顺序——改了其中一句进游戏
    # 没变化，还查不出为什么。
    p = mods / 'ae2.json'
    d = json.loads(p.read_text(encoding='utf-8'))
    d[1]['pairs'] += [{'key': 'Gate Probe Filter Line', 'value': '闸探针甲'},
                      {'key': 'Gate Probe Filter Line', 'value': '闸探针乙'}]
    p.write_text(json.dumps(d, ensure_ascii=False), encoding='utf-8')


@case('Extended 被译成 ExpandedAE 那件东西的名字', 'vp-ae-provider-family')
def _c14(mods):
    # 2026-08-07 的形状：两张升级卡把 Extended（AE2扩展的 ME扩展样板供应器）与
    # Expanded（ExpandedAE 的拓充样板供应器）对调了。对调之后两句话各自读起来
    # 都通顺，只有把原文里的词和译文里的词绑起来才判得了。
    p = mods / 'ae2.json'
    d = json.loads(p.read_text(encoding='utf-8'))
    d[1]['pairs'].append({'key': 'an Extended Pattern Provider',
                          'value': '拓充样板供应器'})
    p.write_text(json.dumps(d, ensure_ascii=False), encoding='utf-8')


@case('压缩方块某一档的倍数写法跑偏', 'compressed-tier-family')
def _c15(mods):
    # 夹具自带这份 lang，不去读真文件：ci.yml 里 test_gates 跑在 assemble.py
    # 之前，那时出货树还不存在，靠真文件就等于这条反例在 CI 里从来没撞过——
    # 而且 glob 落空时闸自爆，输出里照样带着规则 id，反例会假绿。
    d = (mods.parent.parent / 'resourcepacks' / 'ATM10汉化包'
         / 'assets' / 'allthecompressed' / 'lang')
    d.mkdir(parents=True, exist_ok=True)
    (d / 'zh_cn.json').write_text(json.dumps({
        'block.allthecompressed.calcite_1x': '方解石块1x',
        'block.allthecompressed.calcite_2x': '2x方解石',        # 倍数跑到了前面
        'block.allthecompressed.calcite_3x': '白云石块3x',      # 同族词干还飘了
    }, ensure_ascii=False), encoding='utf-8')


@case('物品 tooltip 值里留了换行', 'occultism-tooltip-no-newline')
def _c9(mods):
    # issue #8 的形状：`\n` 在 tooltip 里不断行，而是被当成普通字符去查字形，
    # unifont 给控制字符画的是一个写着 LF 的方框。上游 en_us 自己就带这些换行，
    # 升版重导上游译文时会原样带回来，所以要有闸。
    p = (mods.parent.parent / 'resourcepacks' / 'ATM10汉化包' /
         'assets' / 'occultism' / 'lang' / 'zh_cn.json')
    d = json.loads(p.read_text(encoding='utf-8')) if p.is_file() else {}
    d['item.occultism.chalk_rainbow.auto_tooltip'] = '可代替任意粉笔符文。\n它可以呈现出任何彩色符文的外观。'
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(d, ensure_ascii=False), encoding='utf-8')


def _relics_lang(root, extra):
    """夹具自带这份 lang。理由同 _c15：test_gates 跑在 assemble.py 之前，
    出货树还不存在，靠真文件等于反例在 CI 里从来没撞过；而 glob 落空时闸自爆，
    输出里照样带规则 id，反例会假绿。"""
    p = (root / 'resourcepacks' / 'ATM10汉化包'
         / 'assets' / 'relics' / 'lang' / 'zh_cn.json')
    d = {'relics.description.reflective_necklace.ability.reflection.description':
         '当遗物持有者受到伤害时，有%1$s%%的概率生成一个能量球。'}
    d.update(extra)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(d, ensure_ascii=False), encoding='utf-8')


@case('relic 被译成「收藏品」、bearer 被译成「持眼人」', 'relics-relic-is-yiwu')
def _c18(mods):
    # 经验分散器那条能力说明的原形。同一个 tooltip 的下两行写的是「遗物」，
    # 单看这一句通顺，只有跟本表其余 118 个「遗物」放一起才看得出错。
    _relics_lang(mods.parent.parent, {
        'relics.description.experience_disperser.ability.dispersion.description':
            '当持眼人的任意收藏品获得经验时，所有已装备的收藏品还会额外获得该数量的 %1$s%%。',
    })


def _delta(mods, text):
    p = (mods.parent.parent / 'config' / 'ftbquests' / 'quests' / 'lang' / 'zh_cn'
         / 'chapters' / 'zz_hanhua_zzz_gate_fixture.snbt')
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding='utf-8')


@case('delta 里有不属于任何键的游离行', 'quest-delta-blocks-parse')
def _c13(mods):
    # 2026-08-02 的形状：按行 sort 把多行数组打散，留下 513 个孤零零的 `""`。
    # 当时 check.py 只有按行正则，匹配不上就跳过 → 全绿放行。
    _delta(mods, '{\n\ttitle: "测试"\n\t\t""\n}\n')


@case('delta 里的多行数组到文件尾都没闭合', 'quest-delta-blocks-parse')
def _c14(mods):
    _delta(mods, '{\n\tdescription: [\n\t\t"第一行"\n}\n')



# 注意：**空的 delta 文件不是错误**，所以这里没有对应的反例。
# gen_quest_lang_patches.py 把覆盖打进上游文件后，会照原名发一个 `{\n}` 空壳
# 去盖掉玩家硬盘上的旧 delta（安装器只覆盖不删除）。曾短暂加过一条「不许为空」，
# 结果 ci.yml（生成之前）绿、build.yml（生成之后）35 个文件全红——
# 同一条规则在两条流水线上罩的文件集不一样，加规则前先想清楚它在哪一步跑。


@case('出货树残留字节码补丁', 'vp-no-stray-class-patch')
def _c6(mods):
    f = mods.parent / 'patch' / 'com' / 'ldtteam' / 'blockui' / 'controls' / 'Button.class'
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_bytes(b'\xca\xfe\xba\xbe\x00\x00\x00\x41')


def fixture(tmp):
    """把 src/ + scripts/ 复制一份到临时目录，搭出一棵出货树，返回树的路径。"""
    shutil.copytree(ROOT / 'src', tmp / 'src')
    shutil.copytree(ROOT / 'scripts', tmp / 'scripts')
    # versions/db 是**入库**的（keybinds.json 等），不是生成物。不带上它，
    # 「按键注册名」那条在夹具里就没有前提、跟着静默消失——夹具本身成了假闸。
    if (ROOT / 'versions' / 'db').is_dir():
        shutil.copytree(ROOT / 'versions' / 'db', tmp / 'versions' / 'db')
    tree = tmp / 'build' / 'common'
    (tree / 'vaultpatcher').mkdir(parents=True)
    shutil.copytree(ROOT / 'src' / 'vaultpatcher' / 'modules',
                    tree / 'vaultpatcher' / 'modules')
    for d in ('config', 'resourcepacks', 'kubejs'):
        if (ROOT / 'build' / 'common' / d).is_dir():
            shutil.copytree(ROOT / 'build' / 'common' / d, tree / d, symlinks=True)
    return tree


def run_case(name, inject, rule_id):
    """把 src/ 复制一份到临时目录，注入违规，跑 check.py，看有没有报出那条规则。"""
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        tree = fixture(tmp)
        inject(tmp / 'src' / 'vaultpatcher' / 'modules')
        inject(tree / 'vaultpatcher' / 'modules')
        if rule_id == 'DYNSUB':      # 这条由独立脚本查，不在 check.py 的规则里
            r = subprocess.run([sys.executable,
                                str(tmp / 'scripts' / 'compliance' / 'check_dynamic_substrings.py')],
                               capture_output=True, text=True, cwd=tmp)
            ok = r.returncode != 0
            print(('✅' if ok else '❌') + ' %-28s 期望 %-32s 退出码 %d'
                  % (name, 'check_dynamic_substrings', r.returncode))
            return ok
        r = subprocess.run([sys.executable, str(tmp / 'scripts' / 'check.py'), str(tree)],
                           capture_output=True, text=True, cwd=tmp)
        out = r.stdout + r.stderr
        ok = r.returncode != 0 and rule_id in out
        print(('✅' if ok else '❌') + ' %-28s 期望 %-32s 退出码 %d'
              % (name, rule_id, r.returncode))
        if not ok:
            line = [x for x in out.splitlines() if rule_id in x or '❌' in x]
            print('     实际输出：%s' % (line[0][:120] if line else out.strip()[:160]))
        return ok


# ── 第二组反例：「前提不在 → 静默放过」这类假闸 ────────────────────────────
#
# 前一组撞的是「翻译内容违规」。这一组撞的是另一种假象：检查的前提（生成物、
# 入库的数据文件、mod jar）不在时打一行 ℹ️ 然后**返回成功**——退出码上跟
# 「查过了没问题」一模一样。protect.py 那次就是这么漏了两条闸整整一个版本。
#
# 这里不断言「基线全绿」：夹具里没有完整出货树（ci.yml 把本脚本排在摊树之前），
# check.py 本来就会因别的原因报错。所以只断言**那句话在不在**。
MISSING = []


def missing_case(name):
    def deco(fn):
        MISSING.append((name, fn))
        return fn
    return deco


def check_out(tmp, tree, strict):
    env = dict(os.environ)
    env.pop('GATE_STRICT', None)
    if strict:
        env['GATE_STRICT'] = '1'
    r = subprocess.run([sys.executable, str(tmp / 'scripts' / 'check.py'), str(tree)],
                       capture_output=True, text=True, cwd=tmp, env=env)
    return r.returncode, r.stdout + r.stderr


@missing_case('GATE_STRICT 下「前提是生成物但没生成」→ 必须红')
def _m1(tmp, tree):
    rc, out = check_out(tmp, tree, strict=True)
    return rc != 0 and '没跑成' in out and 'GATE_STRICT' in out


@missing_case('不设 GATE_STRICT 时同一棵树 → 仍按 ℹ️ 跳过（ci.yml 走这条）')
def _m2(tmp, tree):
    rc, out = check_out(tmp, tree, strict=False)
    return 'ℹ️ 跳过' in out and '没跑成' not in out


@missing_case('入库的 keybinds.json 全没了 → 不看 GATE_STRICT 也必须红')
def _m3(tmp, tree):
    shutil.rmtree(tmp / 'versions' / 'db')
    rc, out = check_out(tmp, tree, strict=False)
    return rc != 0 and '按键注册名检查没跑成' in out


@missing_case('GATE_STRICT 下没有 mods 目录 → check_gui_maps 必须红')
def _m4(tmp, tree):
    env = dict(os.environ)
    env['GATE_STRICT'] = '1'
    env.pop('ATM_PACK_ROOT', None)
    r = subprocess.run([sys.executable,
                        str(tmp / 'scripts' / 'compliance' / 'check_gui_maps.py'),
                        str(tmp / '压根不存在' / 'mods')],
                       capture_output=True, text=True, cwd=tmp, env=env)
    return r.returncode != 0 and '没跑成' in (r.stdout + r.stderr)


# ── 第三组反例：KubeJS 类过滤表 ───────────────────────────────────────────
#
# 复刻的事故：`hanhua_update_check.js` 在 vr16-beta4 与 vr16 里发了出去，一次都没工作
# 过。它在事件回调里 `Java.loadClass('java.lang.System')`，而 KubeJS 的过滤表写着
# `- java.lang`——必抛，异常又被 catch 吞掉，于是「进游戏什么都没发生」跟「已经是
# 最新版」长得一样。加载阶段 18/18 全绿，CI 全绿，发出去了也没人看得出来。
#
# 夹具里的过滤表是**现造的最小表**，不抄上游那份：只保留这道闸要判的两条语义
# ——包级前缀拒绝、精确类名放行。
def _kjs_fixture(tmp, loaded, table='- java.lang\n+ java.lang.Integer\n- java.net\n'):
    mods = tmp / 'pack' / 'mods'
    mods.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(mods / 'kubejs-neoforge-2101.7.2-build.368.jar', 'w') as z:
        z.writestr('kubejs.classfilter.txt', '# 夹具\n' + table)
    d = tmp / 'kjstree' / 'kubejs' / 'client_scripts'
    d.mkdir(parents=True, exist_ok=True)
    (d / 'probe.js').write_text(
        '\n'.join("const $C%d = Java.loadClass(%s)" % (i, a) for i, a in enumerate(loaded)) + '\n',
        encoding='utf-8')
    return mods, tmp / 'kjstree'


def _kjs_run(tmp, mods, tree):
    r = subprocess.run([sys.executable,
                        str(tmp / 'scripts' / 'compliance' / 'check_kubejs_classfilter.py'),
                        str(mods), str(tree)],
                       capture_output=True, text=True, cwd=tmp)
    return r.returncode, r.stdout + r.stderr


@missing_case('脚本 loadClass 了 java.net 里的类 → 必须红')
def _m5(tmp, tree):
    mods, kt = _kjs_fixture(tmp, ["'java.net.URI'", "'java.lang.System'"])
    rc, out = _kjs_run(tmp, mods, kt)
    return rc != 0 and 'java.net.URI' in out and 'java.lang.System' in out


@missing_case('包被禁但类被精确放行 → 必须绿（证明这道闸不是一律红）')
def _m6(tmp, tree):
    mods, kt = _kjs_fixture(tmp, ["'java.lang.Integer'", "'org.apache.http.client.methods.HttpGet'"])
    rc, out = _kjs_run(tmp, mods, kt)
    return rc == 0 and '全部放行' in out


@missing_case('loadClass 的参数不是字面量 → 静态判不了，必须红')
def _m7(tmp, tree):
    mods, kt = _kjs_fixture(tmp, ['CLASS_NAME'])
    rc, out = _kjs_run(tmp, mods, kt)
    return rc != 0 and '静态判不了' in out


@missing_case('拿不到 kubejs jar → 类过滤检查必须红')
def _m8(tmp, tree):
    mods, kt = _kjs_fixture(tmp, ["'java.util.HashSet'"])
    for jar in mods.glob('kubejs-*.jar'):
        jar.unlink()
    rc, out = _kjs_run(tmp, mods, kt)
    return rc != 0 and '没跑成' in out


# ── 第四组反例：Iron Jetpacks 的等级名 ────────────────────────────────────
#
# 复刻的事故：游戏里显示「Vibranium能量电池」「Creative喷气背包」。物品名模板在
# lang 里，但 `%s` 来自整合包 config 的 `name` 字段；mod 先查 `jetpack.<name>.name`，
# 查不到就**静默**回退成把 name 首字母大写。回退不报错、不留日志，17 个等级一条
# 没翻，跟全翻好了在任何自动检查里都长得一样，只能靠玩家截图发现。
#
# 档位清单随整合包版本变（ATM 自己加了 allthemodium/vibranium/unobtainium/creative），
# 所以夹具里的上游 config 是现造的，不抄任何一版的真实清单。
def _ijp_fixture(tmp, tiers, keys, make_config=True):
    up = tmp / 'uproot'
    if make_config:
        d = up / 'config' / 'ironjetpacks' / 'jetpacks'
        d.mkdir(parents=True, exist_ok=True)
        for name, disable in tiers:
            (d / ('%s.json' % name)).write_text(
                json.dumps({'name': name, 'disable': disable, 'tier': 1}),
                encoding='utf-8')
    else:
        up.mkdir(parents=True, exist_ok=True)
    lang = (tmp / 'ijptree' / 'resourcepacks' / 'ATM10汉化包'
            / 'assets' / 'ironjetpacks' / 'lang')
    lang.mkdir(parents=True, exist_ok=True)
    (lang / 'zh_cn.json').write_text(
        json.dumps(keys, ensure_ascii=False), encoding='utf-8')
    return up, tmp / 'ijptree'


def _ijp_run(tmp, up, tree):
    r = subprocess.run([sys.executable,
                        str(tmp / 'scripts' / 'compliance' / 'check_jetpack_tiers.py'),
                        str(up), str(tree)],
                       capture_output=True, text=True, cwd=tmp)
    return r.returncode, r.stdout + r.stderr


@missing_case('上游有档位而 lang 里没有对应等级名 → 必须红')
def _m9(tmp, tree):
    up, t = _ijp_fixture(
        tmp,
        [('iron', False), ('vibranium', False)],
        {'jetpack.iron.name': '铁'})
    rc, out = _ijp_run(tmp, up, t)
    return rc != 0 and 'jetpack.vibranium.name' in out


@missing_case('每个档位都有等级名 → 必须绿（证明这道闸不是一律红）')
def _m10(tmp, tree):
    up, t = _ijp_fixture(
        tmp,
        [('iron', False), ('vibranium', False)],
        {'jetpack.iron.name': '铁', 'jetpack.vibranium.name': '振金'})
    rc, out = _ijp_run(tmp, up, t)
    return rc == 0 and '2 个等级名全部有译' in out


@missing_case('等级名是空串 → 必须红（有键不等于有译）')
def _m11(tmp, tree):
    up, t = _ijp_fixture(
        tmp,
        [('iron', False)],
        {'jetpack.iron.name': '   '})
    rc, out = _ijp_run(tmp, up, t)
    return rc != 0 and 'jetpack.iron.name' in out


@missing_case('上游 config 没取到 → 等级名检查必须红，不许「没扫到所以通过」')
def _m12(tmp, tree):
    up, t = _ijp_fixture(tmp, [], {'jetpack.iron.name': '铁'}, make_config=False)
    rc, out = _ijp_run(tmp, up, t)
    return rc != 0 and 'config/ironjetpacks/jetpacks' in out


@missing_case('档位被 disable → mod 不注册它，不要求译名，必须绿')
def _m13(tmp, tree):
    up, t = _ijp_fixture(
        tmp,
        [('iron', False), ('wood', True)],
        {'jetpack.iron.name': '铁'})
    rc, out = _ijp_run(tmp, up, t)
    return rc == 0 and '1 个等级名全部有译' in out


# ── 第五组反例：任务书里的蜜蜂名 ─────────────────────────────────────────
#
# 复刻的事故：任务正文写「倒在幽灵蜜蜂蛋上」，而 JEI 里那个物品叫「恶魂蜜蜂」。
# 照着任务书搜是搜不到的。顺同一条线索机械扫描又找出三处同类（BeeBee /
# KamikazBee 留着英文原名、Shroombees 整个漏译）——一次报告只是一个表面。
#
# 夹具里的两张名字表是现造的最小表，不抄上游那 463 条。
def _bee_fixture(tmp, en_quest, zh_quest, en_names=None, zh_names=None):
    en_names = dict(en_names or {'entity.productivebees.ghostly_bee': 'Ghostly Bee'})
    zh_names = dict(zh_names or {'entity.productivebees.ghostly_bee': '恶魂蜜蜂'})
    # 蜜脾/蜜脾块/刷怪蛋的名字模板：新版闸拿它来拼派生名，缺了要 fail-closed
    en_names.setdefault('block.productivebees.comb_configurable', '%s Comb Block')
    zh_names.setdefault('block.productivebees.comb_configurable', '%s蜜脾块')
    en_names.setdefault('item.productivebees.honeycomb_configurable', '%s Comb')
    zh_names.setdefault('item.productivebees.honeycomb_configurable', '%s蜜脾')
    mods = tmp / 'beepack' / 'mods'
    mods.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(mods / 'productivebees-1.21.1-fixture.jar', 'w') as z:
        z.writestr('assets/productivebees/lang/en_us.json',
                   json.dumps(en_names, ensure_ascii=False))
    up = tmp / 'beeup' / 'config' / 'ftbquests' / 'quests' / 'lang' / 'en_us' / 'chapters'
    up.mkdir(parents=True, exist_ok=True)
    (up / 'c.snbt').write_text('{\n\tquest.AAA.quest_desc: "%s"\n}\n' % en_quest,
                               encoding='utf-8')
    tree = tmp / 'beetree'
    zq = tree / 'config' / 'ftbquests' / 'quests' / 'lang' / 'zh_cn' / 'chapters'
    zq.mkdir(parents=True, exist_ok=True)
    (zq / 'zz_hanhua_c.snbt').write_text('{\n\tquest.AAA.quest_desc: "%s"\n}\n' % zh_quest,
                                         encoding='utf-8')
    zl = tree / 'resourcepacks' / 'ATM10汉化包' / 'assets' / 'productivebees' / 'lang'
    zl.mkdir(parents=True, exist_ok=True)
    (zl / 'zh_cn.json').write_text(json.dumps(zh_names, ensure_ascii=False),
                                   encoding='utf-8')
    return mods, tmp / 'beeup', tree


def _bee_run(tmp, mods, up, tree):
    r = subprocess.run([sys.executable,
                        str(tmp / 'scripts' / 'compliance' / 'check_bee_names_in_quests.py'),
                        str(mods), str(up), str(tree)],
                       capture_output=True, text=True, cwd=tmp)
    return r.returncode, r.stdout + r.stderr


@missing_case('任务书用了物品名之外的蜜蜂叫法 → 必须红')
def _m14(tmp, tree):
    mods, up, t = _bee_fixture(tmp,
                               'pour it over a Ghostly Bee egg',
                               '倒在幽灵蜜蜂蛋上')
    rc, out = _bee_run(tmp, mods, up, t)
    return rc != 0 and '恶魂蜜蜂' in out


@missing_case('任务书用的就是物品名 → 必须绿（证明这道闸不是一律红）')
def _m15(tmp, tree):
    mods, up, t = _bee_fixture(tmp,
                               'pour it over a Ghostly Bee egg',
                               '倒在恶魂蜜蜂蛋上')
    rc, out = _bee_run(tmp, mods, up, t)
    return rc == 0 and '全部与物品名一致' in out


@missing_case('短名落在长名里 → 不算命中，不许误报')
def _m16(tmp, tree):
    # Dragonsteel Bee 会带词边界落在 Lightning Dragonsteel Bee 里，
    # 第一版扫描器就是这么多报了一条，而「龙霆钢蜜蜂」本来是对的。
    en = {'entity.productivebees.dragonsteel_bee': 'Dragonsteel Bee',
          'entity.productivebees.lightning_dragonsteel_bee': 'Lightning Dragonsteel Bee'}
    zh = {'entity.productivebees.dragonsteel_bee': '龙钢蜜蜂',
          'entity.productivebees.lightning_dragonsteel_bee': '龙霆钢蜜蜂'}
    mods, up, t = _bee_fixture(tmp, 'Lightning Dragonsteel Bee', '龙霆钢蜜蜂', en, zh)
    rc, out = _bee_run(tmp, mods, up, t)
    return rc == 0


@missing_case('上游英文任务书没取到 → 蜜蜂名检查必须红')
def _m17(tmp, tree):
    mods, up, t = _bee_fixture(tmp, 'a Ghostly Bee', '恶魂蜜蜂')
    shutil.rmtree(up / 'config')
    rc, out = _bee_run(tmp, mods, up, t)
    return rc != 0 and 'config/ftbquests/quests/lang/en_us' in out


@missing_case('拿不到 productivebees jar → 蜜蜂名检查必须红')
def _m18(tmp, tree):
    mods, up, t = _bee_fixture(tmp, 'a Ghostly Bee', '恶魂蜜蜂')
    for jar in mods.glob('productivebees*.jar'):
        jar.unlink()
    rc, out = _bee_run(tmp, mods, up, t)
    return rc != 0 and '英文名表取不到' in out


# ── 第六组反例：任务书断行用的空格处理 ──────────────────────────────────
#
# 复刻的事故：issue #10 报了 11 条「断行错误」，issue #11 又报了 9 条。根因是中文里
# 留着英文词间空格，FTB Quests 在空格处断行，于是断在「有 / 3 个」「抄写台 / 来」
# 「会失去全部 / AI，」这种地方，而且断出来的是半截空行。
#
# 头一版只删「中文␠中文」与「中文␠数字␠中文」，中西之间的空格当作正常混排排版
# 特意留着——issue #11 那九条证明这条线划错了：`失去全部 AI，`、`来自 Reliquary，`、
# `上下调整 1，` 全是被留下来的那种，而且数字后面直接跟中文标点时，旧的「两侧都要
# 有空格」也匹配不上。现在规则收敛成一条：空格挨着中文就删。
#
# 这一组保的是**反向**风险：处理得太狠，把两侧都是 ASCII 的空格也删掉，
# 那会毁掉键名行、SNBT 结构和英文词组本身。
#
# 「空格挨着中文就删」这条也划错了，而且是**我们自己造的**伤：成对符号只要有一侧
# 挨着中文就被吃掉半边，`原油&r -> 硫酸轻燃油` 变成 `原油&r-> 硫酸轻燃油`、
# `9 粒 → 1 锭` 变成 `9粒→ 1锭`。对抗审计在 2290 个删除点里分出 460 个箭头、
# 293 个短横、73 个序号。病根是 `&#RRGGBB` 不在当时的颜色码正则里，于是箭头右边
# 隔着色码看不出是中文。现在的判据是「两侧都得是词，且至少一侧是中文」，外加序号
# 与命令两条例外。下面 _m25/_m26 就是钉这一版的。
def _space(src):
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        'qsf', str(ROOT / 'scripts' / 'gen_quest_space_fix.py'))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m.fix(src)[0]


@missing_case('中文之间的空格要删掉')
def _m19(tmp, tree):
    return (_space('模组包均受 &e保留所有权利&r 许可') == '模组包均受&e保留所有权利&r许可'
            and _space('一个&6抄写台&r 来为你') == '一个&6抄写台&r来为你')


@missing_case('中文夹短数字两侧的空格也要删（有 3 个）')
def _m20(tmp, tree):
    return _space('你开始时有 3 个基本形态') == '你开始时有3个基本形态'


@missing_case('数字后面直接跟中文标点时也要删（issue #11 的九条全是这个形状）')
def _m21(tmp, tree):
    return (_space('这个数值上下调整 1，最高可到 16。') == '这个数值上下调整1，最高可到16。'
            and _space('最高可到 32,767。') == '最高可到32,767。'
            and _space('额外获得 0.5% 的概率') == '额外获得0.5%的概率')


@missing_case('中文与拉丁字母之间的空格同样要删（断行点不分中西）')
def _m23(tmp, tree):
    return (_space('这些生物会失去全部 AI，基本') == '这些生物会失去全部AI，基本'
            and _space('护符碎片来自 Reliquary，可以') == '护符碎片来自Reliquary，可以'
            and _space('&6AllTheMods 团队') == '&6AllTheMods团队'
            and _space('还是需要 3x3 的空间') == '还是需要3x3的空间')


@missing_case('两侧都是 ASCII 的空格一个都不许动（英文词组、SNBT 结构）')
def _m24(tmp, tree):
    return (_space('Just Enough Items is a mod') == 'Just Enough Items is a mod'
            and _space('\t{ id: "0123", type: "item" }') == '\t{ id: "0123", type: "item" }'
            and _space('quest.ABC.quest_desc: ["中文"]') == 'quest.ABC.quest_desc: ["中文"]')


@missing_case('成对符号两侧的空格不许单边吃掉（&#RRGGBB 也算颜色码）')
def _m25(tmp, tree):
    # 头一版真造出来的伤，逐条钉死：箭头、运算符、列表短横、等号
    return (_space('&8原油&r -> &#D2CD2D硫酸轻燃油')
            == '&8原油&r -> &#D2CD2D硫酸轻燃油'
            and _space('9 粒 → 1 锭') == '9粒 → 1锭'
            and _space('按 Shift + 左键') == '按Shift + 左键'
            and _space('&7铝棒&r - 10') == '&7铝棒&r - 10'
            and _space('干尸 - 生成于沙漠') == '干尸 - 生成于沙漠'
            and _space('20刻 = 1秒') == '20刻 = 1秒'
            and _space('&a第一章&r: &b开端') == '&a第一章&r: &b开端')


@missing_case('列表序号与命令串两侧的空格要留（删了会粘成一坨）')
def _m26(tmp, tree):
    return (_space('1. 放在副手 2. 必须') == '1. 放在副手 2. 必须'
            and _space('输入 /kubejs hand 来查找') == '输入 /kubejs hand 来查找'
            # 小数不是序号：`0.5%` 的空格照删
            and _space('额外获得 0.5% 的概率') == '额外获得0.5%的概率'
            # 词中间的斜杠不是命令：`25MFE/t` 不许因此保住整句的空格
            and _space('输出 25MFE/t 的能量') == '输出25MFE/t的能量')


@missing_case('键名、颜色码、\\n 转义一个字节都不许动')
def _m22(tmp, tree):
    src = '\tquest.ABC123.quest_desc: ["前面 后面\\\\n\\\\n下一段"]'
    out = _space(src)
    return (out == '\tquest.ABC123.quest_desc: ["前面后面\\\\n\\\\n下一段"]'
            and 'quest.ABC123.quest_desc' in out and '\\\\n\\\\n' in out)


# ── 第七组反例：任务书里的物品名 ─────────────────────────────────────────
#
# 复刻的事故：反馈说任务书写「XP 果冻豆」「XP 固化机」「空灵魂宝石」，而 JEI 里
# 分别叫「经验果冻宝宝」「经验固化器」「灵魂宝石（空）」。照任务书去搜，搜不到。
#
# 这一组更要紧的是**做这道闸时自己踩的四个坑**——每个都曾让它误报或静默漏判：
#   ① 颜色码把词边界吃掉（&8Wither 里 8 和 W 都是 \w，\bWither 匹配不上）
#   ② 同名跨模组（Rotten Egg：MGU 叫腐烂鸡蛋，冰与火叫烂鸡蛋）
#   ③ 最长匹配按整段算，短名被长名整条吃掉（Divination Rod / Glass Divination Rod）
#   ④ 不区分大小写，把 `a falling star` 当成了遗物 Falling Star
NS_ALL = ('mob_grinding_utils', 'occultism', 'relics')
IF_TIER_EN = {
    'text.industrialforegoing.tooltip.infinitydrill.poor': 'Poor',
    'text.industrialforegoing.tooltip.infinitydrill.common': 'Common',
    'text.industrialforegoing.tooltip.infinitydrill.uncommon': 'Uncommon',
    'text.industrialforegoing.tooltip.infinitydrill.rare': 'Rare',
    'text.industrialforegoing.tooltip.infinitydrill.epic': 'Epic',
    'text.industrialforegoing.tooltip.infinitydrill.legendary': 'Legendary',
    'text.industrialforegoing.tooltip.infinitydrill.artifact': 'Artifact',
}
IF_TIER_ZH = dict(zip(IF_TIER_EN, ('差', '普通', '罕见', '稀有', '史诗', '传说', '神器')))
IF_TIER_QUEST = 'quest.41E8550FC36ABCA5.quest_desc'


def _item_fixture(tmp, en_quest, zh_quest, names=None, skip_ns=(), extra=None,
                  tier_zh=None, drop_tier_key=None, drop_tier_quest=False):
    """names: {命名空间: {键: (英文, 中文)}}；缺省给三个命名空间各垫一条。"""
    names = names or {'occultism': {'item.occultism.soul_gem_empty':
                                    ('Empty Soul Gem', '灵魂宝石（空）')}}
    mods = tmp / 'ipack' / 'mods'
    mods.mkdir(parents=True, exist_ok=True)
    for ns in NS_ALL:
        if ns in skip_ns:
            continue
        tbl = names.get(ns) or {'item.%s.filler' % ns: ('Filler Item', '填充物')}
        with zipfile.ZipFile(mods / ('%s-fixture.jar' % ns), 'w') as z:
            z.writestr('assets/%s/lang/en_us.json' % ns,
                       json.dumps({k: v[0] for k, v in tbl.items()}, ensure_ascii=False))
            z.writestr('assets/%s/lang/zh_cn.json' % ns,
                       json.dumps({k: v[1] for k, v in tbl.items()}, ensure_ascii=False))
    for ns, tbl in (extra or {}).items():           # 不在强制表里的别的模组
        with zipfile.ZipFile(mods / ('%s-fixture.jar' % ns), 'w') as z:
            z.writestr('assets/%s/lang/en_us.json' % ns,
                       json.dumps({k: v[0] for k, v in tbl.items()}, ensure_ascii=False))
            z.writestr('assets/%s/lang/zh_cn.json' % ns,
                       json.dumps({k: v[1] for k, v in tbl.items()}, ensure_ascii=False))
    tier_en, tier_lang_zh = dict(IF_TIER_EN), dict(IF_TIER_ZH)
    if drop_tier_key:
        tier_en.pop(drop_tier_key, None)
        tier_lang_zh.pop(drop_tier_key, None)
    with zipfile.ZipFile(mods / 'industrialforegoing-fixture.jar', 'w') as z:
        z.writestr('assets/industrialforegoing/lang/en_us.json',
                   json.dumps(tier_en, ensure_ascii=False))
        z.writestr('assets/industrialforegoing/lang/zh_cn.json',
                   json.dumps(tier_lang_zh, ensure_ascii=False))
    up = tmp / 'iup' / 'config' / 'ftbquests' / 'quests' / 'lang' / 'en_us' / 'chapters'
    up.mkdir(parents=True, exist_ok=True)
    en_rows = ['\tquest.AAA.quest_desc: "%s"' % en_quest]
    if not drop_tier_quest:
        en_rows.append('\t%s: "%s"' % (IF_TIER_QUEST, ' '.join(IF_TIER_EN.values())))
    (up / 'c.snbt').write_text('{\n%s\n}\n' % '\n'.join(en_rows), encoding='utf-8')
    tree = tmp / 'itree'
    zq = tree / 'config' / 'ftbquests' / 'quests' / 'lang' / 'zh_cn' / 'chapters'
    zq.mkdir(parents=True, exist_ok=True)
    zh_rows = ['\tquest.AAA.quest_desc: "%s"' % zh_quest]
    if not drop_tier_quest:
        tier_zh = tier_zh if tier_zh is not None else ' '.join(IF_TIER_ZH.values())
        zh_rows.append('\t%s: "%s"' % (IF_TIER_QUEST, tier_zh))
    (zq / 'zz_hanhua_c.snbt').write_text('{\n%s\n}\n' % '\n'.join(zh_rows), encoding='utf-8')
    return mods, tmp / 'iup', tree


def _item_run(tmp, mods, up, tree):
    r = subprocess.run([sys.executable,
                        str(tmp / 'scripts' / 'compliance' / 'check_item_names_in_quests.py'),
                        str(mods), str(up), str(tree)],
                       capture_output=True, text=True, cwd=tmp)
    return r.returncode, r.stdout + r.stderr


@missing_case('任务书用了物品名之外的叫法 → 必须红')
def _m23(tmp, tree):
    rc, out = _item_run(tmp, *_item_fixture(tmp, 'make an Empty Soul Gem', '制作一个空灵魂宝石'))
    return rc != 0 and '灵魂宝石（空）' in out


@missing_case('任务书用的就是物品名 → 必须绿（证明这道闸不是一律红）')
def _m24(tmp, tree):
    rc, out = _item_run(tmp, *_item_fixture(tmp, 'make an Empty Soul Gem', '制作一个灵魂宝石（空）'))
    return rc == 0


@missing_case('颜色码紧贴名字时照样要判（&8 会吃掉词边界）')
def _m25(tmp, tree):
    names = {'occultism': {'block.occultism.wither_skeleton_skull_dummy':
                           ('Wither Skeleton Skull', '凋灵骷髅头颅')}}
    rc, out = _item_run(tmp, *_item_fixture(
        tmp, 'Brew it with a &8Wither Skeleton Skull&r', '用&8凋零骷髅头骨&r酿造', names))
    return rc != 0 and '凋灵骷髅头颅' in out


@missing_case('同名跨模组：用了另一个模组那件的物品名也算过')
def _m26(tmp, tree):
    names = {'mob_grinding_utils': {'item.mob_grinding_utils.rotten_egg':
                                    ('Rotten Egg', '腐烂鸡蛋')}}
    extra = {'iceandfire': {'item.iceandfire.rotten_egg': ('Rotten Egg', '烂鸡蛋')}}
    rc, out = _item_run(tmp, *_item_fixture(
        tmp, 'Toss a Rotten Egg at it', '朝它投掷一个烂鸡蛋', names, extra=extra))
    return rc == 0


@missing_case('长短名同段都出现时，短名不许被整段吃掉')
def _m27(tmp, tree):
    names = {'occultism': {'item.occultism.divination_rod': ('Divination Rod', '探测杖'),
                           'item.occultism.divination_rod_t1':
                           ('Glass Divination Rod', '玻璃探测杖')}}
    rc, out = _item_run(tmp, *_item_fixture(
        tmp, 'The cheapest Divination Rod, the Glass Divination Rod.',
        '最便宜的占卜杖，玻璃占卜杖。', names))
    return rc != 0 and '探测杖' in out


@missing_case('大小写敏感：小写的普通名词不算提到那件物品')
def _m28(tmp, tree):
    names = {'relics': {'item.relics.falling_star': ('Falling Star', '落星')}}
    rc, out = _item_run(tmp, *_item_fixture(
        tmp, 'a chance to call down a falling star', '有概率召来一颗坠落之星', names))
    return rc == 0


@missing_case('某个命名空间的英文表取不到 → 必须红，不许当成没问题')
def _m29(tmp, tree):
    rc, out = _item_run(tmp, *_item_fixture(
        tmp, 'make an Empty Soul Gem', '制作一个灵魂宝石（空）', skip_ns=('relics',)))
    return rc != 0 and 'relics' in out


@missing_case('无限工具任务沿用英文档位、跟 tooltip 不一致 → 必须红')
def _m41(tmp, tree):
    rc, out = _item_run(tmp, *_item_fixture(
        tmp, 'an unrelated quest', '一条无关任务', tier_zh=' '.join(IF_TIER_EN.values())))
    return rc != 0 and '差 / 普通 / 罕见 / 稀有 / 史诗 / 传说 / 神器' in out


@missing_case('无限工具任务七档跟 tooltip 一致 → 必须绿')
def _m42(tmp, tree):
    rc, out = _item_run(tmp, *_item_fixture(tmp, 'an unrelated quest', '一条无关任务'))
    return rc == 0 and '1 组界面术语' in out


@missing_case('无限工具任一 tooltip 参照键取不到 → 必须红')
def _m43(tmp, tree):
    missing = 'text.industrialforegoing.tooltip.infinitydrill.artifact'
    rc, out = _item_run(tmp, *_item_fixture(
        tmp, 'an unrelated quest', '一条无关任务', drop_tier_key=missing))
    return rc != 0 and missing in out and '参照已经失效' in out


@missing_case('绑定的无限工具任务键取不到 → 必须红')
def _m44(tmp, tree):
    rc, out = _item_run(tmp, *_item_fixture(
        tmp, 'an unrelated quest', '一条无关任务', drop_tier_quest=True))
    return rc != 0 and IF_TIER_QUEST in out and '任务可能改版' in out


@missing_case('蜜脾块的名字是拿蜂名拼的，任务书对不上也必须红')
def _m30(tmp, tree):
    mods, up, t = _bee_fixture(tmp, 'the &8Withered Comb Block&r', '&8凋亡蜜脾块',
                               {'entity.productivebees.withered_bee': 'Withered Bee'},
                               {'entity.productivebees.withered_bee': '凋灵蜜蜂'})
    rc, out = _bee_run(tmp, mods, up, t)
    return rc != 0 and '凋灵蜜蜂蜜脾块' in out


@missing_case('用了拼出来的那个全名 → 必须绿（中文不删「蜜蜂」，这是 mod 的行为）')
def _m31(tmp, tree):
    mods, up, t = _bee_fixture(tmp, 'the &8Withered Comb Block&r', '&8凋灵蜜蜂蜜脾块',
                               {'entity.productivebees.withered_bee': 'Withered Bee'},
                               {'entity.productivebees.withered_bee': '凋灵蜜蜂'})
    rc, out = _bee_run(tmp, mods, up, t)
    return rc == 0


@missing_case('模板键取不到 → 必须红，不许「派生名判不了就当没问题」')
def _m32(tmp, tree):
    mods, up, t = _bee_fixture(tmp, 'a Ghostly Bee egg', '恶魂蜜蜂蛋',
                               {'entity.productivebees.ghostly_bee': 'Ghostly Bee',
                                'block.productivebees.comb_configurable': 'no placeholder',
                                'item.productivebees.honeycomb_configurable': 'no placeholder'},
                               {'entity.productivebees.ghostly_bee': '恶魂蜜蜂',
                                'block.productivebees.comb_configurable': '没有占位符',
                                'item.productivebees.honeycomb_configurable': '没有占位符'})
    rc, out = _bee_run(tmp, mods, up, t)
    return rc != 0 and 'comb_configurable' in out


# ── 第八组反例：资源包生效自检的探针 ─────────────────────────────────────
#
# 这道闸守的是一个**会伤到正常用户**的功能：`hanhua_pack_check.js` 查不到探针键
# 就告诉玩家「你没启用汉化资源包」。所以只要脚本与资源包对不上——文件放错、键名
# 只改了一边、版本号没被同一次替换填上——所有配置完全正常的玩家都会每次进游戏
# 被弹一次红字，比不做这个功能还糟。这几种对不上全是静态可判定的。
#
# 夹具是现造的最小出货树：一份脚本 + 一份探针 lang，别的什么都没有。
def _probe_fixture(tmp, consts, lang, ns_dir=None, drop_lang=False):
    tree = tmp / 'probetree'
    d = tree / 'kubejs' / 'client_scripts'
    d.mkdir(parents=True, exist_ok=True)
    (d / 'hanhua_pack_check.js').write_text(
        '(function () {\n'
        + ''.join("  const %s = '%s'\n" % kv for kv in consts.items())
        + '})()\n', encoding='utf-8')
    if not drop_lang:
        ld = (tree / 'resourcepacks' / 'ATM10汉化包' / 'assets'
              / (ns_dir or consts['PROBE_NAMESPACE']) / 'lang')
        ld.mkdir(parents=True, exist_ok=True)
        (ld / 'zh_cn.json').write_text(json.dumps(lang, ensure_ascii=False),
                                       encoding='utf-8')
    return tree


def _probe_run(tmp, tree):
    r = subprocess.run([sys.executable,
                        str(tmp / 'scripts' / 'compliance' / 'check_pack_probe.py'),
                        str(tree)],
                       capture_output=True, text=True, cwd=tmp)
    return r.returncode, r.stdout + r.stderr


_PROBE_OK = {'PROBE_KEY': 'atm10zhcn.pack.version',
             'PROBE_NAMESPACE': 'atm10zhcn',
             'PACK_VERSION': 'r19'}


@missing_case('探针键名与值都跟脚本对得上 → 必须绿（证明这道闸不是一律红）')
def _m33(tmp, tree):
    t = _probe_fixture(tmp, _PROBE_OK, {'atm10zhcn.pack.version': 'r19'})
    rc, out = _probe_run(tmp, t)
    return rc == 0 and 'atm10zhcn.pack.version' in out


@missing_case('资源包里根本没有探针 lang → 必须红')
def _m34(tmp, tree):
    t = _probe_fixture(tmp, _PROBE_OK, {}, drop_lang=True)
    rc, out = _probe_run(tmp, t)
    return rc != 0 and '缺少探针文件' in out


@missing_case('探针键名与脚本里的 PROBE_KEY 不一致 → 必须红')
def _m35(tmp, tree):
    t = _probe_fixture(tmp, _PROBE_OK, {'atm10zhcn.pack.ver': 'r19'})
    rc, out = _probe_run(tmp, t)
    return rc != 0 and '没有键' in out


@missing_case('探针值与脚本里的 PACK_VERSION 不一致 → 必须红（否则误报旧包）')
def _m36(tmp, tree):
    t = _probe_fixture(tmp, _PROBE_OK, {'atm10zhcn.pack.version': 'r18'})
    rc, out = _probe_run(tmp, t)
    return rc != 0 and '与脚本对不上' in out


@missing_case('版本号还是 @@PATCHVER@@ → 必须红，不许把占位符发出去')
def _m37(tmp, tree):
    consts = dict(_PROBE_OK, PACK_VERSION='@@PATCHVER@@')
    t = _probe_fixture(tmp, consts, {'atm10zhcn.pack.version': '@@PATCHVER@@'})
    rc, out = _probe_run(tmp, t)
    return rc != 0 and '还是占位符' in out


@missing_case('lang 放到了别的命名空间目录下 → 必须红（顺序自检会认不出自己）')
def _m38(tmp, tree):
    t = _probe_fixture(tmp, _PROBE_OK, {'atm10zhcn.pack.version': 'r19'},
                       ns_dir='atm10hanhua')
    rc, out = _probe_run(tmp, t)
    return rc != 0 and '缺少探针文件' in out


@missing_case('全串匹配与子串替换成对出现 → 必须绿（这是两种模式，不是冲突）')
def _m39(tmp, tree):
    # 这条是给 vp-no-conflicting-values 配的对照。minecolonies_styles 里 124 条
    # 风格名都是这个形状：`Fortress→要塞` 全串匹配、`Fortress→@要塞` 子串替换。
    # 闸要是不认这两种模式，它就变成一律红——那等于没有闸，只会被人关掉。
    p = tree / 'vaultpatcher' / 'modules' / 'minecolonies_styles.json'
    d = json.loads(p.read_text(encoding='utf-8'))
    d[1]['pairs'] += [{'key': 'Gate Probe Style', 'value': '闸探针样式'},
                      {'key': 'Gate Probe Style', 'value': '@闸探针样式'}]
    p.write_text(json.dumps(d, ensure_ascii=False), encoding='utf-8')
    r = subprocess.run([sys.executable, str(tmp / 'scripts' / 'check.py'), str(tree)],
                       capture_output=True, text=True, cwd=tmp)
    return 'vp-no-conflicting-values' not in (r.stdout + r.stderr)


@missing_case('relics 说明里写「遗物」「遗物持有者」→ 必须绿（证明这道闸不是一律红）')
def _m40(tmp, tree):
    # 没有这条对照，上面那条反例区分不了「闸拦住了」和「闸因为 glob 落空自爆」——
    # 两种情况的输出里都带着 relics-relic-is-yiwu 这个 id。
    _relics_lang(tree, {
        'relics.description.experience_disperser.ability.dispersion.description':
            '当遗物持有者的任意遗物获得经验时，所有已装备的遗物还会额外获得该数量的 %1$s%%。',
    })
    r = subprocess.run([sys.executable, str(tmp / 'scripts' / 'check.py'), str(tree)],
                       capture_output=True, text=True, cwd=tmp)
    return 'relics-relic-is-yiwu' not in (r.stdout + r.stderr)


# ── 第九组反例：「该版不适用」的上游改动登记 ──────────────────────────────
#
# `gen_upstream_patches.py` 找不到原文就退出，这条是整套结构的支点。
# `versions/<版本>/unpatchable.json` 是这个支点上**唯一**的口子：上游只在某一版
# 改了那段原文（ATM 8.0 重做了三章任务书、重写了公告清单），而别的版本还在，
# 删映射会把老版本一起删掉。
#
# 口子只要开一次，就得有反例证明它没被开大：登记过期（原文又回来了）、序号越界、
# 没写理由、登记了一个根本不存在的文件——四种写歪的登记都必须红，
# 否则这个文件就成了「往里加一行就能让任何构建变绿」的开关。
#
# 夹具是现造的最小仓库：一个脚本副本 + 一份映射 + 一份官方文件，跟真仓库无关。
def _up_fixture(tmp, official, edits, reg=None, name='9.9', vedits=None, vsrc='demo.txt'):
    r = tmp / 'uprepo'
    (r / 'scripts').mkdir(parents=True, exist_ok=True)
    shutil.copy(ROOT / 'scripts' / 'gen_upstream_patches.py', r / 'scripts')
    d = r / 'src' / 'upstream' / 'demo'
    d.mkdir(parents=True, exist_ok=True)
    (d / 'demo.txt.json').write_text(
        json.dumps({'src': 'demo.txt', 'edits': edits}, ensure_ascii=False),
        encoding='utf-8')
    (r / 'pack').mkdir(exist_ok=True)
    (r / 'pack' / 'demo.txt').write_text(official, encoding='utf-8')
    if reg is not None:
        v = r / 'versions' / name
        v.mkdir(parents=True, exist_ok=True)
        (v / 'unpatchable.json').write_text(json.dumps(reg, ensure_ascii=False),
                                            encoding='utf-8')
    if vedits is not None:
        vd = r / 'versions' / name / 'upstream'
        vd.mkdir(parents=True, exist_ok=True)
        (vd / 'demo.json').write_text(
            json.dumps({'src': vsrc, 'edits': vedits}, ensure_ascii=False),
            encoding='utf-8')
    return r


def _up_run(r, version='9.9'):
    argv = [sys.executable, str(r / 'scripts' / 'gen_upstream_patches.py'),
            str(r / 'pack'), str(r / 'out')]
    if version is not None:
        argv.append(version)
    x = subprocess.run(argv, capture_output=True, text=True, cwd=r)
    return x.returncode, x.stdout + x.stderr


_UP_EDIT = [{'find': ['原文\n'], 'replace': ['译文\n']}]
_UP_WHY = {'edits': {'demo.txt': {'which': 'all', 'why': '上游在这一版把这行删了'}}}


@missing_case('上游删了这段、又没登记 → 必须红（原来的行为，一个字没松）')
def _m41(tmp, tree):
    rc, out = _up_run(_up_fixture(tmp, '别的行\n', _UP_EDIT))
    return rc != 0 and '在官方文件里找不到' in out


@missing_case('登记过了 → 绿，且产物就是官方原文（不是「旧上游 + 我们的改动」）')
def _m42(tmp, tree):
    r = _up_fixture(tmp, '别的行\n', _UP_EDIT, _UP_WHY)
    rc, out = _up_run(r)
    return (rc == 0 and '不出货 1 处' in out
            and (r / 'out' / 'demo.txt').read_text(encoding='utf-8') == '别的行\n')


@missing_case('登记了、原文却还在 → 必须红（登记过期，上游又把它加回来了）')
def _m43(tmp, tree):
    rc, out = _up_run(_up_fixture(tmp, '原文\n', _UP_EDIT, _UP_WHY))
    return rc != 0 and '登记已经过期' in out


@missing_case('登记的序号越界 → 必须红（以为登记上了，其实一条都没登记上）')
def _m44(tmp, tree):
    reg = {'edits': {'demo.txt': {'which': [2], 'why': '越界'}}}
    rc, out = _up_run(_up_fixture(tmp, '别的行\n', _UP_EDIT, reg))
    return rc != 0 and 'which 不对' in out


@missing_case('登记没写 why → 必须红（下一版没人知道该不该撤掉它）')
def _m45(tmp, tree):
    reg = {'edits': {'demo.txt': {'which': 'all', 'why': '   '}}}
    rc, out = _up_run(_up_fixture(tmp, '别的行\n', _UP_EDIT, reg))
    return rc != 0 and '没写 why' in out


@missing_case('登记了一个 src/upstream 下没人改的文件 → 必须红（登记写错了地方）')
def _m46(tmp, tree):
    reg = {'edits': {'别的.txt': {'which': 'all', 'why': '写错路径'}}}
    rc, out = _up_run(_up_fixture(tmp, '别的行\n', _UP_EDIT, reg))
    return rc != 0 and '没有哪份映射改这个文件' in out


@missing_case('不传版本 → 必须红（少个参数就等于把整张登记表悄悄作废）')
def _m47(tmp, tree):
    rc, out = _up_run(_up_fixture(tmp, '别的行\n', _UP_EDIT, _UP_WHY), version=None)
    return rc != 0 and 'unpatchable' in out


# 该版专属映射：登记只能「这一版不改」，改成了另一副样子还想译，就得单给一份。
# 它跟通用映射叠加在**同一份文本**上，所以三件事都要撞：叠加真的发生了、
# 找不到原文照样红、改一个没人管的文件也红（那种映射永远轮不到执行）。
@missing_case('该版专属映射与通用映射叠加 → 两处都要落在同一份产物里')
def _m48(tmp, tree):
    r = _up_fixture(tmp, '原文\n该版专属\n', _UP_EDIT, None,
                    vedits=[{'find': ['该版专属\n'], 'replace': ['该版译文\n']}])
    rc, out = _up_run(r)
    return (rc == 0 and '该版专属改动 1 处' in out
            and (r / 'out' / 'demo.txt').read_text(encoding='utf-8') == '译文\n该版译文\n')


@missing_case('该版专属映射找不到原文 → 必须红（不因为「是该版专属」就放松）')
def _m49(tmp, tree):
    r = _up_fixture(tmp, '原文\n', _UP_EDIT, None,
                    vedits=[{'find': ['没有这一行\n'], 'replace': ['x\n']}])
    rc, out = _up_run(r)
    return rc != 0 and '在官方文件里找不到' in out


@missing_case('该版专属映射改的文件没有通用映射 → 必须红（它永远不会被套用）')
def _m50(tmp, tree):
    r = _up_fixture(tmp, '原文\n', _UP_EDIT, None,
                    vedits=[{'find': ['原文\n'], 'replace': ['x\n']}], vsrc='别的.txt')
    rc, out = _up_run(r)
    return rc != 0 and '永远不会被套用' in out


# ── 10. CurseForge 上取不到的 jar，必须逐个登记才放行 ─────────────────────
#
# 撞的是同一种假象的另一个面：**「下不来」被当成「这一版没有」**。
# 拿残缺的 jar 集合建版本库，vaultpatcher.json 里那些 "missing" 就成了假判定——
# 不是这一版没有这个 key，只是我们没看到那个 jar，而两者在产物里长得一模一样。
# 所以放行的唯一路径是 versions/<版本>/unobtainable.json 里**逐个** fileID 登记。
#
# 三条反例分别撞：登记齐了要放行、少登记一个要红、登记文件整份不在时**默认必须红**
# （最后这条最要命：文件名写错、目录搬家都会让机制静默失效，默认放行就等于没有闸）。

def _unob(tmp, ver, files):
    """在临时树里摆 versions/<ver>/unobtainable.json，files 为 None 表示整份不放。"""
    sys.path.insert(0, str(ROOT / 'scripts'))
    import fetch_pack
    d = tmp / 'versions' / ver
    d.mkdir(parents=True, exist_ok=True)
    if files is not None:
        (d / 'unobtainable.json').write_text(
            json.dumps({'files': {str(i): {'http': 404} for i in files}}),
            encoding='utf-8')
    old = fetch_pack.ROOT
    fetch_pack.ROOT = tmp
    try:
        return fetch_pack.unregistered_missing(ver, [7948263, 8005487])
    finally:
        fetch_pack.ROOT = old


@missing_case('取不到的 jar 全部登记在案 → 放行（这一版的缺口是既有事实）')
def _m51(tmp, tree):
    return _unob(tmp, '9.9', [7948263, 8005487]) == []


@missing_case('取不到的 jar 少登记了一个 → 必须红，且点名是哪个')
def _m52(tmp, tree):
    return _unob(tmp, '9.9', [7948263]) == [8005487]


@missing_case('unobtainable.json 整份不存在 → 必须红，不许默认放行')
def _m53(tmp, tree):
    return _unob(tmp, '9.9', None) == [7948263, 8005487]


def _prune(tmp, upstream_has):
    """造一版出货树 + 一版官方文件，跑 gen_missing_questpics.py --prune。

    返回 (退出码, 我们画的那张还在不在)。`upstream_has=None` 表示**根本没取到**
    该版的官方文件——那时「上游有没有这张图」是不知道，不是「没有」。
    """
    rel = 'create/create_shaft.png'
    up = tmp / 'packsrc'
    if upstream_has is not None:
        (up / 'kubejs/assets/atm/textures/questpics/create').mkdir(parents=True)
        if upstream_has:
            (up / 'kubejs/assets/atm/textures/questpics' / rel).write_bytes(b'\x89PNG up')
    tree = tmp / 'tree'
    ours = tree / 'resourcepacks' / 'ATM10汉化包' / 'assets/atm/textures/questpics' / rel
    ours.parent.mkdir(parents=True)
    ours.write_bytes(b'\x89PNG ours')
    r = subprocess.run(
        [sys.executable, str(ROOT / 'scripts' / 'gen_missing_questpics.py'),
         '--prune', str(up), str(tree)],
        capture_output=True, text=True)
    return r.returncode, ours.is_file()


@missing_case('这一版上游自己有那张图 → 把我们画的剔掉，不许覆盖上游')
def _m54(tmp, tree):
    return _prune(tmp, True) == (0, False)


@missing_case('这一版上游没有那张图 → 保留我们画的（老版本全靠它）')
def _m55(tmp, tree):
    return _prune(tmp, False) == (0, True)


@missing_case('取不到该版官方文件 → 必须红，不许当成「上游没有」而覆盖过去')
def _m56(tmp, tree):
    rc, _ = _prune(tmp, None)
    return rc != 0


def run_missing(name, fn):
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        ok = fn(tmp, fixture(tmp))
    print(('✅' if ok else '❌') + ' %s' % name)
    return ok


def main():
    print('闸的反例测试：每条都复刻一次真实事故，验它真的会红\n')
    ok = sum(run_case(*c) for c in CASES)
    print('\n%d/%d 条闸经反例验证确实会红' % (ok, len(CASES)))
    print('\n前提缺失时不许静默放过：\n')
    ok2 = sum(run_missing(*m) for m in MISSING)
    print('\n%d/%d 条' % (ok2, len(MISSING)))
    if ok != len(CASES) or ok2 != len(MISSING):
        print('有闸没拦住反例——它现在是假闸，修好之前不许发版。')
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
