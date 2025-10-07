#!/usr/bin/env bash
set -euo pipefail

queries=(
  "무분별한토지이용 논란"
  "무분별한토지이용 문제"
  "무분별한토지이용 부정적"
  "무분별한토지이용 악화"
  "무분별한토지이용 위기"
  "생물다양성파괴 논란"
  "생물다양성파괴 문제"
  "생물다양성파괴 부정적"
  "생물다양성파괴 악화"
  "생물다양성파괴 위기"
  "생태계파괴 논란"
  "생태계파괴 문제"
  "생태계파괴 부정적"
  "생태계파괴 악화"
  "생태계파괴 위기"

)

for q in "${queries[@]}"; do
  PYTHONUTF8=1 PYTHONIOENCODING=utf-8 \
  python -X utf8 main.py compare-sentences \
    --query "$q" \
    --input ./input/articles5.xlsx \
    -e results5.xlsx
done
