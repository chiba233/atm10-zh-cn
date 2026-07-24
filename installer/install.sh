#!/usr/bin/env bash
# ATM10 7.2 汉化补丁「绿油油版」安装器 (macOS / Linux)
# 用法：把整个汉化文件夹放进 ATM10 实例根目录后运行：
#   bash install.sh                    # 交互菜单
#   bash install.sh apply              # 应用汉化（自动先备份，不含可选mods）
#   bash install.sh apply-with-pinyin  # 应用汉化 + 安装可选 JEI 拼音搜索 mod
#   bash install.sh backup             # 仅备份
#   bash install.sh restore [备份名]   # 恢复备份
set -euo pipefail
cd "$(dirname "$0")"
SCRIPT_DIR="$(pwd)"
TARGET="$(cd .. && pwd)"
PACK_DIRS="config kubejs mods resourcepacks vaultpatcher"
PACK_ENTRY='file/ATM10汉化包-7.2.zip'
PINYIN_DIR="可选mods-拼音搜索"
TS=""
BK=""

say() { printf '%s\n' "$*"; }

check_target() {
  if [ -d "$TARGET/mods" ] && [ -f "$TARGET/options.txt" ]; then
    return
  fi
  say "⚠️ 上一级目录不是游戏实例根目录（含 mods/ 与 options.txt 的那一层）。"
  if [ -t 0 ]; then
    while :; do
      printf '请输入 ATM10 实例根目录完整路径（q 退出）: '
      read -r inp || exit 1
      [ "$inp" = "q" ] && exit 1
      case "$inp" in "~"*) inp="$HOME${inp#\~}" ;; esac
      if [ -d "$inp/mods" ] && [ -f "$inp/options.txt" ]; then
        TARGET="$inp"
        say "✅ 目标实例: $TARGET"
        return
      fi
      say "❌ 该路径下未找到 mods/ 与 options.txt，请重试。"
    done
  fi
  say "   请把整个汉化文件夹放进实例根目录后再运行本脚本。"
  exit 1
}

payload_files() {
  for d in $PACK_DIRS; do
    [ -d "$d" ] && find "$d" -type f ! -name '.DS_Store'
  done
}

do_backup() {
  TS="$(date +%Y%m%d-%H%M%S)"
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
  cp -p "$TARGET/options.txt" "$BK/options.txt"
  say "✅ 已备份 $n 个将被覆盖的文件到 backups/$TS/"
}

patch_options() {
  OPT="$TARGET/options.txt"
  if grep -q "$PACK_ENTRY" "$OPT"; then
    say "options.txt 已启用汉化资源包，跳过"
    return
  fi
  if grep -q '^resourcePacks:\[\]' "$OPT"; then
    sed -i.hanhua-bak "s|^resourcePacks:\[\]|resourcePacks:[\"$PACK_ENTRY\"]|" "$OPT"
  elif grep -q '^resourcePacks:\[' "$OPT"; then
    sed -i.hanhua-bak "s|^resourcePacks:\[\(.*\)\]|resourcePacks:[\1,\"$PACK_ENTRY\"]|" "$OPT"
  else
    say "⚠️ options.txt 中没有 resourcePacks 行，请进游戏手动启用资源包"
    return
  fi
  rm -f "$OPT.hanhua-bak"
  say "✅ 已在 options.txt 启用汉化资源包（不启用会全英文）"
}

do_apply() {
  do_backup
  while IFS= read -r f; do
    mkdir -p "$TARGET/$(dirname "$f")"
    cp -p "$f" "$TARGET/$f"
  done < <(payload_files)
  patch_options
  say "✅ 汉化已应用。备份在 backups/$TS/，如需回退运行: bash install.sh restore $TS"
}

# 可选 mods（JEI 拼音搜索）：装进实例 mods/，并登记进当前备份以便恢复时删除
do_pinyin() {
  if [ ! -d "$PINYIN_DIR" ]; then
    say "（未找到 $PINYIN_DIR 目录，跳过可选mods）"
    return
  fi
  found=0
  for j in "$PINYIN_DIR"/*.jar; do
    [ -e "$j" ] || continue
    found=1
    base="$(basename "$j")"
    if [ -f "$TARGET/mods/$base" ]; then
      mkdir -p "$BK/mods"
      cp -p "$TARGET/mods/$base" "$BK/mods/$base"
    else
      printf 'mods/%s\n' "$base" >> "$BK/新增文件清单.txt"
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
case "${1:-}" in
  apply)             do_apply ;;
  apply-with-pinyin) do_apply; do_pinyin ;;
  backup)            do_backup ;;
  restore)           do_restore "${2:-}" ;;
  *)
    say "══════════════════════════════════════════"
    say " ATM10 7.2 汉化补丁 · 绿油油版 — 安装器"
    say " 目标实例: $TARGET"
    say "══════════════════════════════════════════"
    say " [1] 应用汉化（自动先备份被覆盖文件）"
    say " [2] 仅备份"
    say " [3] 恢复备份"
    say " [q] 退出"
    printf '请选择: '
    read -r c || c=""
    case "$c" in
      1)
        do_apply
        printf '是否同时安装可选的 JEI 拼音搜索 mod？[y/N]: '
        read -r ans || ans=""
        case "$ans" in
          y|Y) do_pinyin ;;
          *)   say "（跳过可选mods，之后可运行: bash install.sh apply-with-pinyin）" ;;
        esac
        ;;
      2) do_backup ;;
      3) do_restore "" ;;
      *) say "已退出" ;;
    esac
    ;;
esac
