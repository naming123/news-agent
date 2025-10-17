# 네이버 뉴스 배치 크롤러

네이버 뉴스를 **엑셀 키워드 기반으로 자동 수집**하고, 결과를 정리된 엑셀 파일로 저장하는 Python 프로젝트입니다.  
개별 크롤러를 확장하여 **여러 키워드를 배치(batch)로 실행**할 수 있도록 설계되었습니다.

## 주요 기능
- 입력: `input.xlsx`의 **Keywords 시트** 또는 **ESG 시트(D열)**에서 키워드 자동 로드
- 처리: 키워드별 네이버 뉴스 검색 → 기사 수집 → 회사/키워드별로 분류
- 출력: `./output/` 폴더에 요약, 전체, 회사별 결과를 포함한 2종 엑셀 자동 저장

## 배치 크롤러 역할
- 엑셀에서 키워드 및 설정(Config) 읽기  
- `NaverNewsCrawler` 실행 및 기사 수집 관리  
- **회사별/키워드별 집계 및 엑셀 저장**까지 책임

## 시간 관련 처리
- 키워드 간 요청은 `min_delay`~`max_delay` 범위에서 **랜덤 대기**로 서버 부하 완화  
- `Config` 시트의 `date_from`, `date_to` 설정으로 **기간 필터링** 지원

<!-- ## 실행 방법
```bash
cd news_analyzer/src
python -m news_collector.ioHandle.batch_crawler /input/input.xlsx 
``` -->

## ★ UI 사용방법
```bash
streamlit run app.py
streamlit run app.py --server.openBrowser false
streamlit run app.py --server.headless true
```


python -m news_collector.ioHandle.batch_crawler --input ../input/NEWS.xlsx --output-sheet output --inplace
