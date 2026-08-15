#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# atm10-zh-cn — All the Mods 10 简体中文汉化补丁「绿油油版」
# Copyright (C) 2026 星野夢華 (Hoshino Yumeka)
# SPDX-License-Identifier: GPL-3.0-or-later
"""把某个版本的 ATM10 整合包备齐成一个能当 ATM_PACK_ROOT 用的目录。

两种用法，成本差一个数量级：

- `--no-jars`：只解 `overrides/`。**打补丁用的官方文件**（ATM 自己的 kubejs/*.js、
  config/*.json）就在里面，每个目标版本都要来一份，构建时对着它套映射。
- 全量：再按 manifest 把 480 个 mod jar 下齐。只有「读 jar 里的 en_us 与注册表」
  的那几个生成器需要（奖杯名、木头名、蜂名、格式串快照），一次构建取最新那版即可。

CurseForge 的网页 API 没有配额说明但会限速。踩过的坑都写进代码里了：
默认 UA 会被挡（必须伪装成浏览器）、并发压到 4、失败按指数退避重试、
整轮重来收漏网的、**不查元数据**直接下载并从跳转后的 CDN 地址取文件名、
下不来时把**真实的 HTTP 错误**打出来（以前吞成 None，只看得到「下得太少」，
分不清是限速还是接口变了，白折腾好几轮）。

用法:
    python3 scripts/fetch_pack.py 7.2 build/packsrc/7.2 --no-jars   # 只要官方文件
    python3 scripts/fetch_pack.py 7.2 pack                          # 含 480 个 jar
"""
import concurrent.futures as cf
import hashlib
import io
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PROJECT = 925200          # CurseForge 上的 All the Mods 10
API = 'https://www.curseforge.com/api/v1/mods/%d' % PROJECT
UA = ('Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/126.0 Safari/537.36')
TRIES = 6


def fetch(url, timeout=180, required=True):
    """取一个 URL，返回 (内容, 最终URL)。限速/抽风就退避重试。

    **失败原因必须留下来**：以前这里把异常吞成 None，CI 上 482 个 jar 全下不来时
    只看得到「jar 下得太少」，看不出到底是限速、403 还是 404，白折腾好几轮。
    """
    last = None
    for i in range(TRIES):
        req = urllib.request.Request(url, headers={'User-Agent': UA})
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read(), r.url
        except urllib.error.HTTPError as e:
            last = 'HTTP %s %s' % (e.code, e.reason)
            if e.code in (403, 408, 425, 429, 500, 502, 503, 504):
                wait = float(e.headers.get('Retry-After') or 0) or (2 ** i)
                time.sleep(min(wait, 60))
                continue
            break                                    # 404/400 这类重试也没用
        except Exception as e:                       # 超时、连接重置
            last = repr(e)
            time.sleep(2 ** i)
    if required:
        sys.exit('❌ 取不到 %s\n   重试 %d 次后仍失败：%s' % (url, TRIES, last))
    return None, last


def get(url, timeout=180, required=True):
    return fetch(url, timeout, required)[0]


class _Head(urllib.request.Request):
    def get_method(self):
        return 'HEAD'


def head_name(url, timeout=60, tries=3):
    """只问跳转后的文件名，不取正文。

    要重试：探不到名字就等于没有交叉验证，而 GET 的跳转**确实会偶发指到别的文件**
    （实测 cc-tweaked 1.113.1 的 ID 拿回来一个 1.120.0）。探不到就返回 None，
    调用方照常下载，但那一份会被当成「来路不明」记下来。
    """
    for i in range(tries):
        try:
            with urllib.request.urlopen(_Head(url, headers={'User-Agent': UA}),
                                        timeout=timeout) as r:
                n = urllib.parse.unquote(str(r.url).rsplit('/', 1)[-1].split('?')[0])
                return n if n.endswith('.jar') else None
        except urllib.error.HTTPError as e:
            if e.code not in (403, 408, 425, 429, 500, 502, 503, 504):
                return None
        except Exception:
            pass
        time.sleep(2 ** i)
    return None


