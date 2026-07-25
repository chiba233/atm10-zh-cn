# -*- coding: utf-8 -*-
# atm10-zh-cn — All the Mods 10 简体中文汉化补丁「绿油油版」
# Copyright (C) 2026 星野夢華 (Hoshino Yumeka)
# SPDX-License-Identifier: GPL-3.0-or-later
"""发版前校验：把踩过的雷全部变成硬检查。

1. vaultpatcher/modules/*.json 必须是合法 JSON 且结构正确
2. 枚举协议值（McJtyLib 存储/网络协议值）绝不允许出现在翻译 key 里 —— 翻了必崩
   （历史事故：choice('忽略红石') → IllegalStateException: Unknown element name）
3. config/vaultpatcher_asm/config.json：load_all_modules 必须 true（否则自建模块不加载），
   debug_mode.is_enable 必须 false（否则刷数千条日志拖性能）
4. 资源包源码目录内所有 lang/*.json 与 pack.mcmeta 必须可解析
5. 资源包内 RFTools 系 .gui 文件的 choice(...) 参数必须保持英文
"""
import json, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PACK_DIR = ROOT / 'resourcepacks' / 'ATM10汉化包-7.2'
errors = []

# McJtyLib 枚举协议值：NamedCodec 按名字反查，翻译后反查失败 → 崩溃
FORBIDDEN_KEYS = {
    'Ignored', 'Off', 'On',                      # RedstoneMode
    'Copy', 'Move', 'Swap', 'Back', 'Collect',   # BuilderMode
    'Loop1', 'Loop2', 'Loop3', 'Loop4',          # SequencerMode
    'Once1', 'Once2', 'Pulse', 'Cycle',
    'Amount+', 'Amount-', 'Mod', 'Name',         # SortingMode 等
    'Shield', 'Solid', 'Invisible',              # ShieldRenderingMode
}

# 1+2: VaultPatcher 模块
for p in sorted((ROOT / 'vaultpatcher' / 'modules').glob('*.json')):
    try:
        mod = json.loads(p.read_text(encoding='utf-8'))
    except Exception as e:
        errors.append(f'{p.name}: JSON 解析失败: {e}')
        continue
    if not isinstance(mod, list):
        errors.append(f'{p.name}: 顶层必须是数组')
        continue
    for blk in mod:
        if not isinstance(blk, dict):
            errors.append(f'{p.name}: 模块元素必须是对象')
            continue
        tcs = blk.get('target_class') or []
        # 仅当替换可能命中 McJtyLib 枚举常量池时才算雷：
        #   - 无 target_class（全局替换）
        #   - 定向到 mcjty.* 的非 client 类（枚举/协议类所在地）
        # 定向到具体 GUI/Screen 类的同名显示标签（如形状卡的 Solid）是安全的
        risky = (not tcs) or any(c.startswith('mcjty.') and '.client.' not in c for c in tcs)
        if not risky:
            continue
        for pair in blk.get('pairs', []):
            k = pair.get('key', '')
            if k.strip() in FORBIDDEN_KEYS:
                where = '全局替换' if not tcs else f'定向 {tcs}'
                errors.append(f'{p.name}: 禁止翻译枚举协议值 "{k}"（{where}，会导致游戏崩溃）')

# 2.5: 服务端模块子集：禁止全局替换块（会污染服务端 NBT/注册名）
# 唯一豁免：key 带前导空格的纯显示文本（如 "    Void mode"）
server_list = [l.strip() for l in (ROOT / 'scripts' / 'server_modules.txt').read_text(encoding='utf-8').splitlines()
               if l.strip() and not l.startswith('#')]
for name in server_list:
    p = ROOT / 'vaultpatcher' / 'modules' / f'{name}.json'
    if not p.exists():
        errors.append(f'server_modules.txt: 清单里的 {name}.json 不存在')
        continue
    for blk in json.loads(p.read_text(encoding='utf-8')):
        if isinstance(blk, dict) and 'pairs' in blk and not blk.get('target_class'):
            bad = [pr['key'] for pr in blk['pairs'] if not pr.get('key', '').startswith(' ')]
            if bad:
                errors.append(f'{name}.json: 服务端模块含全局替换 {bad}（会污染服务端数据，禁止入服务端清单）')

