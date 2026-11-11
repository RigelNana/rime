#!/usr/bin/env bash
set -euo pipefail

reload=false
if [[ $# -gt 1 ]]; then
  echo "用法：bash scripts/deploy.sh [--reload]" >&2
  exit 2
fi
case "${1:-}" in
  "") ;;
  --reload) reload=true ;;
  -h|--help)
    echo "用法：bash scripts/deploy.sh [--reload]"
    echo "准备个人词库、生成蓝三与小鹤扩展词库并编译；--reload 同时重新加载当前用户的 Fcitx5 Rime。"
    exit 0
    ;;
  *)
    echo "未知参数：$1" >&2
    exit 2
    ;;
esac

rime_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
shared_dir="${RIME_SHARED_DATA_DIR:-/usr/share/rime-data}"
python3 "$rime_dir/scripts/prepare.py"
rime_deployer --build "$rime_dir" "$shared_dir"
if [[ "$reload" == true ]]; then
  busctl --user call org.fcitx.Fcitx5 /controller org.fcitx.Fcitx.Controller1 ReloadAddonConfig s rime
fi
