#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# atm10-zh-cn — All the Mods 10 简体中文汉化补丁「绿油油版」
# Copyright (C) 2026 星野夢華 (Hoshino Yumeka)
# SPDX-License-Identifier: GPL-3.0-or-later
"""检查脚本的反例测试：造故意违规的样本，验证每项检查确实会失败。

只跑一遍全部通过，查不出这三种失效：检查脚本没接进流水线（`check_gui_maps.py`、
`check_dynamic_substrings.py`）、只查了一部分文件（`vp-config-ui-no-single-word`）、
glob 命中 0 个文件时静默通过。

第一组反例各复现一次真实事故：

| 反例 | 事故 |
|---|---|
| 模块里放 `top horizontal` | 译了 blockui 的对齐标志串，MineColonies/建筑棒对齐失效 |
| 配置模块放单词键 `Sound` | 单词可能同时是枚举值，译了会被反查或写回配置 |
| 两条 `@` 子串键互为子串 | `String.replace` 顺序不定，长的那条被部分替换，结果半中半英 |
| `class_patch: true` | 数据目录变成代码执行入口 |
| `vaultpatcher/patch/` 下留 `.class` | 旧补丁重新生效 → ClassFormatError 闪退 |
| 标识符样式的键 | 被拿去构造 ResourceLocation → 注册崩溃 |
| 以 `/` 开头的键 | 译了建筑棒的类别路径，查表落空 → NPE 闪退（issue #3） |

第二组测前提缺失时的静默放过：生成物、入库数据或 mod jar 不在时，检查打一行 ℹ️ 就返回
成功，`protect.py` 的两条检查曾因此一整个版本没运行。生成之后的环节一律传
`GATE_STRICT=1`，让这种情况失败。`ci.yml` 用 `--no-jars`，不设。

夹具都在临时目录里创建，用完即删。`assemble.py` 只组装 `src/`，假翻译不会进出货树。

用法:
    python3 scripts/compliance/test_gates.py
"""
import hashlib
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
    # 本该被 PERF_HOLD 排除的模块因脏 build/ 或排除逻辑失效回到包里，
    # 全局替换表从 1086 对涨回 3396 对，掉帧。
    (mods / 'config_ui_generated.json').write_text(
        json.dumps([{'name': 'x', 'dynamic': True, 'i18n': False},
                    {'target_class': ['net.createmod.catnip.config.ui.BaseConfigScreen'],
                     'pairs': [{'key': 'Advanced Capacity', 'value': '进阶容量'}]}],
                   ensure_ascii=False), encoding='utf-8')


@case('同一个任务键落在两份文件里', 'quest-delta-no-duplicate-keys')
def _c11(mods):
    # 出货树里一个任务键只许在一份文件里：splitter 不排序 chapters/（Files.list 直接 forEach），
    # 键在两份文件里时，哪份生效取决于 ext4 的哈希序。
    d = mods.parent.parent / 'config' / 'ftbquests' / 'quests' / 'lang' / 'zh_cn' / 'chapters'
    d.mkdir(parents=True, exist_ok=True)
    key = '\tquest.0000A88BB40B2149.quest_desc: ["闸探针"]\n'
    for n in ('aaa_gate_probe_one.snbt', 'aaa_gate_probe_two.snbt'):
        (d / n).write_text('{\n' + key + '}\n', encoding='utf-8')


@case('两个客户端脚本重名声明', 'client-scripts-no-duplicate-decl')
def _c10(mods):
    # KubeJS client_scripts 共用一个全局作用域，第二个 `const $Component` 抛 redeclaration，
    # 整批脚本加载失败。
    d = mods.parent.parent / 'kubejs' / 'client_scripts'
    d.mkdir(parents=True, exist_ok=True)
    for n in ('aaa_gate_probe_one.js', 'aaa_gate_probe_two.js'):
        (d / n).write_text("const $Component = Java.loadClass('net.minecraft.network.chat.Component')\n",
                           encoding='utf-8')


@case('try 块内部写 const', 'js-no-const-inside-block')
def _c12(mods):
    # KubeJS 的 Rhino 把块里的 const 提升成函数作用域的 var，执行到声明时抛 redeclaration of var。
    # 加载阶段不报错，写在事件回调里就是进游戏没有任何效果。前三句是上游常用的写法
    # （顶格、回调体顶层、块里赋值），不许被拦。
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
    # rftoolsbase.json 与 rftoolsbase_filter_zh.json 给同一个 GuiFilterModule 的
    # 「Filter ignoring damage」各写了一句（「忽略耐久值」「忽略损伤值」），
    # 哪句生效取决于加载顺序与表内顺序。
    p = mods / 'ae2.json'
    d = json.loads(p.read_text(encoding='utf-8'))
    d[1]['pairs'] += [{'key': 'Gate Probe Filter Line', 'value': '闸探针甲'},
                      {'key': 'Gate Probe Filter Line', 'value': '闸探针乙'}]
    p.write_text(json.dumps(d, ensure_ascii=False), encoding='utf-8')


