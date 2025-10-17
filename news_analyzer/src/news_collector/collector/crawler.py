
# naver_news_crawler.py
from __future__ import annotations

import os
import json
import re
import time
import random
from typing import Any, List, Dict, Optional
from datetime import datetime, date, timezone, timedelta
from email.utils import parsedate_to_datetime
import requests
import html
from pathlib import Path


class NaverNewsCrawler:
    """네이버 Open API 기반 뉴스 크롤러 (기간 필터 & 무제한 수집 지원)"""

    BASE_URL = "https://openapi.naver.com/v1/search/news.json"


    def __init__(self, client_id: str | None = None, client_secret: str | None = None, timeout: float = 10.0,
        config: dict | None = None):
        # 1) .env 로드: 어디서 실행하든 루트 .env를 찾게
        try:
            from dotenv import load_dotenv, find_dotenv  # type: ignore
            dotenv_path = find_dotenv(filename=".env", usecwd=True)
            if not dotenv_path:
                # 파일 기준으로 상위 폴더들에서도 탐색
                here = Path(__file__).resolve()
                for p in [here.parent, here.parent.parent, here.parent.parent.parent]:
                    cand = p / ".env"
                    if cand.exists():
                        dotenv_path = str(cand)
                        break
            if dotenv_path:
                load_dotenv(dotenv_path=dotenv_path, override=True)
        except Exception:
            pass
        
        
        # 1) 기본값 + config 병합
        cfg = {
            "timeout": 10.0,
            "min_delay": 2.0,
            "max_delay": 4.0,
            "max_page": 3,
            "max_retries": 3,     # 429 등 재시도 횟수
            "backoff_base": 30,  # 백오프 시작(sec)
        }
        if config:
            # 타입 안전하게 덮어쓰기
            for k, v in config.items():
                cfg[k] = v

        # timeout 우선순위: (인자) > (config) > (기본)
        if timeout is not None:
            cfg["timeout"] = float(timeout)
        # 2) 키 읽기 + 공백/개행 방지
        env_id = (os.getenv("NAVER_CLIENT_ID") or "").strip()
        env_secret = (os.getenv("NAVER_CLIENT_SECRET") or "").strip()

        self.client_id = (client_id or env_id).strip()
        self.client_secret = (client_secret or env_secret).strip()

        if not self.client_id or not self.client_secret:
            raise ValueError(
                "네이버 API 키가 없습니다. .env(NAVER_CLIENT_ID, NAVER_CLIENT_SECRET) 또는 생성자 인자 확인"
            )
        # 3) 세션/헤더/설정
        self.timeout = float(cfg["timeout"])
        self.min_delay = float(cfg.get("min_delay", 2.0))
        self.max_delay = float(cfg.get("max_delay", 4.0))
        self.max_page  = int(cfg.get("max_page", 3))
        self.max_retries = int(cfg.get("max_retries", 3))
        self.backoff_base = int(cfg.get("backoff_base", 30))
        self.session = requests.Session()
        self.timeout = timeout
        self.headers = {
            "X-Naver-Client-Id": self.client_id,
            "X-Naver-Client-Secret": self.client_secret,
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        }

    # ---------------------------
    # Low-level API call
    # ---------------------------
    def search_news(self, query: str, start: int = 1, display: int = 10, sort: str = "date") -> Optional[Dict]:
        """네이버 뉴스 API 호출 (재시도 로직 포함)"""
        params = {"query": query, "start": start, "display": display, "sort": sort}
        
        max_retries = 5
        retry_count = 0
        base_backoff = 1.0
        last_status = None
        last_error = None

        while retry_count < max_retries:
            try:
                resp = self.session.get(self.BASE_URL, headers=self.headers, params=params, timeout=self.timeout)
                last_status = resp.status_code
                print(f"[HTTP] status={resp.status_code} params={params}")

                if resp.status_code == 200:
                    j = resp.json()
                    print(f"[HTTP] total={j.get('total')} items={len(j.get('items') or [])}")
                    return j

                # --- 재시도 케이스 ---
                if resp.status_code == 429:
                    # Rate limit: exponential backoff + jitter
                    wait_time = min(60.0, (base_backoff * (2 ** retry_count)) + random.uniform(0, 1))
                    print(f"[429 Rate Limit] {retry_count+1}/{max_retries} 재시도, {wait_time:.1f}초 대기...")
                    time.sleep(wait_time)
                    retry_count += 1
                    continue

                if 500 <= resp.status_code < 600:
                    # 서버 오류도 재시도 가치 있음
                    wait_time = min(60.0, (base_backoff * (2 ** retry_count)) + random.uniform(0, 1))
                    print(f"[5xx 서버 오류] {resp.status_code} → {retry_count+1}/{max_retries} 재시도, {wait_time:.1f}초 대기...")
                    time.sleep(wait_time)
                    retry_count += 1
                    continue

                # --- 즉시 종료 케이스 ---
                if resp.status_code in (401, 403):
                    print(f"[인증/권한 오류] status={resp.status_code} → 키/권한 확인 필요. 재시도 안 함.")
                    return None

                if 400 <= resp.status_code < 500:
                    print(f"[클라이언트 오류] status={resp.status_code} → 쿼리/파라미터 점검 필요. 재시도 안 함.")
                    return None

                # 기타 예상치 못한 상태코드
                print(f"[API 실패] status={resp.status_code}")
                return None

            except requests.exceptions.RequestException as e:
                last_error = e
                wait_time = min(30.0, (base_backoff * (2 ** retry_count)) + random.uniform(0, 1))
                print(f"[API 예외] {e} → {retry_count+1}/{max_retries} 재시도, {wait_time:.1f}초 대기...")
                time.sleep(wait_time)
                retry_count += 1

        print(f"[종료] 재시도 소진. last_status={last_status}, last_error={last_error}")
        return None

    # ---------------------------
    # Safe access & date parsing
    # ---------------------------
    @staticmethod
    def _safe_get(item: Any, key: str) -> Optional[Any]:
        """dict 또는 객체 속성에서 안전하게 값 가져오기"""
        if isinstance(item, dict):
            return item.get(key)
        return getattr(item, key, None)

    @staticmethod
    def _parse_any_date_string(s: str) -> Optional[date]:
        """여러 문자열 포맷(YYYY-MM-DD/./ /) 및 'n시간/일 전' 상대시간 파싱"""
        s = s.strip()
        # 2025-09-30 / 2025.09.30 / 2025/09/30
        for fmt in ("%Y-%m-%d", "%Y.%m.%d", "%Y/%m/%d"):
            try:
                return datetime.strptime(s[:10], fmt).date()
            except Exception:
                pass
        # 상대시간: '3시간 전', '2일 전', '15분 전' 등
        m = re.match(r"(\d+)\s*(초|분|시간|일)\s*전", s)
        if m:
            n = int(m.group(1))
            unit = m.group(2)
            delta_map = {"초": "seconds", "분": "minutes", "시간": "hours", "일": "days"}
            return (datetime.now() - timedelta(**{delta_map[unit]: n})).date()
        return None

    @classmethod
    def _to_ymd(cls, item: Any) -> date:
        """
        네이버 뉴스 item → date(YYYY-MM-DD)
        우선순위: pubDate(RFC822) > date/datetime/regDate > 상대시간 표현
        실패 시: UTC 오늘
        """
        pub = cls._safe_get(item, "pubDate") or cls._safe_get(item, "pubdate") or cls._safe_get(item, "pub_date")
        if pub:
            try:
                dt = parsedate_to_datetime(str(pub))
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return dt.date()
            except Exception:
                pass

        dval = cls._safe_get(item, "date") or cls._safe_get(item, "datetime") or cls._safe_get(item, "regDate")
        if dval:
            if isinstance(dval, datetime):
                return dval.date()
            if isinstance(dval, date):
                return dval
            parsed = cls._parse_any_date_string(str(dval))
            if parsed:
                return parsed

        # 마지막 보호: 오늘(UTC) 날짜
        return datetime.utcnow().date()

    # ---------------------------
    # Multi-page fetch with date window
    # ---------------------------
    def search_news_multiple_pages(
        self,
        query: str,
        max_results: Optional[int] = None,   # None이면: 결과 소진 or 기간 하한 도달까지
        date_from: Optional[str] = None,     # "YYYY-MM-DD"
        date_to: Optional[str] = None,       # "YYYY-MM-DD"
        sort: str = "date",                  # "date" 권장(최신순)
        sleep_range: tuple[float, float] = (0.1, 0.3),
    ) -> List[Dict]:
        """
        네이버 뉴스 API를 여러 페이지에 걸쳐 수집.
        - 최신순(date) 정렬 가정하에 date_from 이전으로 내려가면 조기 중단.
        - API 제약: start 최대 1000, display 최대 100.
        """
        all_items: List[Dict] = []
        page_size = 100
        current_start = 1
        hard_cap = 10000

        df = datetime.strptime(date_from, "%Y-%m-%d").date() if date_from else None
        dt_ = datetime.strptime(date_to,   "%Y-%m-%d").date() if date_to   else None

        while current_start <= hard_cap:
            if max_results is None:
                display_count = min(page_size, hard_cap - current_start + 1)
            else:
                remaining = max(0, max_results - len(all_items))
                if remaining == 0:
                    break
                display_count = min(page_size, remaining, hard_cap - current_start + 1)

            resp = self.search_news(query=query, start=current_start, display=display_count, sort=sort)
            if not resp or "items" not in resp:
                break
            items = resp["items"]
            if not items:
                break

            # 기간 필터
            batch_dates: List[date] = []
            filtered_batch: List[Dict] = []
            for it in items:
                d = self._to_ymd(it)
                batch_dates.append(d)
                if (df is None or d >= df) and (dt_ is None or d <= dt_):
                    filtered_batch.append(it)
            print(f"[PAGE] start={current_start} got={len(items)} kept={len(filtered_batch)} "
                    f"min={min(batch_dates) if batch_dates else None} max={max(batch_dates) if batch_dates else None} "
                    f"acc={len(all_items)}")
            if filtered_batch:
                all_items.extend(filtered_batch)

            # 1) 수집량 제한 도달
            if max_results is not None and len(all_items) >= max_results:
                all_items = all_items[:max_results]
                break

            # 2) 더 이상 결과 없음
            if len(items) < display_count:
                break

            # 3) 최신순 정렬 가정: 배치의 최저 날짜가 date_from 이전이면 이후는 더 과거 → 조기 종료
            if df is not None and batch_dates:
                if min(batch_dates) < df and max_results is None:
                    break

            current_start += display_count
            time.sleep(random.uniform(*sleep_range))
            print(f"[DONE] collected={len(all_items)}")
        return all_items

    # ---------------------------
    # Formatting
    # ---------------------------
    @staticmethod
    def _remove_html_tags(text: str) -> str:
        clean = re.sub(r"<[^>]+>", "", text or "")
        # HTML 엔티티 해제
        return html.unescape(clean)

    @classmethod
    def _format_date_from_item(cls, item: Dict) -> str:
        """item에서 날짜를 뽑아 YYYY-MM-DD 문자열로 반환"""
        try:
            d = cls._to_ymd(item)
            return d.strftime("%Y-%m-%d")
        except Exception:
            return datetime.utcnow().strftime("%Y-%m-%d")

    def format_news_data(self, items: List[Dict], keyword: str) -> List[Dict]:
        """
        API 응답을 내부 공통 포맷으로 변환
        """
        out: List[Dict] = []
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        for it in items:
            title = self._remove_html_tags(self._safe_get(it, "title") or "")
            description = self._remove_html_tags(self._safe_get(it, "description") or "")
            formatted_item = {
                "keyword": keyword,
                "title": title,
                "description": description,
                "link": self._safe_get(it, "link") or "",
                "original_link": self._safe_get(it, "originallink") or "",
                "pub_date": self._format_date_from_item(it),  # YYYY-MM-DD
                "crawl_time": now,
            }
            out.append(formatted_item)
        return out

    # ---------------------------
    # Lifecycle
    # ---------------------------
    def close(self):
        try:
            self.session.close()
        except Exception:
            pass


