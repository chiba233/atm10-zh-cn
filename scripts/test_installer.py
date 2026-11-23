# -*- coding: utf-8 -*-
# atm10-zh-cn — All the Mods 10 简体中文汉化补丁「绿油油版」
# Copyright (C) 2026 星野夢華 (Hoshino Yumeka)
# SPDX-License-Identifier: GPL-3.0-or-later
"""安装脚本端到端测试（三平台 CI 共用）。

流程：造一个假游戏实例 → 把「释放后的汉化文件夹」放进实例根目录 →
apply → 断言（文件落位 / options.txt 已启用资源包 / 备份完整）→
restore → 断言（被覆盖文件还原 / 新增文件删除 / options.txt 还原）。
macOS/Linux 走 install.sh，Windows 走 install.ps1（powershell 5.1，与用户双击 .bat 一致）。
"""
import hashlib, os, platform, re, shutil, subprocess, sys, tempfile, zipfile
from pathlib import Path

# Windows runner 的 stdout 默认 cp1252，打不出中文/emoji
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')

sys.path.insert(0, str(Path(__file__).resolve().parent))
from paths import COMMON

ROOT = Path(__file__).resolve().parent.parent
IS_WIN = platform.system() == 'Windows'
# 测的是出货树（由 assemble.py 组装）。可以传入合成好的版本树 build/v/<版本>，默认用 build/common。
TREE = Path(sys.argv[1]) if len(sys.argv) > 1 else COMMON
if not TREE.is_dir():
    sys.exit('❌ 出货树不存在: %s\n'
             '   先跑: python3 scripts/assemble.py && ./scripts/generate_all.sh' % TREE)
# ── 静态检查：`$var` 后面紧跟中文 ─────────────────────────────────────────
# 单字节语言环境（CI 容器常见 LANG=C，macOS 自带的 bash 3.2 也是）会把 UTF-8 的头字节算进变量名，
# `$name……` 变成 `$nameâ`，配合 set -u 报 unbound variable。相关提示平时走不到，只能静态检查。
_BAD_VAR = re.compile(r'\$[A-Za-z_][A-Za-z0-9_]*[^\x00-\x7f]')
_offenders = [
    (n, line.strip())
    for n, line in enumerate((ROOT / 'installer' / 'install.sh')
                             .read_text(encoding='utf-8').split('\n'), 1)
    if _BAD_VAR.search(line) and not line.lstrip().startswith('#')
]
if _offenders:
    sys.exit('❌ install.sh 里有 %d 处 `$变量` 紧跟非 ASCII 字符，必须写成 ${变量}：\n%s'
             % (len(_offenders), '\n'.join('   %4d  %s' % o for o in _offenders)))

# 安装器里与整合包版本有关的字样都是 @@MCVER@@ 占位，由 build_dist.sh 填入。测试同样填一遍，
# 测玩家拿到的脚本。
MCVER = sorted((d.name for d in (ROOT / 'versions').iterdir()
                if d.is_dir() and d.name[0].isdigit()),
               key=lambda s: [int(x) for x in s.split('.')])[-1]


def default_packs(ver):
    """该版实测的默认资源包顺序，格式与 build_dist.sh 注入的完全一致"""
    f = ROOT / 'versions' / ver / 'default_resource_packs.txt'
    if not f.is_file():
        return ''
    names = [l.strip() for l in f.read_text(encoding='utf-8').splitlines()
             if l.strip() and not l.startswith('#')]
    return ','.join('"%s"' % n for n in names)


DEFAULT_PACKS = default_packs(MCVER)
# 补丁版本号取什么值都行（联网检查已被 ATM_SKIP_UPDATE_CHECK 关闭），但必须填掉 @@PATCHVER@@。
PATCHVER = 'test'


def materialize(src, dst):
    """按 build_dist.sh 的替换规则填掉安装器模板的占位符，写到 dst。
    漏填 @@DEFAULT_PACKS@@ 时，安装器会把它当资源包名写进 options.txt，测试照样通过。"""
    t = src.read_text(encoding='utf-8')
    t = (t.replace('@@MCVER@@', MCVER)
          .replace('@@DEFAULT_PACKS@@', DEFAULT_PACKS)
          .replace('@@PATCHVER@@', PATCHVER))
    left = re.findall(r'@@[A-Z_]+@@', t)
    if left:
        sys.exit('❌ %s 里还有没填的占位符：%s\n'
                 '   build_dist.sh 加了新占位符，这里要跟着加，否则测的不是玩家拿到的那份。'
                 % (src.name, sorted(set(left))))
    dst.write_text(t, encoding='utf-8')
    return dst


# 子串包含查不出数组中间多出 ] 的语法损坏，也查不出条目没排在最后一位（等于没启用）。
def resource_packs(text):
    """从 options.txt 原文解析 resourcePacks 数组，返回条目列表（单双引号都认），解析失败返回 None。

    `[^\\]]*` 不匹配 "]"，并要求数组后紧跟行尾（`\\r?$`）。数组中间多出 "]"（CRLF 问题的
    典型症状）时整条正则匹配失败，不会只解析出前半段。"""
    m = re.search(r'^resourcePacks:\[([^\]]*)\]\r?$', text, re.M)
    if m is None:
        return None
    return re.findall(r'["\']([^"\']*)["\']', m.group(1))


# 安装器在待装文件少于 50 个时中止。这批用例只测 options.txt，补足占位文件数量即可。
def fill_payload(reld, n=60):
    d = reld / 'config' / 'hanhua_test_payload'
    d.mkdir(parents=True, exist_ok=True)
    for i in range(n):
        (d / f'{i}.json').write_text('{}\n', encoding='utf-8')


# 资源包名带整合包版本号，直接从安装器脚本里读，避免两边各写一份对不上。
ENTRY = re.search(r"PACK_ENTRY='([^']+)'",
                   (ROOT / 'installer' / 'install.sh').read_text(encoding='utf-8')
                   ).group(1).replace('@@MCVER@@', MCVER)
PACK = ENTRY.split('/', 1)[1][:-4]

tmp = Path(tempfile.mkdtemp(prefix='hanhua-test-'))
inst = tmp / 'instance'
(inst / 'mods').mkdir(parents=True)
# 实例判定用「mods 里 jar 数 >= 20」把真实例和汉化包自己的 mods/ 区分开
for i in range(25):
    (inst / 'mods' / f'modpack-{i}.jar').write_text('x', encoding='utf-8')