@case('Extended 被译成 ExpandedAE 那件东西的名字', 'vp-ae-provider-family')
def _c14(mods):
    # 两张升级卡把 Extended（AE2扩展的 ME扩展样板供应器）与 Expanded（ExpandedAE 的
    # 拓充样板供应器）对调了。两句各自通顺，只有把原文的词和译文的词绑定才判断得出。
    p = mods / 'ae2.json'
    d = json.loads(p.read_text(encoding='utf-8'))
    d[1]['pairs'].append({'key': 'an Extended Pattern Provider',
                          'value': '拓充样板供应器'})
    p.write_text(json.dumps(d, ensure_ascii=False), encoding='utf-8')


@case('压缩方块某一档的倍数写法跑偏', 'compressed-tier-family')
def _c15(mods):
    # 夹具自带 lang：ci.yml 里 test_gates 在 assemble.py 之前运行，出货树还不存在。
    # 读真文件的话，glob 落空时检查自己报错，输出同样带规则 id，反例会误判为通过。
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
    # issue #8：tooltip 里的 `\n` 不换行，unifont 把它画成写着 LF 的方框。
    # 上游 en_us 自带这些换行，升版重导上游译文时会带回来。
    p = (mods.parent.parent / 'resourcepacks' / 'ATM10汉化包' /
         'assets' / 'occultism' / 'lang' / 'zh_cn.json')
    d = json.loads(p.read_text(encoding='utf-8')) if p.is_file() else {}
    d['item.occultism.chalk_rainbow.auto_tooltip'] = '可代替任意粉笔符文。\n它可以呈现出任何彩色符文的外观。'
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(d, ensure_ascii=False), encoding='utf-8')


def _relics_lang(root, extra):
    """夹具自带 lang，理由同 _c15。"""
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
    # 按行 sort 会把多行数组打散，留下 513 个孤立的 `""`，按行正则匹配不上就会放行。
    _delta(mods, '{\n\ttitle: "测试"\n\t\t""\n}\n')


@case('delta 里的多行数组到文件尾都没闭合', 'quest-delta-blocks-parse')
def _c14(mods):
    _delta(mods, '{\n\tdescription: [\n\t\t"第一行"\n}\n')



# 空的 delta 文件不是错误，没有反例：gen_quest_lang_patches.py 会按原名发 `{\n}` 空文件，
# 覆盖玩家硬盘上的旧 delta（安装器只覆盖不删除）。同一条规则在 ci.yml（生成前）与
# build.yml（生成后）查到的文件不同，加规则前先确认它在哪一步运行。


@case('出货树残留字节码补丁', 'vp-no-stray-class-patch')
def _c6(mods):
    f = mods.parent / 'patch' / 'com' / 'ldtteam' / 'blockui' / 'controls' / 'Button.class'
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_bytes(b'\xca\xfe\xba\xbe\x00\x00\x00\x41')


def fixture(tmp):
    """把 src/ + scripts/ 复制一份到临时目录，搭出一棵出货树，返回树的路径。"""
    shutil.copytree(ROOT / 'src', tmp / 'src')
    shutil.copytree(ROOT / 'scripts', tmp / 'scripts')
    # versions/db 是入库数据（keybinds.json 等），不带上的话「按键注册名」那条会静默跳过。
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


# ── 第二组反例：前提不在时静默放过 ─────────────────────────────────────
#
# 生成物、入库数据或 mod jar 不在时，检查不许打一行 ℹ️ 就返回成功。
# 只断言提示语是否出现：夹具里没有完整出货树，check.py 会因别的原因报错。
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


@missing_case('GATE_STRICT 下「前提是生成物但没生成」→ 必须失败')
def _m1(tmp, tree):
    rc, out = check_out(tmp, tree, strict=True)
    return rc != 0 and '没跑成' in out and 'GATE_STRICT' in out


@missing_case('不设 GATE_STRICT 时同一棵树 → 仍按 ℹ️ 跳过（ci.yml 走这条）')
def _m2(tmp, tree):
    rc, out = check_out(tmp, tree, strict=False)
    return 'ℹ️ 跳过' in out and '没跑成' not in out


@missing_case('入库的 keybinds.json 全没了 → 不看 GATE_STRICT 也必须失败')
def _m3(tmp, tree):
    shutil.rmtree(tmp / 'versions' / 'db')
    rc, out = check_out(tmp, tree, strict=False)
    return rc != 0 and '按键注册名检查没跑成' in out


@missing_case('GATE_STRICT 下没有 mods 目录 → check_gui_maps 必须失败')
def _m4(tmp, tree):
    env = dict(os.environ)
    env['GATE_STRICT'] = '1'
    env.pop('ATM_PACK_ROOT', None)
    r = subprocess.run([sys.executable,
                        str(tmp / 'scripts' / 'compliance' / 'check_gui_maps.py'),
                        str(tmp / '压根不存在' / 'mods')],
                       capture_output=True, text=True, cwd=tmp, env=env)
    return r.returncode != 0 and '没跑成' in (r.stdout + r.stderr)


# ── 第三组反例：KubeJS 类过滤表 ─────────────────────────────────────────
#
# 事故：`hanhua_update_check.js` 在事件回调里 `Java.loadClass('java.lang.System')`，
# KubeJS 过滤表拒绝 `java.lang`，异常被 catch 吞掉。脚本在 vr16-beta4 与 vr16 里
# 从未生效，加载阶段与 CI 都通过。
#
# 夹具里的过滤表只保留两条语义：包级前缀拒绝、精确类名放行。
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


