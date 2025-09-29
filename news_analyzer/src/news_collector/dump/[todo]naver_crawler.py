# naver_crawler.py
from __future__ import annotations
import os
import random, time
from typing import List, Dict
import itertools
import requests
from bs4 import BeautifulSoup

class NaverNewsCrawler:
    """
    Mock crawler for Naver News search with bot-avoidance strategies:
    - User-Agent rotation
    - Random delay between requests
    NOTE: This is a simulation; no real HTTP calls are made.
    """
    def __init__(self):
        self.allow_network = os.getenv("ALLOW_NETWORK", "0") == "1"

        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36",
            "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148"
        ]
        self._ua_cycle = itertools.cycle(self.user_agents)
        self.session_headers = {"User-Agent": next(self._ua_cycle)}

    def random_delay(self, min_sec: int = 1, max_sec: int = 5) -> None:
        time.sleep(random.uniform(min_sec, max_sec))

    def rotate_user_agent(self) -> None:
        self.session_headers["User-Agent"] = next(self._ua_cycle)

    def search_news_mock(
        self, keyword: str, start_date: str, end_date: str, num_items: int = 3
    ) -> List[Dict]:
        self.rotate_user_agent()
        self.random_delay(1, 2)
        samples = []
        medias = ["연합뉴스", "조선비즈", "매일경제", "한국경제", "서울경제"]
        headlines_pos = [
            f"{keyword} 실적 호조, 성장 기대",
            f"{keyword} 주가 상승",
            f"{keyword} 혁신 신기록",
        ]
        headlines_neg = [
            f"{keyword} 리콜 이슈, 실적 부담",
            f"{keyword} 주가 하락",
            f"{keyword} 악재 노출",
        ]
        headlines_neu = [
            f"{keyword} 보도자료 발표",
            f"{keyword} 신규 사업 검토",
            f"{keyword} 업계 동향",
        ]
        pool = headlines_pos + headlines_neg + headlines_neu
        for i in range(num_items):
            title = random.choice(pool)
            summary = f"{keyword} 관련 요약 기사 내용입니다. 무작위 샘플 {i+1}."
            samples.append({
                "title": title,
                "link": f"https://news.naver.com/mock/{keyword}/{i+1}",
                "media": random.choice(medias),
                "date": random.choice([start_date, end_date]),
                "summary": summary,
                "keyword": keyword,
                "source": "mock"   # 👈 구분 필드 추가
            })
        return samples

    def search_news_html(self, keyword: str, start: int = 1) -> List[Dict]:

        url = (
            f"https://search.naver.com/search.naver"
            f"?where=news&sm=tab_jum&query={keyword}&start={start}"
        )
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/122.0.0.0 Safari/537.36"
            )
        }
        res = requests.get(url, headers=headers)
        soup = BeautifulSoup(res.text, "html.parser")

        items = []
        for a_tag in soup.select("a.news_tit"):
            title = a_tag.get("title")
            link = a_tag.get("href")
            items.append({
                "title": title,
                "link": link,
                "keyword": keyword,
                "source": "html"   # 👈 실제 HTML 파싱 결과 구분
            })
        return items

