# 네이버 뉴스 크롤러 (Naver News Crawler)

네이버 뉴스를 크롤링하여 키워드 기반 뉴스 데이터를 수집하고 엑셀로 저장하는 Python 프로젝트입니다.

## 주요 기능

- **키워드 기반 뉴스 검색**: 원하는 키워드로 뉴스 검색
- **다중 페이지 수집**: 스크롤 효과 시뮬레이션으로 대량 데이터 수집
- **날짜 범위 필터링**: 특정 기간 내 뉴스만 선별 수집
- **AND/OR 검색 조건**: 복합 키워드 검색 지원
- **노이즈 필터링**: 광고, 추천 등 불필요한 콘텐츠 제거
- **엑셀 자동 저장**: 수집된 데이터를 구조화된 엑셀 파일로 저장
- **중복 제거**: 같은 뉴스 중복 수집 방지

## 설치 방법

### 필요한 Python 버전
- Python 3.7 이상

### 의존성 설치
```bash
pip install requests beautifulsoup4 pandas openpyxl
```

### 선택적 의존성 (고급 기능용)
```bash
pip install selenium webdriver-manager  # 동적 콘텐츠 수집용
```

## 프로젝트 구조

```
news_analyzer/
├── src/news_analyzer/
│   ├── naver_crawler.py          # 기본 크롤러
│   ├── advanced_naver_crawler.py # 고급 검색 크롤러
│   └── __init__.py
├── tests/
│   ├── test_crawler_safe.py      # 기본 테스트
│   ├── test_crawler_excel.py     # 엑셀 저장 테스트
│   └── debug_crawler.py          # HTML 구조 디버깅
├── scripts/
│   └── news_search_interface.py  # 사용자 인터페이스
└── README.md
```

## 사용 방법

### 1. 기본 크롤링
```python
from news_analyzer.naver_crawler import NaverNewsCrawler

crawler = NaverNewsCrawler()

# 단일 페이지 검색
items = crawler.search_news_html("삼성전자")

# 다중 페이지 검색 (스크롤 효과 시뮬레이션)
items = crawler.search_news_html_multi_page("삼성전자", max_pages=5)
```

### 2. 고급 검색 (날짜 범위 + AND/OR 조건)
```python
from advanced_naver_crawler import AdvancedNaverNewsCrawler

crawler = AdvancedNaverNewsCrawler()

# AND 검색: 모든 키워드 포함
results = crawler.search_news_advanced(
    keywords=["삼성전자", "반도체"],
    operator="AND",
    start_date="2024-01-01",
    end_date="2024-01-31",
    max_pages=3
)

# OR 검색: 키워드 중 하나라도 포함  
results = crawler.search_news_advanced(
    keywords=["LG화학", "현대차"],
    operator="OR",
    max_pages=2
)
```

### 3. 대화형 인터페이스
```python
from news_search_interface import NewsSearchInterface

interface = NewsSearchInterface()
interface.run()  # 메뉴 기반 대화형 검색
```

### 4. 테스트 및 디버깅
```bash
# 기본 테스트
python tests/test_crawler_safe.py

# 엑셀 저장 테스트  
python tests/test_crawler_excel.py

# HTML 구조 분석
python tests/debug_crawler.py
```

## 핵심 Python 모듈 소개

### 웹 크롤링 관련

#### `requests`
- HTTP 요청 처리를 위한 라이브러리
- 네이버 서버에 GET 요청을 보내 HTML을 가져옴
```python
response = requests.get(url, headers=headers, timeout=10)
```

#### `beautifulsoup4`
- HTML/XML 파싱 라이브러리
- 네이버 뉴스 페이지에서 원하는 요소 추출
```python
soup = BeautifulSoup(response.text, "html.parser")
news_links = soup.find_all("a", href=lambda x: x and "news.naver.com" in x)
```

### 데이터 처리 관련

#### `pandas`
- 데이터 분석 및 조작 라이브러리
- 수집된 뉴스 데이터를 DataFrame으로 구조화
```python
df = pd.DataFrame(news_items)
df.to_excel("news_data.xlsx", index=False)
```

#### `openpyxl`
- Excel 파일 읽기/쓰기 라이브러리
- pandas와 연동하여 엑셀 파일 생성
```python
df.to_excel(filename, index=False, engine='openpyxl')
```

### 시간 및 날짜 처리

#### `datetime`
- 날짜/시간 조작을 위한 내장 모듈
- 크롤링 시간 기록, 날짜 범위 계산
```python
from datetime import datetime, timedelta
crawl_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
```

#### `time`
- 시간 관련 기능 제공
- 요청 간 딜레이로 봇 탐지 회피
```python
import time
time.sleep(random.uniform(1, 3))  # 1-3초 랜덤 대기
```