OPTS_BEFORE = 'version:4189\nresourcePacks:["vanilla","mod_resources"]\nlang:zh_cn\n'
(inst / 'options.txt').write_text(OPTS_BEFORE, encoding='utf-8')

# 预置一个「会被覆盖」的旧文件，验证备份/还原
sample = sorted((COMMON / 'vaultpatcher' / 'modules').glob('*.json'))[0].name
pre = inst / 'vaultpatcher' / 'modules' / sample
pre.parent.mkdir(parents=True)
pre.write_text('OLD-CONTENT', encoding='utf-8')

# 预置 r14 发过、之后停发的两个 dynamic 模块，安装器必须删掉它们：dynamic 表每次替换都要
# 线性扫描，只覆盖不删除的话，装了新版照样掉帧。
STALE = ('config_ui_generated.json', 'catnip_config_ui.json')
for _s in STALE:
    (inst / 'vaultpatcher' / 'modules' / _s).write_text('STALE', encoding='utf-8')

# 模拟释放后的汉化文件夹（与 build_dist.sh 产物同构）
rel = inst / 'ATM10-7.2-汉化补丁-绿油油版'
rel.mkdir()
for d in ('config', 'kubejs', 'mods', 'vaultpatcher'):
    shutil.copytree(TREE / d, rel / d)
(rel / 'resourcepacks').mkdir()
src = TREE / 'resourcepacks' / PACK
with zipfile.ZipFile(rel / 'resourcepacks' / f'{PACK}.zip', 'w', zipfile.ZIP_DEFLATED) as z:
    for p in src.rglob('*'):
        if p.is_file() and p.name != '.DS_Store':
            z.write(p, p.relative_to(src).as_posix())
for s in ('install.sh', 'install.ps1'):
    materialize(ROOT / 'installer' / s, rel / s)
if (TREE / '可选mods-拼音搜索').is_dir():
    shutil.copytree(TREE / '可选mods-拼音搜索', rel / '可选mods-拼音搜索')


def run(*args):
    if IS_WIN:
        cmd = ['powershell', '-NoProfile', '-ExecutionPolicy', 'Bypass',
               '-File', str(rel / 'install.ps1'), *args]
    else:
        cmd = ['bash', str(rel / 'install.sh'), *args]
    r = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace')
    print(r.stdout)
    if r.stderr:
        print(r.stderr, file=sys.stderr)
    assert r.returncode == 0, f'install {args} 退出码 {r.returncode}'
    return (r.stdout or '') + (r.stderr or '')


def read_opts():
    return (inst / 'options.txt').read_text(encoding='utf-8')


# ---- 应用汉化 ----
run('apply')
assert ENTRY in read_opts(), 'options.txt 未启用汉化资源包'
assert (inst / 'resourcepacks' / f'{PACK}.zip').exists(), '资源包未落位'
assert (inst / 'config' / 'vaultpatcher_asm' / 'config.json').exists(), 'config 未落位'
assert pre.read_text(encoding='utf-8') != 'OLD-CONTENT', '旧文件未被新版覆盖'
for _s in STALE:
    assert not (inst / 'vaultpatcher' / 'modules' / _s).exists(), \
        f'{_s} 没被清理，装过 r14 的玩家会继续掉帧'

# ---- 回归：重复安装不许提示「清理了 N 个旧版本残留的任务书语言文件」----
# payload 里 4 字节的空文件 `_X.snbt` 与 `zz_hanhua_X.snbt` 字节相同，clean_legacy_quest_lang
# 会把上次装的删掉再复制回来，每次安装都提示清理了 N 个。第一次安装后盘上才有这些文件，
# 所以在第二次安装时检查。
_again = run('apply')
assert '旧版本残留的任务书语言文件' not in _again, \
    '重复安装仍在清理 payload 自己会覆盖的文件，空文件被删掉又复制回来：\n' + _again
assert (inst / 'config' / 'ftbquests' / 'quests' / 'lang' / 'zh_cn').is_dir(), \
    '第二次安装后任务书语言目录不见了'
print('✅ 重复安装不再自我清理任务书空壳 OK')

# 备份目录名是秒级时间戳，两次 apply 落在同一秒会并成一个，不拿个数当断言，
# 只取最早那个（它一定持有第一次安装前的 OLD-CONTENT）。
bks = sorted(p for p in (rel / 'backups').iterdir() if p.is_dir())[:1]
assert bks, '一个备份都没有'
bk = bks[0]
assert (bk / 'vaultpatcher' / 'modules' / sample).read_text(encoding='utf-8') == 'OLD-CONTENT', \
    '备份里没有被覆盖文件的原内容'
assert (bk / '新增文件清单.txt').exists(), '缺新增文件清单'
assert (bk / 'options.txt').read_text(encoding='utf-8') == OPTS_BEFORE, '备份的 options.txt 不对'

# ---- 恢复备份 ----
run('restore', bk.name)
assert pre.read_text(encoding='utf-8') == 'OLD-CONTENT', '被覆盖文件未还原'
assert ENTRY not in read_opts(), 'options.txt 未还原'
assert not (inst / 'resourcepacks' / f'{PACK}.zip').exists(), '新增的资源包未删除'
assert not (inst / 'kubejs' / 'client_scripts' / 'pb_hanhua_tooltip.js').exists(), '新增的脚本未删除'

