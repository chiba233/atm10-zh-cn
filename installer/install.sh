#!/usr/bin/env bash
# atm10-zh-cn — All the Mods 10 简体中文汉化补丁「绿油油版」
# Copyright (C) 2026 星野夢華 (Hoshino Yumeka)
# SPDX-License-Identifier: GPL-3.0-or-later
# ATM10 @@MCVER@@ 汉化补丁「绿油油版」安装器 (macOS / Linux)
# 版本号用 @@MCVER@@ 占位，由 scripts/build_dist.sh 按目标整合包版本填入。
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
# 就地解压：压缩包内容直接解到了实例根目录，源与目标相同，文件已经到位。
IN_PLACE=0

say() { printf '%s\n' "$*"; }

# ── 版本检查 ────────────────────────────────────────────────────────────
# 补丁版本号，由 build_dist.sh 填入。
PATCH_VER="@@PATCHVER@@"
REPO="chiba233/atm10-zh-cn"

# 取最新正式版的 tag（releases/latest 跳过预发布，测试版不算最新版）。
# 没网、没有 curl/wget、被限流或返回的不是 JSON 时返回空，不影响安装。
RELEASE_JSON=""
LATEST_TAG=""

# Release JSON 只请求一次：版本检查用 tag_name，一键更新用 assets 里的下载地址与 sha256。
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

# 只能取它的输出：写成 `x="$(latest_tag)"` 会在子 shell 里运行，对 LATEST_TAG / RELEASE_JSON
# 的赋值回不到父进程。需要这两个变量时直接调 fetch_latest_release。
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

  # 直接调用：写成 latest="$(latest_tag)" 的话 LATEST_TAG 回不到父进程，菜单里的 has_update 永远为假。
  fetch_latest_release
  latest="$LATEST_TAG"
  if [ "$is_beta" = "1" ]; then
    say ""
    say "⚠️ 你装的是测试版：$PATCH_VER"
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

# 判断目录是不是游戏实例根目录。刚装好没启动过的整合包没有 options.txt（Minecraft 首次退出时
# 才写），汉化包文件夹里也有 mods/（装着 vaultpatcher.jar），所以按 jar 数量区分：ATM10 有 400+ 个。
# ── 一键更新 ────────────────────────────────────────────────────────────
# 与 install.ps1 的 Invoke-OneClickUpdate 流程相同：
# 选 asset → 校验 sha256 → 解包 → 由新版安装器 apply → 归并备份 → 更新源目录。

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

