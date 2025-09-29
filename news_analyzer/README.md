News Analyzer (Modular Demo)

~~~
🧪 테스트
export PYTHONPATH=./src:$PYTHONPATH
# python -m tests/test_datetime.py
~~~
### 해야할일
상황: 현재 엑셀로 필요한 날짜의 링크로 뽑는것까지 됨
- 날짜 입력가능
- 모듈 선택가능
- 링크로 해당 날짜안에 있는건 모두 액셀정리 가능

해야되는것
1. 해당 링크로 들어가서 내용가져오기
2. 내가 원하는 키워드로 검색하게 하기
3. 겹치는 뉴스에 대해서는 어떻게 필터링할지 생각해보기


네이버 뉴스 크롤링 → 감정(키워드) 분석 → 기업 식별 → 저장 파이프라인을 모듈화한 샘플 프로젝트입니다.
실제 네트워크 요청 없이 모의 데이터 또는 로컬 테스트 코드를 통해 동작을 재현합니다.

```markdown
📂 프로젝트 구조
news_analyzer/
  ├─ src/
  │  └─ news_analyzer/
  │     ├─ __init__.py
  │     ├─ sentiment_analyzer.py       # 기사 문장의 감정/키워드 분석기
  │     ├─ company_identifier.py       # 문장에서 기업명 식별기
  │     ├─ naver_crawler.py            # 모의 네이버 뉴스 크롤러 (기본 버전)
  │     ├─ naver_crawler_time.py       # ✅ 날짜 필터링/다중 페이지 지원 크롤러 (완성)
  │     └─ pipeline/
  │        ├─ __init__.py
  │        └─ news_pipeline.py         # 크롤링 → 분석 → 저장 전체 파이프라인
  ├─ scripts/
  │  └─ main.py                        # 데모 실행 스크립트
  ├─ tests/
  │  ├─ test_sentiment_analyzer.py     # 감정 분석기 단위 테스트
  │  ├─ test_company_identifier.py     # 기업 식별기 단위 테스트
  │  ├─ test_pipeline.py               # 전체 파이프라인 테스트
  │  └─ test_datetime.py               # ✅ naver_crawler_time 기능 테스트 (완성)
  ├─ requirements.txt
  └─ pyproject.toml

```

⚙️ 주요 컴포넌트 역할

### naver_crawler.py
간단한 모의 네이버 뉴스 크롤러. 네트워크 대신 무작위 샘플 기사를 반환.

### naver_crawler_time.py ✅
날짜 범위(date_from, date_to)와 다중 페이지 수집을 지원하는 크롤러.
언론사(press), 기사 날짜(date)까지 파싱하도록 확장됨.
테스트 파일 test_datetime.py로 정상 동작 검증 완료.

### sentiment_analyzer.py
뉴스 제목/본문에서 긍정/부정/중립 감정을 식별하고 주요 키워드를 뽑음.

### company_identifier.py
텍스트에서 기업명(예: 삼성전자, 네이버, LG전자 등)을 식별.

### pipeline/news_pipeline.py
크롤러 → 감정 분석 → 기업 식별 → 저장까지 이어지는 처리 파이프라인.

### scripts/main.py
파이프라인 실행 예시.

### tests/
각 모듈별 단위 테스트 + 통합 테스트 포함.
특히 test_datetime.py는 기간 필터링 + 다중 페이지 크롤링이 제대로 동작하는지 확인.

---

## ▶ 실행

개발 모드에서 실행하려면:

#### src 패키지 인식
export PYTHONPATH=./src:$PYTHONPATH
python scripts/main.py

🧪 테스트
export PYTHONPATH=./src:$PYTHONPATH
# python -m tests/test_datetime.py


모든 모듈이 단위 테스트 + 통합 테스트를 통과해야 합니다.
특히 test_datetime.py는 ✅ naver_crawler_time.py를 검증하는 최종 완성 테스트입니다.