#!/usr/bin/env bash
# 打分发包：客户端包 + 服务端包 分开构建（一团浆糊是不行的）
#   dist/ATM10-7.2-汉化补丁-绿油油版-星野夢華-客户端-v<版本>.zip
#   dist/ATM10-7.2-汉化补丁-绿油油版-星野夢華-服务端-v<版本>.zip
# 资源包 zip 与服务端 jar 均不入 git，由本脚本从源码目录现场压缩。
# 用法: ./scripts/build_dist.sh 7.2-release1
set -euo pipefail
cd "$(dirname "$0")/.."

VERSION="${1:?用法: build_dist.sh <版本号, 如 7.2-release1>}"
PACK_NAME="ATM10汉化包-7.2"
BASE="ATM10-7.2-汉化补丁-绿油油版-星野夢華"

python3 scripts/check.py

# ---------- 客户端包 ----------
CSTAGE="dist/${BASE}-客户端"
rm -rf "$CSTAGE"
mkdir -p "$CSTAGE/resourcepacks"
(cd "resourcepacks/${PACK_NAME}" && zip -X -q -r "../../${CSTAGE}/resourcepacks/${PACK_NAME}.zip" . -x '*.DS_Store')
cp -R config kubejs mods vaultpatcher 可选mods-拼音搜索 "$CSTAGE/"
cp installer/install.sh installer/install.ps1 "installer/双击安装-Windows.bat" "$CSTAGE/"
cp README.md CHANGELOG.md LICENSE "关于内置汉化Mod的说明(BBSMC).txt" "原版说明与致谢(BBSMC).txt" "$CSTAGE/"
printf '[InternetShortcut]\r\nURL=https://github.com/chiba233/atm10-zh-cn\r\n' > "$CSTAGE/项目主页与反馈.url"
chmod +x "$CSTAGE/install.sh"

# ---------- 服务端包 ----------
SSTAGE="dist/${BASE}-服务端"
rm -rf "$SSTAGE"
mkdir -p "$SSTAGE/mods" "$SSTAGE/vaultpatcher/modules"
cp mods/vaultpatcher.jar "$SSTAGE/mods/"
# 蜂名迁移脚本（KubeJS 服务端）：按 NBT ID 改写老蜂笼/老实体的显示名
# （不再用语言注入 mod —— 服务端数据必须保持上游英文，否则与 JEI/配方分裂）
mkdir -p "$SSTAGE/kubejs/server_scripts"
cp kubejs/server_scripts/pb_hanhua_cage_migrate.js "$SSTAGE/kubejs/server_scripts/"
# 服务端安全模块子集（清单与准入标准见 scripts/server_modules.txt，check.py 把关）
grep -v '^#' scripts/server_modules.txt | while IFS= read -r m; do
  [ -n "$m" ] && cp "vaultpatcher/modules/$m.json" "$SSTAGE/vaultpatcher/modules/"
done
# 服务端 config 只带任务书语言与 VaultPatcher 主配置。
# ⚠️ mysticalcustomization 绝不能上服务端：服务器带改名后的作物配置会让
# 所有玩家进服时刷 "error creating crop with id null"（2026-07-24 实测定位）。
# 作物名汉化是纯客户端的。
mkdir -p "$SSTAGE/config"
cp -R config/ftbquests config/vaultpatcher_asm "$SSTAGE/config/"
cp SERVER.md "$SSTAGE/README-服务端.md"
cp LICENSE "$SSTAGE/"
printf '[InternetShortcut]\r\nURL=https://github.com/chiba233/atm10-zh-cn\r\n' > "$SSTAGE/项目主页与反馈.url"

# ---------- 压缩 ----------
find dist -name '.DS_Store' -delete
rm -f "dist/${BASE}-客户端-v${VERSION}.zip" "dist/${BASE}-服务端-v${VERSION}.zip"
(cd dist && zip -X -q -r "${BASE}-客户端-v${VERSION}.zip" "${BASE}-客户端")
(cd dist && zip -X -q -r "${BASE}-服务端-v${VERSION}.zip" "${BASE}-服务端")

for f in "dist/${BASE}-客户端-v${VERSION}.zip" "dist/${BASE}-服务端-v${VERSION}.zip"; do
  echo "已生成: $f ($(du -h "$f" | cut -f1))"
done