### 유틸리티 모듈

#### `re` (정규표현식)
- 텍스트 패턴 매칭
- 날짜 형식 파싱 ("3일전" → "2025-09-10")
```python
day_match = re.search(r'(\d+)일전', date_text)
```

#### `urllib.parse`
- URL 인코딩/디코딩
- 검색 파라미터를 URL에 안전하게 추가
```python
url = base_url + "?" + urllib.parse.urlencode(params)
```

#### `itertools`
- 반복자 도구 모음
- User-Agent 순환 사용
```python
self._ua_cycle = itertools.cycle(self.user_agents)
```

#### `random`
- 난수 생성
- 요청 간격을 랜덤화하여 자연스러운 크롤링
```python
delay = random.uniform(1.0, 3.0)
```

### 선택적 모듈 (고급 기능)

#### `selenium` (선택사항)
- 브라우저 자동화 라이브러리
- JavaScript가 동적으로 로드하는 콘텐츠 수집
```python
from selenium import webdriver
driver = webdriver.Chrome()
driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
```

## 데이터 출력 형식

### 기본 데이터 구조
```python
{
    "title": "삼성전자, 3분기 실적 발표...",
    "link": "https://news.naver.com/article/...",
    "keyword": "삼성전자",
    "source": "html",
    "crawl_time": "2025-09-13 14:30:22"
}
```

### 고급 검색 데이터 구조
```python
{
    "title": "삼성전자 반도체 부문 실적...",
    "link": "https://news.naver.com/article/...",
    "keywords": ["삼성전자", "반도체"],
    "operator": "AND",
    "search_start_date": "2024-01-01",
    "search_end_date": "2024-01-31",
    "article_date": "2024-01-15",  # 파싱된 기사 날짜
    "media": "연합뉴스",
    "source": "advanced_search",
    "crawl_time": "2025-09-13 14:30:22"
}
```

## 주요 함수 설명

### `NaverNewsCrawler` 클래스

#### `search_news_html(keyword, start=1)`
- 단일 페이지 뉴스 검색
- 기본적인 HTML 파싱 수행

#### `search_news_html_multi_page(keyword, max_pages=3)`
- 다중 페이지 뉴스 검색
- 스크롤 효과 시뮬레이션
- 중복 제거 자동 수행

#### `save_to_excel(results, filename=None)`
- 수집된 데이터를 엑셀로 저장
- 자동 파일명 생성 (타임스탬프 포함)

### `AdvancedNaverNewsCrawler` 클래스

#### `build_search_query(keywords, operator)`
- 키워드 리스트를 네이버 검색 쿼리로 변환
- AND: "삼성전자 반도체"
- OR: "삼성전자|반도체"

#### `build_search_url(keywords, operator, start_date, end_date, start)`
- 날짜 필터가 포함된 검색 URL 생성
- nso 파라미터로 날짜 범위 지정

#### `search_news_advanced(keywords, operator, start_date, end_date, max_pages)`
- 고급 검색 기능의 메인 함수
- 모든 고급 기능을 통합하여 제공

## 봇 탐지 회피 전략

1. **User-Agent 로테이션**: 여러 브라우저 헤더를 순환 사용
2. **랜덤 딜레이**: 요청 간 1-3초 랜덤 대기
3. **헤더 다양화**: Accept, Language 등 실제 브라우저와 유사한 헤더
4. **요청 속도 제한**: 페이지당 2초 이상 간격 유지

## 문제 해결

### 일반적인 오류

#### ImportError: No module named 'requests'
```bash
pip install requests beautifulsoup4
```

#### 수집된 뉴스가 0개인 경우
- 네이버가 HTML 구조를 변경했을 가능성
- `debug_crawler.py`로 실제 HTML 구조 확인

#### 엑셀 저장 실패
```bash
pip install pandas openpyxl
```

### 성능 최적화

- `max_pages` 값을 적절히 조정 (권장: 2-5페이지)
- 네트워크 상황에 따라 timeout 값 조정
- 메모리 사용량을 고려하여 배치 크기 조정

## 라이선스

MIT License

## 기여하기

1. 이슈 등록: 버그 리포트나 기능 요청
2. 풀 리퀘스트: 코드 개선사항 제출
3. 테스트: 다양한 환경에서의 테스트 결과 공유

## 주의사항

- 네이버 서비스 약관을 준수하여 사용
- 과도한 요청으로 서버에 부하를 주지 않도록 주의
- 상업적 사용 시 저작권 및 이용 약관 확인 필요
- 수집된 데이터의 개인정보 보호 규정 준수