#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# atm10-zh-cn — All the Mods 10 简体中文汉化补丁「绿油油版」
# Copyright (C) 2026 星野夢華 (Hoshino Yumeka)
# SPDX-License-Identifier: GPL-3.0-or-later
"""把某个版本的 ATM10 整合包下载成可当 ATM_PACK_ROOT 用的目录。

- `--no-jars`：只解 `overrides/`，里面有打补丁用的官方文件（ATM 的 kubejs/*.js、config/*.json），
  每个目标版本都要一份。
- 全量：再按 manifest 下载 480 个 mod jar。只有读 jar 里 en_us 与注册表的生成器需要（奖杯名、
  木头名、蜂名、格式串快照），一次构建取最新版即可。

CurseForge 的网页 API 会限速：默认 UA 会被拦截，所以伪装成浏览器。并发 4，失败按指数退避重试，
整轮重来补漏。不查元数据，直接下载并从跳转后的 CDN 地址取文件名。下载失败时打印真实的 HTTP 错误，
以区分限速与接口变化。

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


def unregistered_missing(ver, missing):
    """下载失败的 fileID 里，哪些没在 versions/<版本>/unobtainable.json 登记。

    CurseForge 删过文件，有些版本的官方 jar 永久拿不全。残缺的集合会让版本库里的 "missing"
    分不清是这一版没有这个 key，还是没下载到 jar，所以要逐个登记：登记过的放行，其余失败。
    登记文件不存在时一条都不放行。fetch_pack 与 build_version_db 共用这个函数。
    """
    known = {}
    kf = ROOT / 'versions' / ver / 'unobtainable.json'
    if kf.is_file():
        known = json.loads(kf.read_text(encoding='utf-8')).get('files') or {}
    return [i for i in missing if str(i) not in known]


def fetch(url, timeout=180, required=True):
    """取一个 URL，返回 (内容, 最终URL)。限速或偶发失败时退避重试。

    失败原因必须保留，否则只看得到 jar 下得太少，分不清是限速、403 还是 404。
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

    要重试：GET 的跳转偶尔会指到别的文件（cc-tweaked 1.113.1 的 ID 拿回过 1.120.0），文件名用来
    交叉验证。探不到就返回 None，调用方照常下载，但会把那一份记为来源不明。
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
    """overrides 的确定性指纹：路径与内容，排序后逐个计入。

    `only` 是相对路径清单，必须给：overrides 和下载的 480 个 jar 在同一个目录下，整目录扫描会把 jar
    也算进去，第二次运行就会报指纹不符。

    已发布版本的 overrides 不会变。指纹记在仓库里，CI 无论用缓存还是重新下载都要与它一致，
    CurseForge 换了内容或下载被篡改时构建失败。
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
    """与 versions/<版本>/overrides.sha256 对照，没记录过就打印出来。

    `record=True` 时写入指纹，只用于新版本首次入库的流水线：平时自动写入的话，被污染的下载会变成基线。
    写出的文件仍要人核对后提交。
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
    """问 CurseForge 站点 API 这个文件的真实文件名（不需要 API key），取不到返回 None。"""
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
        """下载一个 jar。不查元数据，下载接口会跳转到带文件名的 CDN 地址，文件名从最终 URL 取。

        同时把 (projectID, fileID, sha256, size) 记进 prov：CurseForge 的 fileID 不可变（重传会得到
        新 ID），与字节哈希绑定，才能证明这份 jar 就是那一版官方用的那份。

        不抛异常：下载失败只少一个 jar，由外层整轮重试处理，抛出去会让 ex.map 中断整个构建。"""
        try:
            url = ('https://www.curseforge.com/api/v1/mods/%d/files/%d/download'
                   % (f['projectID'], f['fileID']))
            # 先用 HEAD 问出跳转后的文件名：本地已有就不再下载正文，补记来源时不用重下四百多个 jar。
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
                # 同一个 fileID，HEAD 与 GET 报的文件名应该一致。不一致说明拿到的不是想要的那份，
                # 当失败交给外层重试。
                errors.append('fileID %d: 跳转文件名不一致 HEAD=%s GET=%s'
                              % (f['fileID'], name, got))
                return None
            name = got
            if not name.endswith('.jar'):
                # 跳转没带出文件名时不能编 `<fileID>.jar`：manifest 的 files[] 里有 mod、资源包、光影包，
                # 改名成 .jar 会把光影包当成 mod 放进 mods/（fileID 8123287 =
                # ComplementaryReimagined_r5.8.1.zip）。向站点 API 查询真实文件名。
                name = site_file_name(f['projectID'], f['fileID']) or name
            # 按 zip 里的内容分目录：有 shaders/ 是光影包，有 pack.mcmeta 是资源包，否则是 mod
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
    # 一并记下 manifest 里应有多少个：少下载了却没有记录，版本库会基于残缺的 jar 集合下结论。
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
    # 对不上任何 fileID 的 jar 来源不明（多半是跳转指错文件留下的），必须列出来。
    stray = sorted(p.name for p in mods.glob('*.jar') if p.name not in prov)
    if stray:
        print('  ⚠️ %d 个 jar 对不上任何 fileID，来路不明，建库前必须处理：' % len(stray))
        for x in stray:
            print('       %s' % x)
    # 一个都不许缺（issue #9 P1-5）：缺了的 jar 里的 en_us 和注册表不参与生成，产物少几百条译文，
    # 退出码却是 0。唯一的例外是 manifest 里有文件被 CurseForge 永久删除（404，重试无用），
    # 必须逐个登记在 versions/<版本>/unobtainable.json 才放行。build_version_db.py 读同一份登记。
    undeclared = unregistered_missing(ver, missing)
    if undeclared:
        for e in errors[:8]:
            print('   %s' % e)
        sys.exit('❌ jar 没下齐（%d/%d），其中以下 fileID 没有登记原因：%s\n'
                 '   生成器会漏内容，中止。上面是前几条真实错误。\n'
                 '   403/429 是限速，稍后重跑。404 如果是这一版确实被删了，'
                 '写进 versions/%s/unobtainable.json 说明情况。'
                 % (len(got), len(todo), undeclared[:8], ver))
    if missing:
        print('  ⚠️ 这一版有 %d 个 jar 已在 CurseForge 上取不到（已登记）：%s'
              % (len(missing), missing))


if __name__ == '__main__':
    # --verify：目录已存在（多半来自 CI 缓存），只核对指纹，不下载。缓存同样可能是坏的。
    if '--verify' in sys.argv:
        a = [x for x in sys.argv[1:] if x != '--verify']
        if len(a) != 2:
            sys.exit(__doc__)
        d = Path(a[1])
        # 只排除按 manifest 下载的 jar 与来源记录文件本身，不能排除整个 mods/：
        # 整合包的 overrides 里也可能带 jar（ATM10 7.2 在 overrides/mods/ 放了 cc-tweaked 1.120.0，
        # 替换 manifest 里会崩溃的 1.113.1），它们属于指纹的一部分。
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
