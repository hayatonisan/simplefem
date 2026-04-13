#!/bin/bash
# SIMPLEFEM / OpenSees / Kratos バトル実行スクリプト
set -e
BATTLE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$BATTLE_DIR"

echo "=============================="
echo " 片持ち梁バトル開始"
echo " L=50mm H=2mm t=0.01mm"
echo " E=210000MPa nu=0 P=0.1N"
echo "=============================="

python3 "$BATTLE_DIR/battle.py" "$@"
