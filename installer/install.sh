#!/usr/bin/env bash
# atm10-zh-cn — All the Mods 10 简体中文汉化补丁「绿油油版」
# Copyright (C) 2026 星野夢華 (Hoshino Yumeka)
# SPDX-License-Identifier: GPL-3.0-or-later
# ATM10 @@MCVER@@ 汉化补丁「绿油油版」安装器 (macOS / Linux)
# 版本号一律用 @@MCVER@@ 占位，由 scripts/build_dist.sh 按目标整合包版本填。
# 写死一个版本号的话，7.0 / 7.1 的包里会印着「ATM10 7.2」——三个包里两个是错的。
# 用法：把整个汉化文件夹放进 ATM10 实例根目录后运行：
#   bash install.sh                    # 交互菜单
#   bash install.sh apply              # 应用汉化（自动先备份，不含可选mods）
#   bash install.sh apply-with-pinyin  # 应用汉化 + 安装可选 JEI 拼音搜索 mod
#   bash install.sh backup             # 仅备份
#   bash install.sh restore [备份名]   # 恢复备份
#   bash install.sh update             # 一键下载最新正式版并更新（与 install.ps1 同一套流程）
set -euo pipefail
cd "$(dirname "$0")"
SCRIPT_DIR="$(pwd)"
TARGET="$(cd .. && pwd)"
PACK_DIRS="config kubejs mods resourcepacks vaultpatcher"
PACK_ENTRY='file/ATM10汉化包-@@MCVER@@.zip'
PINYIN_DIR="可选mods-拼音搜索"
TS=""
BK=""
# 就地解压：用户把压缩包内容直接解到实例根目录，源与目标同一层，
# 再复制一次就是自己覆盖自己。这种情况文件本来就已到位。
IN_PLACE=0

say() { printf '%s\n' "$*"; }

# ── 版本检查 ────────────────────────────────────────────────────────────
# 补丁自己的版本号，由 build_dist.sh 现填（写死的话每次发版都得记得改，必然忘）。
PATCH_VER="@@PATCHVER@@"
REPO="chiba233/atm10-zh-cn"

# 取仓库最新**正式版**的 tag。GitHub 的 releases/latest 天然跳过预发布，
# 正合用：测试版不该被当成「最新版」去催人升级。
# 任何一步不成（没网、没 curl/wget、被限流、返回不是 JSON）都返回空，
# **绝不因此拦住安装**——用户是来装汉化的，不是来做联网检测的。
RELEASE_JSON=""
LATEST_TAG=""

# 整份 Release JSON 只取一次：版本检查要 tag_name，一键更新还要 assets 里的
# 下载地址与 sha256，两处共用同一份，免得同一个请求发两遍。
fetch_latest_release() {
  [ "${ATM_SKIP_UPDATE_CHECK:-0}" = "1" ] && return 0
  [ -n "$RELEASE_JSON" ] && return 0
  url="https://api.github.com/repos/${REPO}/releases/latest"
  if command -v curl >/dev/null 2>&1; then
    RELEASE_JSON="$(curl -fsSL --max-time 6 -H 'Accept: application/vnd.github+json' "$url" 2>/dev/null || true)"
  elif command -v wget >/dev/null 2>&1; then
    RELEASE_JSON="$(wget -qO- --timeout=6 "$url" 2>/dev/null || true)"
  fi
  [ -n "$RELEASE_JSON" ] || return 0
  LATEST_TAG="$(printf '%s' "$RELEASE_JSON" \
    | sed -n 's/.*"tag_name"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' | head -1)"
  return 0
}

# ⚠️ 这个函数只能拿它的**输出**，不能靠它给 LATEST_TAG / RELEASE_JSON 赋值：
# 调用方一写成 `x="$(latest_tag)"`，命令替换就开了子 shell，里面的赋值回不到父进程。
# check_update 曾经这么用，结果菜单里的 [u] 一键更新从 vr12 起就没显示过。
# 需要那两个全局变量的地方，直接调 fetch_latest_release。
latest_tag() {
  fetch_latest_release
  [ -n "$LATEST_TAG" ] && printf '%s' "$LATEST_TAG"
  return 0
}

# 比较时把开头的 v 去掉：tag 是 vr12，包里记的是 r12
norm_ver() { printf '%s' "${1#v}"; }

check_update() {
  [ "${ATM_SKIP_UPDATE_CHECK:-0}" = "1" ] && return 0
  is_beta=0
  case "$PATCH_VER" in *[Bb][Ee][Tt][Aa]*|*[Rr][Cc][0-9]*|dev|DEV) is_beta=1 ;; esac

  # 直接调，不要写成 latest="$(latest_tag)"：命令替换开子 shell，
  # LATEST_TAG 赋不到父进程，随后菜单里的 has_update 就永远为假。
  fetch_latest_release
  latest="$LATEST_TAG"
  if [ "$is_beta" = "1" ]; then
    say ""
    say "⚠️ 你装的是**测试版**：$PATCH_VER"
    say "   测试版可能有没发现的问题。遇到异常请提交 issue："
    say "   https://github.com/${REPO}/issues"
    [ -n "$latest" ] && say "   在问题解决前，建议先切回正式版 ${latest}：" \
                     && say "   https://github.com/${REPO}/releases/latest"
    say ""
    return 0
  fi

  [ -n "$latest" ] || return 0        # 查不到就当没这回事
  if [ "$(norm_ver "$latest")" = "$(norm_ver "$PATCH_VER")" ]; then
    say "✓ 版本检查：$PATCH_VER 已是最新正式版"
  else
    say ""
    say "⚠️ 你装的不是最新版本"
    say "   当前包：$PATCH_VER      最新正式版：$latest"
    say "   建议先下最新版再装，老版本的已知问题不会再修："
    say "   https://github.com/${REPO}/releases/latest"
    say ""
  fi
}

