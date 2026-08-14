#!/usr/bin/env bash
# atm10-zh-cn — All the Mods 10 简体中文汉化补丁「绿油油版」
# Copyright (C) 2026 星野夢華 (Hoshino Yumeka)
# SPDX-License-Identifier: GPL-3.0-or-later
# 打分发包：客户端包 + 服务端包 分开构建（一团浆糊是不行的）
#   dist/atm10-zh_cn-client-v<版本>.zip
#   dist/atm10-zh_cn-server-v<版本>.zip
# 包名与解压出的文件夹名一律用 ASCII —— Windows 上中文压缩包名/目录名在不同解压软件
# 之间编码不一致，用户拿到手就是乱码，安装器再去找路径会找不到。
# 资源包 zip 与服务端 jar 均不入 git，由本脚本从源码目录现场压缩。
#
# 本包按**整合包版本族**发布：公共内容 + versions/<整合包版本>/ 的专属覆盖层，
# 一个补丁版本可以同时产出 7.0 / 7.1 / 7.2 三个包。补丁自己的版本号与整合包版本解耦。
#
# 用法:
#   ./scripts/build_dist.sh r12            # 出 versions/ 下声明过的全部整合包版本
#   ./scripts/build_dist.sh r12 7.2        # 只出 7.2
#   ./scripts/build_dist.sh r12 "7.1 7.2"  # 出指定几个
set -euo pipefail
cd "$(dirname "$0")/.."

VERSION="${1:?用法: build_dist.sh <补丁版本号，如 r12> [整合包版本，默认全部]}"
# 目标整合包版本：没给就取 versions/ 下所有声明过的（**只认仓库里有的**，
# 绝不去 CurseForge 现查——那样 ATM 一发新版 CI 就会自动构建一个没验证过的包）
MC_VERSIONS="${2:-$(ls -d versions/[0-9]* 2>/dev/null | xargs -n1 basename | tr '\n' ' ')}"
[ -n "${MC_VERSIONS// /}" ] || { echo "❌ versions/ 下没有任何整合包版本目录"; exit 1; }
CBASE="atm10-zh_cn-client"
SBASE="atm10-zh_cn-server"

# 仓库里没有出货树，先摊 + 生成。这里只查「摊出来了没有」，不查内容——
# 内容归 check.py（每个版本各查一遍）和 verify_dist.py（拆开 zip 数量）管。
COMMON="build/common"
[ -d "$COMMON/resourcepacks" ] || {
  echo "❌ 还没生成出货树 ($COMMON)"
  echo "   先跑: ./scripts/fetch_fonts.sh && ATM_PACK_ROOT=<整合包目录> ./scripts/generate_all.sh"
  exit 1; }
BANNERS=$(find "$COMMON/resourcepacks/ATM10汉化包/assets/atm/textures/questpics" -name '*.png' 2>/dev/null | wc -l | tr -d ' ')
BUTTONS=$(find "$COMMON/config/fancymenu/assets" -name '*.png' 2>/dev/null | wc -l | tr -d ' ')
# 导览书全是 gen_books.py 现产的（仓库里一份副本都没有），漏了就是一整套英文导览书。
# 下限 1300：原先写 1500，是「把与上游逐字节相同的页也照搬进来」那会儿的量。
# 现在两类页不再输出——套完映射与原文一字不差的（游戏按文件回落到 en_us，
# 发了也是同样的英文），以及模组自己就带中文的——所以基数本来就该低一截。
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
# 该版的出货树 = 版本中立部分 + 该版官方文件套上我们的改动。
# 上游文件（ATM 自己的 kubejs/*.js、config/*.json）**一份副本都不在仓库里**：
# 这里现取该版官方文件、现打补丁，上游改了哪一行都会当场报错（见 gen_upstream_patches.py）。
TREE="build/v/${MC}"
rm -rf "$TREE"; mkdir -p "build/v"; cp -R "$COMMON" "$TREE"
UPROOT="build/packsrc/${MC}"
if [ ! -d "$UPROOT/kubejs" ]; then
  echo "  取 ATM10 ${MC} 的官方文件（只要 overrides，不下 jar）"
  python3 scripts/fetch_pack.py "$MC" "$UPROOT" --no-jars