# ----------------------------------------
# 간단 테스트 & 기존 인터페이스 호환 래퍼
# ----------------------------------------
def search_news_api(keyword: str, num_items: int = 100,
                    date_from: Optional[str] = None, date_to: Optional[str] = None) -> List[Dict]:
    """기존 형태 유지용 래퍼"""
    crawler = NaverNewsCrawler()
    try:
        raw = crawler.search_news_multiple_pages(
            keyword,
            max_results=num_items,
            date_from=date_from,
            date_to=date_to,
        )
        return crawler.format_news_data(raw, keyword)
    finally:
        crawler.close()


if __name__ == "__main__":
    # 간단 실행 테스트
    try:
        crawler = NaverNewsCrawler()
        sample = crawler.search_news("삼성전자", start=1, display=5)
        if sample:
            print("=== API 응답 샘플 ===")
            print(json.dumps(sample, indent=2, ensure_ascii=False))

        print("\n=== 포맷된 뉴스 데이터 (10건, 최근 7일) ===")
        today = datetime.now().date()
        week_ago = (today - timedelta(days=7)).strftime("%Y-%m-%d")
        today_s = today.strftime("%Y-%m-%d")

        items = search_news_api("삼성전자", num_items=10, date_from=week_ago, date_to=today_s)
        for i, it in enumerate(items, 1):
            print(f"\n{i}. {it['title']}")
            print(f"   링크: {it['link']}")
            print(f"   날짜: {it['pub_date']}")
            print(f"   설명: {it['description'][:80]}...")
    except Exception as e:
        print("[테스트 오류]", e)


# 테스트 코드
if __name__ == "__main__":
    # 기본 테스트
    crawler = NaverNewsCrawler()
    
    # 단일 페이지 검색 테스트
    result = crawler.search_news("삼성전자", display=5)
    if result:
        print("=== API 응답 샘플 ===")
        print(json.dumps(result, indent=2, ensure_ascii=False))
    
    # 다중 페이지 검색 테스트
    print("\n=== 포맷된 뉴스 데이터 ===")
    news_items = search_news_api("삼성전자", num_items=10)
    
    for i, item in enumerate(news_items, 1):
        print(f"\n{i}. {item['title']}")
        print(f"   링크: {item['link']}")
        print(f"   날짜: {item['pub_date']}")
        print(f"   설명: {item['description'][:100]}...")