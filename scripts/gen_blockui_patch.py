#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# atm10-zh-cn — All the Mods 10 简体中文汉化补丁「绿油油版」
# Copyright (C) 2026 星野夢華 (Hoshino Yumeka)
# SPDX-License-Identifier: GPL-3.0-or-later
"""让 blockui 的按钮文字居中，改字节码，因为 XML 层根本做不到。

## 为什么必须动字节码

blockui 1.0.211 完全无视 XML 里的 `textalign`。这不是推断，是受控实测：
单独做一个资源包排在最后一位，只改 `windowbuildtool.xml` 的 switch 按钮，
同时把 `label` 换成「探针已加载」、加上 `textalign="BOTTOM_RIGHT"`、不加任何偏移量。
实机结果是按钮显示了「探针已加载」（证明包确实生效）而文字照旧贴在左边
（证明 textalign 无效）。上游自己写了这个属性的地方同样贴左，两次独立证据。

根因在字节里：

    AbstractTextElement.DEFAULT_TEXT_ALIGNMENT = Alignment.MIDDLE_LEFT   // 竖直居中、水平靠左
    innerDrawSelf: 只有 textAlignment.isHorizontalCentered() 为真才做
                   x += (textWidth - renderedTextWidth) / 2

中文比英文宽，靠左的后果比英文严重得多：一排按钮的字全挤在左上角，长一点的直接
压到边框和图标上。而按钮的文字大多是运行时才填的（玩家名、开/关、建筑名、
田地半径），构建期算不出宽度，`textoffset` 那条路只能覆盖标签固定的那一批。

## 实测数据（把 blockui 自己的字段 println 出来看的）

给 `AbstractTextElement.recalcPreparedTextBox` 注入一段 dump 之后，一次开界面拿到
3190 条记录，其中按钮 1808 条：

    稻草人方向数字   width=24  textWidth=24  renderedTextWidth=6   → 居中量 (24-6)/2 = 9px
    选择种子按钮     width=86  textWidth=86  renderedTextWidth=33  → 居中量 26px
    非按钮的文字     MIDDLE_LEFT 1293 条 / TOP_LEFT 43 条          → 原样不动，段落没被误伤

也就是说 `textWidth` 和 `renderedTextWidth` 本来就是对的，缺的只是把对齐设成 MIDDLE。

## 改哪里：只改 Button，不改 AbstractTextElement

把 `DEFAULT_TEXT_ALIGNMENT` 直接翻成 `MIDDLE` 会连「农夫：xxx」这类段落文字
一起居中，那是另一种不可用。所以只在 `Button`（所有按钮的基类）的构造器末尾追加
一句「把自己的对齐设成居中」：

    aload_0
    getstatic  com/ldtteam/blockui/Alignment.MIDDLE
    invokevirtual AbstractTextElement.setTextAlignment(Alignment)V

## 为什么这是最安全的注入姿势

追加在构造器最后一条 `return` 之前：

- 不新增局部变量，`locals` 不变
- 需要的操作数栈深度是 2，而原方法 `stack=3`，够用
- 原方法的两个跳转目标在偏移 22 / 26，都在注入点之前，所以
  StackMapTable 里的帧偏移一个都不用改（这是不敢碰字节码的人最怕的部分）
- 常量池只追加不修改，既有索引全部保持不变

## 怎么随包发：不需要新 mod

VaultPatcher 自带 `ClassPatcher.init(Utils.getVpPath()/"patch")`，它会遍历
`<实例>/vaultpatcher/patch/` 下的 `.class` 直接替换同名类。而 `vaultpatcher/`
本来就是本包发的目录，所以：放一个改好的 `Button.class` 进去 + 把主配置的
`class_patch` 打开，就完事了。不用发新 mod、不用写 mixin、不用给 CI 加 JDK。

## 版本对不上就报错，绝不照旧注入

blockui 的 jar 按 sha256 钉死。升级后类结构可能变，届时构建直接失败，
由人重新核对偏移量，而不是往一个陌生的方法尾巴上盲插三条指令。

用法:
    python3 scripts/gen_blockui_patch.py [<mods 目录>]
    # 缺省读 ATM_PACK_ROOT/mods
"""
import hashlib
import os
import struct
import sys
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from paths import COMMON                                       # noqa: E402

