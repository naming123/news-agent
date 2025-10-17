#!/usr/bin/env bash
set -euo pipefail

queries=(
  "기업탄소배출계수 논란"
  "기업탄소배출계수 문제"
  "기업탄소배출계수 부정적"
  "기업탄소배출계수 악화"
  "기업탄소배출계수 위기"
  "제품온실가스 논란"
  "제품온실가스 문제"
  "제품온실가스 부정적"
  "제품온실가스 악화"
  "제품온실가스 위기"
  "제품탄소발자국 논란"
  "제품탄소발자국 문제"
  "제품탄소발자국 부정적"
  "제품탄소발자국 악화"
  "제품탄소발자국 위기"
)

for q in "${queries[@]}"; do
  PYTHONUTF8=1 PYTHONIOENCODING=utf-8 \
  python -X utf8 main.py compare-sentences \
    --query "$q" \
    --input ./input/articles4.xlsx \
    -e results4.xlsx
done
