#!/usr/bin/env bash
set -euo pipefail

queries=(
  "기후변화유발 논란"
  "기후변화유발 문제"
  "기후변화유발 부정적"
  "기후변화유발 악화"
  "기후변화유발 위기"
  "기후위험 논란"
  "기후위험 문제"
  "기후위험 부정적"
  "기후위험 악화"
  "기후위험 위기"
  "기후취약성 논란"
  "기후취약성 문제"
  "기후취약성 부정적"
  "기후취약성 악화"
  "기후취약성 위기"

)

for q in "${queries[@]}"; do
  PYTHONUTF8=1 PYTHONIOENCODING=utf-8 \
  python -X utf8 main.py compare-sentences \
    --query "$q" \
    --input ./input/articles2.xlsx \
    -e results2.xlsx
done
