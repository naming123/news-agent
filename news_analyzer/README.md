# News Analyzer / Naver News Crawler

네이버 **뉴스 검색 Open API**를 사용해서 키워드/기간 기반으로 뉴스 데이터를 수집하고, 배치 실행(엑셀 입력) 및 자동 재시도/백오프를 지원하는 도구입니다.


## 🧰 요구 사항
- Python 3.9+
- 네이버 개발자센터 **뉴스 검색(Open API – 뉴스)** 권한이 활성화된 애플리케이션
- 패키지: `requests`, `python-dotenv`, `pandas`, `openpyxl` (배치/엑셀 사용 시)

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate
pip install -U pip
pip install requests python-dotenv pandas openpyxl
```

🔐 환경 변수(.env)

루트에 .env 파일을 만들고 다음 값을 설정하세요. 양끝 공백/따옴표/개행이 섞이지 않도록 주의하세요.

```
NAVER_CLIENT_ID=your_client_id
NAVER_CLIENT_SECRET=your_client_secret
```


🚀 빠른 시작
### 1) 단일 쿼리 실행
```
python -m news_collector.search \
  --query "한빛네트 품질논란" \
  --display 100 --sort date \
  --from 2024-01-01 --to 2025-10-03 \
  --out results/hanbitnet_issue.json
```

옵션 설명:
  1. --query: 검색어
  2. --display: 한 번에 가져올 문서 수(최대 100)
  3. --sort: sim(유사도) | date(최신순)
  4. --from, --to: ISO 날짜(로컬 필터링). 네이버 기본 API는 기간 파라미터가 없으므로 결과의 pubDate를 기준으로 내부 필터링합니다.
  5. --out: 저장 경로(JSON/CSV 자동 감지 가능하도록 구현 시 확장자에 맞춰 저장)

### 2) 엑셀 배치 실행

input/NEWS.xlsx의 queries 시트에서 키워드 목록을 읽어 일괄 수집합니다.

```
python -m src.news_collector.ioHandle.batch_crawler     --inp
ut ./input/NEWS.xlsx     --output-sheet output     --inplace 
```

  1. --inplace: 같은 파일 내 output 시트에 결과를 작성
  2. --sheet: 입력 시트명
  3. --output-sheet: 출력 시트명

### 🩺 문제 해결(트러블슈팅)

**401/403 Unauthorized**

 > 개발자센터 사용 API → 검색 → 뉴스가 활성화되어 있는가?
 .env 로딩 경로가 맞는가? (find_dotenv/load_dotenv 사용)
 NAVER_CLIENT_ID/SECRET에 공백/따옴표/개행이 섞이지 않았는가? strip() 권장
 (웹 서비스 환경과 무관) 뉴스 검색은 비로그인 오픈 API라 서비스 URL 등록과는 관계 없음
 앱 제한(허용 IP/Referer)을 걸어놨다면 현재 실행 환경과 일치하는가?

**429 Rate Limit (제일 많이 발생하는 문제)**

> 자동 백오프가 동작합니다. 빈번하면 쿼리 수/동시성을 줄이세요.
4xx 기타(400/404 등)
쿼리/파라미터 형식 점검. 인코딩 문제 여부 확인

### 🧪 연결/인증 점검 (401/403 관련)
**.env파일 확인**
```
curl -v "https://openapi.naver.com/v1/search/news.json?query=한빛네트" \
  -H "X-Naver-Client-Id: <YOUR_ID>" \
  -H "X-Naver-Client-Secret: <YOUR_SECRET>"
```

```
📝 로그 예시와 의미
[HTTP] status=429 params={...}
[429 Rate Limit] 1/5 재시도, 1.6초 대기...
[HTTP] status=200 params={...}
[HTTP] total=123 items=100
```
1. 200 OK: 키 유효
2. 401 Unauthorized: 아래 문제 해결을 참고
3. 429: 호출 한도. 지수 백오프 + 지터로 자동 재시도
4. 5xx: 서버 오류. 백오프 후 재시도
5. 401/403: 인증/권한. 즉시 중단(재시도 무의미) → 아래 체크