# ---- 可选mods（拼音搜索）：apply 不装、apply-with-pinyin 装、restore 删 ----
pin_jars = sorted((rel / '可选mods-拼音搜索').glob('*.jar')) if (rel / '可选mods-拼音搜索').is_dir() else []
if pin_jars:
    jar = pin_jars[0].name
    assert not (inst / 'mods' / jar).exists(), '普通 apply 不应安装可选mods'
    run('apply-with-pinyin')
    assert (inst / 'mods' / jar).exists(), '拼音搜索 mod 未安装'
    bk2 = sorted(p for p in (rel / 'backups').iterdir() if p.is_dir())[-1]
    manifest = (bk2 / '新增文件清单.txt').read_text(encoding='utf-8')
    assert f'mods/{jar}' in manifest, '拼音 mod 未登记进新增文件清单'
    run('restore', bk2.name)
    assert not (inst / 'mods' / jar).exists(), '恢复备份未删除拼音 mod'

    # ---- 已装过拼音搜索：不再问，也不再装 ----
    # 同一个 mod id 有两个 jar 时，NeoForge 报「Mod ID is duplicated」并拒绝启动。
    # 预置的 jar 换了大小写与版本号：必须按 mod id（文件名首段）识别。
    planted = inst / 'mods' / 'JECharacters-1.21.1-neoforge-4.5.20.jar'
    planted.write_text('OLD-JEC', encoding='utf-8')

    def jec_jars():
        return sorted(p.name for p in (inst / 'mods').glob('*.jar')
                      if p.name.lower().startswith('jecharacters'))

    run('apply-with-pinyin')
    assert jec_jars() == [planted.name], \
        f'已装拼音 mod 时不该再装一个：mods/ 里现在有 {jec_jars()}'
    assert planted.read_text(encoding='utf-8') == 'OLD-JEC', '不该覆盖玩家已装的那个'

    # 菜单路径：只输入「1」。如果脚本仍然提问，第二次读取会得到 EOF 并打印「跳过可选mods」，
    # 由此区分「没问」与「问了没答」。
    if IS_WIN:
        _cmd = ['powershell', '-NoProfile', '-ExecutionPolicy', 'Bypass',
                '-File', str(rel / 'install.ps1')]
    else:
        _cmd = ['bash', str(rel / 'install.sh')]
    _r = subprocess.run(_cmd, input='1\n', capture_output=True, text=True,
                        encoding='utf-8', errors='replace')
    print(_r.stdout)
    assert _r.returncode == 0, f'菜单路径退出码 {_r.returncode}'
    assert '已装有拼音搜索 mod' in _r.stdout, '装过了却没提示，说明检测没生效'
    assert '跳过可选mods' not in _r.stdout, '装过了还在问'
    assert jec_jars() == [planted.name], f'菜单路径又装了一个：{jec_jars()}'

    planted.unlink()
else:
    print('（仓库无可选mods jar，跳过拼音分支）')

# ---- 回归：手动输入带引号或空格的实例路径（复制粘贴、拖拽时常见）----
# 释放文件夹放在非实例目录里，触发 check_target 的输入循环。
# 路径同时含空格与中文（PCL2 默认装在中文目录）。
spaced = tmp / '我的 Game Dir With Spaces 绿油油'
(spaced / 'mods').mkdir(parents=True)
for i in range(25):
    (spaced / 'mods' / f'modpack-{i}.jar').write_text('x', encoding='utf-8')
SPACED_OPTS = 'version:4189\nresourcePacks:[]\n'
(spaced / 'options.txt').write_text(SPACED_OPTS, encoding='utf-8')
loose = tmp / 'loose' / 'ATM10-hanhua'   # 父目录 tmp/loose 不含 mods/options.txt
loose.mkdir(parents=True)
(loose / 'config').mkdir()
fill_payload(loose)
for s in ('install.sh', 'install.ps1'):
    materialize(ROOT / 'installer' / s, loose / s)


def run_prompt(script_dir, mode, answer):
    """跑安装脚本，在‘输入实例路径’提示处喂 answer。返回 (returncode, 合并输出)。"""
    if IS_WIN:
        cmd = ['powershell', '-NoProfile', '-ExecutionPolicy', 'Bypass',
               '-File', str(script_dir / 'install.ps1'), mode]
        r = subprocess.run(cmd, input=answer + '\n', capture_output=True,
                           text=True, encoding='utf-8', errors='replace', timeout=120)
        return r.returncode, (r.stdout or '') + (r.stderr or '')
    # Unix：install.sh 用 [ -t 0 ] 判交互，必须用 pty 让 stdin 是终端
    import pty, os
    master, slave = pty.openpty()
    p = subprocess.Popen(['bash', str(script_dir / 'install.sh'), mode],
                         stdin=slave, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    os.close(slave)
    os.write(master, (answer + '\n').encode('utf-8'))
    try:
        p.wait(timeout=60)
    except subprocess.TimeoutExpired:
        os.close(master); p.kill(); p.wait()
        return 124, '（超时：脚本未能解析路径，仍在等待输入）'
    out = p.stdout.read().decode('utf-8', 'replace')
    os.close(master)
    return p.returncode, out


# Unix 常见是单引号粘贴，Windows 拖拽是双引号，各测本平台形态（两种都在脚本里处理）
q = '"' if IS_WIN else "'"
quoted = q + str(spaced) + q
rc, out = run_prompt(loose, 'backup', quoted)
assert rc == 0, f'带引号路径 backup 失败(rc={rc})：\n{out}'
assert '目标实例' in out, f'未从带引号路径解析出实例：\n{out}'
lbks = sorted(p for p in (loose / 'backups').iterdir() if p.is_dir()) if (loose / 'backups').is_dir() else []
assert lbks and (lbks[-1] / 'options.txt').read_text(encoding='utf-8') == SPACED_OPTS, \
    '未正确定位到带空格的实例目录'
print('✅ 引号/空格路径输入清洗 OK')

# ---- 回归：就地解压（压缩包内容直接覆盖到实例根目录，随后又运行安装器）----
# 脚本目录就是实例目录，源与目标相同，复制会失败：Windows 报
# "Cannot overwrite the item ... with itself"，Unix 的 cp 同样失败。
inplace = tmp / 'inplace-instance'
(inplace / 'mods').mkdir(parents=True)
INPLACE_OPTS = 'version:4189\nresourcePacks:[]\nlang:zh_cn\n'
(inplace / 'options.txt').write_text(INPLACE_OPTS, encoding='utf-8')
for i in range(25):
    (inplace / 'mods' / f'modpack-{i}.jar').write_text('x', encoding='utf-8')
for d in ('config', 'kubejs', 'vaultpatcher'):          # 模拟解压覆盖
    shutil.copytree(TREE / d, inplace / d, dirs_exist_ok=True)
(inplace / 'resourcepacks').mkdir(exist_ok=True)
shutil.copy2(rel / 'resourcepacks' / f'{PACK}.zip', inplace / 'resourcepacks' / f'{PACK}.zip')
for s_ in ('install.sh', 'install.ps1'):
    materialize(ROOT / 'installer' / s_, inplace / s_)

if IS_WIN:
    cmd = ['powershell', '-NoProfile', '-ExecutionPolicy', 'Bypass',
           '-File', str(inplace / 'install.ps1'), 'apply']
else:
    cmd = ['bash', str(inplace / 'install.sh'), 'apply']
r = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8',
                   errors='replace', timeout=300)
out = (r.stdout or '') + (r.stderr or '')
assert r.returncode == 0, f'就地解压模式安装失败(rc={r.returncode})：\n{out}'
assert 'with itself' not in out, f'仍在把文件复制到自己头上：\n{out}'
assert ENTRY in (inplace / 'options.txt').read_text(encoding='utf-8'), \
    f'就地解压模式未启用资源包：\n{out}'
