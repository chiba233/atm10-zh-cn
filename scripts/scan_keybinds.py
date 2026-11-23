#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# atm10-zh-cn — All the Mods 10 简体中文汉化补丁「绿油油版」
# Copyright (C) 2026 星野夢華 (Hoshino Yumeka)
# SPDX-License-Identifier: GPL-3.0-or-later
"""扫描每个 `KeyMapping(name, …, category)` 的注册名与分类标题。

- 分类是「按键绑定」界面里的分组标题，可能是翻译键（补 lang 即可），也可能是硬编码字面量
  （`Create`、`Auroras` 等，只能用 VaultPatcher 改常量池）。
- 注册名是 options.txt 里 `key_<name>` 的 name，不能被翻译改动：改掉一个字，玩家保存的绑定
  就对不上，该键位静默回到默认值。

只取构造调用前入栈的字符串常量不够：对照 options.txt 的 494 条真值，只认出 191 个，其中 25 个
是错的（把分类、格式串当成了注册名）。实际代码里名字常见这些形态：

    new KeyMapping(NAME_FIELD, …)                 静态字段
    for (AllKeys k : values()) new KeyMapping(k.description, …)
                                                  枚举实例字段，字段本身由
                                                  `"create.keyinfo." + name` 拼出
    register("key.foo.bar", "key.categories.x")   helper 方法的形参
    "artifacts.key.%s.%s".formatted(a, b)         运行期格式化

所以这里做数据流分析：按 CFG 逐指令模拟操作数栈（分支处合并，`long`/`double` 占两格），按方法
描述符定位第几个参数，再沿取值链回溯，静态字段查 `ConstantValue` 与 `<clinit>`。枚举沿 `<clinit>`
的构造实参 → `<init>` 的 `putfield` 表达式 → getter 的 `getfield` 串起来，形参代入常量实参。
字符串拼接（`invokedynamic makeConcat*`、`StringBuilder`、`String.concat`）一并求值。
取不到的值留空，不猜测，并打印取不到的形态。

用法:
    python3 scripts/scan_keybinds.py <mods 目录> [输出.json] [--truth options.txt]

`--truth` 用一份实际运行过的 options.txt 验收，打印召回率、误报名单和没取到的值的形态。
扫描结果要先通过这项验收才能使用。
"""
import json
import struct
import sys
import zipfile
from collections import Counter
from pathlib import Path

UNK = ('?',)
TOP = ('top',)                      # long/double 占的第二格
MAX_DEPTH = 6                       # 回溯层数上限
MAX_FANOUT = 256                    # 一个构造点最多展开出多少个名字


# ─────────────────────────────── class 文件解析 ───────────────────────────────

def parse_pool(b):
    n = struct.unpack_from('>H', b, 8)[0]
    pool = [None] * n
    i, off = 1, 10
    while i < n:
        tag = b[off]
        if tag == 1:
            ln = struct.unpack_from('>H', b, off + 1)[0]
            pool[i] = (1, b[off + 3:off + 3 + ln].decode('utf-8', 'replace'))
            off += 3 + ln
        elif tag in (7, 8, 16, 19, 20):
            pool[i] = (tag, struct.unpack_from('>H', b, off + 1)[0])
            off += 3
        elif tag == 15:
            pool[i] = (tag, struct.unpack_from('>BH', b, off + 1))
            off += 4
        elif tag in (3, 4):
            pool[i] = (tag, None)
            off += 5
        elif tag in (5, 6):
            pool[i] = (tag, None)
            off += 9
            i += 1                                   # long/double 占两个槽
        else:                                        # 9,10,11,12,17,18
            pool[i] = (tag, struct.unpack_from('>HH', b, off + 1))
            off += 5
        i += 1
    return pool, off