def tree_digest(root, only=None):
    """overrides 的确定性指纹：路径 + 内容，排序后逐个吃进去。

    `only` 给一份相对路径清单，就只算这些文件。**必须给**：解出来的 overrides
    和后面下载的 480 个 jar 落在同一个目录下，整目录扫会把 jar 也算进指纹，
    于是「第一次跑过、第二次跑就报指纹不符」。

    ATM10 的某个已发布版本，它的 overrides 内容是**不会变**的。把指纹记进仓库，
    CI 上无论是从缓存拿的还是现下的，都要跟它对得上——CurseForge 哪天换了内容
    （或者下载被人动了手脚），构建当场红，而不是悄悄拿另一份东西去打补丁。
    """
    root = Path(root)
    if only is None:
        files = [p for p in root.rglob('*') if p.is_file()]
    else:
        files = [root / r for r in only]
    h = hashlib.sha256()
    for p in sorted(files):
        h.update(p.relative_to(root).as_posix().encode())
        h.update(b'\0')
        h.update(hashlib.sha256(p.read_bytes()).digest())
    return h.hexdigest()


def check_digest(ver, digest, record=False):
    """跟 versions/<版本>/overrides.sha256 对照；没记过就打印出来让人记上。

    `record=True` 时把指纹写进去——**只给「新版本首次入库」那条流水线用**。
    平时绝不能自动记：那等于把「下载被污染」变成「悄悄把污染当成基线」。
    写出来的文件仍然要人过目并提交，机器只负责算，不负责拍板。
    """
    f = Path(__file__).resolve().parent.parent / 'versions' / ver / 'overrides.sha256'
    if not f.is_file():
        if record:
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_text(digest + '\n', encoding='utf-8')
            print('  📝 已生成 versions/%s/overrides.sha256（需人工确认后提交）' % ver)
            return
        print('  ⚠️ versions/%s/overrides.sha256 还没记。确认这份没问题后写进去：' % ver)
        print('     echo %s > versions/%s/overrides.sha256' % (digest, ver))
        return
    want = f.read_text(encoding='utf-8').split()[0]
    if want != digest:
        sys.exit('❌ ATM10 %s 的 overrides 内容与仓库记录的指纹对不上\n'
                 '   记录 %s\n   实得 %s\n'
                 '   已发布版本的内容本不该变。要么 CurseForge 换了东西，要么这份下载不干净。\n'
                 '   人工核对无误后再更新 versions/%s/overrides.sha256。'
                 % (ver, want, digest, ver))
    print('  指纹与 versions/%s/overrides.sha256 一致 ✅' % ver)


def find_file_id(ver):
    d = json.loads(get('%s/files?pageSize=50' % API))
    for f in d['data']:
        if f['displayName'].rsplit('-', 1)[-1].strip() == ver:
            return f['id']
    have = sorted({f['displayName'].rsplit('-', 1)[-1].strip() for f in d['data']})
    sys.exit('❌ CurseForge 上找不到 ATM10 %s\n   最近 50 个文件里有: %s'
             % (ver, ' '.join(have)))


def site_file_name(project_id, file_id):
    """问 CurseForge 站点 API 要这个文件的真名（不需要 API key）。

    取不到就返回 None——宁可让外层报错，也别编一个假名字。
    """
    url = 'https://www.curseforge.com/api/v1/mods/%d/files/%d' % (project_id, file_id)
    try:
        req = urllib.request.Request(url, headers={'User-Agent': UA, 'Accept': 'application/json'})
        d = json.load(urllib.request.urlopen(req, timeout=15))
        return ((d.get('data') or {}).get('fileName')) or None
    except Exception:                                            # noqa: BLE001
        return None


