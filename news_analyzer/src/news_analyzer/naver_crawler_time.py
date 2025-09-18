from __future__ import annotations
import os
import time, random, itertools
from typing import List, Dict

import requests
from bs4 import BeautifulSoup


class NaverNewsCrawler:
    """
    Naver News crawler with HTML parsing research
    """

    def __init__(self):
        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148",
        ]
        self._ua_cycle = itertools.cycle(self.user_agents)

    def _rotate_headers(self):
        return {"User-Agent": next(self._ua_cycle)}

    def _dump_debug_html(self, html: str, prefix="debug"):
        ts = time.strftime("%Y%m%d_%H%M%S")
        fname = f"{prefix}_{ts}.html"
        with open(fname, "w", encoding="utf-8") as f:
            f.write(html)
        print(f"💾 디버그 HTML 저장: {fname}")

    def search_news_html(
        self,
        keyword: str,
        date_from: str | None = None,
        date_to: str | None = None,
        start: int = 1
    ) -> List[Dict]:
        # --- URL 빌드 ---
        base_url = "https://search.naver.com/search.naver"
        params = {
            "where": "news",
            "query": keyword,
            "sm": "tab_opt",
            "start": start,
        }

        # 기간 필터 추가
        if date_from and date_to:
            df = date_from.replace("-", ".")
            dt = date_to.replace("-", ".")
            nso_from = date_from.replace(".", "").replace("-", "")
            nso_to = date_to.replace(".", "").replace("-", "")
            params.update({
                "pd": "3",
                "ds": df,
                "de": dt,
                "nso": f"so:r,p:from{nso_from}to{nso_to}"
            })

        # URL 최종 조립
        from urllib.parse import urlencode
        url = f"{base_url}?{urlencode(params, doseq=False)}"

        print(f"\n🔍 keyword={keyword} (start={start})")
        print(f"📡 Request URL: {url}")

        headers = {"User-Agent": next(self._ua_cycle)}
        res = requests.get(url, headers=headers, timeout=10)
        print(f"✅ Response status={res.status_code}, length={len(res.text)}")

        soup = BeautifulSoup(res.text, "html.parser")

        items: List[Dict] = []

        # --- 1차: 표준 DOM ---
        for li in soup.select("ul.list_news > li"):
            a = li.select_one("a.news_tit")
            if not a:
                continue
            title = a.get("title") or a.get_text(strip=True)
            link = a.get("href")

            press_el = li.select_one("a.info.press")
            press = press_el.get_text(strip=True) if press_el else ""

            date_el = li.select_one("span.info")
            date_text = date_el.get_text(strip=True) if date_el else ""

            if title and link:
                items.append({
                    "title": title,
                    "link": link,
                    "press": press,
                    "date": date_text,
                    "keyword": keyword,
                    "date_from": date_from,
                    "date_to": date_to,
                    "selector": "ul.list_news > li a.news_tit",
                })

        # --- 2차: fallback ---
        if not items:
            for a in soup.select("a.news_tit, a[href*='n.news.naver.com']"):
                title = a.get("title") or a.get_text(strip=True)
                link = a.get("href")
                if not (title and link):
                    continue
                items.append({
                    "title": title,
                    "link": link,
                    "press": "",
                    "date": "",
                    "keyword": keyword,
                    "date_from": date_from,
                    "date_to": date_to,
                    "selector": "fallback",
                })

        print(f"📰 최종 수집: {len(items)}개")
        for i, it in enumerate(items[:5], 1):
            print(f"  [{i}] {it['title']} | {it['press']} | {it['date']}")

        return items



    def search_news_html_multi_page(self, keyword: str, max_pages: int = 3) -> List[Dict]:
        all_items = []
        print(f"🔍 {keyword} - {max_pages}페이지 수집 시작")

        for page in range(1, max_pages + 1):
            start = (page - 1) * 10 + 1
            print(f"\n📄 페이지 {page}/{max_pages} (start={start})")
            try:
                items = self.search_news_html(keyword, start=start)
                if items:
                    print(f"✅ page {page}: {len(items)}개 수집")
                    all_items.extend(items)
                else:
                    print(f"⚠️ page {page}: 수집 실패 또는 데이터 없음 → 중단")
                    break
                time.sleep(random.uniform(1, 2))
            except Exception as e:
                print(f"❌ page {page} error: {e}")

        # 중복 제거
        unique, seen = [], set()
        for it in all_items:
            if it["link"] not in seen:
                seen.add(it["link"])
                unique.append(it)

        print(f"\n🎯 최종 결과: raw={len(all_items)}, unique={len(unique)}")
        return unique