class Klass:
    """一个 class 文件里我们用得上的那部分。"""

    def __init__(self, raw):
        self.raw = raw
        self.pool, off = parse_pool(raw)
        self.access = struct.unpack_from('>H', raw, off)[0]
        self.name = self.cls_name(struct.unpack_from('>H', raw, off + 2)[0])
        self.super = self.cls_name(struct.unpack_from('>H', raw, off + 4)[0])
        self.fields = {}                     # 名 -> (描述符, access, 常量值或 None)
        self.methods = {}                    # (名, 描述符) -> (access, code, 异常表)
        self.bootstrap = []                  # invokedynamic 的引导方法表
        p = off + 6
        ifc = struct.unpack_from('>H', raw, p)[0]
        p += 2 + ifc * 2
        p = self._members(p, self.fields, False)
        p = self._members(p, self.methods, True)
        self._class_attrs(p)

    # 常量池取值 ------------------------------------------------------------
    def utf(self, i):
        e = self.pool[i] if 0 < i < len(self.pool) else None
        return e[1] if e and e[0] == 1 else None

    def cls_name(self, i):
        e = self.pool[i] if 0 < i < len(self.pool) else None
        return self.utf(e[1]) if e and e[0] == 7 else None

    def ref(self, i):
        """Fieldref/Methodref/InterfaceMethodref -> (类, 名, 描述符)"""
        e = self.pool[i] if 0 < i < len(self.pool) else None
        if not e or e[0] not in (9, 10, 11):
            return None
        nat = self.pool[e[1][1]]
        if not nat or nat[0] != 12:
            return None
        return (self.cls_name(e[1][0]), self.utf(nat[1][0]), self.utf(nat[1][1]))

    def const_str(self, i):
        e = self.pool[i] if 0 < i < len(self.pool) else None
        if not e:
            return None
        if e[0] == 8:
            return self.utf(e[1])
        if e[0] == 1:
            return e[1]
        return None

    def indy(self, i):
        """InvokeDynamic -> (引导方法序号, 方法名, 描述符)"""
        e = self.pool[i] if 0 < i < len(self.pool) else None
        if not e or e[0] != 18:
            return None
        nat = self.pool[e[1][1]]
        if not nat or nat[0] != 12:
            return None
        return (e[1][0], self.utf(nat[1][0]), self.utf(nat[1][1]))

    def handle_ref(self, i):
        e = self.pool[i] if 0 < i < len(self.pool) else None
        return self.ref(e[1][1]) if e and e[0] == 15 else None

    # 成员解析 --------------------------------------------------------------
    def _members(self, p, into, is_method):
        raw = self.raw
        cnt = struct.unpack_from('>H', raw, p)[0]
        p += 2
        for _ in range(cnt):
            access, ni, di = struct.unpack_from('>HHH', raw, p)
            nm, desc = self.utf(ni), self.utf(di)
            p += 6
            na = struct.unpack_from('>H', raw, p)[0]
            p += 2
            code = exc = cv = None
            for _ in range(na):
                an = self.utf(struct.unpack_from('>H', raw, p)[0])
                ln = struct.unpack_from('>I', raw, p + 2)[0]
                body = p + 6
                if an == 'Code':
                    clen = struct.unpack_from('>I', raw, body + 4)[0]
                    code = raw[body + 8:body + 8 + clen]
                    q = body + 8 + clen
                    en = struct.unpack_from('>H', raw, q)[0]
                    exc = [struct.unpack_from('>HHHH', raw, q + 2 + k * 8)[2]
                           for k in range(en)]
                elif an == 'ConstantValue':
                    cv = self.const_str(struct.unpack_from('>H', raw, body)[0])
                p += 6 + ln
            into[(nm, desc) if is_method else nm] = \
                (access, code, exc) if is_method else (desc, access, cv)
        return p

    def _class_attrs(self, p):
        raw = self.raw
        na = struct.unpack_from('>H', raw, p)[0]
        p += 2
        for _ in range(na):
            an = self.utf(struct.unpack_from('>H', raw, p)[0])
            ln = struct.unpack_from('>I', raw, p + 2)[0]
            body = p + 6
            if an == 'BootstrapMethods':
                q = body + 2
                for _ in range(struct.unpack_from('>H', raw, body)[0]):
                    mh, nargs = struct.unpack_from('>HH', raw, q)
                    args = [struct.unpack_from('>H', raw, q + 4 + k * 2)[0]
                            for k in range(nargs)]
                    self.bootstrap.append((mh, args))
                    q += 4 + nargs * 2
            p += 6 + ln


# ─────────────────────────────── 描述符 ───────────────────────────────

def parse_desc(desc):
    """'(Ljava/lang/String;IJ)V' -> (['Ljava/lang/String;', 'I', 'J'], 'V')"""
    args, i = [], 1
    while desc[i] != ')':
        s = i
        while desc[i] == '[':
            i += 1
        if desc[i] == 'L':
            i = desc.index(';', i)
        args.append(desc[s:i + 1])
        i += 1
    return args, desc[i + 1:]


def width(t):
    return 2 if t in ('J', 'D') else 1


# ─────────────────────────── 字节码：长度与栈效果 ───────────────────────────

_FIXED = {}
for _op in range(0x00, 0x10):
    _FIXED[_op] = 0
for _op, _w in [(0x10, 1), (0x11, 2), (0x12, 1), (0x13, 2), (0x14, 2),
                (0x15, 1), (0x16, 1), (0x17, 1), (0x18, 1), (0x19, 1),
                (0x36, 1), (0x37, 1), (0x38, 1), (0x39, 1), (0x3a, 1),
                (0xa7, 2), (0xa8, 2), (0xa9, 1), (0xbb, 2), (0xbc, 1),
                (0xbd, 2), (0xc0, 2), (0xc1, 2), (0xb2, 2), (0xb3, 2),
                (0xb4, 2), (0xb5, 2), (0xb6, 2), (0xb7, 2), (0xb8, 2),
                (0xb9, 4), (0xba, 4), (0x84, 2), (0xc6, 2), (0xc7, 2),
                (0xc5, 3), (0xc8, 4), (0xc9, 4)]:
    _FIXED[_op] = _w
for _op in range(0x99, 0xa7):
    _FIXED[_op] = 2


def insn_len(code, i):
    op = code[i]
    if op == 0xc4:                                   # wide
        return 6 if code[i + 1] == 0x84 else 4
    if op in (0xaa, 0xab):
        j = i + 1
        while j % 4:
            j += 1
        if op == 0xaa:
            lo, hi = struct.unpack_from('>ii', code, j + 4)
            return j + 12 + (hi - lo + 1) * 4 - i
        n = struct.unpack_from('>i', code, j + 4)[0]
        return j + 8 + n * 8 - i
    return 1 + _FIXED.get(op, 0)


# 剩下那些「压/弹格数固定」的指令。带描述符的、动栈的都在 step() 里单独处理。
_SE = {0x00: (0, 0), 0x01: (0, 1), 0x09: (0, 2), 0x0a: (0, 2),
       0x0b: (0, 1), 0x0c: (0, 1), 0x0d: (0, 1), 0x0e: (0, 2),
       0x0f: (0, 2), 0x10: (0, 1), 0x11: (0, 1), 0x14: (0, 2),
       0x84: (0, 0), 0xb1: (0, 0), 0xbe: (1, 1), 0xbf: (1, 0),
       0xc1: (1, 1), 0xc2: (1, 0), 0xc3: (1, 0), 0x57: (1, 0),
       0x58: (2, 0), 0xbc: (1, 1), 0xbd: (1, 1),
       0xa7: (0, 0), 0xc6: (1, 0), 0xc7: (1, 0), 0xc8: (0, 0),
       0xaa: (1, 0), 0xab: (1, 0), 0xa8: (0, 1), 0xa9: (0, 0),
       0xac: (1, 0), 0xad: (2, 0), 0xae: (1, 0), 0xaf: (2, 0), 0xb0: (1, 0)}