assert (inplace / 'config' / 'vaultpatcher_asm' / 'config.json').exists(), '就地解压模式误删了文件'
# 就地解压这条路径同样要调用 clean_legacy_config_ui，清掉 r14 残留。
for _s in STALE:
    assert not (inplace / 'vaultpatcher' / 'modules' / _s).exists(), \
        f'就地解压模式没清掉 {_s}'
print('✅ 就地解压（源即目标）不再自我复制 OK')

# ---- 回归：刚装好、一次都没启动过的实例（没有 options.txt）----
# Minecraft 退出时才写 options.txt，实例判定依赖它的话，会一直卡在输入路径的循环里。
fresh = tmp / '全新 实例 never-launched'
(fresh / 'mods').mkdir(parents=True)
for i in range(25):
    (fresh / 'mods' / f'modpack-{i}.jar').write_text('x', encoding='utf-8')
frel = fresh / 'atm10-zh_cn-client'
frel.mkdir()
for d in ('config', 'kubejs', 'mods', 'vaultpatcher'):
    shutil.copytree(TREE / d, frel / d)
(frel / 'resourcepacks').mkdir()
shutil.copy2(rel / 'resourcepacks' / f'{PACK}.zip', frel / 'resourcepacks' / f'{PACK}.zip')
for s_ in ('install.sh', 'install.ps1'):
    materialize(ROOT / 'installer' / s_, frel / s_)

if IS_WIN:
    cmd = ['powershell', '-NoProfile', '-ExecutionPolicy', 'Bypass',
           '-File', str(frel / 'install.ps1'), 'apply']
else:
    cmd = ['bash', str(frel / 'install.sh'), 'apply']
r = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8',
                   errors='replace', timeout=300)
out = (r.stdout or '') + (r.stderr or '')
assert r.returncode == 0, f'全新实例（无 options.txt）安装失败(rc={r.returncode})：\n{out}'
assert '不是游戏实例根目录' not in out, f'没识别出全新实例：\n{out}'
assert (fresh / 'config' / 'vaultpatcher_asm' / 'config.json').exists(), '文件未落位'
newopt = fresh / 'options.txt'
assert newopt.exists(), f'全新实例没建出 options.txt：\n{out}'
txt = newopt.read_text(encoding='utf-8')
assert 'lang:zh_cn' in txt, f'新建的 options.txt 没写入中文语言：\n{txt}'
# 逐项比对，子串包含查不出这种错误（issue #9 P1-2）：install.ps1 的 $DefaultPacks 是单引号
# 字符串，"" 会原样写成 resourcePacks:[""vanilla"",...]，数组无法解析，游戏回落默认列表，
# 汉化没有启用。
want = [n.strip() for n in (ROOT / 'versions' / MCVER / 'default_resource_packs.txt')
        .read_text(encoding='utf-8').splitlines()
        if n.strip() and not n.startswith('#')] + [ENTRY]
got = resource_packs(txt)
assert got is not None, f'新建的 resourcePacks 行解析不出来（语法坏了）：\n{txt!r}'
assert got == want, ('新建的 resourcePacks 数组与预期不符\n  实际 %r\n  预期 %r\n  原文 %r'
                     % (got, want, txt))
print('✅ 全新实例（无 options.txt，路径含中文和空格）通过，数组逐项比对')

# ---- 回归：玩过的实例但 options.txt 不见了，不许新建 ----
# 新建一份只有两行的 options.txt，游戏启动时会把其余项按默认值补齐，键位、视频、声音设置
# 全部清空。已有 options.txt 时只改 resourcePacks 一行，其余 598 行逐字节不变。
played = tmp / 'played-instance'
(played / 'mods').mkdir(parents=True)
for i in range(25):
    (played / 'mods' / f'modpack-{i}.jar').write_text('x', encoding='utf-8')
(played / 'logs').mkdir()                      # 启动过的痕迹
(played / 'saves').mkdir()
prel = played / 'ATM10-hanhua'
prel.mkdir()
(prel / 'config').mkdir()
fill_payload(prel)
for s_ in ('install.sh', 'install.ps1'):
    materialize(ROOT / 'installer' / s_, prel / s_)
rc, out = run_prompt(prel, 'apply', str(played))
assert not (played / 'options.txt').exists(), \
    '玩过的实例缺 options.txt 时，安装器不该新建一份（会把玩家设置冲成默认）'
assert '不新建' in out, f'应提示不新建 options.txt：\n{out}'
print('✅ 玩过的实例缺 options.txt 时拒绝新建 OK')

# ---- 回归：装完汉化包没有启用，需要手动拖到最后一位 ----
#
# bash 版 patch_options 用 grep 取 resourcePacks 整行，再用 "${body%]}" 去掉结尾的 "]"。
# Minecraft 在 Windows 上按 CRLF 写 options.txt，行尾是 "]\r"，"${body%]}" 不生效，会拼出
#   resourcePacks:[...]\r,"file/ATM10汉化包-7.2.zip"]
# 这种中间多一个 "]"、夹着 \r 的坏行，汉化包实际没有启用。实例在 Windows 上启动过一次、
# 再拿到 Mac/Linux 安装，options.txt 就是 CRLF。
#
# 同时测重复安装不产生重复项：摘除已有条目时要认单引号和不带 file/ 前缀的写法，
# 否则每装一次多一份。用 resource_packs() 解析数组后逐项断言。
def resline_case(name, opts_text):
    """造一个实例与释放好的安装器文件夹，options.txt 按字节写入（文本模式会转换 \\r\\n）。"""
    instd = tmp / name / 'instance'
    (instd / 'mods').mkdir(parents=True)
    for i in range(25):
        (instd / 'mods' / f'modpack-{i}.jar').write_text('x', encoding='utf-8')
    (instd / 'options.txt').write_bytes(opts_text.encode('utf-8'))
    reld = instd / 'ATM10-hanhua'
    reld.mkdir()
    (reld / 'config').mkdir()
    fill_payload(reld)
    for s_ in ('install.sh', 'install.ps1'):
        materialize(ROOT / 'installer' / s_, reld / s_)
    return instd, reld


