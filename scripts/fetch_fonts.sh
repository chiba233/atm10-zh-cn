#!/usr/bin/env bash
#
# 下载任务书横幅生成脚本用的点阵中文字体。
#
# 字体不入 git（十来 MB，生成好的 PNG 已经在仓库里，玩家和 CI 都不需要它），只有重跑
# scripts/gen_quest_banners.py 时才需要运行这个脚本。版本号固定，保证每次生成的图都一样。
#
# 字体：缝合像素字体 Fusion Pixel Font（OFL-1.1，TakWolf），由方舟像素字体 + Cubic 11 + Galmuri
# 拼合补全覆盖，OFL 一并下载。方舟本体 zh_cn 12px 缺「旋热然聚嗡蟒骏」这类常用字，缺字会渲染成
# .notdef 豆腐块。
set -euo pipefail

VER=2026.07.20
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/assets-src/fonts"
BASE="https://github.com/TakWolf/fusion-pixel-font/releases/download/${VER}"

mkdir -p "$DIR"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

# GitHub 的 release CDN 偶尔会断开连接（curl 35 Recv failure: Connection reset by peer），
# 所以下载带重试。下载后由 toolchain.py --fonts 逐个核对哈希，半截文件或换了版本的字体都会失败。
dl() {
    curl -fsSL --retry 5 --retry-delay 2 --retry-all-errors -o "$1" "$2"
}

for px in 10 12; do
    f="fusion-pixel-font-${px}px-proportional-ttf-v${VER}.zip"
    echo "下载 ${f} ..."
    dl "$TMP/$f" "$BASE/$f"
    unzip -o -q "$TMP/$f" -d "$TMP/x$px"
    cp "$TMP/x$px/fusion-pixel-${px}px-proportional-zh_hans.ttf" "$DIR/pixel-${px}.ttf"
done
cp "$TMP/x12/OFL.txt" "$DIR/pixel-OFL.txt"
rm -rf "$DIR/pixel-LICENSES"
cp -R "$TMP/x12/LICENSES" "$DIR/pixel-LICENSES"

# ---- 矢量三档：思源黑体 / 思源宋体（Noto CJK，OFL-1.1），替代只有 macOS 才有的冬青黑与宋体
#   bold  ← 思源黑体 Bold   （对应冬青黑 W6）
#   thin  ← 思源黑体 Light  （对应冬青黑 W3）
#   serif ← 思源宋体 Black  （对应宋体 SC Black）
echo "下载 思源黑体 SC ..."
dl "$TMP/sans.zip" \
  "https://github.com/notofonts/noto-cjk/releases/download/Sans2.004/18_NotoSansSC.zip"
unzip -o -q "$TMP/sans.zip" -d "$TMP/sans"
cp "$TMP/sans/NotoSansSC-Bold.otf"  "$DIR/bold.otf"
cp "$TMP/sans/NotoSansSC-Light.otf" "$DIR/thin.otf"
cp "$TMP/sans/LICENSE" "$DIR/noto-OFL.txt"

echo "下载 思源宋体 SC ..."
dl "$TMP/serif.zip" \
  "https://github.com/notofonts/noto-cjk/releases/download/Serif2.003/14_NotoSerifSC.zip"
unzip -o -q -j "$TMP/serif.zip" 'SubsetOTF/SC/NotoSerifSC-Black.otf' -d "$TMP"
cp "$TMP/NotoSerifSC-Black.otf" "$DIR/serif.otf"

# 下载后必须核对哈希：字形栅格化决定 PNG 的每个像素，上游重传字体后图会变，
# 而产物哈希对不上时看不出是这里的原因。
echo "核对字体哈希 ..."
python3 "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/toolchain.py" --fonts

echo "完成："
ls -1 "$DIR"