JAR_SHA256 = '5dfffc80c057b4d36123bd5f5cad9f32f86896a9dd993ea4a3ecad315cabd77e'  # blockui-1.0.211
TARGET = 'com/ldtteam/blockui/controls/Button.class'
CTOR_DESC = '(Lcom/ldtteam/blockui/PaneParams;)V'
# ButtonImage(PaneParams) 调的是 7 参 的 Button 构造器，不是 1 参那个，
# 只打 1 参会完全没有效果（实测：注入的 println 一次都没打出来）。所以 4 个构造器全打。
DROP_ATTRS = {'LocalVariableTable', 'LocalVariableTypeTable', 'LineNumberTable'}
# 注入会让方法变长，而 LocalVariableTable 里还写着旧长度，JVM 校验直接
# ClassFormatError: Illegal local variable table length（实测闪退过一次）。
# 这些都是调试用的可选属性，注入时整个剥掉最省事，StackMapTable 保留。
ALIGNMENT = 'com/ldtteam/blockui/Alignment'
OWNER = 'com/ldtteam/blockui/controls/AbstractTextElement'

# 常量池 tag -> 定长部分的字节数（Utf8 变长，单独处理）
FIXED = {3: 4, 4: 4, 5: 8, 6: 8, 7: 2, 8: 2, 9: 4, 10: 4, 11: 4,
         12: 4, 15: 3, 16: 2, 17: 4, 18: 4, 19: 2, 20: 2}
WIDE = (5, 6)              # long / double 占两个槽


def parse_pool(b, off):
    """返回 (entries, end_off)。entries[i] = (tag, payload_bytes)，i 为池索引。"""
    count = struct.unpack_from('>H', b, off)[0]
    off += 2
    entries = {}
    i = 1
    while i < count:
        tag = b[off]
        if tag == 1:
            n = struct.unpack_from('>H', b, off + 1)[0]
            size = 3 + n
        else:
            size = 1 + FIXED[tag]
        entries[i] = (tag, b[off:off + size])
        off += size
        i += 2 if tag in WIDE else 1
    return entries, off, count


def utf8(s):
    raw = s.encode('utf-8')
    return bytes([1]) + struct.pack('>H', len(raw)) + raw


def find_utf8(entries, s):
    want = utf8(s)
    for i, (tag, raw) in entries.items():
        if tag == 1 and raw == want:
            return i
    return None


def find_class(entries, name):
    ni = find_utf8(entries, name)
    if ni is None:
        return None
    want = bytes([7]) + struct.pack('>H', ni)
    for i, (tag, raw) in entries.items():
        if tag == 7 and raw == want:
            return i
    return None


