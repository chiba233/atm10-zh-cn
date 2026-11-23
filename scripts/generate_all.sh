#!/usr/bin/env bash
#
# 从 src/ 组装出货树，再生成全部由脚本产出的汉化资源。
#
# `kubejs/`、`config/`、`resourcepacks/`、`mods/` 都是产物，放在 build/ 下（.gitignore 排除）。
# 仓库里只有 src/（手写的源文件与上游改动映射）和 scripts/（生成器）。
#
# 需要两样东西：
#   - assets-src/fonts/    都是 OFL，由 scripts/fetch_fonts.sh 下载（不入 git）
#   - 整合包本体           ATM_PACK_ROOT 指向实例根目录，或官方包解压出的 overrides 目录
#     读取 mod jar 的几步还要求 mods/ 里有真实的 jar，官方包的 overrides 里没有，
#     所以 CI 上要么指向装好的实例，要么按 manifest 下载 jar（见 build.yml）。
#
# 不依赖 macOS：字体是下载的，源图与 jar 来自整合包。CI 与 macOS 的产物逐张比对，200 张横幅里
# 197 张像素相同，3 张（ATM / ATM之星 / ATM之星自动化）因 freetype 版本不同有细微差别，目视等价。
# PNG 字节因 zlib 版本不同普遍不一样，回归比对要比像素，不比 sha1。
#
# 用法:
#   ATM_PACK_ROOT=/path/to/instance ./scripts/generate_all.sh
set -euo pipefail
cd "$(dirname "$0")/.."

: "${ATM_PACK_ROOT:=/Users/yumeka/Documents/minecraft/.minecraft/versions/All the Mods 10}"
export ATM_PACK_ROOT
[ -d "$ATM_PACK_ROOT/kubejs" ] || {
  echo "❌ ATM_PACK_ROOT 不像整合包目录（缺 kubejs/）: $ATM_PACK_ROOT"; exit 1; }

for f in pixel-10.ttf pixel-12.ttf bold.otf thin.otf serif.otf; do
  [ -f "assets-src/fonts/$f" ] || {
    echo "❌ 缺字体 assets-src/fonts/$f，先运行 scripts/fetch_fonts.sh"; exit 1; }
done

HAVE_JARS=0
[ -d "$ATM_PACK_ROOT/mods" ] && [ "$(ls "$ATM_PACK_ROOT"/mods/*.jar 2>/dev/null | wc -l)" -ge 20 ] && HAVE_JARS=1

echo "▶ 从 src/ 组装出货树（含 VaultPatcher 模块与跟随原版的文件）"
python3 scripts/assemble.py

echo "▶ 给 VaultPatcher 打性能补丁（现拉源现编，全程核哈希，行为等价必须对拍通过）"
python3 scripts/patch_vaultpatcher.py "$(python3 -c "import sys;sys.path.insert(0,'scripts');from paths import COMMON;print(COMMON)")"

echo "▶ 任务书横幅艺术字（200 张）"
python3 scripts/gen_quest_banners.py
echo "▶ 章节配图：补上上游引用了却没发的那几张（顺带核一遍别的都拿得到）"
python3 scripts/gen_missing_questpics.py
echo "▶ 主菜单按钮（14 张）"
python3 scripts/gen_menu_buttons.py
echo "▶ 根源经典教程书：按行宽预切并插空格（它的折行只认 ASCII 空格，中文切不开）"
python3 scripts/gen_rootsclassic_wrap.py
echo "▶ 自动化之火：tooltip 上那行仪式 ID 是数据不是翻译键，只能在显示层换成中文"
python3 scripts/gen_occultism_flame.py

if [ "$HAVE_JARS" = 1 ]; then
  # 这几步要读 mod jar 里的 en_us、注册表与导览书，只有 overrides 不够
  echo "▶ 配置界面标签（按逐词词典生成，缺词的整条跳过不猜）"
  python3 scripts/gen_config_ui.py "$ATM_PACK_ROOT"

  echo "▶ 模组贴图里烤进去的英文（minecolonies 速查手册标题）：擦掉重写中文"
  python3 scripts/gen_mod_textures.py

  echo "▶ 导览书（Patchouli / AE2 Guide / Oracle Index …）：拿 jar 里那份现套译文"
  python3 scripts/gen_books.py

  echo "▶ 正文写死在 JSON 里的书（自耕农手册）：语言文件够不着，只能整份覆盖"
  python3 scripts/gen_literal_books.py

fi

# 任务书里「甲 + 乙」形式的育种公式：名字必须与 JEI 物品名逐字一致，改了树名也要跟着变，
# 所以按育种结构填入中文。结构由 scan_productive_trees.py 在版本入库时扫描一次，存成
# versions/db/<版本>/productive_trees.json，这里只读那份基线，不用 jar，所以不在 HAVE_JARS 块里。
# 产物不入库，路径登记在 assemble.py 的 FORBIDDEN_IN_SRC 里。
echo "▶ 资源树育种公式（按该版基线套中文）"
COMMON_DIR=$(python3 -c "import sys;sys.path.insert(0,'scripts');from paths import COMMON;print(COMMON)")
python3 scripts/gen_productive_trees_quest_lang.py \
    --out "$COMMON_DIR/config/ftbquests/quests/lang/zh_cn/chapters/zz_hanhua_productive_trees_names.snbt"

if [ "$HAVE_JARS" = 1 ]; then

  echo "▶ 资源蜂：双端脚本（真源是资源包的 productivebees/zh_cn.json，这里只做派生）"
  python3 scripts/gen_pb_hanhua.py
  echo "▶ 奖杯名（约 2.5 万条）"
  python3 scripts/gen_trophy_names.py
  echo "▶ 精致存储木头名（约 1500 条）"
  python3 scripts/gen_wood_names.py
  echo "▶ 上游格式串快照（check.py 的占位符校验靠它）"
  python3 scripts/gen_format_snapshot.py "$ATM_PACK_ROOT"
else
  echo "⚠️ ATM_PACK_ROOT 下没有 mod jar，跳过需要读 jar 的生成器"
  echo "   （资源蜂脚本 / 奖杯名 / 木头名 / 格式串快照）"
  echo "   这些产物缺失时 build_dist.sh 会报错，CI 请把 jar 备齐。"
fi
echo "✅ 生成完毕：build/common/"

if [ "$HAVE_JARS" = 1 ]; then
  # 版权检查：出货树里不许有与已装模组逐字节相同的文件。一种是模组自带的中文被原样带进包里，
  # 另一种是别的模组为同一本书提供的 zh_cn 恰好与本包产物相同。两种都不需要分发，Patchouli
  # 与 AE2 导览按文件回落到 en_us，玩家看到的内容一样。列出并剔除。
  # 第三方许可清单：取各 jar 里 mods.toml 声明的 license，附带许可全文的一并放进 licenses/。
  echo "▶ 第三方许可清单"
  python3 scripts/compliance/gen_licenses.py "$ATM_PACK_ROOT/mods" build/common

  echo "▶ 版权检查：剔除与已装模组逐字节相同的文件"
  PACK_DIR=$(python3 -c "import sys;sys.path.insert(0,'scripts');from paths import PACK;print(PACK)")
  python3 scripts/compliance/audit_upstream.py --mods "$ATM_PACK_ROOT/mods" --tree "$PACK_DIR" --drop \
    --manifest build/snapshots/upstream_identical_dropped.json
fi