# 判定一个目录是不是游戏实例根目录。
# 不能只看 options.txt —— **刚装好、一次都没启动过的整合包没有 options.txt**
# （它是 Minecraft 首次退出时才写的）。也不能只看 mods/ —— 汉化包自己的文件夹里
# 也有个 mods/（装着 vaultpatcher.jar）。用 jar 数量区分：ATM10 有 400+ 个，汉化包只有 1 个。
# ── 一键更新 ────────────────────────────────────────────────────────────
# 与 install.ps1 的 Invoke-OneClickUpdate 是同一套流程，逐步对齐：
# 选 asset → 校验 sha256 → 解包 → 由新版安装器 apply → 归并备份 → 更新源目录。
# 以前这套只有 Windows 有，两个安装器行为分叉；这里把 shell 这侧补齐。

has_update() {
  [ -n "$LATEST_TAG" ] || return 1
  [ "$(norm_ver "$LATEST_TAG")" != "$(norm_ver "$PATCH_VER")" ]
}

sha256_of() {
  if command -v shasum >/dev/null 2>&1; then
    shasum -a 256 "$1" 2>/dev/null | cut -d' ' -f1
  elif command -v sha256sum >/dev/null 2>&1; then
    sha256sum "$1" 2>/dev/null | cut -d' ' -f1
  else
    return 1
  fi
}

# Release 里同时挂着 7.0/7.1/7.2 三个 ATM 版本 × 客户端/服务端共六个包。
# 必须按**本包的 ATM 版本**精确挑客户端 zip——取第一个 asset 会把 7.0 用户升到 7.2。
# 输出三行：文件名 / 下载地址 / sha256；挑不到或没有摘要就返回 1。
pick_client_asset() {
  flat="$(printf '%s' "$RELEASE_JSON" | tr '\n' ' ')"
  # 从我们要的那个 name 开始截到行尾。GitHub 的 asset 对象里字段顺序是
  # name → …uploader{}… → digest → browser_download_url，所以截断之后
  # **第一个** digest / browser_download_url 就是这个 asset 自己的。
  name="$(printf '%s' "$flat" \
    | grep -o '"atm10-zh_cn-client-[^"]*-atm@@MCVER@@\.zip"' | head -1 | tr -d '"')"
  [ -n "$name" ] || return 1
  after="${flat#*\"$name\"}"
  url="$(printf '%s' "$after" \
    | grep -o '"browser_download_url"[[:space:]]*:[[:space:]]*"[^"]*"' | head -1 \
    | sed 's/.*"\([^"]*\)"$/\1/')"
  sha="$(printf '%s' "$after" \
    | grep -o '"digest"[[:space:]]*:[[:space:]]*"sha256:[0-9a-fA-F]\{64\}"' | head -1 \
    | sed 's/.*sha256:\([0-9a-fA-F]*\)"$/\1/')"
  [ -n "$url" ] && [ -n "$sha" ] || return 1
  printf '%s\n%s\n%s\n' "$name" "$url" "$sha"
}