for _op in range(0x02, 0x09):
    _SE[_op] = (0, 1)
for _op in range(0x2e, 0x36):                        # 数组读
    _SE[_op] = (2, 2 if _op in (0x2f, 0x31) else 1)
for _op in range(0x4f, 0x57):                        # 数组写
    _SE[_op] = (4 if _op in (0x50, 0x52) else 3, 0)
for _op in range(0x60, 0x84):                        # 算术 / 位运算
    if 0x74 <= _op <= 0x77:                          # ?neg
        _SE[_op] = (2, 2) if _op in (0x75, 0x77) else (1, 1)
    elif _op in (0x79, 0x7b, 0x7d):                  # lshl / lshr / lushr
        _SE[_op] = (3, 2)
    elif _op in (0x78, 0x7a, 0x7c):                  # ishl / ishr / iushr
        _SE[_op] = (2, 1)
    elif _op % 4 in (1, 3) and _op < 0x78:           # long / double 二元
        _SE[_op] = (4, 2)
    elif _op in (0x7f, 0x81, 0x83):                  # land / lor / lxor
        _SE[_op] = (4, 2)
    else:
        _SE[_op] = (2, 1)
for _op, _v in {0x85: (1, 2), 0x86: (1, 1), 0x87: (1, 2), 0x88: (2, 1),
                0x89: (2, 2), 0x8a: (2, 2), 0x8b: (1, 1), 0x8c: (1, 2),
                0x8d: (1, 2), 0x8e: (2, 1), 0x8f: (2, 2), 0x90: (2, 1),
                0x91: (1, 1), 0x92: (1, 1), 0x93: (1, 1), 0x94: (4, 1),
                0x95: (2, 1), 0x96: (2, 1), 0x97: (4, 1), 0x98: (4, 1)}.items():
    _SE[_op] = _v
for _op in range(0x99, 0x9f):
    _SE[_op] = (1, 0)
for _op in range(0x9f, 0xa7):
    _SE[_op] = (2, 0)

_JUMP_UNCOND = {0xa7, 0xc8, 0xa9, 0xaa, 0xab, 0xbf} | set(range(0xac, 0xb2))
_BRANCHING = {0xaa, 0xab, 0xc6, 0xc7, 0xc8, 0xa7} | set(range(0x99, 0xa7))

CONCAT = 'java/lang/invoke/StringConcatFactory'
LAMBDA = 'java/lang/invoke/LambdaMetafactory'


# ─────────────────────────────── 数据流模拟 ───────────────────────────────