def run_apply_only(reld):
    """运行 apply，返回 (returncode, 合并输出)。不用 run()：这批用例的释放文件夹只有占位 config/。"""
    if IS_WIN:
        cmd = ['powershell', '-NoProfile', '-ExecutionPolicy', 'Bypass',
               '-File', str(reld / 'install.ps1'), 'apply']
    else:
        cmd = ['bash', str(reld / 'install.sh'), 'apply']
    r = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8',
                       errors='replace', timeout=300)
    return r.returncode, (r.stdout or '') + (r.stderr or '')


BARE = PACK + '.zip'   # 不带 file/ 前缀、带 .zip 后缀的裸文件名写法

CASES = [
    # 实测的默认资源包顺序，即首次启动后的状态
    ('内置包十几个-LF-无本包',
     'version:4189\nresourcePacks:[%s]\nlang:zh_cn\n' % DEFAULT_PACKS),
    ('内置包十几个-CRLF-无本包',      # ← CRLF：反馈的核心复现场景
     'version:4189\r\nresourcePacks:[%s]\r\nlang:zh_cn\r\n' % DEFAULT_PACKS),
    ('本包已存在但不在最后-CRLF',      # ← CRLF + 需要挪位：反馈的核心复现场景
     'version:4189\r\nresourcePacks:[%s]\r\nlang:zh_cn\r\n'
     % ','.join(['"vanilla"', '"%s"' % ENTRY, '"mod_resources"',
                 '"add_xycraft_overrides_stone"'])),
    ('本包重复项-单引号带file前缀',
     'version:4189\nresourcePacks:["vanilla",\'%s\',"mod_resources"]\nlang:zh_cn\n' % ENTRY),
    ('本包重复项-双引号不带file前缀',
     'version:4189\nresourcePacks:["vanilla","%s","mod_resources"]\nlang:zh_cn\n' % BARE),
    ('本包重复项-单引号不带file前缀',
     'version:4189\nresourcePacks:["vanilla",\'%s\',"mod_resources"]\nlang:zh_cn\n' % BARE),
    ('数组尾随逗号-无本包',
     'version:4189\nresourcePacks:["vanilla","mod_resources",]\nlang:zh_cn\n'),
    ('数组尾随逗号-CRLF',
     'version:4189\r\nresourcePacks:["vanilla","mod_resources",]\r\nlang:zh_cn\r\n'),
]

for label, opts_before in CASES:
    c_instd, c_reld = resline_case(label, opts_before)
    rc, out = run_apply_only(c_reld)
    raw = (c_instd / 'options.txt').read_bytes().decode('utf-8')
    packs = resource_packs(raw)
    assert rc == 0, f'[{label}] apply 失败(rc={rc})：\n{out}'
    assert packs is not None, f'[{label}] resourcePacks 行语法损坏，解析不出来：\n{raw!r}'
    assert packs.count(ENTRY) == 1, \
        f'[{label}] 汉化包条目应恰好 1 份，实际 {packs.count(ENTRY)} 份：{packs}'
    assert packs[-1] == ENTRY, \
        f'[{label}] 汉化包不在列表最后一位（不在最后等于没启用）：{packs}'
print(f'✅ resourcePacks 各种写法 + CRLF + 重复安装 回归 OK（{len(CASES)} 个用例）')

# 幂等：本包已在最后一位时不重写，CRLF 行尾也保持原样。
idempo_instd, idempo_reld = resline_case(
    '本包已在最后-CRLF-幂等',
    'version:4189\r\nresourcePacks:["vanilla","mod_resources","%s"]\r\nlang:zh_cn\r\n' % ENTRY)
rc, out = run_apply_only(idempo_reld)
assert rc == 0, f'幂等用例 apply 失败(rc={rc})：\n{out}'
assert '跳过' in out, f'汉化包已在最后一位时应提示跳过而不是重写：\n{out}'
idempo_packs = resource_packs((idempo_instd / 'options.txt').read_bytes().decode('utf-8'))
assert idempo_packs is not None and idempo_packs == ['vanilla', 'mod_resources', ENTRY], \
    f'幂等跳过后数组不应变化：{idempo_packs}'
print('✅ 汉化包已在最后一位时正确识别为跳过、CRLF 原样保留 OK')

# ---- 一键更新：挑选 asset（离线，用夹具 JSON）--------------------------
# Release 里有 7.0/7.1/7.2 × 客户端/服务端六个包，挑错会把 7.0 用户升级到 7.2 的包。
# 缺 sha256 摘要时不许安装。夹具照抄 GitHub 的真实字段顺序：name → uploader{…} → digest →
# browser_download_url，uploader 是嵌套对象，按 "},{" 切块的解析会出错。
def _asset(name, digest=True):
    sha = ('%064x' % (abs(hash(name)) % (1 << 256)))[:64]
    d = '"digest": "sha256:%s", ' % sha if digest else ''
    return ('{"id": 1, "name": "%s", "label": null, '
            '"uploader": {"login": "x", "id": 2, "type": "User"}, '
            '"content_type": "application/zip", "state": "uploaded", "size": 123, %s'
            '"download_count": 0, '
            '"browser_download_url": "https://example.invalid/%s"}' % (name, d, name))


FAKE_RELEASE = ('{\n  "tag_name": "vr99",\n  "assets": [\n    ' + ',\n    '.join(
    [_asset('atm10-zh_cn-client-r99-atm%s.zip' % v) for v in ('7.0', '7.1', '7.2')]
    + [_asset('atm10-zh_cn-server-r99-atm%s.zip' % v) for v in ('7.0', '7.1', '7.2')]
) + '\n  ]\n}\n')


def pick_asset(mcver, release_json):
    """取出 install.sh 里的 pick_client_asset，按指定 ATM 版本运行。"""
    src = (ROOT / 'installer' / 'install.sh').read_text(encoding='utf-8').replace('@@MCVER@@', mcver)
    m = re.search(r'^pick_client_asset\(\) \{.*?^\}', src, re.S | re.M)
    assert m, 'install.sh 里找不到 pick_client_asset，改名后要同步改这个测试'
    f = tmp / ('picker-%s.sh' % mcver)
    f.write_text(m.group(0) + '\n', encoding='utf-8')
    r = subprocess.run(['bash', '-c',
                        'set -euo pipefail; RELEASE_JSON="$1"; . "$2"; pick_client_asset',
                        '_', release_json, str(f)],
                       capture_output=True, text=True, encoding='utf-8', timeout=60)
    return r.returncode, [l for l in (r.stdout or '').split('\n') if l]


