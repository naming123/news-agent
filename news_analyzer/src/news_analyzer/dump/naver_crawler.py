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
    Naver News crawler with HTML parsing research
    """
    def __init__(self):
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
                "source": "mock"
            })
        return samples

    def search_news_html(self, keyword: str, start: int = 1) -> List[Dict]:
        url = (
            f"https://search.naver.com/search.naver"
            f"?where=news&ie=utf8&sm=nws_hty&query={keyword}&start={start}"
        )
        
        print(f"🔍 Original keyword: {keyword}")
        print(f"📡 Request URL: {url}")
        
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/122.0.0.0 Safari/537.36"
            )
        }
        res = requests.get(url, headers=headers)
        
        print(f"✅ Response status: {res.status_code}")
        print(f"📄 HTML length: {len(res.text)} chars")
        
        soup = BeautifulSoup(res.text, "html.parser")
        
        # HTML 구조 디버깅 - 실제 네이버 뉴스 셀렉터들
        selectors_to_try = [
            "a.news_tit",                           # 기존 방식
            ".list_news a[href*='news.naver.com']", # 뉴스 목록에서 네이버 뉴스 링크
            ".api_subject_bx a",                    # API 결과 영역의 링크
            ".news_wrap a",                         # 뉴스 래핑 영역
            ".group_news a",                        # 뉴스 그룹 영역
            "div[data-module] a[href*='news.naver.com']", # 데이터 모듈 내 뉴스 링크
            ".news_area a",                         # 뉴스 영역
            "a[href*='news.naver.com'][title]"      # title 속성을 가진 네이버 뉴스 링크
        ]
        
        items = []
        print("\n🔍 셀렉터별 검색 결과:")
        
        for selector in selectors_to_try:
            try:
                elements = soup.select(selector)
                print(f"  {selector}: {len(elements)}개 발견")
                
                if elements and not items:  # 첫 번째로 발견된 셀렉터 사용
                    print(f"✅ '{selector}' 사용하여 파싱 시작")
                    
                    for i, a_tag in enumerate(elements[:10]):  # 최대 10개
                        title = a_tag.get("title") or a_tag.get_text(strip=True)
                        link = a_tag.get("href")
                        
                        # 뉴스 제목 길이 및 유효성 체크
                        if title and link and len(title) > 5:
                            print(f"    [{i+1}] {title[:50]}...")
                            items.append({
                                "title": title,
                                "link": link,
                                "keyword": keyword,
                                "source": "html",
                                "selector": selector
                            })
            except Exception as e:
                print(f"  ❌ {selector}: 에러 {e}")
        
        # 마지막 수단: 모든 링크에서 뉴스 관련 것만 추출
        if not items:
            print("\n🔍 마지막 수단: 모든 링크 분석")
            all_links = soup.find_all("a", href=True)
            news_links = [
                a for a in all_links 
                if "news.naver.com" in a.get("href", "")
                or any(cls in (a.get("class", []) or []) for cls in ["news", "tit", "title"])
            ]
            
            print(f"  전체 링크: {len(all_links)}개")
            print(f"  뉴스 관련 링크: {len(news_links)}개")
            
            for i, a_tag in enumerate(news_links[:10]):
                title = a_tag.get("title") or a_tag.get_text(strip=True)
                link = a_tag.get("href")
                
                if title and len(title) > 5:
                    print(f"    [{i+1}] {title[:50]}...")
                    items.append({
                        "title": title,
                        "link": link,
                        "keyword": keyword,
                        "source": "html",
                        "selector": "fallback_search"
                    })
        
        print(f"\n📰 총 {len(items)}개 뉴스 아이템 수집 완료")
        return items
    def search_news_html_multi_page(self, keyword: str, max_pages: int = 3) -> List[Dict]:
        """
        여러 페이지에서 뉴스 수집 (스크롤 효과 시뮬레이션)
        """
        all_items = []
        
        print(f"🔍 {keyword} - {max_pages}페이지 수집 시작")
        
        for page in range(1, max_pages + 1):
            start = (page - 1) * 10 + 1  # 네이버는 10개씩 페이징
            
            print(f"\n📄 페이지 {page}/{max_pages} (start={start})")
            print("-" * 50)
            
            try:
                # 각 페이지 수집
                items = self.search_news_html(keyword, start=start)
                
                if items:
                    print(f"✅ 페이지 {page}: {len(items)}개 수집")
                    all_items.extend(items)
                else:
                    print(f"❌ 페이지 {page}: 수집 실패 또는 데이터 없음")
                    break  # 더 이상 데이터가 없으면 중단
                
                # 페이지 간 딜레이 (너무 빠른 요청 방지)
                if page < max_pages:
                    print("⏱️  다음 페이지까지 2초 대기...")
                    time.sleep(2)
                    
            except Exception as e:
                print(f"❌ 페이지 {page} 수집 중 오류: {e}")
                continue
        
        # 중복 제거 (같은 링크는 한 번만)
        unique_items = []
        seen_links = set()
        
        for item in all_items:
            if item["link"] not in seen_links:
                unique_items.append(item)
                seen_links.add(item["link"])
        
        print(f"\n🎯 수집 완료:")
        print(f"   - 총 페이지: {max_pages}페이지")
        print(f"   - 원본 수집: {len(all_items)}개")
        print(f"   - 중복 제거 후: {len(unique_items)}개")
        
        return unique_items