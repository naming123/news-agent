### setting
pip install -r requirements.txt




# output 시트에서 기사 읽고, ESG 시트의 '뉴스 키워드 후보'별 키워드 묶음을 자동 적용
python score_esg_negative.py --dedup dedup.xlsx --esg ESGvsFinancialKeywords_UI.xlsx

# 텍스트 컬럼 지정이 필요하면
python test.py --dedup ./input/input.xlsx --esg ./input/ESGvsFinancialKeywords_UI.xlsx --text-col 기사제목

# 임계치/출력 경로 조정
python score_esg_negative.py --dedup dedup.xlsx --esg ESGvsFinancialKeywords_UI.xlsx --threshold 0.5 --out result.xlsx