# 2.7: 资源蜜蜂译名单一真源：脚本表必须与资源包 zh_cn 一致（由 gen_pb_hanhua.py 生成）
pb_pack = json.loads((PACK_DIR / 'assets/productivebees/lang/zh_cn.json').read_text(encoding='utf-8'))
club = ROOT / 'kubejs' / 'client_scripts' / 'pb_hanhua_tooltip.js'
mm = re.search(r'const PB_ID2ZH = (\{.*?\});', club.read_text(encoding='utf-8'), re.S)
if not mm:
    errors.append('pb_hanhua_tooltip.js: 缺 PB_ID2ZH（必须由 gen_pb_hanhua.py 生成）')
else:
    for base, zh in json.loads(mm.group(1)).items():
        expect = pb_pack.get(f'entity.productivebees.{base}_bee', pb_pack.get(f'entity.productivebees.{base}'))
        if expect is not None and expect != zh:
            errors.append(f'蜂名漂移: {base} 脚本={zh!r} 资源包={expect!r}（真源是资源包，请重跑 gen_pb_hanhua.py）')

# 2.8: 旧译名残留检查：废弃译名只允许出现在别名表/生成器（作为归一的键）
LEGACY_NAMES = ('联调蜂', '神蜂特工队')
LEGACY_WHITELIST = {
    'kubejs/client_scripts/pb_hanhua_tooltip.js',
    'kubejs/server_scripts/pb_hanhua_cage_migrate.js',
    'scripts/gen_pb_hanhua.py',
    'scripts/check.py',
}
for p2 in ROOT.rglob('*'):
    if not p2.is_file() or '.git' in p2.parts or 'dist' in p2.parts:
        continue
    rel2 = p2.relative_to(ROOT).as_posix()
    if rel2 in LEGACY_WHITELIST or p2.suffix in ('.jar', '.png', '.zip'):
        continue
    try:
        txt = p2.read_text(encoding='utf-8')
    except Exception:
        continue
    for ln in LEGACY_NAMES:
        if ln in txt:
            errors.append(f'{rel2}: 含废弃译名 "{ln}"（真源已更名，此处是漂移的旧拷贝）')
# 遗留的 VaultPatcher 蜂名模块（已被 kubejs 显示层取代，全局替换有污染风险）禁止复活
if (ROOT / 'vaultpatcher' / 'modules' / 'productivebees_gene_zh.json').exists():
    errors.append('productivebees_gene_zh.json: 遗留蜂名全局替换模块，已废弃，禁止复活（显示层走 kubejs）')

# 3: VaultPatcher 主配置
cfg_path = ROOT / 'config' / 'vaultpatcher_asm' / 'config.json'
cfg = json.loads(cfg_path.read_text(encoding='utf-8'))
if cfg.get('load_all_modules') is not True:
    errors.append('config.json: load_all_modules 必须为 true，否则自建模块不加载')
if cfg.get('debug_mode', {}).get('is_enable') is not False:
    errors.append('config.json: debug_mode.is_enable 必须为 false（发布版禁止开调试日志）')

# 4+5: 资源包源码目录
CJK = re.compile(r'[一-鿿]')
if not PACK_DIR.is_dir():
    errors.append(f'缺少资源包源码目录: {PACK_DIR.relative_to(ROOT)}')
else:
    try:
        json.loads((PACK_DIR / 'pack.mcmeta').read_text(encoding='utf-8'))
    except Exception as e:
        errors.append(f'pack.mcmeta 解析失败: {e}')
    for p in PACK_DIR.rglob('*'):
        rel = p.relative_to(PACK_DIR)
        if p.suffix == '.json' and '/lang/' in f'/{rel.as_posix()}/':
            try:
                json.loads(p.read_text(encoding='utf-8'))
            except Exception as e:
                errors.append(f'{rel}: JSON 解析失败: {e}')
        elif p.suffix == '.gui':
            text = p.read_text(encoding='utf-8', errors='replace')
            for m in re.finditer(r"choice\(\s*'([^']*)'", text):
                if CJK.search(m.group(1)):
                    errors.append(
                        f"{rel}: choice('{m.group(1)}') 是协议值，必须保持英文（翻译会崩溃）")