@missing_case('脚本 loadClass 了 java.net 里的类 → 必须失败')
def _m5(tmp, tree):
    mods, kt = _kjs_fixture(tmp, ["'java.net.URI'", "'java.lang.System'"])
    rc, out = _kjs_run(tmp, mods, kt)
    return rc != 0 and 'java.net.URI' in out and 'java.lang.System' in out


@missing_case('包被禁但类被精确放行 → 必须通过（证明这项检查不是一律失败）')
def _m6(tmp, tree):
    mods, kt = _kjs_fixture(tmp, ["'java.lang.Integer'", "'org.apache.http.client.methods.HttpGet'"])
    rc, out = _kjs_run(tmp, mods, kt)
    return rc == 0 and '全部放行' in out


@missing_case('loadClass 的参数不是字面量 → 静态判不了，必须失败')
def _m7(tmp, tree):
    mods, kt = _kjs_fixture(tmp, ['CLASS_NAME'])
    rc, out = _kjs_run(tmp, mods, kt)
    return rc != 0 and '静态判不了' in out


@missing_case('拿不到 kubejs jar → 类过滤检查必须失败')
def _m8(tmp, tree):
    mods, kt = _kjs_fixture(tmp, ["'java.util.HashSet'"])
    for jar in mods.glob('kubejs-*.jar'):
        jar.unlink()
    rc, out = _kjs_run(tmp, mods, kt)
    return rc != 0 and '没跑成' in out


# ── 第四组反例：Iron Jetpacks 的等级名 ───────────────────────────────────
#
# 事故：游戏里显示「Vibranium能量电池」「Creative喷气背包」。名字模板在 lang 里，`%s` 来自
# 整合包 config 的 `name` 字段。mod 查不到 `jetpack.<name>.name` 就把 name 首字母大写，
# 不报错也不留日志。档位清单随整合包版本变，所以夹具里的 config 是专门造的。
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


@missing_case('上游有档位而 lang 里没有对应等级名 → 必须失败')
def _m9(tmp, tree):
    up, t = _ijp_fixture(
        tmp,
        [('iron', False), ('vibranium', False)],
        {'jetpack.iron.name': '铁'})
    rc, out = _ijp_run(tmp, up, t)
    return rc != 0 and 'jetpack.vibranium.name' in out


@missing_case('每个档位都有等级名 → 必须通过（证明这项检查不是一律失败）')
def _m10(tmp, tree):
    up, t = _ijp_fixture(
        tmp,
        [('iron', False), ('vibranium', False)],
        {'jetpack.iron.name': '铁', 'jetpack.vibranium.name': '振金'})
    rc, out = _ijp_run(tmp, up, t)
    return rc == 0 and '2 个等级名全部有译' in out


@missing_case('等级名是空串 → 必须失败（有键不等于有译）')
def _m11(tmp, tree):
    up, t = _ijp_fixture(
        tmp,
        [('iron', False)],
        {'jetpack.iron.name': '   '})
    rc, out = _ijp_run(tmp, up, t)
    return rc != 0 and 'jetpack.iron.name' in out


@missing_case('上游 config 没取到 → 等级名检查必须失败，不许「没扫到所以通过」')
def _m12(tmp, tree):
    up, t = _ijp_fixture(tmp, [], {'jetpack.iron.name': '铁'}, make_config=False)
    rc, out = _ijp_run(tmp, up, t)
    return rc != 0 and 'config/ironjetpacks/jetpacks' in out


@missing_case('档位被 disable → mod 不注册它，不要求译名，必须通过')
def _m13(tmp, tree):
    up, t = _ijp_fixture(
        tmp,
        [('iron', False), ('wood', True)],
        {'jetpack.iron.name': '铁'})
    rc, out = _ijp_run(tmp, up, t)
    return rc == 0 and '1 个等级名全部有译' in out


# ── 第五组反例：任务书里的蜜蜂名 ───────────────────────────────────────
#
# 事故：任务正文写「倒在幽灵蜜蜂蛋上」，JEI 里那个物品叫「恶魂蜜蜂」，照任务书搜不到。
# 同类还有 BeeBee、KamikazBee 留着英文、Shroombees 漏译。夹具里的两张名字表是最小表。
def _bee_fixture(tmp, en_quest, zh_quest, en_names=None, zh_names=None):
    en_names = dict(en_names or {'entity.productivebees.ghostly_bee': 'Ghostly Bee'})
    zh_names = dict(zh_names or {'entity.productivebees.ghostly_bee': '恶魂蜜蜂'})
    # 蜜脾/蜜脾块/刷怪蛋的名字模板：检查用它拼派生名，缺了要 fail-closed
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


@missing_case('任务书用了物品名之外的蜜蜂叫法 → 必须失败')
def _m14(tmp, tree):
    mods, up, t = _bee_fixture(tmp,
                               'pour it over a Ghostly Bee egg',
                               '倒在幽灵蜜蜂蛋上')
    rc, out = _bee_run(tmp, mods, up, t)
    return rc != 0 and '恶魂蜜蜂' in out


