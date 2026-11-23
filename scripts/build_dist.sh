#!/usr/bin/env bash
# atm10-zh-cn — All the Mods 10 简体中文汉化补丁「绿油油版」
# Copyright (C) 2026 星野夢華 (Hoshino Yumeka)
# SPDX-License-Identifier: GPL-3.0-or-later
# 打分发包，客户端包与服务端包分开构建：
#   dist/atm10-zh_cn-client-v<版本>.zip
#   dist/atm10-zh_cn-server-v<版本>.zip
# 包名与解压出的文件夹名一律用 ASCII：中文名在 Windows 的不同解压软件之间编码不一致，
# 会变成乱码，安装器找不到路径。资源包 zip 与服务端 jar 不入 git，由本脚本从源目录压缩。
#
# 本包按整合包版本发布：公共内容加上 versions/<整合包版本>/ 的专属覆盖层，一个补丁版本
# 可以同时产出 7.0 / 7.1 / 7.2 三个包。补丁版本号与整合包版本无关。
#
# 用法:
#   ./scripts/build_dist.sh r12            # 出 versions/whitelist.txt 里的全部整合包版本
#   ./scripts/build_dist.sh r12 7.2        # 只出 7.2
#   ./scripts/build_dist.sh r12 "7.1 7.2"  # 出指定几个
set -euo pipefail
cd "$(dirname "$0")/.."

VERSION="${1:?用法: build_dist.sh <补丁版本号，如 r12> [整合包版本，默认全部]}"
# 目标整合包版本：没给就取 versions/ 下声明过的全部版本，不查 CurseForge
# （否则 ATM 一发新版，CI 就会构建一个没验证过的包）。
REQUESTED="${2:-$(ls -d versions/[0-9]* 2>/dev/null | xargs -n1 basename | tr '\n' ' ')}"
[ -n "${REQUESTED// /}" ] || { echo "❌ versions/ 下没有任何整合包版本目录"; exit 1; }
# 只打 versions/whitelist.txt 里的版本。没列进去的是维护版本，跳过并点名。
ALLOWED="$(python3 scripts/release_versions.py)"
MC_VERSIONS=""
for v in $REQUESTED; do
  case " $ALLOWED " in
    *" $v "*) MC_VERSIONS="$MC_VERSIONS $v" ;;
    *) echo "跳过 $v：不在 versions/whitelist.txt 里，不打包" ;;
  esac
done
[ -n "${MC_VERSIONS// /}" ] || { echo "❌ 要打包的版本一个都不在 versions/whitelist.txt 里"; exit 1; }
CBASE="atm10-zh_cn-client"
SBASE="atm10-zh_cn-server"

# 先组装并生成出货树。这里只查是否组装出来了，内容由 check.py（逐版本）
# 和 verify_dist.py（解开 zip 清点）检查。
COMMON="build/common"
[ -d "$COMMON/resourcepacks" ] || {
  echo "❌ 还没生成出货树 ($COMMON)"
  echo "   先跑: ./scripts/fetch_fonts.sh && ATM_PACK_ROOT=<整合包目录> ./scripts/generate_all.sh"
  exit 1; }
BANNERS=$(find "$COMMON/resourcepacks/ATM10汉化包/assets/atm/textures/questpics" -name '*.png' 2>/dev/null | wc -l | tr -d ' ')
BUTTONS=$(find "$COMMON/config/fancymenu/assets" -name '*.png' 2>/dev/null | wc -l | tr -d ' ')
# 导览书都由 gen_books.py 生成，缺了就是整套英文导览书。下限 1300：与原文完全相同的页
# （游戏会回落到 en_us）和模组自带中文的页都不输出。
BOOKS=$(find "$COMMON/resourcepacks/ATM10汉化包/assets" \
  -path '*patchouli_books*' -o -path '*ae2guide*' -o -path '*oracle-index*' 2>/dev/null | grep -c . || true)
MISSING=""
[ "${BOOKS:-0}" -ge 1300 ] || MISSING="$MISSING 导览书(${BOOKS}/1300)"
[ "${BANNERS:-0}" -ge 200 ] || MISSING="$MISSING 横幅(${BANNERS}/200)"
[ "${BUTTONS:-0}" -ge 14 ]  || MISSING="$MISSING 按钮(${BUTTONS}/14)"
for f in \
  "$COMMON/resourcepacks/ATM10汉化包/assets/hanhua_trophies/lang/zh_cn.json" \
  "$COMMON/resourcepacks/ATM10汉化包/assets/hanhua_wood_names/lang/zh_cn.json" \
  "$COMMON/kubejs/client_scripts/pb_hanhua_tooltip.js" \
  "$COMMON/kubejs/client_scripts/occultism_flame_tooltip.js" \
  "$COMMON/kubejs/server_scripts/pb_hanhua_cage_migrate.js" \
  "build/snapshots/upstream_format_en_us.json"; do
  [ -f "$f" ] || MISSING="$MISSING $(basename "$f")"