# 新版安装器把备份写在它自己的目录里，而用户日后仍然从原目录运行 restore。
# 更新成功后必须把备份归并回原入口，否则回滚功能等于没了。
merge_update_backups() {
  from="$1/backups"
  [ -d "$from" ] || return 0
  to="$SCRIPT_DIR/backups"
  mkdir -p "$to"
  for b in "$from"/*; do
    [ -d "$b" ] || continue
    dest="$to/$(basename "$b")"
    n=1
    while [ -e "$dest" ]; do
      dest="$to/$(basename "$b")-update-$n"
      n=$((n + 1))
    done
    mv "$b" "$dest"
  done
}

# 用户今后还会运行最初解压出来的这个 install.sh。只更新游戏实例而不更新源目录，
# 下次跑旧脚本会再提示升级，甚至把旧 payload 覆盖回去。
# 就地解压时源目录就是实例，新版安装器刚刚已经覆盖过 payload，绝不能删。
update_source_package() {
  newdir="$1"
  if [ "$IN_PLACE" != "1" ]; then
    for d in $PACK_DIRS "$PINYIN_DIR"; do
      [ -d "$SCRIPT_DIR/$d" ] && rm -rf "$SCRIPT_DIR/$d"
      [ -d "$newdir/$d" ] && cp -R "$newdir/$d" "$SCRIPT_DIR/$d"
    done
  fi
  # bash 是**边读边执行**的：直接覆盖正在跑的这个文件会让它读到一半错位。
  # 所以先写到临时文件再原子替换（mv 换的是目录项，当前进程的 fd 仍指向老 inode）。
  for f in install.sh install.ps1 双击安装-Windows.bat install-windows.bat; do
    [ -f "$newdir/$f" ] || continue
    cp "$newdir/$f" "$SCRIPT_DIR/.$f.new"
    mv "$SCRIPT_DIR/.$f.new" "$SCRIPT_DIR/$f"
  done
  chmod +x "$SCRIPT_DIR/install.sh" 2>/dev/null || true
  say "✅ 已将原安装包更新为新版；以后继续运行原来的 install.sh 即可。"
}

do_update() {
  fetch_latest_release
  if [ -z "$RELEASE_JSON" ]; then
    say "❌ 无法获取最新版信息，请检查网络后重试。"
    return 0
  fi
  if ! has_update; then
    say "✓ $PATCH_VER 已是最新正式版，无需更新。"
    return 0
  fi
  for t in unzip; do
    command -v "$t" >/dev/null 2>&1 || {
      say "❌ 系统里没有 ${t}，无法解包。请手动到 Releases 下载新版："
      say "   https://github.com/${REPO}/releases/latest"
      return 0; }
  done
  if ! command -v shasum >/dev/null 2>&1 && ! command -v sha256sum >/dev/null 2>&1; then
    # 没法校验就**不装**：这包解压出来是要直接执行的，比大小/凭运气都不算数
    say "❌ 系统里没有 shasum / sha256sum，无法校验下载文件，拒绝自动更新。"
    say "   请手动到 Releases 下载新版：https://github.com/${REPO}/releases/latest"
    return 0
  fi

  asset="$(pick_client_asset || true)"
  if [ -z "$asset" ]; then
    say "❌ 最新版 $LATEST_TAG 没有 ATM10 @@MCVER@@ 的客户端安装包（或缺少 SHA-256 摘要），未做任何改动。"
    return 0
  fi
  name="$(printf '%s' "$asset" | sed -n '1p')"
  url="$(printf '%s'  "$asset" | sed -n '2p')"
  want="$(printf '%s' "$asset" | sed -n '3p')"

  stamp="$(date +%Y%m%d-%H%M%S)"
  stage="$TARGET/.atm10-hanhua-update-$stamp"
  zipf="$stage/$name"
  started=0; installed=0; merged=0; newdir=""
  mkdir -p "$stage"

  # ⚠️ 变量后面紧跟中文时必须写 ${var}：在单字节 Latin 语言环境下（CI 容器常见 LANG=C），
  # bash 会把 UTF-8 的头字节当成标识符的一部分，`$name……` 变成 `$nameâ` → unbound variable。
  say "正在下载 ${name}……"
  ok=1
  if command -v curl >/dev/null 2>&1; then
    curl -fsSL --max-time 300 -H 'User-Agent: atm10-zh-cn-installer' -o "$zipf" "$url" || ok=0
  else
    wget -q --timeout=300 -O "$zipf" "$url" || ok=0
  fi
  if [ "$ok" != "1" ] || [ ! -s "$zipf" ]; then
    say "❌ 一键更新失败：下载失败。"
    say "   新版安装器尚未启动；已下载的临时文件（如有）保留在：$stage"
    return 0
  fi

  got="$(sha256_of "$zipf" || true)"
  if [ -z "$got" ] || [ "$(printf '%s' "$got" | tr 'A-Z' 'a-z')" != "$(printf '%s' "$want" | tr 'A-Z' 'a-z')" ]; then
    say "❌ 一键更新失败：下载文件的 SHA-256 与 GitHub Release 摘要不一致。"
    say "   期望 $want"
    say "   实际 ${got:-（算不出来）}"
    say "   新版安装器尚未启动；文件保留在：$stage"
    return 0
  fi

  unzip -q -o "$zipf" -d "$stage" || {
    say "❌ 一键更新失败：解包失败。"
    say "   新版安装器尚未启动；文件保留在：$stage"
    return 0; }
  newdir="$(find "$stage" -type d -name 'atm10-zh_cn-client' 2>/dev/null | head -1 || true)"
  if [ -z "$newdir" ] || [ ! -f "$newdir/install.sh" ]; then
    say "❌ 一键更新失败：下载包中没有预期的客户端安装器。"
    say "   新版安装器尚未启动；文件保留在：$stage"
    return 0
  fi

  say "下载完成，正在由新版安装器备份并应用汉化……"
  started=1
  if ATM_TARGET="$TARGET" bash "$newdir/install.sh" apply; then
    installed=1
  fi
  if [ "$installed" != "1" ]; then
    say "❌ 一键更新失败：新版安装器返回非零退出码。"
    say "   新版安装器已经启动，实例可能只完成了部分更新。"
    say "   请先用新版安装器的 restore 功能恢复本次备份：$newdir/backups"
    return 0
  fi
  merge_update_backups "$newdir"; merged=1
  update_source_package "$newdir"
  say "✅ 已更新到 ${LATEST_TAG}。新版安装器保留在：$stage"
  say "   本次备份已归入原安装包：$SCRIPT_DIR/backups"
  say "   请退出并重新启动游戏后生效；确认无误前不要删除该目录。"
}

is_instance() {
  [ -d "$1/mods" ] || return 1
  [ -f "$1/options.txt" ] && return 0
  n=$(ls "$1"/mods/*.jar 2>/dev/null | wc -l | tr -d ' ')
  [ "${n:-0}" -ge 20 ]
}

set_in_place() {
  if [ "$(cd "$SCRIPT_DIR" && pwd -P)" = "$(cd "$TARGET" && pwd -P)" ]; then
    IN_PLACE=1
    say "ℹ️ 检测到汉化文件已经在实例根目录里（压缩包内容被直接解压到了这一层）。"
    say "   文件本来就已到位，无需复制；本次只做 options.txt 的资源包启用。"
    say "   ⚠️ 这种装法没有备份可回退——原文件在你解压覆盖的那一刻就没了。"
    say "   想要可回退的安装，请解压到别处、把整个文件夹放进实例根目录再运行安装器。"
  fi
}

check_target() {
  # 一键更新时，新版安装器是从 <实例>/.atm10-hanhua-update-*/ 里被调起来的，
  # 它的上一级目录不是实例。用这个环境变量把目标传进去（对应 ps1 的 -TargetPath）。
  if [ -n "${ATM_TARGET:-}" ] && is_instance "${ATM_TARGET}"; then
    TARGET="${ATM_TARGET%/}"
    set_in_place
    return
  fi
  if is_instance "$TARGET"; then
    set_in_place
    return
  fi
  # 就地解压：脚本自己所在的这一层就是实例根目录
  if is_instance "$SCRIPT_DIR"; then
    TARGET="$SCRIPT_DIR"
    set_in_place
    return
  fi
  say "⚠️ 上一级目录不是游戏实例根目录（含 mods/ 的那一层）。"
  if [ -t 0 ]; then
    while :; do
      printf '请输入 ATM10 实例根目录完整路径（q 退出）: '
      read -r inp || exit 1
      [ "$inp" = "q" ] && exit 1
      # 清洗输入：复制/粘贴/拖拽常带成对引号或反斜杠转义空格
      case "$inp" in
        \"*\") inp="${inp#\"}"; inp="${inp%\"}" ;;
        \'*\') inp="${inp#\'}"; inp="${inp%\'}" ;;
      esac
      case "$inp" in *\\*) inp="$(printf '%s' "$inp" | sed 's/\\\(.\)/\1/g')" ;; esac
      inp="${inp%/}"
      case "$inp" in "~"*) inp="$HOME${inp#\~}" ;; esac
      if is_instance "$inp"; then
        TARGET="$inp"
        say "✅ 目标实例: $TARGET"
        set_in_place
        return
      fi
      say "❌ 该路径下没找到 ATM10 的 mods/（应该有几百个 .jar），请重试。"
    done
  fi
  say "   请把整个汉化文件夹放进实例根目录（含 mods/ 的那一层）后再运行本脚本。"
  exit 1
}