class Sim:
    """在一个方法体上跑操作数栈模拟，遇到 KeyMapping 构造就回调。

    按 CFG 做，不是线性扫：三元表达式那种 `goto` 会让线性扫的栈深度错位，
    错位之后「第几个参数」全是错的。分支汇合处逐格合并，值不一致就退化成未知，
    宁可未知也不能给一个错的值。
    """

    def __init__(self, kl, key, on_ctor=None, is_ctor_target=None):
        self.kl = kl
        self.on_ctor = on_ctor or (lambda *a: None)
        self.is_ctor_target = is_ctor_target or (lambda r: False)
        self.access, self.code, self.exc = kl.methods[key]
        self.key = key
        args, _ = parse_desc(key[1])
        self.params = []                     # (局部变量槽, 第几个参数)
        slot = 0 if (self.access & 0x0008) else 1
        for i, a in enumerate(args):
            self.params.append((slot, i))
            slot += width(a)
        self.nlocals = slot + 64
        self.returns = {}
        self.dirty = False

    def local0(self):
        loc = [UNK] * self.nlocals
        if not (self.access & 0x0008):
            loc[0] = ('this',)
        for s, i in self.params:
            loc[s] = ('p', i)
        return tuple(loc)

    def run(self):
        if not self.code:
            return self
        seen = {}
        work = [(0, (), self.local0())]
        for h in (self.exc or []):
            work.append((h, (UNK,), self.local0()))
        steps = 0
        while work:
            off, stack, loc = work.pop()
            steps += 1
            if steps > 30000:
                self.dirty = True
                return self
            old = seen.get(off)
            if old is not None:
                st, lc = old
                if len(st) != len(stack):
                    self.dirty = True
                    continue
                m = (tuple(a if a == b else UNK for a, b in zip(st, stack)),
                     tuple(a if a == b else UNK for a, b in zip(lc, loc)))
                if m == old:
                    continue
                stack, loc = m
            seen[off] = (stack, loc)
            try:
                work.extend(self.step(off, list(stack), list(loc)))
            except Exception:
                self.dirty = True
        return self

    # 一条指令 -------------------------------------------------------------
    def step(self, i, st, loc):
        code, kl = self.code, self.kl
        op = code[i]
        ln = insn_len(code, i)
        nxt = []

        if op in (0x12, 0x13):                                   # ldc / ldc_w
            idx = code[i + 1] if op == 0x12 else struct.unpack_from('>H', code, i + 1)[0]
            e = kl.pool[idx] if idx < len(kl.pool) else None
            s = kl.utf(e[1]) if e and e[0] == 8 else None
            st.append(('s', s) if s is not None else UNK)
        elif 0x15 <= op <= 0x19:                                 # ?load n
            n = code[i + 1]
            st.append(loc[n] if n < len(loc) else UNK)
            if op in (0x16, 0x18):
                st.append(TOP)
        elif 0x1a <= op <= 0x2d:                                 # ?load_n
            base, n = divmod(op - 0x1a, 4)
            st.append(loc[n] if n < len(loc) else UNK)
            if base in (1, 3):
                st.append(TOP)
        elif 0x36 <= op <= 0x3a:                                 # ?store n
            n = code[i + 1]
            if op in (0x37, 0x39):
                st.pop()
            v = st.pop()
            if n < len(loc):
                loc[n] = v
        elif 0x3b <= op <= 0x4e:                                 # ?store_n
            base, n = divmod(op - 0x3b, 4)
            if base in (1, 3):
                st.pop()
            v = st.pop()
            if n < len(loc):
                loc[n] = v
        elif op == 0x59:                                         # dup
            st.append(st[-1])
        elif op in (0x5a, 0x5b):                                 # dup_x1 / dup_x2
            st.insert(len(st) - (2 if op == 0x5a else 3), st[-1])
        elif op == 0x5c:                                         # dup2
            st.extend(st[-2:])
        elif op in (0x5d, 0x5e):                                 # dup2_x1 / dup2_x2
            k = 3 if op == 0x5d else 4
            top2 = st[-2:]
            st[len(st) - k:len(st) - k] = top2
        elif op == 0x5f:                                         # swap
            st[-1], st[-2] = st[-2], st[-1]
        elif op == 0xb2:                                         # getstatic
            r = kl.ref(struct.unpack_from('>H', code, i + 1)[0])
            st.append(('gs',) + r if r else UNK)
            if r and r[2] in ('J', 'D'):
                st.append(TOP)
        elif op == 0xb3:                                         # putstatic
            r = kl.ref(struct.unpack_from('>H', code, i + 1)[0])
            if r and r[2] in ('J', 'D'):
                st.pop()
            self.on_put_static(r, st.pop())
        elif op == 0xb4:                                         # getfield
            r = kl.ref(struct.unpack_from('>H', code, i + 1)[0])
            o = st.pop()
            st.append(('gf', r[0], r[1], r[2], o) if r else UNK)
            if r and r[2] in ('J', 'D'):
                st.append(TOP)
        elif op == 0xb5:                                         # putfield
            r = kl.ref(struct.unpack_from('>H', code, i + 1)[0])
            if r and r[2] in ('J', 'D'):
                st.pop()
            v = st.pop()
            self.on_put_field(r, st.pop(), v)
        elif op in (0xb6, 0xb7, 0xb8, 0xb9):                     # invoke*
            r = kl.ref(struct.unpack_from('>H', code, i + 1)[0])
            if not r:
                raise ValueError('bad methodref')
            args, ret = parse_desc(r[2])
            n = sum(width(a) for a in args)
            vals = st[len(st) - n:] if n else []
            del st[len(st) - n:]
            recv = st.pop() if op != 0xb8 else None
            packed = pack(args, vals)
            self.on_invoke(r, recv, packed, i)
            if op == 0xb7 and r[1] == '<init>':
                init_obj(st, loc, recv, r[0], packed)
            elif ret != 'V':
                st.append(self.call_value(r, recv, packed))
                if ret in ('J', 'D'):
                    st.append(TOP)
        elif op == 0xba:                                         # invokedynamic
            idx = struct.unpack_from('>H', code, i + 1)[0]
            d = kl.indy(idx)
            if not d:
                raise ValueError('bad indy')
            args, ret = parse_desc(d[2])
            n = sum(width(a) for a in args)
            vals = st[len(st) - n:] if n else []
            del st[len(st) - n:]
            if ret != 'V':
                st.append(self.indy_value(d, pack(args, vals)))
                if ret in ('J', 'D'):
                    st.append(TOP)
        elif op == 0xbb:                                         # new
            st.append(('un', kl.cls_name(struct.unpack_from('>H', code, i + 1)[0]), i))
        elif op == 0xc0:                                         # checkcast：值不变
            pass
        elif op == 0xc5:                                         # multianewarray
            del st[len(st) - code[i + 3]:]
            st.append(UNK)
        elif op == 0xc4:                                         # wide
            sub = code[i + 1]
            n = struct.unpack_from('>H', code, i + 2)[0]
            if 0x15 <= sub <= 0x19:
                st.append(loc[n] if n < len(loc) else UNK)
                if sub in (0x16, 0x18):
                    st.append(TOP)
            elif 0x36 <= sub <= 0x3a:
                if sub in (0x37, 0x39):
                    st.pop()
                v = st.pop()
                if n < len(loc):
                    loc[n] = v
        else:
            pop, push = _SE.get(op, (0, 0))
            if pop:
                del st[len(st) - pop:]
            for _ in range(push):
                st.append(UNK)

        if op == 0xb0 and st:                                    # areturn
            self.returns[i] = st[-1]                             # 同一条只留最终值
        if op in _BRANCHING:
            for j in self.branch_targets(i):
                nxt.append((j, tuple(st), tuple(loc)))
        if op not in _JUMP_UNCOND and i + ln < len(code):
            nxt.append((i + ln, tuple(st), tuple(loc)))
        return nxt

    def branch_targets(self, i):
        code = self.code
        op = code[i]
        if op in (0xa7, 0xc8):
            return [i + struct.unpack_from('>i' if op == 0xc8 else '>h', code, i + 1)[0]]
        if 0x99 <= op <= 0xa6 or op in (0xc6, 0xc7):
            return [i + struct.unpack_from('>h', code, i + 1)[0]]
        if op in (0xaa, 0xab):
            j = i + 1
            while j % 4:
                j += 1
            out = [i + struct.unpack_from('>i', code, j)[0]]
            if op == 0xaa:
                lo, hi = struct.unpack_from('>ii', code, j + 4)
                out += [i + struct.unpack_from('>i', code, j + 12 + k * 4)[0]
                        for k in range(hi - lo + 1)]
            else:
                n = struct.unpack_from('>i', code, j + 4)[0]
                out += [i + struct.unpack_from('>i', code, j + 12 + k * 8)[0]
                        for k in range(n)]
            return out
        return []

    # 值的构造 -------------------------------------------------------------
    def call_value(self, r, recv, args):
        """老式字符串拼接也要认：javac 21 用 invokedynamic，更老的用 StringBuilder。"""
        if r[0] == 'java/lang/StringBuilder':
            if r[1] == 'append':
                return ('cat', tuple(parts_of(recv)) + tuple(args[:1]))
            if r[1] == 'toString':
                return ('cat', tuple(parts_of(recv)))
        if r[0] == 'java/lang/String':
            if r[1] == 'concat':
                return ('cat', (recv,) + tuple(args[:1]))
            if r[1] == 'valueOf' and args:
                return args[0]
            if r[1] in ('intern', 'toString', 'strip', 'trim'):
                return recv
        return ('iv', r[0], r[1], r[2], recv, tuple(args))

    def indy_value(self, d, args):
        bsm_i, _, _ = d
        if bsm_i >= len(self.kl.bootstrap):
            return UNK
        mh, bargs = self.kl.bootstrap[bsm_i]
        ref = self.kl.handle_ref(mh)
        if not ref:
            return UNK
        if ref[0] == LAMBDA and len(bargs) >= 2:
            impl = self.kl.handle_ref(bargs[1])
            # 捕获变量是实现方法的前 n 个形参，lambda 自己的参数排在后面
            return ('lam',) + impl + (tuple(args),) if impl else UNK
        if ref[0] != CONCAT:
            return UNK
        if ref[1] == 'makeConcat':
            return ('cat', tuple(args))
        if ref[1] != 'makeConcatWithConstants' or not bargs:
            return UNK
        recipe = self.kl.const_str(bargs[0])
        consts = [self.kl.const_str(x) for x in bargs[1:]]
        if recipe is None:
            return UNK
        parts, lit, ai, ci = [], [], 0, 0
        for ch in recipe:
            if ch == '\x01':      # 一个动态参数
                if lit:
                    parts.append(('s', ''.join(lit)))
                    lit = []
                parts.append(args[ai] if ai < len(args) else UNK)
                ai += 1
            elif ch == '\x02':    # 一个引导常量
                if lit:
                    parts.append(('s', ''.join(lit)))
                    lit = []
                parts.append(('s', consts[ci]) if ci < len(consts)
                             and consts[ci] is not None else UNK)
                ci += 1
            else:
                lit.append(ch)
        if lit:
            parts.append(('s', ''.join(lit)))
        return ('cat', tuple(parts))

    # 子类/调用方按需覆盖 ---------------------------------------------------
    def on_put_static(self, ref, val):
        pass

    def on_put_field(self, ref, obj, val):
        pass

    def on_invoke(self, ref, recv, args, off):
        if self.is_ctor_target(ref):
            self.on_ctor(self, ref, args, off)