if not IS_WIN:                       # install.sh 只跑在 macOS / Linux
    for ver in ('7.0', '7.1', '7.2'):
        rc, got = pick_asset(ver, FAKE_RELEASE)
        assert rc == 0, f'ATM {ver}：pick_client_asset 退出码 {rc}'
        want = 'atm10-zh_cn-client-r99-atm%s.zip' % ver
        assert got and got[0] == want, f'ATM {ver}：挑成了 {got[:1]}，应为 {want}'
        assert len(got) == 3 and re.fullmatch(r'[0-9a-f]{64}', got[2]), f'ATM {ver}：摘要不对 {got}'
    rc, got = pick_asset('7.2', FAKE_RELEASE.replace('"digest"', '"nodigest"'))
    assert rc != 0 or not got, f'缺 sha256 摘要时不该挑得出 asset：rc={rc} got={got}'
    only_72 = '{"tag_name": "vr99", "assets": [%s]}' % _asset('atm10-zh_cn-client-r99-atm7.2.zip')
    rc, got = pick_asset('7.0', only_72)
    assert rc != 0 or not got, f'该版没有对应包时不该挑到别版：rc={rc} got={got}'
    print('✅ 一键更新挑包：按 ATM 版本精确匹配 + 缺摘要拒绝 OK')

# ---- 一键更新：端到端（离线，localhost 上的 HTTP 服务提供假 Release）------------
# 测完整流程：下载 → 校验 sha256 → 解包 → 用 ATM_TARGET 调起新版安装器 apply
#   → 把新版目录里的备份归并回原入口 → 把原入口的 payload 与脚本换成新版
# materialize() 填占位符时把 api.github.com 改写成 localhost，安装器本身不加测试开关。
if not IS_WIN:                       # install.sh 只跑在 macOS / Linux
    import hashlib
    import http.server
    import json as _json
    import socketserver
    import threading

    SERVED = {}                      # path -> (content-type, bytes)

    class _H(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            item = SERVED.get(self.path)
            if item is None:
                self.send_error(404)
                return
            ctype, body = item
            self.send_response(200)
            self.send_header('Content-Type', ctype)
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *a):
            pass

    httpd = socketserver.TCPServer(('127.0.0.1', 0), _H)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    BASE = 'http://127.0.0.1:%d' % httpd.server_address[1]

    def make_case(tag, break_digest=False):
        """搭一套「实例 + 旧安装包目录 + 新版 zip + 假 Release」，返回 (实例, 源目录)。"""
        root = tmp / ('upd-' + tag)
        instd = root / 'instance'
        (instd / 'mods').mkdir(parents=True)
        for i in range(25):
            (instd / 'mods' / f'm{i}.jar').write_text('x', encoding='utf-8')
        (instd / 'options.txt').write_text(OPTS_BEFORE, encoding='utf-8')

        def payload(d, mark):
            """最小 payload，够 do_apply 运行。"""
            (d / 'config' / 'vaultpatcher_asm').mkdir(parents=True)
            (d / 'config' / 'vaultpatcher_asm' / 'config.json').write_text(
                '{"class_patch": false}\n', encoding='utf-8')
            (d / 'vaultpatcher' / 'modules').mkdir(parents=True)
            (d / 'vaultpatcher' / 'modules' / 'probe.json').write_text(mark, encoding='utf-8')
            (d / 'resourcepacks').mkdir()
            with zipfile.ZipFile(d / 'resourcepacks' / f'{PACK}.zip', 'w') as z:
                z.writestr('pack.mcmeta', '{}')
            fill_payload(d)     # 凑够文件数，否则被「装了 0 个不许报成功」那道闸拦下
            for s_ in ('install.sh', 'install.ps1'):
                t = (ROOT / 'installer' / s_).read_text(encoding='utf-8')
                t = (t.replace('@@MCVER@@', MCVER).replace('@@PATCHVER@@', PATCHVER)
                      .replace('@@DEFAULT_PACKS@@', DEFAULT_PACKS)
                      .replace('https://api.github.com', BASE))
                if mark == 'NEW':      # 水印：验证原入口的脚本确实被换成了新版
                    t += '\n# ATM10-TEST-NEW-INSTALLER\n'
                (d / s_).write_text(t, encoding='utf-8')

        srcd = instd / 'atm10-zh_cn-client'
        srcd.mkdir()
        payload(srcd, 'OLD')
        newd = root / 'newpkg' / 'atm10-zh_cn-client'
        newd.mkdir(parents=True)
        payload(newd, 'NEW')

        zname = f'atm10-zh_cn-client-r99-atm{MCVER}.zip'
        zpath = root / zname
        with zipfile.ZipFile(zpath, 'w', zipfile.ZIP_DEFLATED) as z:
            for q in newd.rglob('*'):
                if q.is_file():
                    z.write(q, ('atm10-zh_cn-client/' + q.relative_to(newd).as_posix()))
        blob = zpath.read_bytes()
        sha = hashlib.sha256(blob).hexdigest()
        if break_digest:
            sha = 'f' * 64          # 摘要对不上：必须拒绝，且一个文件都不许动
        rel_json = _json.dumps({
            'tag_name': 'vr99',
            'assets': [{
                'name': zname,
                'uploader': {'login': 'x'},          # 嵌套对象，照抄真实形状
                'digest': 'sha256:' + sha,
                'browser_download_url': f'{BASE}/dl/{tag}/{zname}',
            }],
        })
        SERVED[f'/repos/chiba233/atm10-zh-cn/releases/latest'] = ('application/json',
                                                                  rel_json.encode())
        SERVED[f'/dl/{tag}/{zname}'] = ('application/zip', blob)
        return instd, srcd

    # CI 为整个 job 设了 ATM_SKIP_UPDATE_CHECK=1。这几条用例要走联网路径（指向 localhost），所以去掉它。
    UPD_ENV = {k: v for k, v in os.environ.items() if k != 'ATM_SKIP_UPDATE_CHECK'}

    # ① 正常路径
    instd, srcd = make_case('ok')
    r = subprocess.run(['bash', str(srcd / 'install.sh'), 'update'],
                       capture_output=True, text=True, encoding='utf-8',
                       errors='replace', timeout=300, env=UPD_ENV)
    out = (r.stdout or '') + (r.stderr or '')
    assert r.returncode == 0, f'一键更新退出码 {r.returncode}：\n{out}'
    assert '已更新到 vr99' in out, f'没走到更新成功那步：\n{out}'
    assert (instd / 'vaultpatcher' / 'modules' / 'probe.json').read_text(encoding='utf-8') == 'NEW', \
        f'实例里落地的不是新版 payload：\n{out}'
    assert (srcd / 'vaultpatcher' / 'modules' / 'probe.json').read_text(encoding='utf-8') == 'NEW', \
        f'原安装包目录没被换成新版 payload：\n{out}'
    assert 'ATM10-TEST-NEW-INSTALLER' in (srcd / 'install.sh').read_text(encoding='utf-8'), \
        f'原入口的 install.sh 没被换成新版：\n{out}'
    assert any((srcd / 'backups').glob('*')), f'新版安装器的备份没归并回原入口：\n{out}'
    assert list(instd.glob('.atm10-hanhua-update-*')), f'没留下新版安装器目录：\n{out}'

    # ② 摘要对不上：必须拒绝，且实例与原入口一个字节都不许动
    instd2, srcd2 = make_case('bad', break_digest=True)
    r = subprocess.run(['bash', str(srcd2 / 'install.sh'), 'update'],
                       capture_output=True, text=True, encoding='utf-8',
                       errors='replace', timeout=300, env=UPD_ENV)
    out2 = (r.stdout or '') + (r.stderr or '')
    assert 'SHA-256' in out2, f'摘要不符时没报出来：\n{out2}'
    assert not (instd2 / 'vaultpatcher').exists(), f'摘要不符却已经动了实例：\n{out2}'
    assert 'ATM10-TEST-NEW-INSTALLER' not in (srcd2 / 'install.sh').read_text(encoding='utf-8'), \
        f'摘要不符却已经换掉了原入口的安装器：\n{out2}'
    # ③ 关闭开关时一步都不许走：不联网、不下载、不动任何文件
    instd3, srcd3 = make_case('off')
    r = subprocess.run(['bash', str(srcd3 / 'install.sh'), 'update'],
                       capture_output=True, text=True, encoding='utf-8', errors='replace',
                       timeout=300, env={**UPD_ENV, 'ATM_SKIP_UPDATE_CHECK': '1'})
    out3 = (r.stdout or '') + (r.stderr or '')
    assert not (instd3 / 'vaultpatcher').exists(), f'关了更新检查却还是动了实例：\n{out3}'
    assert not list(instd3.glob('.atm10-hanhua-update-*')), f'关了更新检查却还是下载了：\n{out3}'

    # ④ 回归：菜单里必须列出 [u]
    #
    # check_update 里 latest="$(latest_tag)" 在子 shell 里运行，fetch_latest_release 对 LATEST_TAG
    # 的赋值回不到父进程，菜单的 `has_update && say " [u] …"` 永远为假，提示语却照常打印。
    # 上面三条直接运行 `install.sh update`，绕过了菜单，测不出这个问题。
    instd4, srcd4 = make_case('menu')
    r = subprocess.run(['bash', str(srcd4 / 'install.sh')], input='q\n',
                       capture_output=True, text=True, encoding='utf-8',
                       errors='replace', timeout=300, env=UPD_ENV)
    out4 = (r.stdout or '') + (r.stderr or '')
    assert r.returncode == 0, f'菜单退出码 {r.returncode}：\n{out4}'
    assert '你装的不是最新版本' in out4, f'版本检查没提示新版本：\n{out4}'
    assert '[u] 一键下载并更新到 vr99' in out4, \
        f'有新版本，菜单里却没有 [u]：\n{out4}'
    assert not (instd4 / 'vaultpatcher').exists(), f'只看菜单却动了实例：\n{out4}'

    httpd.shutdown()
    print('✅ 一键更新端到端：下载→校验→解包→子安装器→归并备份→换源目录 OK'
          '（含摘要不符拒绝、ATM_SKIP_UPDATE_CHECK 关闭、菜单列出 [u]）')