@missing_case('任务书用的就是物品名 → 必须通过（证明这项检查不是一律失败）')
def _m15(tmp, tree):
    mods, up, t = _bee_fixture(tmp,
                               'pour it over a Ghostly Bee egg',
                               '倒在恶魂蜜蜂蛋上')
    rc, out = _bee_run(tmp, mods, up, t)
    return rc == 0 and '全部与物品名一致' in out


@missing_case('短名落在长名里 → 不算命中，不许误报')
def _m16(tmp, tree):
    # Dragonsteel Bee 按词边界也能匹配到 Lightning Dragonsteel Bee 里，会误报「龙霆钢蜜蜂」。
    en = {'entity.productivebees.dragonsteel_bee': 'Dragonsteel Bee',
          'entity.productivebees.lightning_dragonsteel_bee': 'Lightning Dragonsteel Bee'}
    zh = {'entity.productivebees.dragonsteel_bee': '龙钢蜜蜂',
          'entity.productivebees.lightning_dragonsteel_bee': '龙霆钢蜜蜂'}
    mods, up, t = _bee_fixture(tmp, 'Lightning Dragonsteel Bee', '龙霆钢蜜蜂', en, zh)
    rc, out = _bee_run(tmp, mods, up, t)
    return rc == 0


@missing_case('上游英文任务书没取到 → 蜜蜂名检查必须失败')
def _m17(tmp, tree):
    mods, up, t = _bee_fixture(tmp, 'a Ghostly Bee', '恶魂蜜蜂')
    shutil.rmtree(up / 'config')
    rc, out = _bee_run(tmp, mods, up, t)
    return rc != 0 and 'config/ftbquests/quests/lang/en_us' in out


@missing_case('拿不到 productivebees jar → 蜜蜂名检查必须失败')
def _m18(tmp, tree):
    mods, up, t = _bee_fixture(tmp, 'a Ghostly Bee', '恶魂蜜蜂')
    for jar in mods.glob('productivebees*.jar'):
        jar.unlink()
    rc, out = _bee_run(tmp, mods, up, t)
    return rc != 0 and '英文名表取不到' in out


# ── 第六组反例：任务书断行用的空格处理 ──────────────────────────────────
#
# 事故（issue #10、#11）：中文里留着英文词间空格，FTB Quests 在空格处断行，断在「有 / 3 个」
# 「会失去全部 / AI，」这类地方。中西之间的空格（`失去全部 AI，`、`来自 Reliquary，`）
# 同样会断行。
#
# 反向风险：两侧都是 ASCII 的空格不能删，否则会破坏键名行、SNBT 结构和英文词组。成对符号
# 不能只因一侧挨着中文就删（`9 粒 → 1 锭` 不能变成 `9粒→ 1锭`），`&#RRGGBB` 也要按颜色码
# 处理。判据是「两侧都是词，且至少一侧是中文」，外加序号与命令两条例外，由 _m25/_m26 固定。
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
    # 会被误删空格的几类，逐条固定：箭头、运算符、列表短横、等号
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


# ── 第七组反例：任务书里的物品名 ───────────────────────────────────────
#
# 事故：任务书写「XP 果冻豆」「XP 固化机」「空灵魂宝石」，JEI 里叫「经验果冻宝宝」
# 「经验固化器」「灵魂宝石（空）」。下面还测这项检查容易出错的四处：
#   ① 颜色码吃掉词边界（&8Wither 里 8 和 W 都是 \w，\bWither 匹配不上）
#   ② 同名跨模组（Rotten Egg：MGU 叫腐烂鸡蛋，冰与火叫烂鸡蛋）
#   ③ 按整段取最长匹配，短名被长名整条吃掉（Divination Rod / Glass Divination Rod）
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
    """names: {命名空间: {键: (英文, 中文)}}。缺省给三个命名空间各垫一条。"""
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


@missing_case('任务书用了物品名之外的叫法 → 必须失败')
def _m23(tmp, tree):
    rc, out = _item_run(tmp, *_item_fixture(tmp, 'make an Empty Soul Gem', '制作一个空灵魂宝石'))
    return rc != 0 and '灵魂宝石（空）' in out


@missing_case('任务书用的就是物品名 → 必须通过（证明这项检查不是一律失败）')
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


@missing_case('某个命名空间的英文表取不到 → 必须失败，不许当成没问题')
def _m29(tmp, tree):
    rc, out = _item_run(tmp, *_item_fixture(
        tmp, 'make an Empty Soul Gem', '制作一个灵魂宝石（空）', skip_ns=('relics',)))
    return rc != 0 and 'relics' in out


@missing_case('无限工具任务沿用英文档位、跟 tooltip 不一致 → 必须失败')
def _m41(tmp, tree):
    rc, out = _item_run(tmp, *_item_fixture(
        tmp, 'an unrelated quest', '一条无关任务', tier_zh=' '.join(IF_TIER_EN.values())))
    return rc != 0 and '差 / 普通 / 罕见 / 稀有 / 史诗 / 传说 / 神器' in out


@missing_case('无限工具任务七档跟 tooltip 一致 → 必须通过')
def _m42(tmp, tree):
    rc, out = _item_run(tmp, *_item_fixture(tmp, 'an unrelated quest', '一条无关任务'))
    return rc == 0 and '1 组界面术语' in out


