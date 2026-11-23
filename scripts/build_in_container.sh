#!/usr/bin/env bash
# atm10-zh-cn — All the Mods 10 简体中文汉化补丁「绿油油版」
# Copyright (C) 2026 星野夢華 (Hoshino Yumeka)
# SPDX-License-Identifier: GPL-3.0-or-later
#
# 在锁定的容器里构建，产出字节可复现的包。
#
# 平时直接跑 build_dist.sh 也能出包，只是那份包的 sha256 不作数，你的 Pillow、
# 你的 freetype、你的 zlib 都跟别人不一样，PNG 的字节自然不一样。要拿哈希跟
# CI 的产物对，就得在同一套工具链里跑，那套工具链钉在 src/toolchain.lock.json。
#
# 用法:
#   ./scripts/build_in_container.sh                 # 默认跑 generate_all + build_dist
#   ./scripts/build_in_container.sh python3 -V      # 或者在里面跑任意命令
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOCK="$ROOT/src/toolchain.lock.json"

DIGEST=$(python3 -c "import json;print(json.load(open('$LOCK'))['canonical_env']['digest'])")
IMAGE=$(python3 -c "import json;print(json.load(open('$LOCK'))['canonical_env']['image'].split(':')[0])")
REF="${IMAGE}@${DIGEST}"

RUNTIME=""
for c in podman docker; do
    if command -v "$c" >/dev/null 2>&1; then RUNTIME="$c"; break; fi
done
if [ -z "$RUNTIME" ]; then
    echo "❌ 没有 podman 也没有 docker。" >&2
    echo "   装一个，或者接受「本机构建、哈希不作数」——" >&2
    echo "   scripts/toolchain.py 会明说这一点，不会假装能比。" >&2
    exit 1
fi

echo "镜像: $REF"
echo "运行时: $RUNTIME"

# 按 digest 拉，不按 tag：tag 会被重新指向，digest 不会。
exec "$RUNTIME" run --rm \
    -v "$ROOT:/w" -w /w \
    -e ATM_TOOLCHAIN_DIGEST="$DIGEST" \
    -e ATM_PACK_ROOT="${ATM_PACK_ROOT:-}" \
    "$REF" \
    bash -euo pipefail -c '
        python -m pip install --quiet --require-hashes -r requirements.lock
        python3 scripts/toolchain.py --strict
        '"${*:-./scripts/generate_all.sh && ./scripts/build_dist.sh}"'
    '