# ── 覆盖安装：文件真的被覆盖了吗 ───────────────────────────────────────
#
# 事故：Windows 上全部显示成功，却「已备份 0 个将被覆盖的文件」，也就是一个文件都没装上，
# 安装器照样打印「✅ 汉化已应用」。路径里有 `[0.9.1正式版]`，方括号是 PowerShell 的通配符。
# 所以夹具路径带上常见的特殊字符：方括号、空格、中文、&、'、#、$。

def build_case(root, opts=OPTS_BEFORE):
    """在 root 下造一个「已经玩过一阵」的实例 + 释放好的汉化文件夹。"""
    ins = root / 'instance'
    (ins / 'mods').mkdir(parents=True)
    for i in range(25):
        (ins / 'mods' / f'modpack-{i}.jar').write_text('x', encoding='utf-8')
    (ins / 'options.txt').write_text(opts, encoding='utf-8')
    reld = ins / 'ATM10-汉化补丁'
    reld.mkdir()
    for d in ('config', 'kubejs', 'mods', 'vaultpatcher'):
        shutil.copytree(TREE / d, reld / d)
    (reld / 'resourcepacks').mkdir()
    shutil.copy(rel / 'resourcepacks' / f'{PACK}.zip', reld / 'resourcepacks' / f'{PACK}.zip')
    for s in ('install.sh', 'install.ps1'):
        materialize(ROOT / 'installer' / s, reld / s)
    return ins, reld


def payload_of(reld):
    return sorted(p.relative_to(reld).as_posix()
                  for d in ('config', 'kubejs', 'mods', 'resourcepacks', 'vaultpatcher')
                  for p in (reld / d).rglob('*') if p.is_file() and p.name != '.DS_Store')


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def longpath(p):
    """Windows 上超过 MAX_PATH 的路径，Python 自己也读不到，要加扩展前缀。"""
    s = str(p)
    return '\\\\?\\' + s if IS_WIN and len(s) > 259 else s


HOSTILE = tmp / "带 [0.9.1正式版] 和 [3月23日更新] 的 & 目录'"
HOSTILE.mkdir()
inst2, rel2 = build_case(HOSTILE)

# 预置本包会整份替换的整合包任务书语言文件，内容打上标记，断言装完后与包里那份相同。
QL = 'config/ftbquests/quests/lang/zh_cn/chapters'
shipped_ql = sorted(p.name for p in (rel2 / QL).glob('*.snbt'))
assert len(shipped_ql) >= 30, f'包里任务书语言文件只有 {len(shipped_ql)} 个，夹具不成立'
UPSTREAM_MARK = '{\n\tquest.UPSTREAM_ORIGINAL.title: "整合包原文，装完必须被换掉"\n}\n'
preset = shipped_ql[:5] + [n for n in shipped_ql if n.startswith('zz_hanhua_')][:3]
(inst2 / QL).mkdir(parents=True)
for n in preset:
    (inst2 / QL / n).write_text(UPSTREAM_MARK, encoding='utf-8')