@missing_case('无限工具任一 tooltip 参照键取不到 → 必须失败')
def _m43(tmp, tree):
    missing = 'text.industrialforegoing.tooltip.infinitydrill.artifact'
    rc, out = _item_run(tmp, *_item_fixture(
        tmp, 'an unrelated quest', '一条无关任务', drop_tier_key=missing))
    return rc != 0 and missing in out and '参照已经失效' in out


@missing_case('绑定的无限工具任务键取不到 → 必须失败')
def _m44(tmp, tree):
    rc, out = _item_run(tmp, *_item_fixture(
        tmp, 'an unrelated quest', '一条无关任务', drop_tier_quest=True))
    return rc != 0 and IF_TIER_QUEST in out and '任务可能改版' in out


@missing_case('蜜脾块的名字是拿蜂名拼的，任务书对不上也必须失败')
def _m30(tmp, tree):
    mods, up, t = _bee_fixture(tmp, 'the &8Withered Comb Block&r', '&8凋亡蜜脾块',
                               {'entity.productivebees.withered_bee': 'Withered Bee'},
                               {'entity.productivebees.withered_bee': '凋灵蜜蜂'})
    rc, out = _bee_run(tmp, mods, up, t)
    return rc != 0 and '凋灵蜜蜂蜜脾块' in out


@missing_case('用了拼出来的那个全名 → 必须通过（中文不删「蜜蜂」，这是 mod 的行为）')
def _m31(tmp, tree):
    mods, up, t = _bee_fixture(tmp, 'the &8Withered Comb Block&r', '&8凋灵蜜蜂蜜脾块',
                               {'entity.productivebees.withered_bee': 'Withered Bee'},
                               {'entity.productivebees.withered_bee': '凋灵蜜蜂'})
    rc, out = _bee_run(tmp, mods, up, t)
    return rc == 0


@missing_case('模板键取不到 → 必须失败，不许「派生名判不了就当没问题」')
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
# `hanhua_pack_check.js` 查不到探针键就提示玩家没启用汉化资源包。脚本与资源包对不上时
# （文件放错、键名只改了一边、版本号没填），配置正常的玩家每次进游戏都会看到红字。
# 这几种都能静态判断。夹具只有一份脚本和一份探针 lang。
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


@missing_case('探针键名与值都跟脚本对得上 → 必须通过（证明这项检查不是一律失败）')
def _m33(tmp, tree):
    t = _probe_fixture(tmp, _PROBE_OK, {'atm10zhcn.pack.version': 'r19'})
    rc, out = _probe_run(tmp, t)
    return rc == 0 and 'atm10zhcn.pack.version' in out


@missing_case('资源包里根本没有探针 lang → 必须失败')
def _m34(tmp, tree):
    t = _probe_fixture(tmp, _PROBE_OK, {}, drop_lang=True)
    rc, out = _probe_run(tmp, t)
    return rc != 0 and '缺少探针文件' in out


@missing_case('探针键名与脚本里的 PROBE_KEY 不一致 → 必须失败')
def _m35(tmp, tree):
    t = _probe_fixture(tmp, _PROBE_OK, {'atm10zhcn.pack.ver': 'r19'})
    rc, out = _probe_run(tmp, t)
    return rc != 0 and '没有键' in out


@missing_case('探针值与脚本里的 PACK_VERSION 不一致 → 必须失败（否则误报旧包）')
def _m36(tmp, tree):
    t = _probe_fixture(tmp, _PROBE_OK, {'atm10zhcn.pack.version': 'r18'})
    rc, out = _probe_run(tmp, t)
    return rc != 0 and '与脚本对不上' in out


@missing_case('版本号还是 @@PATCHVER@@ → 必须失败，不许把占位符发出去')
def _m37(tmp, tree):
    consts = dict(_PROBE_OK, PACK_VERSION='@@PATCHVER@@')
    t = _probe_fixture(tmp, consts, {'atm10zhcn.pack.version': '@@PATCHVER@@'})
    rc, out = _probe_run(tmp, t)
    return rc != 0 and '还是占位符' in out


@missing_case('lang 放到了别的命名空间目录下 → 必须失败（顺序自检会认不出自己）')
def _m38(tmp, tree):
    t = _probe_fixture(tmp, _PROBE_OK, {'atm10zhcn.pack.version': 'r19'},
                       ns_dir='atm10hanhua')
    rc, out = _probe_run(tmp, t)
    return rc != 0 and '缺少探针文件' in out


@missing_case('全串匹配与子串替换成对出现 → 必须通过（这是两种模式，不是冲突）')
def _m39(tmp, tree):
    # vp-no-conflicting-values 的对照：minecolonies_styles 的 124 条风格名同时有
    # `Fortress→要塞` 全串匹配与 `Fortress→@要塞` 子串替换，这两种模式不算冲突。
    p = tree / 'vaultpatcher' / 'modules' / 'minecolonies_styles.json'
    d = json.loads(p.read_text(encoding='utf-8'))
    d[1]['pairs'] += [{'key': 'Gate Probe Style', 'value': '闸探针样式'},
                      {'key': 'Gate Probe Style', 'value': '@闸探针样式'}]
    p.write_text(json.dumps(d, ensure_ascii=False), encoding='utf-8')
    r = subprocess.run([sys.executable, str(tmp / 'scripts' / 'check.py'), str(tree)],
                       capture_output=True, text=True, cwd=tmp)
    return 'vp-no-conflicting-values' not in (r.stdout + r.stderr)