payload_files() {
  for d in $PACK_DIRS; do
    [ -d "$d" ] && find "$d" -type f ! -name '.DS_Store'
  done
}

do_backup() {
  if [ "$IN_PLACE" = "1" ]; then
    say "⚠️ 就地解压模式下没有可备份的原文件（已被解压覆盖），跳过备份。"
    return
  fi
  # 备份是**覆盖**式写入：同一秒里装第二次会撞上同一个目录，于是第二次备份的是
  # 已经汉化过的文件，把第一次那份原文盖掉，玩家的回退数据就没了。
  # 撞上就往后加序号，绝不复用已存在的目录。
  TS="$(date +%Y%m%d-%H%M%S)"
  # 序号补零：do_restore 默认取 `ls -1 | tail -1`（字典序最后）当「最近一次」，
  # 不补零的话 -10 会排在 -2 前面，默认就挑错了。
  if [ -e "$SCRIPT_DIR/backups/$TS" ]; then
    i=2
    while [ -e "$SCRIPT_DIR/backups/$(printf '%s-%02d' "$TS" "$i")" ]; do i=$((i + 1)); done
    TS="$(printf '%s-%02d' "$TS" "$i")"
  fi
  BK="$SCRIPT_DIR/backups/$TS"
  mkdir -p "$BK"
  n=0
  while IFS= read -r f; do
    if [ -f "$TARGET/$f" ]; then
      mkdir -p "$BK/$(dirname "$f")"
      cp -p "$TARGET/$f" "$BK/$f"
      n=$((n + 1))
    else
      printf '%s\n' "$f" >> "$BK/新增文件清单.txt"
    fi
  done < <(payload_files)
  [ -f "$TARGET/options.txt" ] && cp -p "$TARGET/options.txt" "$BK/options.txt"
  say "✅ 已备份 $n 个将被覆盖的文件到 backups/$TS/"
}