done
if [ -n "$MISSING" ]; then
  echo "❌ 生成物不全：$MISSING"
  echo "   先跑: ./scripts/fetch_fonts.sh && ATM_PACK_ROOT=<整合包目录> ./scripts/generate_all.sh"
  exit 1
fi

build_one() {
MC="$1"
# 该版出货树 = 版本中立部分 + 该版官方文件套上本包的改动。上游文件（ATM 的 kubejs/*.js、
# config/*.json）不在仓库里，这里下载该版官方文件再打补丁，上游改了哪一行都会报错
# （见 gen_upstream_patches.py）。
TREE="build/v/${MC}"
rm -rf "$TREE"; mkdir -p "build/v"; cp -R "$COMMON" "$TREE"
UPROOT="build/packsrc/${MC}"
if [ ! -d "$UPROOT/kubejs" ]; then
  echo "  取 ATM10 ${MC} 的官方文件（只要 overrides，不下 jar）"
  python3 scripts/fetch_pack.py "$MC" "$UPROOT" --no-jars
fi
python3 scripts/gen_upstream_patches.py "$UPROOT" "$TREE" "$MC"
# 资源包译文按命名空间和键索引，各版本通用。例外是 versions/<版本>/pack_overrides.json：
# 同一个键在两版里参数个数不同时，一份中文对不了两版。
python3 scripts/gen_pack_overrides.py "$MC" "$TREE"
# 任务书缺图按版本判断：ATM 从 8.1 起自带 create_shaft.png，7.0–8.0 没有。
# 版本中立的树里照样画了（老版本要用），这里按该版官方文件剔除，不覆盖上游。
python3 scripts/gen_missing_questpics.py --prune "$UPROOT" "$TREE"
# 任务书语言：把本包的覆盖打进上游的章节文件，按原文件名出货（含该版专属覆盖）。
# splitter 在 Linux 上的合并顺序是随机的，同一个键只能在一份文件里，详见 gen_quest_lang_patches.py。
python3 scripts/gen_quest_lang_patches.py "$UPROOT" "$TREE" "$MC"
# FTB Quests 在空格处断行，上游中文里的英文词间空格会让它断在「有 / 3 个」这类地方（issue #10）。
# 这类空格有几千处，所以在构建时统一处理。
python3 scripts/gen_quest_space_fix.py "$TREE"
NF=$(cat "versions/$MC/neoforge.txt" 2>/dev/null | tr -d " \n")
# 加载器版本随整合包版本变，不能手写：SERVER.md 写死 21.1.241 时，7.0(228)/7.1(234)/7.3(247)
# 的服主照着装会起不来。
[ -n "$NF" ] || { echo "❌ versions/$MC/neoforge.txt 缺失或为空"; exit 1; }
python3 scripts/gen_hanhua_update_check.py "$VERSION" "$TREE"
# VaultPatcher 模块头部要写该版真实的 jar 文件名（7.2 那份拿到 7.0 只有 83/152 对得上）
python3 scripts/gen_vaultpatcher.py "$MC" "$TREE"
python3 scripts/check.py "$TREE"
# KubeJS 的类过滤表拒绝一批 java.* 类（`- java.net`、`- java.lang` 等）。脚本 loadClass 被拒的类时
# 运行时抛异常，写在事件回调里就是进游戏没有效果，加载阶段不报错。按目标版本 kubejs jar 里的表检查。
python3 scripts/compliance/check_kubejs_classfilter.py "${ATM_PACK_ROOT:-pack}/mods" "$TREE"
# 资源包生效自检用脚本里的键名与版本号查语言表，任何一处对不上，配置正常的玩家每次进游戏都会
# 看到红字。文件缺失、键名、值、命名空间四种不一致都能静态判断。
python3 scripts/compliance/check_pack_probe.py "$TREE"
# Iron Jetpacks 的等级名（振金、难得素、创造等）在整合包 config 里，不在 lang 里。lang 缺
# `jetpack.<name>.name` 会回退成英文且不报错。档位清单随整合包版本变，按该版官方 config 检查。
python3 scripts/compliance/check_jetpack_tiers.py "$UPROOT" "$TREE"
# 任务书提到某只蜜蜂时，必须用玩家在 JEI 里搜得到的名字
# （例如物品叫「恶魂蜜蜂」，任务书不能写「幽灵蜜蜂」）。
python3 scripts/compliance/check_bee_names_in_quests.py \
  "${ATM_PACK_ROOT:-pack}/mods" "$UPROOT" "$TREE"
# 同一判据用到其他模组：任务书写「XP 果冻豆」而 JEI 里叫「经验果冻宝宝」。工业先锋的无限工具
# 档位不是物品名，按目标任务键绑定 jar 的 tooltip 语言键逐档核对。名字表取全包所有模组的并集：
# Rotten Egg 在两个模组里各有一件，只按一个模组判断会误报。
python3 scripts/compliance/check_item_names_in_quests.py \
  "${ATM_PACK_ROOT:-pack}/mods" "$UPROOT" "$TREE"
# 神谕目录的书有两套目录约定（V1 的 translated/ 与 Legacy 的 .translated/），由书的
# sinytra-wiki.json 声明。放错路径的译文不会被读取，也不报错。各版本的 mod 版本不同，逐版本判断。
python3 scripts/compliance/check_oracle_index_paths.py "${ATM_PACK_ROOT:-pack}/mods" "$TREE"
# 资源包内容各版本通用（lang 按命名空间索引，多余的键不生效，缺的回退），源目录只有一份，
# 只有 zip 文件名带版本号。
PACK_SRC="$TREE/resourcepacks/ATM10汉化包"
PACK_NAME="ATM10汉化包-${MC}"
echo "───── 构建 整合包 ${MC} ─────"

# ---------- 客户端包 ----------
CSTAGE="dist/${CBASE}"
rm -rf "$CSTAGE"
mkdir -p "$CSTAGE/resourcepacks"
# pack.mcmeta 的 description 里有 @@MCVER@@ 占位，在这里按版本填入，资源包界面里能看出是哪一版。
PSTAGE="dist/.packsrc-${MC}"
rm -rf "$PSTAGE"; cp -R "$PACK_SRC" "$PSTAGE"
python3 - "$PSTAGE/pack.mcmeta" "$MC" <<'PY'
import pathlib, sys
p = pathlib.Path(sys.argv[1])
p.write_text(p.read_text(encoding='utf-8').replace('@@MCVER@@', sys.argv[2]), encoding='utf-8')
PY
python3 scripts/mkzip.py "${CSTAGE}/resourcepacks/${PACK_NAME}.zip" "$PSTAGE"
rm -rf "$PSTAGE"
cp -R "$TREE/config" "$TREE/kubejs" "$TREE/mods" "$TREE/vaultpatcher" "$TREE/可选mods-拼音搜索" "$CSTAGE/"
# 该版专属的任务书覆盖已由 gen_quest_lang_patches.py 打进上游文件，这里不再单独发 delta，
# 否则同一个键会出现在两份文件里。
cp installer/install.sh installer/install.ps1 "installer/双击安装-Windows.bat" "$CSTAGE/"
# ASCII 别名：中文名在解压软件里乱码时，还有一个认得出的入口
cp "installer/双击安装-Windows.bat" "$CSTAGE/install-windows.bat"
# 该版实测的默认资源包顺序（versions/<版本>/default_resource_packs.txt）。
# 没实测过就注入空串，安装器会走两步流程。
DP="$(grep -v '^#' "versions/${MC}/default_resource_packs.txt" 2>/dev/null | sed '/^[[:space:]]*$/d' \
     | sed 's/.*/"&"/' | paste -sd, - || true)"
# 安装器里与整合包版本有关的字样（资源包文件名、界面标题、注释）都用占位符填入，
# 漏填会被 verify_dist.py 的 @@ 残留检查拦下。
for f in "$CSTAGE/install.sh" "$CSTAGE/install.ps1"; do
  [ -f "$f" ] || continue
  DP="$DP" MC="$MC" PV="$VERSION" NF="$NF" python3 -c "
import os, pathlib, sys
p = pathlib.Path(sys.argv[1])
t = p.read_text(encoding='utf-8')
t = (t.replace('@@MCVER@@', os.environ['MC'])
      .replace('@@DEFAULT_PACKS@@', os.environ['DP'])
      .replace('@@PATCHVER@@', os.environ['PV'])
      .replace('@@NEOFORGE@@', os.environ['NF']))
p.write_text(t, encoding='utf-8')
" "$f"
done
# 说明文档在包里叫「请安装前务必看我.md」：多数人从别处拿到 zip，不会去看 GitHub 上的 README。
cp README.md "$CSTAGE/请安装前务必看我.md"
cp CHANGELOG.md LICENSE LICENSE-GPL-3.0 "$CSTAGE/"
# 仓库里叫 CREDITS.md（源码侧一律 ASCII），包里给玩家的是中文名
cp CREDITS.md "$CSTAGE/致谢与技术说明.md"
printf '[InternetShortcut]\r\nURL=https://github.com/chiba233/atm10-zh-cn\r\n' > "$CSTAGE/项目主页与反馈.url"
chmod +x "$CSTAGE/install.sh"

# ---------- 服务端包 ----------
SSTAGE="dist/${SBASE}"
rm -rf "$SSTAGE"
mkdir -p "$SSTAGE/mods" "$SSTAGE/vaultpatcher/modules"
cp "$TREE/mods/vaultpatcher.jar" "$SSTAGE/mods/"
# 蜂名迁移脚本（KubeJS 服务端）：按 NBT ID 改写老蜂笼、老实体的显示名。
# 服务端数据保持上游英文，否则与 JEI、配方对不上。
mkdir -p "$SSTAGE/kubejs/server_scripts"
cp "$TREE/kubejs/server_scripts/pb_hanhua_cage_migrate.js" "$SSTAGE/kubejs/server_scripts/"
# 进服公告：整合包自带的 kubejs/server_scripts/announcements/announcements.js 在服务端运行，
# 联机时玩家看到的是服务器上那份，所以服务端包也要带上译文。它是聊天栏文本，
# 不参与配方匹配，也不进 JEI 搜索，和下面的 kubejs/data 是同一类。
[ -d "$TREE/kubejs/server_scripts/announcements" ] \
  && cp -R "$TREE/kubejs/server_scripts/announcements" "$SSTAGE/kubejs/server_scripts/"
# 数据包覆盖（法术书风味文本等）：联机时由服务端下发，客户端那份会被忽略。这些只改显示用的
# 数据组件，不参与配方匹配、不进 JEI 搜索，与「服务端数据保持上游英文」针对的物品名不同。
[ -d "$TREE/kubejs/data" ] && cp -R "$TREE/kubejs/data" "$SSTAGE/kubejs/"
# 服务端安全模块子集（清单与准入标准见 scripts/server_modules.txt，check.py 把关）
grep -v '^#' scripts/server_modules.txt | while IFS= read -r m; do
  [ -n "$m" ] && cp "$TREE/vaultpatcher/modules/$m.json" "$SSTAGE/vaultpatcher/modules/"
done
# 服务端 config 只带任务书语言与 VaultPatcher 主配置。mysticalcustomization 不能放进服务端：
# 改名后的作物配置会让所有玩家进服时刷 "error creating crop with id null"。作物名汉化只在客户端。
mkdir -p "$SSTAGE/config"
cp -R "$TREE/config/ftbquests" "$TREE/config/vaultpatcher_asm" "$SSTAGE/config/"
# 服务端说明里的「适用于 ATM10 x.y 专用服务器」随版本填入，写死的话 7.0 / 7.1 的包里会印着 7.2。
MC="$MC" NF="$NF" python3 -c "
import os, pathlib, sys
src, dst = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2])
dst.write_text(src.read_text(encoding='utf-8')
                  .replace('@@MCVER@@', os.environ['MC'])
                  .replace('@@NEOFORGE@@', os.environ['NF']),
               encoding='utf-8')