@missing_case('relics 说明里写「遗物」「遗物持有者」→ 必须通过（证明这项检查不是一律失败）')
def _m40(tmp, tree):
    # 没有这条对照，上面那条反例区分不了「检查拦住了」和「检查因为 glob 落空而报错」，
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
# `gen_upstream_patches.py` 找不到原文就退出，`versions/<版本>/unpatchable.json` 是唯一例外：
# 上游只在某一版改了那段原文时（例如 ATM 8.0 重做了三章任务书、重写了公告），删映射会连
# 老版本一起删。登记过期（原文又出现）、序号越界、没写理由、登记不存在的文件，都必须失败。
# 夹具是最小仓库：一个脚本副本、一份映射、一份官方文件。
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


@missing_case('上游删了这段、又没登记 → 必须失败（原来的行为，一个字没松）')
def _m41(tmp, tree):
    rc, out = _up_run(_up_fixture(tmp, '别的行\n', _UP_EDIT))
    return rc != 0 and '在官方文件里找不到' in out


@missing_case('登记过了 → 绿，且产物就是官方原文（不是「旧上游 + 我们的改动」）')
def _m42(tmp, tree):
    r = _up_fixture(tmp, '别的行\n', _UP_EDIT, _UP_WHY)
    rc, out = _up_run(r)
    return (rc == 0 and '不出货 1 处' in out
            and (r / 'out' / 'demo.txt').read_text(encoding='utf-8') == '别的行\n')


@missing_case('登记了、原文却还在 → 必须失败（登记过期，上游又把它加回来了）')
def _m43(tmp, tree):
    rc, out = _up_run(_up_fixture(tmp, '原文\n', _UP_EDIT, _UP_WHY))
    return rc != 0 and '登记已经过期' in out


@missing_case('登记的序号越界 → 必须失败（以为登记上了，其实一条都没登记上）')
def _m44(tmp, tree):
    reg = {'edits': {'demo.txt': {'which': [2], 'why': '越界'}}}
    rc, out = _up_run(_up_fixture(tmp, '别的行\n', _UP_EDIT, reg))
    return rc != 0 and 'which 不对' in out


@missing_case('登记没写 why → 必须失败（下一版没人知道该不该撤掉它）')
def _m45(tmp, tree):
    reg = {'edits': {'demo.txt': {'which': 'all', 'why': '   '}}}
    rc, out = _up_run(_up_fixture(tmp, '别的行\n', _UP_EDIT, reg))
    return rc != 0 and '没写 why' in out


@missing_case('登记了一个 src/upstream 下没人改的文件 → 必须失败（登记写错了地方）')
def _m46(tmp, tree):
    reg = {'edits': {'别的.txt': {'which': 'all', 'why': '写错路径'}}}
    rc, out = _up_run(_up_fixture(tmp, '别的行\n', _UP_EDIT, reg))
    return rc != 0 and '没有哪份映射改这个文件' in out


@missing_case('不传版本 → 必须失败（少个参数就等于把整张登记表悄悄作废）')
def _m47(tmp, tree):
    rc, out = _up_run(_up_fixture(tmp, '别的行\n', _UP_EDIT, _UP_WHY), version=None)
    return rc != 0 and 'unpatchable' in out


# 该版专属映射叠加在通用映射之上，测三件事：叠加确实发生、找不到原文会失败、
# 改一个没有通用映射的文件也失败（那种映射永远不会执行）。
@missing_case('该版专属映射与通用映射叠加 → 两处都要落在同一份产物里')
def _m48(tmp, tree):
    r = _up_fixture(tmp, '原文\n该版专属\n', _UP_EDIT, None,
                    vedits=[{'find': ['该版专属\n'], 'replace': ['该版译文\n']}])
    rc, out = _up_run(r)
    return (rc == 0 and '该版专属改动 1 处' in out
            and (r / 'out' / 'demo.txt').read_text(encoding='utf-8') == '译文\n该版译文\n')


@missing_case('该版专属映射找不到原文 → 必须失败（不因为「是该版专属」就放松）')
def _m49(tmp, tree):
    r = _up_fixture(tmp, '原文\n', _UP_EDIT, None,
                    vedits=[{'find': ['没有这一行\n'], 'replace': ['x\n']}])
    rc, out = _up_run(r)
    return rc != 0 and '在官方文件里找不到' in out


@missing_case('该版专属映射改的文件没有通用映射 → 必须失败（它永远不会被套用）')
def _m50(tmp, tree):
    r = _up_fixture(tmp, '原文\n', _UP_EDIT, None,
                    vedits=[{'find': ['原文\n'], 'replace': ['x\n']}], vsrc='别的.txt')
    rc, out = _up_run(r)
    return rc != 0 and '永远不会被套用' in out