# 6: 占位符 / 颜色码安全（2026-07-25 对抗与踩坑后固化）
#    真源 scripts/upstream_format_en_us.json（gen_format_snapshot.py 生成）
#    红线一：译文的占位符集合必须 ⊆ 英文原文的 —— 可以少，绝不可以多。
#      多出参数 = 运行时参数不足 → TranslatableFormatException。
#      「少」是译者的合法选择，**禁止擅自补回来**：精致存储 `%s%s木桶` 的第二个
#      参数其实只是个空格，补上去反而变成「限类Pink Ipe 木桶 I」。
#    红线二：同一序号的转换符不许从 %s 降级成 %d/%f（类型对不上，两条渲染路径都炸）。
#    红线三：结尾裸 % —— MC 的 FORMAT_PATTERN 会匹配到字符串结尾并抛异常
#      （原版自带的反例键就是 translation.test.invalid = "hi %"）。
#    红线四：§ 后面跟非法字符 → 那个字符被渲染器静默吞掉。
FMT_SNAPSHOT = ROOT / 'scripts' / 'upstream_format_en_us.json'
if FMT_SNAPSHOT.exists():
    up = json.loads(FMT_SNAPSHOT.read_text(encoding='utf-8'))
    TOK = re.compile(r'%(?:(\d+)\$)?(\d+)?(?:\.(\d+))?([a-zA-Z%])')
    TRAIL = re.compile(r'(?<!%)%$')
    SECT_OK = set('0123456789abcdefklmnorABCDEFKLMNOR')

    def _profile(s):
        prof, seq = {}, 0
        for m in TOK.finditer(s):
            conv = m.group(4)
            if conv == '%':
                continue
            if m.group(1):
                idx = int(m.group(1))
            else:
                seq += 1
                idx = seq
            prof.setdefault(idx, conv)
        return prof

    def _bad_sect(s):
        return {m.group(1) for m in re.finditer('§(.)', s) if m.group(1) not in SECT_OK}

    # 豁免：上游 en_us 自己写坏了，我们的译文才是对的（每条都写清理由，防止豁免变成垃圾桶）
    FMT_ALLOW = {
        # 上游把 "%3$s" 打成了 "%3$"（缺转换符），模组实际传 3 个参数
        'death.attack.freeze.item',
        # 上游把 "%s" 打成了 "% s"（多一个空格），导致英文版根本不替换
        'item.occultism.book_of_calling_djinni.tooltip.deposit',
    }
    lang_files = list(PACK_DIR.rglob('lang/zh_cn.json'))
    lang_files += list((ROOT / 'kubejs' / 'assets').rglob('lang/zh_cn.json'))
    for p in lang_files:
        rel = p.relative_to(ROOT).as_posix()
        try:
            d = json.loads(p.read_text(encoding='utf-8'))
        except Exception:
            continue                       # 4 已经报过 JSON 错
        for k, zh in d.items():
            if not isinstance(zh, str):
                continue
            if k == '_comment' or k in FMT_ALLOW:
                continue               # _comment 是注释键，永远不会被渲染
            en = up.get(k)
            if en is None:
                continue
            pe, pz = _profile(en), _profile(zh)
            extra = sorted(set(pz) - set(pe))
            if extra:
                errors.append(f'{rel}: {k} 译文多出英文没有的占位符 {extra}'
                              f'（运行时参数不足会抛 TranslatableFormatException）'
                              f'\n      en={en!r}\n      zh={zh!r}')
            downgrade = sorted(i for i in set(pe) & set(pz)
                               if pe[i] == 's' and pz[i] != 's')
            if downgrade:
                errors.append(f'{rel}: {k} 第 {downgrade} 个参数把 %s 降级成了 %{pz[downgrade[0]]}'
                              f'（类型对不上，必炸）\n      en={en!r}\n      zh={zh!r}')
            if TRAIL.search(zh) and not TRAIL.search(en):
                errors.append(f'{rel}: {k} 译文以裸 % 结尾（MC 会当非法格式抛异常）\n      zh={zh!r}')
            new_sect = _bad_sect(zh) - _bad_sect(en)
            if new_sect:
                errors.append(f'{rel}: {k} 非法 § 颜色码 {sorted(new_sect)}'
                              f'（§ 后面那个字会被渲染器吞掉）\n      zh={zh!r}')

if errors:
    print(f'❌ 校验失败，共 {len(errors)} 处：')
    for e in errors:
        print('  -', e)
    sys.exit(1)
print('✅ 全部校验通过（VaultPatcher 模块 / 枚举协议值 / 主配置 / 资源包 lang / .gui choice）')