##
# 清理本补丁旧版本（v7.2-release8 之前）遗留的文件。
#
# 那之前本包的任务书 delta 用的是 `<章节名>.snbt`，与整合包自带的同名文件**撞名**，
# 安装时直接覆盖 —— 整合包那一章上百条翻译当场没了，任务书变英文。
# （已经启动过的实例看不出来：整合包那批早合并完并改名成 .snbt_merged 了。）
#
# 现在统一加 zz_hanhua_ 前缀，不会再撞名。这里把旧名字的残留删掉，
# 且只在**内容与本包同名新文件逐字节相同**时才删 —— 这样能确定它是本包的旧产物，
# 绝不会误删整合包自己的文件。
# r14 之前的版本往实例里装过 CC: Tweaked 的中文 help 文档
# （kubejs/data/computercraft/lua/rom/help/，97 个 .txt）。
# 那是个方向性错误：CC 的终端用自带的 term_font.png——256 个字形、没有汉字，
# 中文进去整屏乱码。新版已经不再生成这些文件，但安装器只覆盖不删除，
# 旧文件会一直留在玩家盘上，于是"装了新版还是乱码"。这里主动清掉。
clean_legacy_cc_help() {
  # 只认这一个目录：旧版本就是往 lua/rom/help/ 里放译好的 .txt，别的地方一律不碰。
  # 旧代码是 `find "$TARGET/kubejs/data/computercraft" -name '*.txt' -delete`——
  # 整棵树、不看内容、不进备份。玩家自己放在那底下的 .txt（CC 程序的数据文件、
  # 别的补丁的东西）会**永久消失**，restore 也拿不回来，因为 do_backup 只枚举
  # 当前 payload，而这些文件早就不在 payload 里了。（issue #9 P1-1）
  CCD="$TARGET/kubejs/data/computercraft/lua/rom/help"
  [ -d "$CCD" ] || return 0
  # `|| true`：set -euo pipefail 下 find 一旦非零退出（例如有不可读子目录），
  # 这个赋值就会让安装器**静默退出**，什么都不打印。
  LIST=$(find "$CCD" -name '*.txt' -type f 2>/dev/null || true)
  [ -n "$LIST" ] || return 0
  hit=0
  while IFS= read -r f; do
    [ -f "$f" ] || continue
    # 判据：文件里有非 ASCII 字节。我们发的是中译本，CC 自带的 help 全是英文；
    # 纯 ASCII 的一律不动。万一还是判错，下面已经先备份了，restore 能拿回来。
    LC_ALL=C tr -d '\000-\177' < "$f" 2>/dev/null | LC_ALL=C grep -q . || continue
    rel="${f#"$TARGET"/}"
    if [ -n "${BK:-}" ] && [ -d "$BK" ]; then
      mkdir -p "$BK/$(dirname "$rel")"
      cp -p "$f" "$BK/$rel" 2>/dev/null || true
    fi
    rm -f "$f"
    hit=$((hit + 1))
  done <<EOF
$LIST
EOF
  [ "$hit" -gt 0 ] || return 0
  # 自底向上删空目录；非空的一律留着
  find "$CCD" -depth -type d -empty -exec rmdir {} + 2>/dev/null || true
  say "🧹 清理了旧版本装进去的 CC: Tweaked 中文 help 文档（$hit 个文件，已备份）。"
  say "   CC 的终端只有 256 个自带字形、没有汉字，中文在那里必然是乱码，"
  say "   所以这部分改回英文——这是终端本身的限制，不是漏翻。"
}

# r14 发过「模组配置界面汉化」那两个 VaultPatcher 模块（合计 2232 条），本版起不再发。
# 它们是 dynamic 模块，而 VaultPatcher 的 dynamic 表是**全局的、每次替换调用都要线性扫一遍**
# 的全局开销——留在盘上就等于全场景掉帧照旧，装了新版也修不掉。安装器只覆盖不删除，
# 所以必须在这里主动清掉。
clean_legacy_config_ui() {
  VPM="$TARGET/vaultpatcher/modules"
  [ -d "$VPM" ] || return 0
  hit=0
  for f in config_ui_generated.json catnip_config_ui.json; do
    if [ -f "$VPM/$f" ]; then
      # 这两个文件不在 payload 里，do_backup 不会备份它们——删掉就永久没了，
      # restore 也拿不回来。所以这里自己塞进本次备份目录（就地解压模式没有备份，
      # 那条路本来就无从回退，见 do_apply 的提示）。
      if [ -n "${BK:-}" ] && [ -d "$BK" ]; then
        mkdir -p "$BK/vaultpatcher/modules"
        cp -p "$VPM/$f" "$BK/vaultpatcher/modules/$f" 2>/dev/null || true
      fi
      rm -f "$VPM/$f"
      hit=$((hit + 1))
    fi
  done
  if [ "$hit" -gt 0 ]; then
    say "🧹 清理了 $hit 个 r14 装进去的配置界面汉化模块。"
    say "   那套替换表是全局开销（全局的，表越大越慢），留着会掉帧；"
    say "   代价是 Create 及其附属的配置界面回到英文（只有它们用这套界面）。"
  fi
}

# 旧命名（r13 及更早的 `<章节>.snbt` / `_<章节>.snbt`）留在玩家盘上的任务书语言文件。
#
# **payload 里有同名文件的一律不碰。** gen_quest_lang_patches.py 现在会为每个
# `zz_hanhua_X.snbt` 一并发出 `X.snbt`（上游全文 + 我们的覆盖）和 `_X.snbt`（空壳），
# 复制那一步就把它们盖掉了——覆盖比删除彻底，也不会误伤。
#
# 不加这个判断会怎样：payload 自己发的 4 字节空壳 `_X.snbt` 与 `zz_hanhua_X.snbt`
# 内容一模一样，`cmp -s` 必然相等 → 每次安装都「删掉上次装的、再抄回来」，
# 计数恒等于空壳个数（实测 37），还跟着弹一句早已不成立的警告。
# 2026-08-08 用户实机报的就是这个：数字和提示永远不变。
clean_legacy_quest_lang() {
  QD="$TARGET/config/ftbquests/quests/lang/zh_cn/chapters"
  SD="$SCRIPT_DIR/config/ftbquests/quests/lang/zh_cn/chapters"
  [ -d "$QD" ] && [ -d "$SD" ] || return 0
  hit=0
  for new in "$SD"/zz_hanhua_*.snbt; do
    [ -f "$new" ] || continue
    base="$(basename "$new")"; base="${base#zz_hanhua_}"
    for old in "$QD/$base" "$QD/_$base"; do
      # payload 会写同名文件 → 交给复制那一步，这里不删也不计数
      [ -f "$SD/$(basename "$old")" ] && continue
      if [ -f "$old" ] && cmp -s "$old" "$new"; then
        rm -f "$old"
        hit=$((hit + 1))
      fi
    done
  done
  if [ "$hit" -gt 0 ]; then
    say "🧹 清理了 $hit 个旧版本残留的任务书语言文件。"
  fi
}

