```
word2vec_similarity/
├── config/
│   ├── __init__.py
│   └── settings.py          # 설정 (모델, 지표 정의)
├── models/
│   ├── __init__.py
│   └── loader.py            # 모델 로더
├── metrics/
│   ├── __init__.py
│   ├── base.py              # 추상 클래스
│   └── implementations.py   # 유사도 지표 구현
├── analyzers/
│   ├── __init__.py
│   └── analyzer.py          # 분석 엔진
├── utils/
│   ├── __init__.py
│   ├── result.py            # 결과 클래스
│   └── exporter.py          # 엑셀/CSV 출력
├── cli.py                   # CLI 인터페이스
├── main.py                  # 메인 + 한 줄 실행 함수
├── results/                 # 출력 폴더 (자동 생성)
└── requirements.txt
```




# 1. 엑셀 파일 입력
```
python main.py compare-sentences \
  -q "부정" \
  --input ./input/articles.xlsx \
  --column "설명" \
  -m fasttext-multilingual \
  --metric cosine \
  -e result.xlsx
```

# ★ 2. sentence-transformers
```
user@DESKTOP-JM15LC3 MINGW64 ~/yalco-Docker/data_project/PosNeg (main)it/s가 몇 초?
$ python main.py compare-sentences --query "부정" --input ./input/articles.xlsx -e result.xlsx
```

# 3. 영한 혼용
mixed.xlsx

```
python main.py compare-sentences \
  -q "negative" \
  -m multilingual \
  --input mixed.xlsx \
  -e result.xlsx


python main.py compare-sentences -q "부정" -m multilingual --input sentences.xlsx
```