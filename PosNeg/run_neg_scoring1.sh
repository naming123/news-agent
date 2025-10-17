#!/usr/bin/env bash
set -euo pipefail

queries=(
  "그린하우스가스(GHG)배출 논란"
  "그린하우스가스(GHG)배출 문제"
  "그린하우스가스(GHG)배출 부정적"
  "그린하우스가스(GHG)배출 악화"
  "그린하우스가스(GHG)배출 위기"
  "온실가스배출 논란"
  "온실가스배출 문제"
  "온실가스배출 부정적"
  "온실가스배출 악화"
  "온실가스배출 위기"
  "탄소배출 논란"
  "탄소배출 문제"
  "탄소배출 부정적"
  "탄소배출 악화"
  "탄소배출 위기"
)

for q in "${queries[@]}"; do
  PYTHONUTF8=1 PYTHONIOENCODING=utf-8 \
  python -X utf8 main.py compare-sentences \
    --query "$q" \
    --input ./input/articles1.xlsx \
    -e results1.xlsx
done