# ATM10 @@MCVER@@ 默认启用的资源包，顺序照抄游戏自己写出来的 options.txt。
# 为什么要写死这一串：全新实例没有 options.txt，如果只写我们一个包，
# 游戏首次启动会把这 15 个内置包**全部插到我们后面**（实测汉化包落到第 3 位，
# 被 mod_resources 和五百多个模组包压在底下，汉化基本不生效）。
# 资源包是**后面的覆盖前面的**，我们必须排在最后一个。
DEFAULT_PACKS='@@DEFAULT_PACKS@@'
DEFAULT_PACKS_UNUSED='"modularbees:dynamic_assets","vanilla","mod_resources","add_xycraft_overrides_stone","add_xycraft_overrides_metal","add_xycraft_overrides_glass","moonlight:merged_pack","mod/towntalk:respack","mod/dyenamicsandfriends:compat_packs/productivemetalworks/","mod/dyenamicsandfriends:compat_packs/connectedglass/","mod/dyenamicsandfriends:compat_packs/luminax/","mod/dyenamicsandfriends:compat_packs/cookingforblockheads/","mod/dyenamicsandfriends:compat_packs/botanypots/","mod/dyenamicsandfriends:compat_packs/chromacarvings/","modern_industrialization/generated"'

patch_options() {
  OPT="$TARGET/options.txt"
  # 全新实例还没启动过，options.txt 尚不存在（Minecraft 退出时才写）。
  # 建一份含默认包列表 + 汉化包（放最后）的：Minecraft 启动时会把其余选项
  # 按默认值补齐再回写，部分 options.txt 是合法的。
  # （不要指望 config/defaultoptions —— ATM10 并没有装 DefaultOptions 模组，
  #   那个目录是历史遗留；本包 R12 起已不再往里写东西。）
  if [ ! -f "$OPT" ]; then
    # ⚠️ 只有**从没启动过**的实例才允许新建 options.txt。
    # 一个玩过的实例必然有 logs/ 或 saves/；这时 options.txt 却不见了，只有两种可能：
    #   a) 选错了目录（启动器没做版本隔离时，设置其实在 .minecraft/options.txt）；
    #   b) 别的什么东西把它挪走了。
    # 这两种情况下写一份只有两行的 options.txt，游戏启动会把其余项全部按**默认值**补齐
    # ——玩家的键位 / 视频 / 音量设置当场全没。有玩家报过这个（R12 修复）。
    # 宁可不写、让玩家自己启用资源包，也绝不能把人家的设置冲掉。
    if [ -d "$TARGET/logs" ] || [ -d "$TARGET/saves" ] || [ -f "$TARGET/usercache.json" ]; then
      say "⚠️ 这个实例明显启动过（有 logs/ 或 saves/），却找不到 options.txt。"
      say "   为避免把你的键位 / 视频 / 音量设置冲掉，本次**不新建** options.txt。"
      say "   请确认目标目录是否正确：$TARGET"
      say "   （启动器没开「版本隔离」时，设置在 .minecraft/options.txt，那一层才是实例根目录）"
      say "   确认无误后进游戏 → 选项 → 资源包，手动把「汉化包」拖到已启用一侧的**最后一位**。"
      return
    fi
    if [ -n "$DEFAULT_PACKS" ]; then
      printf 'lang:zh_cn\nresourcePacks:[%s,"%s"]\n' "$DEFAULT_PACKS" "$PACK_ENTRY" > "$OPT"
      say "ℹ️ 这个实例还没启动过（没有 options.txt），已新建一份并写入中文语言与汉化资源包。"
      say "   💡 若首次进游戏后发现翻译没生效，退出游戏再跑一次本安装器即可——"
      say "      那说明你的整合包比预期多了几个内置资源包，重跑会把汉化包重新挪到最后一位。"
    else
      # 这一版的内置资源包顺序没实测过。**绝不伪造**——只写我们一个包的话，
      # 游戏首次启动会把内置包全插到它后面，汉化包等于没启用（实测会掉到第 10/546 位）。
      printf 'lang:zh_cn\n' > "$OPT"
      say "ℹ️ 这个实例还没启动过（没有 options.txt），已写入中文语言。"
      say "   ⚠️ 资源包顺序需要两步：**先启动一次游戏**让 Minecraft 生成完整的资源包列表，"
      say "      退出游戏后**再运行一次本安装器**，它会把汉化包挪到列表最后一位（必须在最后才生效）。"
    fi
    return
  fi
  cur_raw="$(grep '^resourcePacks:' "$OPT" | head -1)"
  if [ -z "$cur_raw" ]; then
    say "⚠️ options.txt 中没有 resourcePacks 行，请进游戏手动启用资源包"
    return
  fi
  # Minecraft 在 Windows 上用 CRLF 写 options.txt（Java println 按系统行尾）。
  # 这种文件被本脚本（Unix 侧）处理时，grep 取出的整行末尾会带一个 \r。
  # 旧版没剥它，导致 "${body%]}" 因为末尾其实是 "]\r" 而不是 "]" 匹配不上、
  # 不做任何裁剪，结果拼出 resourcePacks:[...]\r,"file/xxx.zip"] 这种带多余
  # 括号和散落 \r 的坏行——资源包实际没启用，这正是玩家反馈的那个 bug。
  # 这里记下原来是否有 \r，剥掉再处理，写回时按原样把 \r 补回这一行。
  crlf=0
  case "$cur_raw" in
    *$'\r') crlf=1; cur="${cur_raw%$'\r'}" ;;
    *) cur="$cur_raw" ;;
  esac
  body="${cur#resourcePacks:[}"; body="${body%]}"
  # 先把已有的汉化包条目摘掉，再追加到**末尾**。
  # 不能只判断「已存在就跳过」——旧版本装出来的实例里它可能排在很前面，
  # 那样等于没启用（后面的包会把它整个盖掉），必须重新挪到最后。
  # 摘除时同时兼容双引号/单引号、带/不带 file/ 前缀四种写法——重复安装、
  # 或旧工具用了不同写法留下的残留条目，都得认得出来，否则会越装越多份重复项。
  PACK_BASENAME="${PACK_ENTRY#file/}"
  body="$(printf '%s' "$body" | sed \
    "s|\"$PACK_ENTRY\"||g; s|'$PACK_ENTRY'||g; s|\"$PACK_BASENAME\"||g; s|'$PACK_BASENAME'||g; s|,,*|,|g; s|^,||; s|,\$||")"
  if [ -n "$body" ]; then
    new="resourcePacks:[$body,\"$PACK_ENTRY\"]"
  else
    new="resourcePacks:[\"$PACK_ENTRY\"]"
  fi
  if [ "$new" = "$cur" ]; then
    say "options.txt 已正确启用汉化资源包（在列表最后），跳过"
    return
  fi
  out="$new"
  [ "$crlf" = 1 ] && out="$new"$'\r'
  awk -v n="$out" '/^resourcePacks:/{print n; next} {print}' "$OPT" > "$OPT.hanhua-tmp" \
    && mv "$OPT.hanhua-tmp" "$OPT"
  say "✅ 已在 options.txt 启用汉化资源包并置于列表最后（不在最后会被其他包盖掉）"
}