# Release 里有 7.0/7.1/7.2 × 客户端/服务端共六个包，按本包的 ATM 版本精确挑客户端 zip。
# 输出三行：文件名 / 下载地址 / sha256。挑不到或没有摘要就返回 1。
pick_client_asset() {
  flat="$(printf '%s' "$RELEASE_JSON" | tr '\n' ' ')"
  # 从目标 name 截到行尾。asset 的字段顺序是 name → …uploader{}… → digest → browser_download_url，
  # 截断后第一个 digest / browser_download_url 就是这个 asset 的。
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

# 新版安装器把备份写在自己的目录里，而 restore 仍从原目录运行，所以更新后把备份归并回原入口。
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

# 玩家以后还会运行原来解压出的 install.sh。只更新实例的话，旧脚本会再提示升级，
# 甚至覆盖回旧 payload。就地解压时源目录就是实例，新版安装器已经覆盖过 payload，不能删。
update_source_package() {
  newdir="$1"
  if [ "$IN_PLACE" != "1" ]; then
    for d in $PACK_DIRS "$PINYIN_DIR"; do
      [ -d "$SCRIPT_DIR/$d" ] && rm -rf "$SCRIPT_DIR/$d"
      [ -d "$newdir/$d" ] && cp -R "$newdir/$d" "$SCRIPT_DIR/$d"
    done
  fi
  # bash 边读边执行，直接覆盖正在运行的文件会读错位置。
  # 先写临时文件再 mv 替换，当前进程的 fd 仍指向旧 inode。
  for f in install.sh install.ps1 双击安装-Windows.bat install-windows.bat; do
    [ -f "$newdir/$f" ] || continue
    cp "$newdir/$f" "$SCRIPT_DIR/.$f.new"
    mv "$SCRIPT_DIR/.$f.new" "$SCRIPT_DIR/$f"
  done
  chmod +x "$SCRIPT_DIR/install.sh" 2>/dev/null || true
  say "✅ 已将原安装包更新为新版。以后继续运行原来的 install.sh 即可。"
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
    # 无法校验就不装：解压出的脚本会被直接执行
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

  # 变量后面紧跟中文时必须写 ${var}：单字节语言环境（CI 容器常见 LANG=C）下，bash 会把 UTF-8 的
  # 头字节算进变量名，`$name……` 变成 `$nameâ`，报 unbound variable。
  say "正在下载 ${name}……"
  ok=1
  if command -v curl >/dev/null 2>&1; then
    curl -fsSL --max-time 300 -H 'User-Agent: atm10-zh-cn-installer' -o "$zipf" "$url" || ok=0
  else
    wget -q --timeout=300 -O "$zipf" "$url" || ok=0
  fi
  if [ "$ok" != "1" ] || [ ! -s "$zipf" ]; then
    say "❌ 一键更新失败：下载失败。"
    say "   新版安装器尚未启动。已下载的临时文件（如有）保留在：$stage"
    return 0
  fi

  got="$(sha256_of "$zipf" || true)"
  if [ -z "$got" ] || [ "$(printf '%s' "$got" | tr 'A-Z' 'a-z')" != "$(printf '%s' "$want" | tr 'A-Z' 'a-z')" ]; then
    say "❌ 一键更新失败：下载文件的 SHA-256 与 GitHub Release 摘要不一致。"
    say "   期望 $want"
    say "   实际 ${got:-（算不出来）}"
    say "   新版安装器尚未启动。文件保留在：$stage"
    return 0
  fi

  unzip -q -o "$zipf" -d "$stage" || {
    say "❌ 一键更新失败：解包失败。"
    say "   新版安装器尚未启动。文件保留在：$stage"
    return 0; }
  newdir="$(find "$stage" -type d -name 'atm10-zh_cn-client' 2>/dev/null | head -1 || true)"
  if [ -z "$newdir" ] || [ ! -f "$newdir/install.sh" ]; then
    say "❌ 一键更新失败：下载包中没有预期的客户端安装器。"
    say "   新版安装器尚未启动。文件保留在：$stage"
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
  say "   请退出并重新启动游戏后生效。确认无误前不要删除该目录。"
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
    say "   文件已经到位，无需复制。本次只在 options.txt 里启用资源包。"
    say "   ⚠️ 这种装法没有备份可回退：原文件在你解压覆盖时就没了。"
    say "   想要可回退的安装，请解压到别处、把整个文件夹放进实例根目录再运行安装器。"
  fi
}

check_target() {
  # 一键更新时新版安装器在 <实例>/.atm10-hanhua-update-*/ 里运行，上一级不是实例，
  # 用这个环境变量传入目标（对应 ps1 的 -TargetPath）。
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
      # 去掉复制、粘贴、拖拽常带的成对引号，以及转义空格的反斜杠
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
  # 同一秒内安装两次会落到同一个备份目录，第二次会用已汉化的文件覆盖第一次的原文备份。
  # 目录已存在就加序号。
  TS="$(date +%Y%m%d-%H%M%S)"
  # 序号补零：do_restore 默认按字典序取最后一个，不补零的话 -10 会排在 -2 前面。
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
# 那些版本的任务书 delta 叫 `<章节名>.snbt`，与整合包自带的同名文件冲突，安装时会覆盖整章翻译
# （启动过的实例看不出来：整合包的文件已合并并改名成 .snbt_merged）。现在统一加 zz_hanhua_ 前缀。
# 旧名字的残留只在内容与本包同名新文件逐字节相同时才删，确保删的是本包的旧文件。
# r14 之前的版本往实例里装过 CC: Tweaked 的中文 help 文档
# （kubejs/data/computercraft/lua/rom/help/，97 个 .txt）。CC 终端用自带的 term_font.png，
# 256 个字形没有汉字，中文是乱码。安装器只覆盖不删除，所以这里主动清理。
clean_legacy_cc_help() {
  # 只处理 lua/rom/help/，旧版本的译文都在这里。别处的 .txt 可能是玩家的 CC 程序数据或别的补丁，
  # 不在 payload 里，do_backup 不会备份，删了无法恢复（issue #9 P1-1）。
  CCD="$TARGET/kubejs/data/computercraft/lua/rom/help"
  [ -d "$CCD" ] || return 0
  # `|| true`：set -euo pipefail 下 find 非零退出（例如有不可读的子目录）会让安装器无提示退出。
  LIST=$(find "$CCD" -name '*.txt' -type f 2>/dev/null || true)
  [ -n "$LIST" ] || return 0
  hit=0
  while IFS= read -r f; do
    [ -f "$f" ] || continue
    # 有非 ASCII 字节的才是本包的中译本，CC 自带的 help 都是英文。
    # 下面已先备份，判错也能 restore。
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
  # 自底向上删空目录。非空的一律留着
  find "$CCD" -depth -type d -empty -exec rmdir {} + 2>/dev/null || true
  say "🧹 清理了旧版本装进去的 CC: Tweaked 中文 help 文档（$hit 个文件，已备份）。"
  say "   CC 的终端只有 256 个自带字形、没有汉字，中文在那里必然是乱码，"
  say "   所以这部分改回英文。这是终端本身的限制，不是漏翻。"
}

# r14 发过「模组配置界面汉化」的两个 VaultPatcher dynamic 模块（共 2232 条），之后停发。
# dynamic 表每次替换都要线性扫描，留在盘上会全场景掉帧。安装器只覆盖不删除，所以这里主动清理。
clean_legacy_config_ui() {
  VPM="$TARGET/vaultpatcher/modules"
  [ -d "$VPM" ] || return 0
  hit=0
  for f in config_ui_generated.json catnip_config_ui.json; do
    if [ -f "$VPM/$f" ]; then
      # 这两个文件不在 payload 里，do_backup 不会备份，这里自己放进本次备份目录。
      # 就地解压模式没有备份，无法回退（见 do_apply 的提示）。
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
    say "   那套替换表是全局开销，表越大越慢，留着会掉帧。"
    say "   代价是 Create 及其附属的配置界面回到英文（只有它们用这套界面）。"
  fi
}

# 旧命名（r13 及更早的 `<章节>.snbt` / `_<章节>.snbt`）留在玩家盘上的任务书语言文件。
#
# payload 里有同名文件的不处理：gen_quest_lang_patches.py 会为每个 `zz_hanhua_X.snbt` 同时发
# `X.snbt`（上游全文加本包覆盖）和 `_X.snbt`（空文件），复制时会覆盖它们。不跳过的话，
# 4 字节的 `_X.snbt` 与 `zz_hanhua_X.snbt` 内容相同，每次安装都会删掉再复制回来，
# 还会提示清理了 37 个。
clean_legacy_quest_lang() {
  QD="$TARGET/config/ftbquests/quests/lang/zh_cn/chapters"
  SD="$SCRIPT_DIR/config/ftbquests/quests/lang/zh_cn/chapters"
  [ -d "$QD" ] && [ -d "$SD" ] || return 0
  hit=0
  for new in "$SD"/zz_hanhua_*.snbt; do
    [ -f "$new" ] || continue
    base="$(basename "$new")"; base="${base#zz_hanhua_}"
    for old in "$QD/$base" "$QD/_$base"; do
      # payload 会写同名文件，交给复制那一步，不删也不计数
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

# ATM10 @@MCVER@@ 默认启用的资源包，顺序照抄游戏写出的 options.txt。资源包后面的覆盖前面的，
# 全新实例只写本包一个的话，游戏首次启动会把内置包插到它后面（实测落到第 3 位，汉化基本不生效）。
DEFAULT_PACKS='@@DEFAULT_PACKS@@'
DEFAULT_PACKS_UNUSED='"modularbees:dynamic_assets","vanilla","mod_resources","add_xycraft_overrides_stone","add_xycraft_overrides_metal","add_xycraft_overrides_glass","moonlight:merged_pack","mod/towntalk:respack","mod/dyenamicsandfriends:compat_packs/productivemetalworks/","mod/dyenamicsandfriends:compat_packs/connectedglass/","mod/dyenamicsandfriends:compat_packs/luminax/","mod/dyenamicsandfriends:compat_packs/cookingforblockheads/","mod/dyenamicsandfriends:compat_packs/botanypots/","mod/dyenamicsandfriends:compat_packs/chromacarvings/","modern_industrialization/generated"'

patch_options() {
  OPT="$TARGET/options.txt"
  # 全新实例还没有 options.txt（Minecraft 退出时才写），建一份含默认包列表、汉化包放最后的，
  # Minecraft 启动时会按默认值补齐其余选项。ATM10 没装 DefaultOptions，不用 config/defaultoptions。
  if [ ! -f "$OPT" ]; then
    # 只有从没启动过的实例才新建 options.txt。玩过的实例一定有 logs/ 或 saves/，这时 options.txt
    # 不见了，可能是选错了目录（启动器没做版本隔离时，设置在 .minecraft/options.txt）。新建只有
    # 两行的 options.txt 会让键位、视频、音量设置全部变回默认，所以不写，让玩家自己启用资源包。
    if [ -d "$TARGET/logs" ] || [ -d "$TARGET/saves" ] || [ -f "$TARGET/usercache.json" ]; then
      say "⚠️ 这个实例明显启动过（有 logs/ 或 saves/），却找不到 options.txt。"
      say "   为避免把你的键位 / 视频 / 音量设置冲掉，本次不新建 options.txt。"
      say "   请确认目标目录是否正确：$TARGET"
      say "   （启动器没开「版本隔离」时，设置在 .minecraft/options.txt，那一层才是实例根目录）"
      say "   确认无误后进游戏，打开「选项」里的「资源包」，手动把「汉化包」拖到已启用一侧的最后一位。"
      return
    fi
    if [ -n "$DEFAULT_PACKS" ]; then
      printf 'lang:zh_cn\nresourcePacks:[%s,"%s"]\n' "$DEFAULT_PACKS" "$PACK_ENTRY" > "$OPT"
      say "ℹ️ 这个实例还没启动过（没有 options.txt），已新建一份并写入中文语言与汉化资源包。"
      say "   💡 如果首次进游戏后翻译没生效，退出游戏再运行一次本安装器即可。"
      say "      你的整合包比预期多了几个内置资源包，重跑会把汉化包重新挪到最后一位。"
    else
      # 这一版的内置资源包顺序没实测过，不伪造。只写本包一个的话，首次启动后它会落到内置包后面
      # （实测第 10/546 位），等于没启用。
      printf 'lang:zh_cn\n' > "$OPT"
      say "ℹ️ 这个实例还没启动过（没有 options.txt），已写入中文语言。"
      say "   ⚠️ 资源包顺序需要两步：先启动一次游戏，让 Minecraft 生成完整的资源包列表，"
      say "      退出游戏后再运行一次本安装器，它会把汉化包挪到列表最后一位（必须在最后才生效）。"
    fi
    return
  fi
  cur_raw="$(grep '^resourcePacks:' "$OPT" | head -1)"
  if [ -z "$cur_raw" ]; then
    say "⚠️ options.txt 中没有 resourcePacks 行，请进游戏手动启用资源包"
    return
  fi
  # Minecraft 在 Windows 上按 CRLF 写 options.txt，grep 取出的行末尾带 \r，"${body%]}" 会因为
  # 行尾是 "]\r" 而不生效，拼出 resourcePacks:[...]\r,"file/xxx.zip"] 这种坏行。
  # 先剥掉 \r，写回时再补上。
  crlf=0
  case "$cur_raw" in
    *$'\r') crlf=1; cur="${cur_raw%$'\r'}" ;;
    *) cur="$cur_raw" ;;
  esac
  body="${cur#resourcePacks:[}"; body="${body%]}"
  # 先摘掉已有的汉化包条目，再追加到末尾：旧版本装出的实例里它可能排在前面，会被后面的包覆盖。
  # 摘除时认双引号、单引号、带或不带 file/ 前缀四种写法，否则重复安装会越积越多。
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
  # 待装文件少于 50 个就报错退出，不改动任何文件。正常包有数百个文件，少于 50 说明解压不完整、
  # 脚本不在汉化文件夹里，或路径导致文件枚举失败。出现过「备份 0 个、提示汉化已应用、实际没装」。
  n_payload=$(payload_files | grep -c . || true)
  if [ "${n_payload:-0}" -lt 50 ]; then
    say "❌ 只找到 ${n_payload:-0} 个待安装文件，正常应有数百个。"
    say "   常见原因：压缩包没解压完整，或 install.sh 不在解压出来的汉化文件夹里。"
    say "   已中止，没有改动实例里的任何文件。"
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
  # 再核对一遍文件是否落地：cp 静默失败、目标只读、路径被通配符解析，都会在这里暴露。
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

# 实例里是否已有拼音搜索 mod。mod id 取随包 jar 文件名的首段
# （jecharacters-1.21.1-neoforge-4.5.26.jar → jecharacters），换 jar 不用改这里。
# 同一个 mod id 有两个 jar 时，NeoForge 报「Mod ID is duplicated」并拒绝启动。
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
    say "（已装有拼音搜索 mod：${PINYIN_FOUND}，跳过。同一个 mod 装两个 jar 会让游戏起不来）"
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
        # 已经装过就不再问
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