# ── 10. CurseForge 上取不到的 jar，必须逐个登记才放行 ─────────────────────
#
# 用残缺的 jar 集合建版本库，vaultpatcher.json 里的 "missing" 就分不清是这一版没有这个 key，
# 还是没下载到 jar。所以只有在 versions/<版本>/unobtainable.json 里逐个 fileID 登记才放行。
# 三条反例：登记齐了放行、少登记一个失败、登记文件不存在时失败。

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


@missing_case('取不到的 jar 少登记了一个 → 必须失败，且点名是哪个')
def _m52(tmp, tree):
    return _unob(tmp, '9.9', [7948263]) == [8005487]


@missing_case('unobtainable.json 整份不存在 → 必须失败，不许默认放行')
def _m53(tmp, tree):
    return _unob(tmp, '9.9', None) == [7948263, 8005487]


def _prune(tmp, upstream_has):
    """造一版出货树与官方文件，运行 gen_missing_questpics.py --prune。

    返回 (退出码, 本包画的那张是否还在)。`upstream_has=None` 表示没取到该版官方文件，
    此时不知道上游有没有这张图。
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


@missing_case('取不到该版官方文件 → 必须失败，不许当成「上游没有」而覆盖过去')
def _m56(tmp, tree):
    rc, _ = _prune(tmp, None)
    return rc != 0


# versions/<版本>/pack_overrides.json：同一个键在两版里参数个数不同时，一份中文对不了两版，
# 多写参数会让 TranslatableContents 抛异常，整行显示成未替换的模板。
# 写错命名空间、登记过期、没写理由、值不是字符串、文件损坏，都必须失败。
def _po_fixture(tmp, doc=None, base=None):
    """造一棵最小出货树 + 一份该版覆盖，返回 (仓库根, 那份 zh_cn.json)。"""
    r = tmp / 'porepo'
    (r / 'scripts').mkdir(parents=True, exist_ok=True)
    shutil.copy(ROOT / 'scripts' / 'gen_pack_overrides.py', r / 'scripts')
    lang = r / 'tree' / 'resourcepacks' / 'ATM10汉化包' / 'assets' / 'demo' / 'lang'
    lang.mkdir(parents=True)
    f = lang / 'zh_cn.json'
    f.write_text(json.dumps(base if base is not None else {'demo.k': '公共树的值'},
                            ensure_ascii=False), encoding='utf-8')
    if doc is not None:
        d = r / 'versions' / '9.9'
        d.mkdir(parents=True, exist_ok=True)
        (d / 'pack_overrides.json').write_text(
            doc if isinstance(doc, str) else json.dumps(doc, ensure_ascii=False),
            encoding='utf-8')
    return r, f


def _po_run(r):
    x = subprocess.run([sys.executable, str(r / 'scripts' / 'gen_pack_overrides.py'),
                        '9.9', str(r / 'tree')], capture_output=True, text=True, cwd=r)
    return x.returncode, x.stdout + x.stderr


_PO_OK = {'lang': {'demo': {'demo.k': {'value': '该版的值', 'why': '这一版上游多了个参数'}}}}


@missing_case('该版覆盖生效 → 出货树里的值真的换了，并打印条数')
def _m57(tmp, tree):
    r, f = _po_fixture(tmp, _PO_OK)
    rc, out = _po_run(r)
    return (rc == 0 and '覆盖资源包译文 1 条' in out
            and json.loads(f.read_text(encoding='utf-8'))['demo.k'] == '该版的值')


@missing_case('没有这份覆盖文件 → 什么都不做（不是每版都需要分叉）')
def _m58(tmp, tree):
    r, f = _po_fixture(tmp)
    rc, out = _po_run(r)
    return rc == 0 and '覆盖资源包译文' not in out


@missing_case('覆盖的命名空间在出货树里没有 zh_cn.json → 必须失败')
def _m59(tmp, tree):
    doc = {'lang': {'不存在的命名空间': {'x': {'value': 'v', 'why': 'w'}}}}
    rc, out = _po_run(_po_fixture(tmp, doc)[0])
    return rc != 0 and '永远不会生效' in out


@missing_case('覆盖的值与公共树完全相同 → 必须失败（这条登记已经过期）')
def _m60(tmp, tree):
    doc = {'lang': {'demo': {'demo.k': {'value': '公共树的值', 'why': 'w'}}}}
    rc, out = _po_run(_po_fixture(tmp, doc)[0])
    return rc != 0 and '白写' in out


@missing_case('覆盖没写 why → 必须失败')
def _m61(tmp, tree):
    doc = {'lang': {'demo': {'demo.k': {'value': '该版的值', 'why': '   '}}}}
    rc, out = _po_run(_po_fixture(tmp, doc)[0])
    return rc != 0 and '没写 why' in out


@missing_case('覆盖的 value 不是字符串 → 必须失败')
def _m62(tmp, tree):
    doc = {'lang': {'demo': {'demo.k': {'value': 123, 'why': 'w'}}}}
    rc, out = _po_run(_po_fixture(tmp, doc)[0])
    return rc != 0 and 'value 不是字符串' in out


@missing_case('覆盖文件是坏 JSON → 必须失败，不许当成「没有覆盖」放过')
def _m63(tmp, tree):
    rc, out = _po_run(_po_fixture(tmp, '{坏')[0])
    return rc != 0 and '解析失败' in out


def _po_file_fixture(tmp, layers, public='公共页', sources=None, target=True):
    """造最小文件覆盖层。sources 是 {层名: 文件内容}。"""
    r, _ = _po_fixture(tmp, {'files': layers})
    rel = Path('assets/demo/guide/page.md')
    if target:
        f = r / 'tree/resourcepacks/ATM10汉化包' / rel
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(public, encoding='utf-8')
    for name, body in (sources or {}).items():
        f = r / 'src/pack_overrides' / name / rel
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(body, encoding='utf-8')
    return r, r / 'tree/resourcepacks/ATM10汉化包' / rel


def _po_record_dropped(r, public='公共页', sha256=None):
    """登记一份确由版权检查从公共树剔除的源页。"""
    rel = Path('assets/demo/guide/page.md')
    source = r / 'src/pack' / rel
    source.parent.mkdir(parents=True, exist_ok=True)
    source.write_text(public, encoding='utf-8')
    got = hashlib.sha256(source.read_bytes()).hexdigest()
    manifest = r / 'build/snapshots/upstream_identical_dropped.json'
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text(json.dumps({'files': {rel.as_posix(): {
        'sha256': sha256 or got,
        'jar': 'demo.jar',
        'entry': rel.as_posix(),
    }}}), encoding='utf-8')


@missing_case('整文件版本层生效 → 覆盖公共页，并打印文件数与层名')
def _m64(tmp, tree):
    r, f = _po_file_fixture(
        tmp, {'old-books': {'why': '旧版模组仍使用旧剧情'}},
        sources={'old-books': '旧版专属页'})
    rc, out = _po_run(r)
    return (rc == 0 and f.read_text(encoding='utf-8') == '旧版专属页'
            and '覆盖资源包文件 1 个（old-books）' in out)


@missing_case('登记的文件层不存在或为空 → 必须失败')
def _m65(tmp, tree):
    r, _ = _po_file_fixture(tmp, {'missing': {'why': 'w'}})
    rc, out = _po_run(r)
    return rc != 0 and '不存在或为空' in out


@missing_case('整文件版本层没写 why → 必须失败')
def _m66(tmp, tree):
    r, _ = _po_file_fixture(tmp, {'old-books': {'why': ' '}},
                            sources={'old-books': '旧版专属页'})
    rc, out = _po_run(r)
    return rc != 0 and '没写 why' in out


@missing_case('整文件覆盖与公共页相同 → 必须失败（登记已过期）')
def _m67(tmp, tree):
    r, _ = _po_file_fixture(tmp, {'old-books': {'why': 'w'}},
                            sources={'old-books': '公共页'})
    rc, out = _po_run(r)
    return rc != 0 and '白写' in out


@missing_case('整文件覆盖的目标不在公共树 → 必须失败，不许悄悄新塞文件')
def _m68(tmp, tree):
    r, _ = _po_file_fixture(tmp, {'old-books': {'why': 'w'}},
                            sources={'old-books': '旧版专属页'}, target=False)
    rc, out = _po_run(r)
    return rc != 0 and '公共树里没有这个文件' in out


@missing_case('两个文件层撞同一路径 → 必须失败，不许靠层名顺序决定')
def _m69(tmp, tree):
    layers = {'old-a': {'why': 'w'}, 'old-b': {'why': 'w'}}
    r, _ = _po_file_fixture(tmp, layers,
                            sources={'old-a': '旧页 A', 'old-b': '旧页 B'})
    rc, out = _po_run(r)
    return rc != 0 and '只能有一个所有者' in out


@missing_case('版权检查剔除的公共页 → 路径与哈希都匹配才允许版本层恢复')
def _m70(tmp, tree):
    r, f = _po_file_fixture(tmp, {'new-books': {'why': '新版正文已改写'}},
                            sources={'new-books': '新版专属页'}, target=False)
    _po_record_dropped(r)
    rc, out = _po_run(r)
    return (rc == 0 and f.read_text(encoding='utf-8') == '新版专属页'
            and '覆盖资源包文件 1 个（new-books）' in out)


@missing_case('版权检查剔除记录哈希不符 → 必须失败，不许拿旧清单新增文件')
def _m71(tmp, tree):
    r, _ = _po_file_fixture(tmp, {'new-books': {'why': '新版正文已改写'}},
                            sources={'new-books': '新版专属页'}, target=False)
    _po_record_dropped(r, sha256='0' * 64)
    rc, out = _po_run(r)
    return rc != 0 and '匹配剔除记录' in out


def run_missing(name, fn):
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        ok = fn(tmp, fixture(tmp))
    print(('✅' if ok else '❌') + ' %s' % name)
    return ok


def main():
    print('检查脚本的反例测试：每条复现一次真实事故，验证检查确实会失败\n')
    ok = sum(run_case(*c) for c in CASES)
    print('\n%d/%d 项检查经反例验证确实会失败' % (ok, len(CASES)))
    print('\n前提缺失时不许静默放过：\n')
    ok2 = sum(run_missing(*m) for m in MISSING)
    print('\n%d/%d 条' % (ok2, len(MISSING)))
    if ok != len(CASES) or ok2 != len(MISSING):
        print('有检查没拦住反例，修好之前不许发版。')
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