def main(ver, out, jars=True, record=False):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    fid = find_file_id(ver)
    print('ATM10 %s → fileID %s' % (ver, fid))
    z = out.parent / ('atm10-%s.zip' % ver)
    if not z.exists():
        z.parent.mkdir(parents=True, exist_ok=True)
        z.write_bytes(get('%s/files/%s/download' % (API, fid)))
    rels = []
    with zipfile.ZipFile(z) as zf:
        manifest = json.loads(zf.read('manifest.json'))
        for n in zf.namelist():
            if n.startswith('overrides/') and not n.endswith('/'):
                rel = n[len('overrides/'):]
                t = out / rel
                t.parent.mkdir(parents=True, exist_ok=True)
                t.write_bytes(zf.read(n))
                rels.append(rel)
    digest = tree_digest(out, rels)
    print('  overrides 解出 %d 个文件，指纹 %s' % (len(rels), digest[:16]))
    check_digest(ver, digest, record)
    if not jars:
        return
    mods = out / 'mods'
    mods.mkdir(exist_ok=True)

    errors = []

    prov = {}

    def one(f):
        """下一个 jar。**不查元数据**——下载接口会跳转到带文件名的 CDN 地址，
        文件名直接从最终 URL 取。少一半请求，也少一个会 404 的接口。

        顺手把 (projectID, fileID, sha256, size) 记进 prov：CurseForge 的 fileID
        是不可变的（重传会得到新 ID），把它和实际字节的哈希绑在一起，才谈得上
        「这份 jar 就是那一版官方用的那一份」。只记文件名等于什么都没记。

        任何异常都不许抛：一个文件下不来只该少一个 jar，由外层整轮重试兜住；
        抛出去会顺着 ex.map 把整个构建炸掉。"""
        try:
            url = ('https://www.curseforge.com/api/v1/mods/%d/files/%d/download'
                   % (f['projectID'], f['fileID']))
            # 先用 HEAD 把跳转后的文件名问出来：本地已经有了就不必再拉一遍正文。
            # 少了这一步，补记出处就得把四百多个 jar 整包重下。
            name = head_name(url)
            p = mods / name if name else None
            if p is not None and p.exists():
                prov[name] = {'projectID': f['projectID'], 'fileID': f['fileID'],
                              'sha256': hashlib.sha256(p.read_bytes()).hexdigest(),
                              'size': p.stat().st_size}
                return name
            d, final = fetch(url, required=False)
            if not d or len(d) < 500:
                errors.append('fileID %d: %s' % (f['fileID'], final))
                return None
            got = urllib.parse.unquote(str(final).rsplit('/', 1)[-1].split('?')[0])
            if name and got != name:
                # 保险：同一个 fileID，HEAD 与 GET 报的文件名理应一致。
                # 对不上说明这次请求拿到的不是想要的那份，当失败交给外层重试，
                # 别把来路不明的文件收下。
                errors.append('fileID %d: 跳转文件名不一致 HEAD=%s GET=%s'
                              % (f['fileID'], name, got))
                return None
            name = got
            if not name.endswith('.jar'):
                # 跳转没带出文件名时，**别**编一个 `<fileID>.jar` 出来：manifest 的
                # files[] 里混着 mod / 资源包 / 光影包，改名成 .jar 会把光影包伪装成
                # mod 丢进 mods/（实测 fileID 8123287 = ComplementaryReimagined_r5.8.1.zip
                # 这么进过 mods/）。站点 API 能给真名，问它。
                name = site_file_name(f['projectID'], f['fileID']) or name
            # 分目录不靠名字猜，看 zip 里面有什么（确定性）：
            #   有 shaders/ → 光影包；有 pack.mcmeta → 资源包；否则当 mod
            if name.endswith('.jar'):
                p = mods / name
            else:
                try:
                    inner = zipfile.ZipFile(io.BytesIO(d)).namelist()
                except Exception:                                # noqa: BLE001
                    inner = []
                sub = ('shaderpacks' if any(x.startswith('shaders/') for x in inner)
                       else 'resourcepacks' if any(x == 'pack.mcmeta' for x in inner)
                       else 'mods')
                (mods.parent / sub).mkdir(parents=True, exist_ok=True)
                p = mods.parent / sub / name
            if not p.exists():
                p.write_bytes(d)
            prov[name] = {'projectID': f['projectID'], 'fileID': f['fileID'],
                          'sha256': hashlib.sha256(p.read_bytes()).hexdigest(),
                          'size': p.stat().st_size}
            return name
        except Exception as e:
            errors.append('fileID %d: %r' % (f['fileID'], e))
        return None

    todo = manifest['files']
    got = {}
    for rnd in range(3):                      # 整轮重来，专收被限速漏掉的
        left = [f for f in todo if f['fileID'] not in got]
        if not left:
            break
        if rnd:
            print('  第 %d 轮补下 %d 个（上一轮被限速）' % (rnd + 1, len(left)))
            time.sleep(20)
        with cf.ThreadPoolExecutor(4) as ex:
            for i, (f, r) in enumerate(zip(left, ex.map(one, left)), 1):
                if r:
                    got[f['fileID']] = r
                if i % 50 == 0:
                    print('  jar %d/%d' % (i, len(left)), flush=True)
    print('  mod jar %d/%d，目录共 %d 个'
          % (len(got), len(todo), len(list(mods.glob('*.jar')))))
    # manifest 里应有多少个必须一起记下来。少下了几个而不留痕，
    # 后面建出来的版本库会拿一个残缺的 jar 集合去下「这一版没有这个 key」的结论。
    for r in rels:
        if r.startswith('mods/') and r.endswith('.jar'):
            f = out / r
            prov.setdefault(f.name, {
                'source': 'overrides',
                'sha256': hashlib.sha256(f.read_bytes()).hexdigest(),
                'size': f.stat().st_size})
    missing = sorted(f['fileID'] for f in todo if f['fileID'] not in got)
    (out / 'mods.provenance.json').write_text(
        json.dumps({'version': ver, 'expected': len(todo), 'got': len(prov),
                    'missing_file_ids': missing,
                    'jars': dict(sorted(prov.items()))},
                   ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    print('  出处已记入 mods.provenance.json（fileID ↔ sha256，%d/%d）'
          % (len(prov), len(todo)))
    # 目录里出现了对不上任何 fileID 的 jar，就是来路不明的（多半是某次
    # 跳转指错文件留下的）。留着它会污染整个集合，必须点名。
    stray = sorted(p.name for p in mods.glob('*.jar') if p.name not in prov)
    if stray:
        print('  ⚠️ %d 个 jar 对不上任何 fileID，来路不明，建库前必须处理：' % len(stray))
        for x in stray:
            print('       %s' % x)
    # 一个都不许缺。以前的阈值是 98%：482 项里少 9 个照样继续，而少掉的那几个 jar
    # 里的 en_us / 注册表就这么静默地没参与生成——产物少几百条译文，退出码还是 0。
    # 「大部分下到了」不是可复现构建，缺就是缺。（issue #9 P1-5）
    # 唯一的例外：这一版的 manifest 里确有文件被 CurseForge 永久删除（404，重试无用）。
    # 那不是「下漏了」，是这一版的官方集合**已经拿不全了**，而且必须一个个登记在
    # versions/<版本>/unobtainable.json 里才算数——登记过的照常放行，没登记的照旧红。
    # 缺口的边界因此始终摆在明面上，而不是藏在一次静默的下载失败里。
    # （build_version_db.py 建库时读的是同一份登记，两边的判据是同一个。）
    known = {}
    kf = ROOT / 'versions' / ver / 'unobtainable.json'
    if kf.is_file():
        known = json.loads(kf.read_text(encoding='utf-8')).get('files') or {}
    undeclared = [i for i in missing if str(i) not in known]
    if undeclared:
        for e in errors[:8]:
            print('   %s' % e)
        sys.exit('❌ jar 没下齐（%d/%d），其中以下 fileID 没有登记原因：%s\n'
                 '   生成器会漏内容，中止。上面是前几条真实错误。\n'
                 '   403/429 是限速，稍后重跑；404 若是这一版真的被删了，'
                 '写进 versions/%s/unobtainable.json 说明情况。'
                 % (len(got), len(todo), undeclared[:8], ver))
    if missing:
        print('  ⚠️ 这一版有 %d 个 jar 已在 CurseForge 上取不到（已登记）：%s'
              % (len(missing), missing))


if __name__ == '__main__':
    # --verify：目录已经在（多半来自 CI 缓存），只核对指纹，一个字节都不下。
    # 缓存命中也必须核——缓存里的东西同样可能是坏的。
    if '--verify' in sys.argv:
        a = [x for x in sys.argv[1:] if x != '--verify']
        if len(a) != 2:
            sys.exit(__doc__)
        d = Path(a[1])
        # 排除的只有「按 manifest 下载的 jar」与出处文件本身。
        # **不能一刀切排除 mods/**：整合包自己的 overrides 里就可能带 jar
        # （ATM10 7.2 在 overrides/mods/ 放了 cc-tweaked 1.120.0 去盖掉 manifest
        # 里那个会崩的 1.113.1），那是指纹的正当组成部分。
        skip = {'mods.provenance.json'}
        pf = d / 'mods.provenance.json'
        if pf.is_file():
            for n, v in (json.loads(pf.read_text(encoding='utf-8')).get('jars')
                         or {}).items():
                if v.get('fileID'):
                    skip.add('mods/' + n)
        rels = [r for r in (p.relative_to(d).as_posix() for p in d.rglob('*')
                            if p.is_file()) if r not in skip]
        check_digest(a[0], tree_digest(d, rels))
        sys.exit(0)
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    main(sys.argv[1], sys.argv[2], '--no-jars' not in sys.argv,
         '--record' in sys.argv)