fi
python3 scripts/gen_upstream_patches.py "$UPROOT" "$TREE" "$MC"
# 任务书语言：把本包的覆盖打进上游那份章节文件，按原文件名出货（含该版专属覆盖）。
# splitter 的合并顺序在 Linux 上是随机的，同一个键必须只由一份文件持有——
# 详见 gen_quest_lang_patches.py 顶部。
python3 scripts/gen_quest_lang_patches.py "$UPROOT" "$TREE" "$MC"
# FTB Quests 在空格处断行。上游中文里留着大量英文词间空格，每一个都是断行点，
# 于是断在「有 / 3 个」「抄写台 / 来」这种地方。issue #10 里被当成 11 条独立瑕疵
# 报上来，其实是同一个成因、几千处。逐条存覆盖 delta 会暴涨，改成构建时统一处理。
python3 scripts/gen_quest_space_fix.py "$TREE"
NF=$(cat "versions/$MC/neoforge.txt" 2>/dev/null | tr -d " \n")
# 加载器版本是版本相关字段，禁手写：SERVER.md 里那行写死成 21.1.241，
# 对 7.0(228)/7.1(234)/7.3(247) 一直是错的，服务主照它钉加载器会起不来。
[ -n "$NF" ] || { echo "❌ versions/$MC/neoforge.txt 缺失或为空"; exit 1; }
python3 scripts/gen_hanhua_update_check.py "$VERSION" "$TREE"
# VaultPatcher 模块头部要写该版真实的 jar 文件名（7.2 那份拿到 7.0 只有 83/152 对得上）
python3 scripts/gen_vaultpatcher.py "$MC" "$TREE"
python3 scripts/check.py "$TREE"
# KubeJS 自带的类过滤表会拒掉一批 java.* 类（`- java.net`、`- java.lang` 等）。
# 脚本里 loadClass 一个被拒的类，运行时当场抛异常；躺在事件回调里就表现成
# 「进游戏什么都没发生」——vr16 的更新提示就是这么发出去的，加载阶段还全绿。
# 拿**目标版本 kubejs jar 里的那张表**现查，不在仓库里存副本。
python3 scripts/compliance/check_kubejs_classfilter.py "${ATM_PACK_ROOT:-pack}/mods" "$TREE"
# 资源包生效自检拿脚本里写的键名与版本号去查语言表。这条链子上任何一环对不上，
# 后果都是给配置完全正常的玩家每次进游戏弹一次红字——比不做这个功能还糟。
# 四种对不上（文件缺失／键名不一致／值不一致／命名空间不一致）全部静态可判定。
python3 scripts/compliance/check_pack_probe.py "$TREE"
# Iron Jetpacks 的等级名（振金/难得素/创造…）不在 lang 里，在整合包 config 里；
# lang 缺 `jetpack.<name>.name` 就静默回退成英文，跟翻好了完全无法区分。
# 档位清单随整合包版本变，拿该版官方 config 现查，不手写死在仓库里。
python3 scripts/compliance/check_jetpack_tiers.py "$UPROOT" "$TREE"
# 任务书提到某只蜜蜂时，用的必须是玩家在 JEI 里搜得到的那个名字。
# 「幽灵蜜蜂」vs 物品名「恶魂蜜蜂」这种，照任务书去搜是搜不到的——比漏翻更难受。
python3 scripts/compliance/check_bee_names_in_quests.py \
  "${ATM_PACK_ROOT:-pack}/mods" "$UPROOT" "$TREE"
# 同一条判据推到别的模组：任务书写「XP 果冻豆」而 JEI 里叫「经验果冻宝宝」，
# 写「空灵魂宝石」而物品叫「灵魂宝石（空）」。反馈报了 4 组，机械扫出 19 处。
# 工业先锋的无限工具档位不是物品名，另按目标任务键绑定 jar 的 tooltip 语言键逐档核对。
# 名字表和「更长的名字」都取全包所有模组的并集——Rotten Egg 在两个模组里各有一件，
# 只按其中一个判，会理直气壮地要求改成另一个模组的物品名。
python3 scripts/compliance/check_item_names_in_quests.py \
  "${ATM_PACK_ROOT:-pack}/mods" "$UPROOT" "$TREE"
# 神谕目录的书有两套目录约定（V1 的 translated/ 与 Legacy 的 .translated/），
# 由书自己的 sinytra-wiki.json 声明。放错那条路径的译文永远不会被读，且不报错。
# 各版本的 mod 版本不同，声明也可能不同，所以按版本现判。
python3 scripts/compliance/check_oracle_index_paths.py "${ATM_PACK_ROOT:-pack}/mods" "$TREE"
# 资源包**内容**跨版本通用（lang 按命名空间索引，多余键不生效、缺的回退），
# 所以源目录只有一份；只有产出的 zip 文件名带版本号，方便用户认。
PACK_SRC="$TREE/resourcepacks/ATM10汉化包"
PACK_NAME="ATM10汉化包-${MC}"
echo "───── 构建 整合包 ${MC} ─────"