def pack(args, vals):
    """把带 TOP 填充的原始栈值按参数还原成一格一个。"""
    out, k = [], 0
    for a in args:
        out.append(vals[k] if k < len(vals) else UNK)
        k += width(a)
    return out


def parts_of(v):
    return list(v[1]) if isinstance(v, tuple) and v and v[0] == 'cat' else [v]


def init_obj(st, loc, recv, cls, args):
    """`new`/`<init>` 之后，把栈与局部变量里那个未初始化引用替换成成品。"""
    if not (isinstance(recv, tuple) and recv and recv[0] == 'un'):
        return
    done = ('cat', ()) if cls == 'java/lang/StringBuilder' \
        else ('obj', cls, tuple(args))
    if cls == 'java/lang/StringBuilder' and args:
        done = ('cat', tuple(args[:1]))
    for k, v in enumerate(st):
        if v == recv:
            st[k] = done
    for k, v in enumerate(loc):
        if v == recv:
            loc[k] = done


# ─────────────────────────────── 一个 jar ───────────────────────────────

class Jar:
    """一个 jar 里的类索引 + 取值回溯。跨 jar 的引用查不到就算查不到。"""

    def __init__(self, path):
        self.path = path
        self.zf = zipfile.ZipFile(path)
        self.entries = {n[:-6]: n for n in self.zf.namelist() if n.endswith('.class')}
        self.cache = {}
        self.memo = {}
        self.fails = []

    def cls(self, name):
        if name in self.cache:
            return self.cache[name]
        k = None
        if name in self.entries:
            try:
                k = Klass(self.zf.read(self.entries[name]))
            except Exception as e:
                self.fails.append('%s: %r' % (name, e))
        self.cache[name] = k
        return k

    def _memo(self, key, fn):
        if key not in self.memo:
            self.memo[key] = None            # 递归保护
            self.memo[key] = fn()
        return self.memo[key]

    # ── 静态字段 ──
    def static_value(self, owner, fname):
        def go():
            k = self.cls(owner)
            if not k:
                return None
            f = k.fields.get(fname)
            if f and f[2] is not None:
                return ('s', f[2])
            got = []

            class S(Sim):
                def on_put_static(s, ref, val):
                    if ref and ref[0] == owner and ref[1] == fname:
                        got.append(val)
            if ('<clinit>', '()V') in k.methods:
                S(k, ('<clinit>', '()V')).run()
            return got[0] if len(set(got)) == 1 else None
        return self._memo(('sv', owner, fname), go)

    # ── 「类里那一堆静态常量实例」：枚举，或手写的静态注册表 ──
    def instances(self, owner):
        """-> {常量名: 构造实参元组}"""
        def go():
            k = self.cls(owner)
            if not k:
                return {}
            got = {}

            class C(Sim):
                def on_put_static(s, ref, val):
                    if ref and ref[0] == owner and isinstance(val, tuple) \
                            and val and val[0] == 'obj' and val[1] == owner:
                        got[ref[1]] = val[2]
            if ('<clinit>', '()V') in k.methods:
                C(k, ('<clinit>', '()V')).run()
            return got
        return self._memo(('inst', owner), go)

    def field_expr(self, owner, field):
        """构造器里存进这个实例字段的表达式（可能含 ('p', k) 形参占位）。"""
        def go():
            k = self.cls(owner)
            if not k:
                return None
            for key in k.methods:
                if key[0] != '<init>' or k.methods[key][1] is None:
                    continue
                hit = []

                class I(Sim):
                    def on_put_field(s, ref, obj, val):
                        if ref and ref[1] == field and obj == ('this',):
                            hit.append(val)
                I(k, key).run()
                if len(set(hit)) == 1:
                    return hit[0]
            return None
        return self._memo(('fe', owner, field), go)

    def method_expr(self, owner, mname, mdesc):
        """方法的返回值表达式（里面的 ('p', k) / ('this',) 由调用方代入）。"""
        def go():
            k = self.cls(owner)
            if not k or (mname, mdesc) not in k.methods \
                    or k.methods[(mname, mdesc)][1] is None:
                return None
            s = Sim(k, (mname, mdesc)).run()
            vals = set(s.returns.values())
            return vals.pop() if len(vals) == 1 else None
        return self._memo(('ge', owner, mname, mdesc), go)

    def impl_exprs(self, mname, mdesc):
        """jar 里所有声明了这个签名的类各自的返回值表达式。

        接口方法调用（`IArmorUpgradeHandler.getStringKey(rl)`）在字节码里指向的是
        接口，接口自己往往没有方法体。只给 atoms() 用：多收几个实现类的字面量
        只会让门控更宽，不会漏报。
        """
        def go():
            out = []
            for cn in self.entries:
                k = self.cls(cn)
                if not k or (mname, mdesc) not in k.methods:
                    continue
                if k.methods[(mname, mdesc)][1] is None:
                    continue
                e = self.method_expr(cn, mname, mdesc)
                if e is not None:
                    out.append(e)
                if len(out) > 16:
                    break
            return out
        return self._memo(('ie', mname, mdesc), go)

    # ── lambda 体：回到 invokedynamic 那里取捕获变量 ──
    def lambda_sites(self, owner, mname, mdesc):
        def go():
            out = []

            class S(Sim):
                def indy_value(s, d, args):
                    v = Sim.indy_value(s, d, args)
                    if isinstance(v, tuple) and v and v[0] == 'lam' \
                            and v[1:4] == (owner, mname, mdesc):
                        out.append((s.kl, s.key, tuple(v[4])))
                    return v
            self._scan_all(mname.encode(), S)
            return out
        return self._memo(('ls', owner, mname, mdesc), go)

    def _scan_all(self, needle, sim_cls):
        """对 jar 里提到 needle 的每个类跑一遍模拟。"""
        for cn, entry in self.entries.items():
            try:
                raw = self.zf.read(entry)
            except Exception:
                continue
            if needle not in raw:
                continue
            k = self.cls(cn)
            if not k:
                continue
            for key in list(k.methods):
                if k.methods[key][1] is None:
                    continue
                try:
                    sim_cls(k, key).run()
                except Exception:
                    pass

    # ── 方法形参：回到调用点取实参 ──
    def call_sites(self, owner, mname, mdesc):
        def go():
            need = (owner.encode(), mname.encode())
            out = []
            for cn, entry in self.entries.items():
                try:
                    raw = self.zf.read(entry)
                except Exception:
                    continue
                if not all(x in raw for x in need):
                    continue
                k = self.cls(cn)
                if not k:
                    continue
                for key in list(k.methods):
                    if k.methods[key][1] is None:
                        continue

                    class S(Sim):
                        def on_invoke(s, ref, recv, args, off):
                            if ref and ref[0] == owner and ref[1] == mname \
                                    and ref[2] == mdesc:
                                out.append((k, key, tuple(args)))
                    try:
                        S(k, key).run()
                    except Exception:
                        pass
            return out
        return self._memo(('cs', owner, mname, mdesc), go)