" SERVER.md "$SSTAGE/请安装前务必看我.md"
cp LICENSE LICENSE-GPL-3.0 "$SSTAGE/"
printf '[InternetShortcut]\r\nURL=https://github.com/chiba233/atm10-zh-cn\r\n' > "$SSTAGE/项目主页与反馈.url"

# ---------- 压缩 ----------
find dist -name '.DS_Store' -delete
# 用 mkzip.py 而不是系统 zip：Info-ZIP 不设 UTF-8 标志位，Windows 自带解压会把中文名按 GBK
# 解成乱码（详见 scripts/mkzip.py）
CZIP="dist/${CBASE}-${VERSION}-atm${MC}.zip"
SZIP="dist/${SBASE}-${VERSION}-atm${MC}.zip"
rm -f "$CZIP" "$SZIP"
python3 scripts/mkzip.py "$CZIP" "$CSTAGE" "${CBASE}"
python3 scripts/mkzip.py "$SZIP" "$SSTAGE" "${SBASE}"
for f in "$CZIP" "$SZIP"; do
  echo "  已生成: $f ($(du -h "$f" | cut -f1))"
done
}

for mc in $MC_VERSIONS; do build_one "$mc"; done
echo
# 最后解开每个 zip 逐项清点内容：0 字节的 lang、全透明的横幅、只剩几条键的资源包都能通过
# 存在性检查，数量少一大块说明某个生成环节失败了。
python3 scripts/compliance/verify_dist.py dist/*-${VERSION}-atm*.zip
echo
echo "全部完成：$(ls dist/*-${VERSION}-atm*.zip | wc -l | tr -d " ") 个包"
ls -1 dist/*-${VERSION}-atm*.zip