# ---------- 客户端包 ----------
CSTAGE="dist/${CBASE}"
rm -rf "$CSTAGE"
mkdir -p "$CSTAGE/resourcepacks"
# 资源包源目录是版本中立的；pack.mcmeta 的 description 里留了 @@MCVER@@ 占位，
# 在这里按版本填上，玩家在资源包界面能一眼看出装的是哪一版。
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
# 该版专属的任务书覆盖已经由 gen_quest_lang_patches.py 打进上游文件了（它优先级最高），
# 这里不再单独发一个 delta 文件——发了就又是「同一个键两份文件」。
cp installer/install.sh installer/install.ps1 "installer/双击安装-Windows.bat" "$CSTAGE/"
# ASCII 别名：万一中文名在用户的解压软件下还是乱码，起码还有一个认得出的入口
cp "installer/双击安装-Windows.bat" "$CSTAGE/install-windows.bat"
# 该版实测的默认资源包顺序（versions/<版本>/default_resource_packs.txt）。
# 没实测过就注入空串，安装器会走两步流程而不是伪造一个列表。
DP="$(grep -v '^#' "versions/${MC}/default_resource_packs.txt" 2>/dev/null | sed '/^[[:space:]]*$/d' \
     | sed 's/.*/"&"/' | paste -sd, - || true)"
# 安装器里凡是跟整合包版本有关的字样，一律占位符现填：资源包文件名、界面标题、注释。
# 以前只用 sed 换资源包文件名，界面上那句「ATM10 7.2 汉化补丁」原样留在 7.0/7.1 的包里。
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
# 说明文档在包里改名叫「请安装前务必看我.md」：大部分人是从别处拿到 zip 的，
# 根本不会去 GitHub 看 README，文件名就得自己把话说完。
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
# 蜂名迁移脚本（KubeJS 服务端）：按 NBT ID 改写老蜂笼/老实体的显示名
# （不再用语言注入 mod —— 服务端数据必须保持上游英文，否则与 JEI/配方分裂）
mkdir -p "$SSTAGE/kubejs/server_scripts"
cp "$TREE/kubejs/server_scripts/pb_hanhua_cage_migrate.js" "$SSTAGE/kubejs/server_scripts/"
# 数据包覆盖（法术书风味文本等）：联机时配方由服务端下发，客户端那份会被忽略，
# 不带上服务器玩家就看英文。这些只改显示用的数据组件，不参与配方匹配、不进 JEI
# 搜索，与上面那条「服务端数据保持上游英文」针对的物品名不是一回事。
[ -d "$TREE/kubejs/data" ] && cp -R "$TREE/kubejs/data" "$SSTAGE/kubejs/"
# 服务端安全模块子集（清单与准入标准见 scripts/server_modules.txt，check.py 把关）
grep -v '^#' scripts/server_modules.txt | while IFS= read -r m; do
  [ -n "$m" ] && cp "$TREE/vaultpatcher/modules/$m.json" "$SSTAGE/vaultpatcher/modules/"
done
# 服务端 config 只带任务书语言与 VaultPatcher 主配置。
# ⚠️ mysticalcustomization 绝不能上服务端：服务器带改名后的作物配置会让
# 所有玩家进服时刷 "error creating crop with id null"（2026-07-24 实测定位）。
# 作物名汉化是纯客户端的。
mkdir -p "$SSTAGE/config"
cp -R "$TREE/config/ftbquests" "$TREE/config/vaultpatcher_asm" "$SSTAGE/config/"
# 服务端说明里写着「适用于 ATM10 x.y 专用服务器」，那是**本包**的适用版本，
# 必须跟着走；写死一个的话 7.0 / 7.1 的包里都印着 7.2（玩家实际报过这个）。
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
# 用 mkzip.py 而不是系统 zip：Info-ZIP 不置 UTF-8 标志位，
# Windows 自带解压会把中文名按 GBK 解成乱码（详见 scripts/mkzip.py）
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
# 最后一道闸：拆开每个 zip 逐项核内容。开头那道守卫只查文件在不在，
# 而「在」不等于「对」——0 字节的 lang、纯透明的横幅、只剩几条键的资源包
# 都能骗过存在性检查。这里查的是量，少一大块就说明某个生成环节悄悄失败了。
python3 scripts/compliance/verify_dist.py dist/*-${VERSION}-atm*.zip
echo
echo "全部完成：$(ls dist/*-${VERSION}-atm*.zip | wc -l | tr -d " ") 个包"
ls -1 dist/*-${VERSION}-atm*.zip