# ─────────────────────────────── 取值 ───────────────────────────────

def subst(val, actual, this=None):
    """把表达式里的 ('p', k) 换成实参、('this',) 换成接收者。"""
    if not isinstance(val, tuple) or not val:
        return val
    if val[0] == 'p':
        return actual[val[1]] if val[1] < len(actual) else UNK
    if val[0] == 'this' and this is not None:
        return this
    if val[0] == 'cat':
        return ('cat', tuple(subst(x, actual, this) for x in val[1]))
    if val[0] == 'gf':
        return ('gf', val[1], val[2], val[3], subst(val[4], actual, this))
    if val[0] == 'iv':
        return ('iv', val[1], val[2], val[3], subst(val[4], actual, this),
                tuple(subst(x, actual, this) for x in val[5]))
    if val[0] == 'lam':
        return val[:4] + (tuple(subst(x, actual, this) for x in val[4]),)
    return val


def resolve(jar, val, depth=0):
    """把一个栈值化成字符串集合。取不到就返回空集，不猜。"""
    if not isinstance(val, tuple) or not val or depth > MAX_DEPTH:
        return set()
    kind = val[0]
    if kind == 's':
        return {val[1]}
    if kind == 'cat':
        out = {''}
        for part in val[1]:
            got = resolve(jar, part, depth + 1)
            if not got:
                return set()
            out = {a + b for a in out for b in sorted(got)}
            if len(out) > MAX_FANOUT:
                return set()
        return out
    if kind == 'gs':
        if val[3] == 'Ljava/lang/String;':
            v = jar.static_value(val[1], val[2])
            return resolve(jar, v, depth + 1) if v is not None else set()
        return set()
    if kind == 'gf':
        return resolve_member(jar, val[1], jar.field_expr(val[1], val[2]),
                              val[4], depth)
    if kind == 'iv':
        recv, args = val[4], val[5]
        is_lam = isinstance(recv, tuple) and recv and recv[0] == 'lam'
        if not val[3].endswith(')Ljava/lang/String;') and not (
                is_lam and val[3].endswith(')Ljava/lang/Object;')):
            return set()
        if is_lam:
            # 函数式接口调用：真正的实现是那个 lambda 体，
            # 捕获变量排在实现方法形参的最前面，lambda 自己的参数跟在后面
            expr = jar.method_expr(recv[1], recv[2], recv[3])
            return resolve(jar, subst(expr, tuple(recv[4]) + tuple(args)),
                           depth + 1) if expr is not None else set()
        expr = jar.method_expr(val[1], val[2], val[3])
        if expr is None:
            return set()
        return resolve(jar, subst(expr, args, recv), depth + 1)
    return set()


