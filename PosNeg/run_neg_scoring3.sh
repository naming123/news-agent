#!/usr/bin/env bash
set -euo pipefail

queries=(
  "ESG금융 논란"
  "ESG금융 문제"
  "ESG금융 부정적"
  "ESG금융 악화"
  "ESG금융 위기"
  "녹색금융 논란"
  "녹색금융 문제"
  "녹색금융 부정적"
  "녹색금융 악화"
  "녹색금융 위기"
  "환경영향금융 논란"
  "환경영향금융 문제"
  "환경영향금융 부정적"
  "환경영향금융 악화"
  "환경영향금융 위기"

)

for q in "${queries[@]}"; do
  PYTHONUTF8=1 PYTHONIOENCODING=utf-8 \
  python -X utf8 main.py compare-sentences \
    --query "$q" \
    --input ./input/articles3.xlsx \
    -e results3.xlsx
done