do_apply() {
  if [ "$IN_PLACE" = "1" ]; then
    clean_legacy_quest_lang
    clean_legacy_cc_help
    clean_legacy_config_ui
    patch_options
    say "✅ 汉化文件已在位，options.txt 已处理完毕。"
    return
  fi
  # ⚠️ fail-closed：数不出足够的待装文件就**一个字节都不动**地退出。
  # 2026-08-01 玩家反馈过一次「备份 0 个 + 一路绿勾 + 实际什么都没装」——
  # 那种情况下安装器照样打印「✅ 汉化已应用」，玩家没有任何办法知道装失败了。
  # 正常包有数百个文件；少于 50 只可能是解压不完整、脚本不在汉化文件夹里，
  # 或路径把文件枚举搞没了。宁可当场报错，也不许假装成功。
  n_payload=$(payload_files | grep -c . || true)
  if [ "${n_payload:-0}" -lt 50 ]; then
    say "❌ 只找到 ${n_payload:-0} 个待安装文件，正常应有数百个。"
    say "   常见原因：压缩包没解压完整；或 install.sh 不在解压出来的汉化文件夹里。"
    say "   已中止，**没有改动实例里的任何文件**。"
    exit 1
  fi
  do_backup
  clean_legacy_quest_lang
  clean_legacy_cc_help
  clean_legacy_config_ui
  n_copied=0
  while IFS= read -r f; do
    mkdir -p "$TARGET/$(dirname "$f")"
    [ "$SCRIPT_DIR/$f" = "$TARGET/$f" ] && continue   # 双保险：源即目标就跳过
    cp -p "$f" "$TARGET/$f"
    n_copied=$((n_copied + 1))
  done < <(payload_files)
  # 再核一遍是否真的落地：cp 静默失败、目标只读、路径被通配符吃掉都在这里露馆。
  n_missing=0
  while IFS= read -r f; do
    [ -f "$TARGET/$f" ] || n_missing=$((n_missing + 1))
  done < <(payload_files)
  if [ "$n_missing" -gt 0 ]; then
    say "❌ 有 $n_missing 个文件没能写进实例（共 $n_payload 个）。汉化未完整安装。"
    say "   可用 bash install.sh restore $TS 回退。"
    exit 1
  fi
  patch_options
  say "✅ 汉化已应用（$n_copied 个文件）。备份在 backups/$TS/，如需回退运行: bash install.sh restore $TS"
}

