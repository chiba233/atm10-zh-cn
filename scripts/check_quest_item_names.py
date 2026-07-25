#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""任务书 ↔ 绑定物品 反查对齐。

思路（用户提的，比按英文文本匹配精确得多）：
每条任务在 chapters/*.snbt 里都绑定了具体物品 ID（tasks[].item）。
拿这个 ID 反查物品的中文真名，任务标题里就该出现这个名字。
对不上 = 任务书自己另造了一套词，玩家照着去 JEI 搜不到。
"""
import json, os, re, sys, zipfile
from collections import defaultdict

INST = "/Users/yumeka/Documents/minecraft/.minecraft/versions/All the Mods 10"
MCROOT = "/Users/yumeka/Documents/minecraft/.minecraft"
REPO = "/Users/yumeka/Documents/projects/atm10-zh-cn"
PACK = os.path.join(REPO, "resourcepacks/ATM10汉化包-7.2")
QDIR = os.path.join(INST, "config/ftbquests/quests")
CODE = re.compile(r'[&§](?:#[0-9A-Fa-f]{6}|[0-9a-fk-orA-FK-OR])')
strip = lambda s: CODE.sub('', s)
# 比较时归一化空格：「16k 存储元件」和「16k存储元件」不算不一致
norm = lambda s: re.sub(r'[\s\u00a0]+', '', strip(s))


# ---------- 1. 任务 → 绑定物品 ----------
def parse_chapter(path):
    """→ {quest_id: [item_id, ...]}（只取 tasks，不取 rewards）

    字符级扫描：SNBT 里 `tasks: [{` 常写在同一行，行级正则会漏掉九成。
    """
    src = open(path, encoding='utf-8').read()
    out = {}
    stack = []          # [(容器符, 键名)]
    pending = None      # 刚读到的 `键:`
    cur_q = None        # 当前任务块的 (深度, id, items)
    i, n = 0, len(src)
    while i < n:
        c = src[i]
        if c == '"':
            j = i + 1
            while j < n and not (src[j] == '"' and src[j - 1] != '\\'):
                j += 1
            val = src[i + 1:j]
            path_keys = [k for _, k in stack]
            if cur_q is not None and pending == 'id' and len(stack) == cur_q[0]:
                if re.fullmatch(r'[0-9A-F]{16}', val) and cur_q[1] is None:
                    cur_q[1] = val
            if cur_q is not None and 'tasks' in path_keys[cur_q[0] - 1:] \
                    and pending in ('item', 'id') and ':' in val:
                if re.fullmatch(r'[a-z0-9_.-]+:[a-z0-9_./-]+', val):
                    cur_q[2].append(val)
            pending = None
            i = j + 1
            continue
        if c in '{[':
            stack.append((c, pending))
            if pending is None and len(stack) >= 2 and stack[-2][1] == 'quests' \
                    and c == '{' and cur_q is None:
                cur_q = [len(stack), None, []]
            pending = None
            i += 1
            continue
        if c in '}]':
            if cur_q is not None and len(stack) == cur_q[0] and c == '}':
                if cur_q[1]:
                    out[cur_q[1]] = cur_q[2]
                cur_q = None
            if stack:
                stack.pop()
            pending = None
            i += 1
            continue
        m = re.match(r'([A-Za-z_][A-Za-z0-9_]*)\s*:', src[i:])
        if m:
            pending = m.group(1)
            i += m.end()
            continue
        i += 1
    return out


# ---------- 2. 物品 ID → 中文真名 ----------
def build_item_names():
    def loadb(b):
        try:
            return json.loads(b.decode('utf-8-sig'))
        except Exception:
            return {}

    jar_zh, jar_en = {}, {}
    for j in sorted(os.listdir(os.path.join(INST, 'mods'))):
        if not j.endswith('.jar'):
            continue
        try:
            z = zipfile.ZipFile(os.path.join(INST, 'mods', j))
        except Exception:
            continue
        with z:
            for n in z.namelist():
                if not n.startswith('assets/'):
                    continue
                if n.endswith('/lang/zh_cn.json'):
                    jar_zh.update(loadb(z.read(n)))
                elif n.endswith('/lang/en_us.json'):
                    jar_en.update(loadb(z.read(n)))
    with zipfile.ZipFile(os.path.join(INST, 'All the Mods 10.jar')) as z:
        jar_en.update(loadb(z.read('assets/minecraft/lang/en_us.json')))
    idx = json.load(open(os.path.join(MCROOT, 'assets/indexes/17.json')))['objects']
    h = idx['minecraft/lang/zh_cn.json']['hash']
    jar_zh.update(json.load(open(os.path.join(MCROOT, 'assets/objects', h[:2], h),
                                 encoding='utf-8')))
    pack_zh = {}
    for base in (PACK, os.path.join(REPO, 'kubejs/assets')):
        for dp, _, fns in os.walk(base):
            if os.path.basename(dp) != 'lang':
                continue
            for fn in fns:
                if fn == 'zh_cn.json':
                    pack_zh.update(json.load(open(os.path.join(dp, fn), encoding='utf-8')))
    eff = dict(jar_zh)
    eff.update(pack_zh)
    return eff, jar_en


def name_of(eff, jar_en, item_id):
    ns, path = item_id.split(':', 1)
    for pre in ('item', 'block'):
        k = '%s.%s.%s' % (pre, ns, path.replace('/', '.'))
        if k in eff:
            return eff[k], jar_en.get(k), k
    return None, None, None


# ---------- 3. 任务标题 ----------
def parse_lang(path):
    lines = open(path, encoding='utf-8').read().split('\n')
    out, i = {}, 0
    while i < len(lines):
        m = re.match(r'\t([A-Za-z0-9_.]+):\s*(.*)$', lines[i])
        if not m:
            i += 1
            continue
        k, rest = m.group(1), m.group(2)
        if rest.startswith('['):
            buf, bal = [rest], rest.count('[') - rest.count(']')
            while bal > 0 and i + 1 < len(lines):
                i += 1
                buf.append(lines[i])
                bal += lines[i].count('[') - lines[i].count(']')
            out[k] = '\n'.join(buf)
        else:
            out[k] = rest.strip('"')
        i += 1
    return out


def main():
    q2i = {}
    for f in sorted(os.listdir(os.path.join(QDIR, 'chapters'))):
        if f.endswith('.snbt'):
            q2i.update(parse_chapter(os.path.join(QDIR, 'chapters', f)))
    eff, jar_en = build_item_names()
    zh = parse_lang(os.path.join(QDIR, 'lang/zh_cn.snbt'))
    en = parse_lang(os.path.join(QDIR, 'lang/en_us.snbt'))
    print('任务 %d 条（其中绑定了物品的 %d 条）'
          % (len(q2i), sum(1 for v in q2i.values() if v)))

    bad = []
    for qid, items in sorted(q2i.items()):
        if not items:
            continue
        title = zh.get('quest.%s.title' % qid)
        if not title:
            continue                       # 没自定义标题 → 游戏直接显示物品名，天然一致
        t = strip(title)
        et = strip(en.get('quest.%s.title' % qid, ''))
        ok, cands = False, []
        for it in dict.fromkeys(items):
            zh_name, en_name, key = name_of(eff, jar_en, it)
            if not zh_name or not en_name:
                continue
            # 判据：英文标题里出现了该物品的英文名，中文标题才必须出现它的中文名。
            # 英文标题是概括性的（Chainmail Armor / The Metal Age）时不作要求。
            if not re.search(r'(?<![A-Za-z])%s' % re.escape(en_name), et, re.I):
                continue
            cands.append((it, zh_name, en_name))
            if norm(zh_name) in norm(t):
                ok = True
                break
        if not ok and cands:
            bad.append((qid, t, et, cands))
    print('标题没用上绑定物品中文名的：%d 条' % len(bad))
    return bad


if __name__ == '__main__':
    bad = main()
    show = int(sys.argv[1]) if len(sys.argv) > 1 else 40
    for qid, t, ent, cands in bad[:show]:
        it, zh_name, en_name = cands[0]
        print('  %s  标题=%-22s 英文标题=%-26s 绑定=%s → 真名「%s」(en=%s)'
              % (qid, t[:22], ent[:26], it, zh_name, en_name))