before = {f: sha(rel2 / f) for f in payload_of(rel2)}
assert len(before) >= 50, f'夹具里待装文件只有 {len(before)} 个'

rc, out = run_apply_only(rel2)
assert rc == 0, f'含方括号/空格/中文的路径下安装失败（退出码 {rc}）：\n{out}'

# ① 每个待装文件都真的落地，且与包里那份逐字节相同
bad = [f for f, h in before.items()
       if not (inst2 / f).is_file() or sha(inst2 / f) != h]
assert not bad, f'{len(bad)} 个文件没装上或内容不符，例如 {bad[:3]}\n{out}'

# ② 预置的 8 个文件确实被覆盖
still_old = [n for n in preset
             if (inst2 / QL / n).read_text(encoding='utf-8') == UPSTREAM_MARK]
assert not still_old, f'这些文件没被覆盖，等于没装：{still_old}\n{out}'

# ③ 备份里存着被覆盖前的原内容，restore 能一字不差地还回去
bk2 = sorted(p for p in (rel2 / 'backups').iterdir() if p.is_dir())[-1]
for n in preset:
    b = bk2 / QL / n
    assert b.is_file(), f'{n} 被覆盖了却没进备份'
    assert b.read_text(encoding='utf-8') == UPSTREAM_MARK, f'{n} 备份的不是原内容'
r = subprocess.run((['powershell', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File',
                     str(rel2 / 'install.ps1'), 'restore', bk2.name] if IS_WIN else
                    ['bash', str(rel2 / 'install.sh'), 'restore', bk2.name]),
                   capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=300)
assert r.returncode == 0, f'restore 失败：{r.stdout}{r.stderr}'
for n in preset:
    assert (inst2 / QL / n).read_text(encoding='utf-8') == UPSTREAM_MARK, f'{n} 没还原回原内容'
print(f'✅ 覆盖安装：{len(before)} 个文件逐字节核对通过。'
      f'{len(preset)} 个原有任务书语言文件确实被覆盖并可还原（路径含方括号/空格/中文）')

# ④ 反例：待装文件被削到 50 以下，安装器必须报错退出，且一个字节都不许动实例
HOSTILE2 = tmp / 'counterexample'
HOSTILE2.mkdir()
inst3, rel3 = build_case(HOSTILE2)
(inst3 / 'vaultpatcher').mkdir(parents=True, exist_ok=True)
(inst3 / 'vaultpatcher' / 'canary.json').write_text('UNTOUCHED', encoding='utf-8')
for d in ('config', 'kubejs', 'resourcepacks', 'vaultpatcher'):
    shutil.rmtree(rel3 / d)     # 只剩 mods/ 里那一个 jar，模拟「压缩包没解压完整」
rc3, out3 = run_apply_only(rel3)
assert rc3 != 0, f'待装文件被削光了，安装器却报成功（退出码 {rc3}）：\n{out3}'
assert (inst3 / 'vaultpatcher' / 'canary.json').read_text(encoding='utf-8') == 'UNTOUCHED', \
    '中止前动了实例里的文件'
assert not (rel3 / 'backups').exists() or not any((rel3 / 'backups').iterdir()), \
    '中止了却还是建了备份'
print('✅ 反例：待装文件不足时安装器报错退出，未改动实例')

# ⑤ 长路径：备份路径比载荷自己的路径多出 `\backups\<时间戳>` 这一截。Windows 的
#    MAX_PATH=260 算的是完整路径，于是会出现「载荷装得进去、它的备份写不出来」，
#    而且报的是 DirectoryNotFoundException，看着像目录没建成。这里把实例目录垫进那条
#    窄窗口，让最深的那个文件正好落在「源 <260、备份 >260」上。非 Windows 上没有这条
#    上限，用例照跑，只是不构成压力。
DEEP_REL = max(payload_of(rel), key=len)
# 源   = 实例 + \ATM10-汉化补丁\ + 相对路径      = L + R + 12
# 备份 = 源   + \backups\<15 位时间戳>           = L + R + 36
WANT = 236 - len(DEEP_REL)          # 源 248、备份 272，两边离边界都有余量
pad = WANT - len(str(tmp)) - 10
assert pad >= 1, (f'临时目录 {len(str(tmp))} 字符、最深相对路径 {len(DEEP_REL)} 字符，'
                  f'构造不出「源 <260、备份 >260」的路径长度，这条用例必须跨过 260')
DEEP = tmp / ('d' * pad)
DEEP.mkdir()
inst5, rel5 = build_case(DEEP)
deep_dst = inst5 / DEEP_REL
deep_dst.parent.mkdir(parents=True, exist_ok=True)
deep_dst.write_text('OLD-DEEP', encoding='utf-8')
assert len(str(rel5 / DEEP_REL)) < 260, '夹具的载荷路径自己就超了 260，垫过头了'

rc5, out5 = run_apply_only(rel5)
assert rc5 == 0, f'深目录下安装失败（退出码 {rc5}）：\n{out5}'
bk5 = sorted(p for p in (rel5 / 'backups').iterdir() if p.is_dir())[-1]
bak5 = bk5 / DEEP_REL
assert len(str(bak5)) > 260, f'备份路径只有 {len(str(bak5))} 字符，没跨过 MAX_PATH，等于没测'
assert os.path.isfile(longpath(bak5)), f'深路径文件被覆盖了却没进备份（{len(str(bak5))} 字符）\n{out5}'
with open(longpath(bak5), encoding='utf-8') as _fh:
    assert _fh.read() == 'OLD-DEEP', '深路径备份里不是覆盖前的原内容'
assert deep_dst.read_text(encoding='utf-8') != 'OLD-DEEP', '深路径文件没被覆盖，等于没装'
r = subprocess.run((['powershell', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File',
                     str(rel5 / 'install.ps1'), 'restore', bk5.name] if IS_WIN else
                    ['bash', str(rel5 / 'install.sh'), 'restore', bk5.name]),
                   capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=300)
assert r.returncode == 0, f'深目录下 restore 失败：{r.stdout}{r.stderr}'
assert deep_dst.read_text(encoding='utf-8') == 'OLD-DEEP', '深路径文件没还原回原内容'
print(f'✅ 长路径：备份路径 {len(str(bak5))} 字符（> MAX_PATH=260），备份、安装、还原三步都过')

shutil.rmtree(longpath(tmp), ignore_errors=True)
print(f'✅ 安装脚本端到端测试通过（{platform.system()}）')
