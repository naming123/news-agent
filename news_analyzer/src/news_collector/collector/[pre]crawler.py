# news_analyzer/collector/crawler.py
import os
import re
import time
import random
import hashlib
import logging
from pathlib import Path
from typing import List, Optional
from urllib.parse import urlencode

import requests
from bs4 import BeautifulSoup

from ..config.models import CrawlerConfig, NewsArticle

logger = logging.getLogger(__name__)


class NaverNewsCrawler:
    BASE_URL = "https://search.naver.com/search.naver"

    def __init__(self, config: CrawlerConfig):
        self.config = config
        self.session = requests.Session()

        # 실제 브라우저 UA 풀 (필요시 추가)
        self._ua_pool = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_6_1) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.3 Safari/605.1.15",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
        ]
        # (선택) 크롬에서 복사한 쿠키를 환경변수로 주입하면 사용: NV_COOKIE="NNB=...; nid_b=...; ..."
        self._cookie_str = os.environ.get("NV_COOKIE", "").strip()

    def close(self):
        self.session.close()

    # --------------------- Helpers ---------------------
    def _build_headers(self) -> dict:
        import random
        ref_pool = [
            "https://www.naver.com/",
            "https://news.naver.com/",
            "https://search.naver.com/search.naver?sm=tab_hty.top&where=nexearch&query=%EB%89%B4%EC%8A%A4",
        ]
        h = {
            "User-Agent": random.choice(self._ua_pool),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
            "Referer": random.choice(ref_pool),
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        }
        if self._cookie_str:
            h["Cookie"] = self._cookie_str
        return h


    def _looks_blocked(self, html: str) -> bool:
        text = (html or "").lower()
        hit_words = [
            "자동 입력 방지", "자동입력 방지", "로봇이 아닙니다",
            "captcha", "vaptcha", "비정상적인 트래픽",
            "잠시 후 다시", "보호조치", "access denied",
        ]
        return any(w.lower() in text for w in hit_words)

    def _to_nso_range(self, date_from: Optional[str], date_to: Optional[str]) -> str:
        """
        입력이 'YYYY.MM.DD' 또는 'YYYY-MM-DD' 모두 올 수 있으니 숫자만 남겨서 NSO 구성.
        """
        if not date_from or not date_to:
            return ""
        f = re.sub(r"\D", "", date_from)  # 2024.01.01 or 2024-01-01 -> 20240101
        t = re.sub(r"\D", "", date_to)
        if len(f) != 8 or len(t) != 8:
            return ""
        return f"so:dd,p:from{f}to{t}"

    def _build_url(self, query: str, page: int, date_from: Optional[str], date_to: Optional[str]) -> str:
        start = (page - 1) * 10 + 1  # 1, 11, 21, ...
        nso = self._to_nso_range(date_from, date_to)
        params = {
            "where": "news",
            "query": query,
            "sm": "tab_opt",
            "start": start,
            "sort": 1,  # 최신순
        }
        if nso:
            params["nso"] = nso
        return f"{self.BASE_URL}?{urlencode(params, doseq=True)}"

    def _debug_dump(self, query: str, page: int, html: str, reason: str = "no_results"):
        try:
            safe = hashlib.md5(query.encode("utf-8")).hexdigest()[:8]
            outdir = Path("./debug/html")
            outdir.mkdir(parents=True, exist_ok=True)
            path = outdir / f"{safe}_p{page}_{reason}.html"
            path.write_text(html or "", encoding="utf-8")
            logger.warning(f"[DEBUG] Saved HTML snapshot -> {path}")
        except Exception as e:
            logger.error(f"[DEBUG] dump failed: {e}", exc_info=True)

    def _parse_news(self, html: str, query: str) -> List[NewsArticle]:
        """
        파싱 기준: 항상 존재하는 제목 앵커 a.news_tit를 기준으로 주변에서 press/날짜를 추출.
        """
        soup = BeautifulSoup(html, "html.parser")

        title_anchors = soup.select("a.news_tit")
        if not title_anchors:
            # 백업: 예외 구조
            title_anchors = soup.select("a[role='link'][href*='news.naver.com']")
            if not title_anchors:
                return []

        articles: List[NewsArticle] = []
        for a in title_anchors:
            title = a.get("title") or a.get_text(strip=True)
            link = a.get("href") or ""

            # 주변 정보
            wrap = a.find_parent(class_="news_wrap")
            info = wrap.select_one("div.news_info") if wrap else None
            if not info:
                # 상위/형제 탐색
                parent = a.parent
                for _ in range(3):
                    if not parent:
                        break
                    sib = parent.find_next_sibling()
                    if sib and (sib.select_one("div.news_info") or sib.select_one("span.info")):
                        info = sib
                        break
                    parent = parent.parent

            # 언론사
            press = ""
            if info:
                press_el = info.select_one("a.info.press") or info.select_one("span.info")
                if press_el:
                    press = press_el.get_text(strip=True)

            # 날짜(후보들 중 날짜/상대시간 추정)
            date_text = ""
            if info:
                infos = [i.get_text(strip=True) for i in info.select("span.info")]
                for t in reversed(infos):
                    if any(ch in t for ch in [".", "전", "오전", "오후", ":"]):
                        date_text = t
                        break

            articles.append(NewsArticle(
                title=title, link=link, press=press, date=date_text,
                keyword="", company="",
            ))
        return articles

    # --------------------- Main ---------------------
    def search(self, keyword: str, date_from: Optional[str] = None, date_to: Optional[str] = None,
           max_pages: int = 3) -> List[NewsArticle]:
        """
        네이버 뉴스 검색 (페이지네이션: 1,11,21…)
        - 랜덤 지연으로 사람처럼 동작
        - 403 시 지수 백오프 + 스냅샷
        - 차단 페이지 감지 시 쿨다운 후 '해당 키워드만' 포기
        """
        import random, time

        all_res: List[NewsArticle] = []
        seen = set()

        base_sleep = max(self.config.min_delay or 1.5, 1.5)   # 기본을 조금 더 느리게
        max_sleep  = max(self.config.max_delay or 4.5, base_sleep + 2.0)
        max_403_retry = 2  # 총 3회 시도

        for page in range(1, max_pages + 1):
            url = self._build_url(keyword, page, date_from, date_to)
            logger.info(f"Crawling page {page}: {url}")

            # 요청 전 랜덤 지연
            time.sleep(random.uniform(base_sleep, max_sleep))

            # 403 백오프 루프
            for attempt in range(max_403_retry + 1):
                try:
                    resp = self.session.get(url, headers=self._build_headers(), timeout=self.config.timeout)

                    if resp.status_code == 403:
                        logger.warning(f"403 Forbidden (page {page}, try {attempt+1}/{max_403_retry})")
                        self._debug_dump(keyword, page, resp.text, f"http_403_try{attempt+1}")
                        if attempt < max_403_retry:
                            time.sleep(base_sleep * (2 ** attempt) + random.uniform(0.7, 1.8))
                            continue
                        else:
                            logger.error(f"403 persisted. stop this query: {keyword}")
                            # 이 키워드 포기 (다음 키워드로)
                            return all_res

                    resp.raise_for_status()

                    # 차단/캡차 페이지 감지 → 쿨다운 후 '이 키워드'만 포기
                    if self._looks_blocked(resp.text):
                        logger.warning(f"Page looks blocked (captcha/robot) at page {page}; saving snapshot and cooling down.")
                        self._debug_dump(keyword, page, resp.text, "blocked")
                        time.sleep(random.uniform(max(6.0, base_sleep*2), max(12.0, max_sleep*2)))
                        return all_res

                    break  # 정상 응답

                except Exception as e:
                    logger.error(f"request failed (page {page}, try {attempt+1}): {e}", exc_info=True)
                    html = ""
                    try:
                        if hasattr(e, "response") and e.response is not None:
                            html = e.response.text
                    except Exception:
                        pass
                    self._debug_dump(keyword, page, html, "http_error")

                    if attempt >= max_403_retry:
                        # 이 키워드 포기 (다음 키워드로)
                        return all_res
                    time.sleep(base_sleep * (2 ** attempt) + random.uniform(0.7, 1.8))

            # ===== 파싱 =====
            page_articles = self._parse_news(resp.text, keyword)
            if not page_articles:
                logger.info(f"No more results at page {page} (stop early)")
                self._debug_dump(keyword, page, resp.text, "no_results")
                break

            # 중복 제거(링크 기준)
            added = 0
            for a in page_articles:
                if a.link and a.link in seen:
                    continue
                seen.add(a.link)
                all_res.append(a)
                added += 1

            # 다음 페이지 전 랜덤 지연
            time.sleep(random.uniform(base_sleep, max_sleep))

            if added == 0:
                logger.info(f"No incremental results at page {page} (stop early)")
                break

        return all_res