def patch(data):
    """给 Button 的每一个构造器末尾追加 setTextAlignment(MIDDLE)，并剥掉调试属性。"""
    entries, pool_end, count = parse_pool(data, 8)
    add, nxt = [], count

    def emit(raw):
        nonlocal nxt
        add.append(raw)
        nxt += 1
        return nxt - 1

    def want_utf8(s):
        i = find_utf8(entries, s)
        return i if i else emit(utf8(s))

    def want_class(name):
        i = find_class(entries, name)
        return i if i else emit(bytes([7]) + struct.pack('>H', want_utf8(name)))

    al = 'L%s;' % ALIGNMENT
    nat_a = emit(bytes([12]) + struct.pack('>HH', want_utf8('MIDDLE'), want_utf8(al)))
    fref = emit(bytes([9]) + struct.pack('>HH', want_class(ALIGNMENT), nat_a))
    nat_s = emit(bytes([12]) + struct.pack('>HH', want_utf8('setTextAlignment'),
                                           want_utf8('(%s)V' % al)))
    mref = emit(bytes([10]) + struct.pack('>HH', want_class(OWNER), nat_s))
    inject = bytes([0x2A, 0xB2]) + struct.pack('>H', fref) + bytes([0xB6]) + struct.pack('>H', mref)

    head = bytearray(data[:8]) + struct.pack('>H', nxt)
    for i in sorted(entries):
        head += entries[i][1]
    for raw in add:
        head += raw

    tail = bytearray(data[pool_end:])
    out = bytearray()
    o = 6
    o += 2 + struct.unpack_from('>H', tail, o)[0] * 2
    last, hit = 0, []
    for section in ('fields', 'methods'):
        n = struct.unpack_from('>H', tail, o)[0]
        o += 2
        for _ in range(n):
            _, ni, di = struct.unpack_from('>HHH', tail, o)
            nm = entries[ni][1][3:].decode()
            ds = entries[di][1][3:].decode()
            o += 6
            an = struct.unpack_from('>H', tail, o)[0]
            o += 2
            for _ in range(an):
                ai, alen = struct.unpack_from('>HI', tail, o)
                aname = entries[ai][1][3:].decode()
                body = o + 6
                if section == 'methods' and nm == '<init>' and aname == 'Code':
                    ms, ml = struct.unpack_from('>HH', tail, body)
                    cl = struct.unpack_from('>I', tail, body + 4)[0]
                    c0 = body + 8
                    code = bytes(tail[c0:c0 + cl])
                    if code[-1] != 0xB1:
                        sys.exit('❌ Button%s 末尾不是 return，注入点不成立。' % ds)
                    p2 = c0 + cl
                    exn = struct.unpack_from('>H', tail, p2)[0]
                    ex = bytes(tail[p2:p2 + 2 + exn * 8])
                    p2 += 2 + exn * 8
                    acnt = struct.unpack_from('>H', tail, p2)[0]
                    p2 += 2
                    kept = []
                    for _ in range(acnt):
                        sai, salen = struct.unpack_from('>HI', tail, p2)
                        sname = entries[sai][1][3:].decode()
                        blob = bytes(tail[p2:p2 + 6 + salen])
                        p2 += 6 + salen
                        if sname not in DROP_ATTRS:
                            kept.append(blob)
                    newcode = code[:-1] + inject + b'\xb1'
                    nb = (struct.pack('>HH', max(ms, 2), ml) + struct.pack('>I', len(newcode))
                          + newcode + ex + struct.pack('>H', len(kept)) + b''.join(kept))
                    out += tail[last:o]
                    out += struct.pack('>HI', ai, len(nb)) + nb
                    last = o + 6 + alen
                    hit.append(ds)
                o += 6 + alen
    out += tail[last:]
    if len(hit) < 4:
        sys.exit('❌ 只打到 %d 个构造器（应为 4 个）——类结构变了，停下。' % len(hit))
    for ds in hit:
        print('   注入 Button%s' % ds)
    return bytes(head + out)


def main(argv):
    mods = Path(argv[0]) if argv else Path(os.environ.get('ATM_PACK_ROOT', '')) / 'mods'
    jars = sorted(mods.glob('blockui-*.jar'))
    if not jars:
        sys.exit('❌ 找不到 blockui jar：%s' % mods)
    raw = jars[0].read_bytes()
    got = hashlib.sha256(raw).hexdigest()
    if JAR_SHA256 and got != JAR_SHA256:
        sys.exit('❌ blockui 变了（记的是 %s，实际 %s）——注入点按旧版本量的，'
                 '重新核对再改这里。' % (JAR_SHA256, got))
    if not JAR_SHA256:
        print('ℹ️ blockui sha256 = %s（把它填进 JAR_SHA256 钉死）' % got)
    z = zipfile.ZipFile(jars[0])
    out = COMMON / 'vaultpatcher' / 'patch' / TARGET
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(patch(z.read(TARGET)))
    print('✅ 已生成 %s' % out.relative_to(COMMON))
    print('   按钮文字将统一居中；段落文字不受影响（只改 Button，没动 AbstractTextElement 的默认值）')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