def resolve_member(jar, owner, expr, recv, depth):
    """实例字段 / getter：把接收者可能的每个常量实例代进表达式。

    接收者是具体常量（`AllKeys.TOOLBELT`）就只代那一个。接收者是循环变量
    （`for (AllKeys k : values())`）则把全部常量代一遍，那个 for 循环本来
    就会给每个常量都注册一个键位。
    """
    if expr is None:
        return set()
    insts = narrow(jar, owner, recv)
    if not insts:
        return set()
    out = set()
    for args in insts.values():
        out |= resolve(jar, subst(expr, args), depth + 1)
        if len(out) > MAX_FANOUT:
            return set()
    return out


def atoms(jar, val, depth=0, seen=None):
    """把 name 表达式里能追到的全部字符串字面量收齐。

    这才是安全门控要的东西。最终名字常常要到运行期才拼得出来
    （`"artifacts.key.%s.%s".formatted(…)`），但组成它的那几个字面量是死的、
    在常量池里躺着的，而 VaultPatcher 改的正是常量池。所以只要我们替换的串
    落进这个集合，就一定动到了某个按键注册名，不管最终名字长什么样。

    与 resolve() 的区别：resolve 要求整条链每一环都算得出来，算不出就整体作废。
    atoms 只要沿途见到字面量就收，链断了也把已经收到的留下。
    """
    if not isinstance(val, tuple) or not val or depth > MAX_DEPTH:
        return set()
    seen = set() if seen is None else seen
    kind = val[0]
    if kind == 's':
        return {val[1]}
    if kind == 'cat':
        out = set()
        for x in val[1]:
            out |= atoms(jar, x, depth + 1, seen)
        return out
    if kind == 'gs':
        v = jar.static_value(val[1], val[2])
        return atoms(jar, v, depth + 1, seen) if v is not None else set()
    if kind == 'lam':
        out = set()
        for x in val[4]:
            out |= atoms(jar, x, depth + 1, seen)
        e = jar.method_expr(val[1], val[2], val[3])
        return out | (atoms(jar, e, depth + 1, seen) if e is not None else set())
    if kind == 'gf':
        key = val[:4]
        if key in seen:
            return set()
        seen = seen | {key}
        out = atoms(jar, val[4], depth + 1, seen)
        e = jar.field_expr(val[1], val[2])
        if e is None:
            return out
        # 只把这个字段的表达式逐实例代入，不能把常量的全部构造实参都收进来：
        # 那会把整个枚举（包括 tooltip 整句）算成按键名的片段，检查会全是误报。
        insts = narrow(jar, val[1], val[4])
        for a in (insts.values() if insts else [None]):
            out |= atoms(jar, e if a is None else subst(e, a), depth + 1, seen)
        return out
    if kind == 'iv':
        key = val[:4]
        if key in seen:
            return set()
        seen = seen | {key}
        out = atoms(jar, val[4], depth + 1, seen)
        for x in val[5]:
            out |= atoms(jar, x, depth + 1, seen)
        e = jar.method_expr(val[1], val[2], val[3])
        if e is None:                        # 接口方法：去找实现类
            for e2 in jar.impl_exprs(val[2], val[3]):
                out |= atoms(jar, e2, depth + 1, seen)
            return out
        return out | atoms(jar, subst(e, val[5], val[4]), depth + 1, seen)
    return set()


def narrow(jar, owner, recv):
    """接收者已知是哪个常量实例就只取那个，未知就取全部。"""
    insts = jar.instances(owner)
    if isinstance(recv, tuple) and recv and recv[0] == 'gs' and recv[1] == owner:
        return {recv[2]: insts[recv[2]]} if recv[2] in insts else {}
    if isinstance(recv, tuple) and recv and recv[0] == 'obj' and recv[1] == owner:
        return {'<literal>': recv[2]}
    return insts


def expand(jar, kl, mkey, args, depth=0):
    """构造点的参数里有形参占位，就回到调用点把实参代进来。"""
    if depth >= MAX_DEPTH:
        return [args]
    if not any(has_param(a) for a in args):
        return [args]
    if mkey[0].startswith('lambda$'):
        sites = jar.lambda_sites(kl.name, mkey[0], mkey[1])
    else:
        sites = jar.call_sites(kl.name, mkey[0], mkey[1])
    if not sites:
        return [args]
    out = []
    for ck, ckey, actual in sites[:64]:
        sub = [subst(a, actual) for a in args]
        out += expand(jar, ck, ckey, sub, depth + 1)
        if len(out) > MAX_FANOUT:
            break
    return out or [args]


def has_param(v):
    if not isinstance(v, tuple) or not v:
        return False
    if v[0] == 'p':
        return True
    if v[0] == 'cat':
        return any(has_param(x) for x in v[1])
    if v[0] == 'gf':
        return has_param(v[4])
    if v[0] == 'iv':
        return has_param(v[4]) or any(has_param(x) for x in v[5])
    if v[0] == 'lam':
        return any(has_param(x) for x in v[4])
    return False


# ─────────────────────────────── 主流程 ───────────────────────────────

def is_keymapping_ctor(ref):
    return bool(ref) and ref[1] == '<init>' and ref[0] \
        and ref[0].rsplit('/', 1)[-1].endswith('KeyMapping')