# 实例里是否已经有拼音搜索 mod。mod id 取自我们随包 jar 的文件名首段
# （jecharacters-1.21.1-neoforge-4.5.26.jar → jecharacters），不写死，
# 换 jar 时不用改这里。
#
# 这不只是省一次按键：同一个 mod id 出现两个 jar，NeoForge 会以
# 「Mod ID is duplicated」拒绝启动。装过的人按下 y 就进不去游戏了。
PINYIN_FOUND=""
pinyin_installed() {
  PINYIN_FOUND=""
  [ -d "$PINYIN_DIR" ] || return 1
  [ -d "$TARGET/mods" ] || return 1
  for j in "$PINYIN_DIR"/*.jar; do
    [ -e "$j" ] || continue
    id="$(basename "$j")"
    id="$(printf '%s' "${id%%-*}" | tr 'A-Z' 'a-z')"
    [ -n "$id" ] || continue
    for m in "$TARGET"/mods/*.jar; do
      [ -e "$m" ] || continue
      mb="$(basename "$m")"
      case "$(printf '%s' "$mb" | tr 'A-Z' 'a-z')" in
        "$id"-*.jar|"$id".jar) PINYIN_FOUND="mods/$mb"; return 0 ;;
      esac
    done
  done
  return 1
}

# 可选 mods（JEI 拼音搜索）：装进实例 mods/，并登记进当前备份以便恢复时删除
do_pinyin() {
  if [ ! -d "$PINYIN_DIR" ]; then
    say "（未找到 $PINYIN_DIR 目录，跳过可选mods）"
    return
  fi
  if pinyin_installed; then
    say "（已装有拼音搜索 mod：${PINYIN_FOUND}，跳过——同一个 mod 装两个 jar 会让游戏起不来）"
    return
  fi
  found=0
  for j in "$PINYIN_DIR"/*.jar; do
    [ -e "$j" ] || continue
    found=1
    base="$(basename "$j")"
    # 就地解压模式没有本次备份（BK 为空），只装不登记
    if [ -n "$BK" ]; then
      if [ -f "$TARGET/mods/$base" ]; then
        mkdir -p "$BK/mods"
        cp -p "$TARGET/mods/$base" "$BK/mods/$base"
      else
        printf 'mods/%s\n' "$base" >> "$BK/新增文件清单.txt"
      fi
    fi
    cp -p "$j" "$TARGET/mods/$base"
    say "  已安装: mods/$base"
  done
  if [ "$found" = 1 ]; then
    say "✅ 可选 mod（JEI 拼音搜索）已安装"
  else
    say "（$PINYIN_DIR 内没有 jar，跳过）"
  fi
}

do_restore() {
  BROOT="$SCRIPT_DIR/backups"
  if [ ! -d "$BROOT" ] || [ -z "$(ls -1 "$BROOT" 2>/dev/null)" ]; then
    say "❌ 没有任何备份"
    exit 1
  fi
  choice="${1:-}"
  if [ -z "$choice" ]; then
    say "可用备份："
    ls -1 "$BROOT"
    latest="$(ls -1 "$BROOT" | tail -1)"
    printf '要恢复的备份名 [回车 = %s]: ' "$latest"
    read -r choice || choice=""
    [ -z "$choice" ] && choice="$latest"
  fi
  BKR="$BROOT/$choice"
  if [ ! -d "$BKR" ]; then
    say "❌ 备份不存在: $choice"
    exit 1
  fi
  if [ -f "$BKR/新增文件清单.txt" ]; then
    while IFS= read -r f; do
      rm -f "$TARGET/$f"
    done < "$BKR/新增文件清单.txt"
  fi
  (cd "$BKR" && find . -type f ! -name '新增文件清单.txt' | while IFS= read -r f; do
    f="${f#./}"
    mkdir -p "$TARGET/$(dirname "$f")"
    cp -p "$f" "$TARGET/$f"
  done)
  say "✅ 已恢复备份 ${choice}（含 options.txt，安装时新增的文件已删除）"
}

check_target
check_update
case "${1:-}" in
  apply)             do_apply ;;
  apply-with-pinyin) do_apply; do_pinyin ;;
  backup)            do_backup ;;
  restore)           do_restore "${2:-}" ;;
  update)            do_update ;;
  *)
    say "══════════════════════════════════════════"
    say " ATM10 @@MCVER@@ 汉化补丁 · 绿油油版 — 安装器"
    say " 目标实例: $TARGET"
    say "══════════════════════════════════════════"
    say " [1] 应用汉化（自动先备份被覆盖文件）"
    has_update && say " [u] 一键下载并更新到 $LATEST_TAG"
    say " [2] 仅备份"
    say " [3] 恢复备份"
    say " [q] 退出"
    printf '请选择: '
    read -r c || c=""
    case "$c" in
      1)
        do_apply
        # 已经装过就别问了：每次更新汉化都要按一次 N 属实多余。
        if pinyin_installed; then
          say "（已装有拼音搜索 mod：${PINYIN_FOUND}，无需重复安装）"
        else
          printf '是否同时安装可选的 JEI 拼音搜索 mod？[y/N]: '
          read -r ans || ans=""
          case "$ans" in
            y|Y) do_pinyin ;;
            *)   say "（跳过可选mods，之后可运行: bash install.sh apply-with-pinyin）" ;;
          esac
        fi
        ;;
      u|U) do_update ;;
      2) do_backup ;;
      3) do_restore "" ;;
      *) say "已退出" ;;
    esac
    ;;
esac
