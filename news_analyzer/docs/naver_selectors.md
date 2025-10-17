# 네이버 뉴스 크롤러 셀렉터 & 파라미터 (요약)

네이버 뉴스 DOM은 자주 바뀌므로, 크롤러 유지보수에 필요한 핵심 정보만 정리합니다.

---

## 1. 주요 셀렉터
- **제목/링크**: `a.news_tit`
- **언론사**: `a.info.press`
- **날짜**: `span.info`

> 기본 루트: `ul.list_news > li a.news_tit`  
> 폴백: `div.news_area a.news_tit`, `.list_news a[href*='news.naver.com']`, `a[href*='n.news.naver.com']`

---

## 2. 날짜 필터 파라미터
- `pd=3` : 사용자 지정 기간
- `ds=YYYY.MM.DD` : 시작일
- `de=YYYY.MM.DD` : 종료일
- `nso=so:r,p:fromYYYYMMDDtoYYYYMMDD`

예시:
...?where=news&query=삼성전자&pd=3&ds=2024.09.01&de=2024.09.13&nso=so:r,p:from20240901to20240913

yaml
코드 복사

---

## 3. 페이지네이션
- `start=1`   → 1~10번째 기사
- `start=11`  → 11~20번째 기사
- `start=21`  → 21~30번째 기사

공식: **page N → start = (N-1) * 10 + 1**

---

## 4. 안티봇 신호
HTML에 아래 단어가 있으면 차단 상태일 수 있음:
- `보안문자`
- `로봇이 아닙니다`
- `captcha`

👉 대응: 헤더 강화, 요청 간 랜덤 지연, 세션 유지, 디버그 HTML 저장

---