def shape(v):
    """把一个取不到的值压成一句可读的形态描述，用来汇总「还差哪几类」。"""
    if not isinstance(v, tuple) or not v:
        return '?'
    if v[0] == 'iv':
        return '%s.%s()' % (v[1].rsplit('/', 1)[-1], v[2])
    if v[0] == 'gf':
        return '%s.%s' % (v[1].rsplit('/', 1)[-1], v[2])
    if v[0] == 'gs':
        return '%s.%s (static)' % (v[1].rsplit('/', 1)[-1], v[2])
    if v[0] == 'lam':
        return 'lambda %s.%s' % (v[1].rsplit('/', 1)[-1], v[2])
    if v[0] == 'cat':
        return '拼接(%s)' % '+'.join(shape(x) for x in v[1][:4])
    if v[0] == 'p':
        return '形参#%d' % v[1]
    return v[0]


def scan_jar(path):
    jar = Jar(path)
    hits, unresolved, total = [], [], []
    for cn, entry in list(jar.entries.items()):
        try:
            raw = jar.zf.read(entry)
        except Exception:
            continue
        if b'KeyMapping' not in raw:
            continue
        kl = jar.cls(cn)
        if not kl:
            continue
        for key in list(kl.methods):
            if kl.methods[key][1] is None:
                continue
            found = []
            try:
                Sim(kl, key,
                    lambda s, r, a, o, _f=found: _f.append((r, list(a))),
                    is_keymapping_ctor).run()
            except Exception as e:
                jar.fails.append('%s.%s: %r' % (cn, key[0], e))
                continue
            for ref, args in found:
                types, _ = parse_desc(ref[2])
                si = [i for i, t in enumerate(types) if t == 'Ljava/lang/String;']
                if len(si) < 2:
                    continue                 # name 与 category 分不开，宁可不报
                for sub in expand(jar, kl, key, args):
                    nm = resolve(jar, sub[si[0]])
                    ct = resolve(jar, sub[si[-1]])
                    at = atoms(jar, sub[si[0]])
                    total.append(bool(at))
                    if not nm:
                        unresolved.append(shape(sub[si[0]]))
                    hits.append((nm, ct, at, cn))
    return hits, jar.fails, unresolved, total


def main(mods_dir, out_path=None, truth=None):
    cats, names, sites, fails = {}, {}, [], []
    name_atoms, covered = {}, [0, 0]
    shapes = Counter()
    jars = sorted(Path(mods_dir).glob('*.jar'))
    for n, jar in enumerate(jars, 1):
        if n % 100 == 0:
            print('  %d/%d' % (n, len(jars)), flush=True)
        try:
            hits, f, unres, tot = scan_jar(jar)
        except Exception as e:
            fails.append('%s: %r' % (jar.name, e))
            continue
        fails += ['%s!%s' % (jar.name, x) for x in f]
        shapes.update(unres)
        covered[0] += sum(1 for x in tot if x)
        covered[1] += len(tot)
        for nm, ct, at, cls in hits:
            for c in ct:
                cats.setdefault(c, set()).add(jar.name)
            for x in nm:
                names.setdefault(x, set()).add(jar.name)
            for x in at:
                name_atoms.setdefault(x, set()).add(jar.name)
            sites.append({'jar': jar.name, 'class': cls, 'names': sorted(nm),
                          'categories': sorted(ct), 'name_atoms': sorted(at)})
    keys = sorted(c for c in cats if c.startswith('key.'))
    lits = sorted(c for c in cats if not c.startswith('key.'))
    print('按键分类 %d 个（翻译键 %d、硬编码字面量 %d），解出的完整注册名 %d 个'
          % (len(cats), len(keys), len(lits), len(names)))
    print('KeyMapping 构造点 %d 处，其中 %d 处能追到字符串片段（%.1f%%），片段共 %d 个'
          % (covered[1], covered[0], 100.0 * covered[0] / max(1, covered[1]),
             len(name_atoms)))
    if shapes:
        print('取不到注册名的构造点 %d 处，形态前几名:' % sum(shapes.values()))
        for s, c in shapes.most_common(8):
            print('   %4d × %s' % (c, s))
    if fails:
        print('⚠️ %d 处解析失败（前 3 条）:' % len(fails))
        for x in fails[:3]:
            print('   ', x)
    if truth:
        report(names, truth)
    if out_path:
        Path(out_path).write_text(json.dumps(
            {'keys': keys, 'literals': {c: sorted(cats[c]) for c in lits},
             'names': {x: sorted(v) for x, v in sorted(names.items())},
             'name_atoms': {x: sorted(v) for x, v in sorted(name_atoms.items())},
             'unresolved': dict(shapes.most_common()), 'sites': sites},
            ensure_ascii=False, indent=1), encoding='utf-8')
        print('已写出 %s' % out_path)
    return keys, lits, names


def report(names, options_txt):
    """用一份实际运行过的 options.txt 当真值，打印召回率与误报。报数之前必须先通过这项验收。"""
    truth = set()
    for line in Path(options_txt).read_text(encoding='utf-8').splitlines():
        if line.startswith('key_'):
            truth.add(line[4:].split(':')[0])
    got = set(names)
    miss, extra = sorted(truth - got), sorted(got - truth)
    print('── 拿 %s 验收 ──' % options_txt)
    print('  真值 %d 条，命中 %d（召回 %.1f%%），漏 %d，不在真值里的 %d'
          % (len(truth), len(truth & got),
             100.0 * len(truth & got) / max(1, len(truth)), len(miss), len(extra)))
    for label, lst in (('漏', miss), ('多', extra)):
        for x in lst[:10]:
            print('   %s %s' % (label, x))
        if len(lst) > 10:
            print('   %s …还有 %d 条' % (label, len(lst) - 10))
    return truth & got, miss, extra


if __name__ == '__main__':
    a = [x for x in sys.argv[1:] if not x.startswith('--')]
    t = None
    for i, x in enumerate(sys.argv):
        if x == '--truth':
            t = sys.argv[i + 1]
            a = [y for y in a if y != t]
    if not a:
        sys.exit(__doc__)
    main(a[0], a[1] if len(a) > 1 else None, t)
