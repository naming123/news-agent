"""
메인 크롤링 로직 (검색 URL 생성, 페이지 순회)
"""
import time
import random
import logging
from typing import List, Optional
from urllib.parse import urlencode


from news_analyzer.config.models import CrawlerConfig, NewsArticle
from news_analyzer.http.request_handler import RequestHandler
from news_analyzer.collector.parser import NewsParser

logger = logging.getLogger(__name__)


class NaverNewsCrawler:
    """네이버 뉴스 크롤러 메인 클래스"""
    
    BASE_URL = "https://search.naver.com/search.naver"
    
    def __init__(self, config: Optional[CrawlerConfig] = None):
        self.config = config or CrawlerConfig()
        self.request_handler = RequestHandler(self.config)
        self.parser = NewsParser()
        
    def search(
        self,
        keyword: str,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        max_pages: int = 1,
        start_page: int = 1
    ) -> List[NewsArticle]:
        """
        뉴스 검색
        
        Args:
            keyword: 검색 키워드
            date_from: 시작 날짜 (YYYY-MM-DD)
            date_to: 종료 날짜 (YYYY-MM-DD)
            max_pages: 최대 페이지 수
            start_page: 시작 페이지
            
        Returns:
            List[NewsArticle]: 수집된 뉴스 기사 리스트
        """
        all_articles = []
        
        for page in range(start_page, start_page + max_pages):
            try:
                articles = self._search_page(
                    keyword=keyword,
                    date_from=date_from,
                    date_to=date_to,
                    page=page
                )
                
                if not articles:
                    logger.info(f"No more results at page {page}")
                    break
                    
                all_articles.extend(articles)
                
                # 다음 페이지 요청 전 대기
                if page < start_page + max_pages - 1:
                    delay = random.uniform(self.config.min_delay, self.config.max_delay)
                    time.sleep(delay)
                    
            except Exception as e:
                logger.error(f"Error at page {page}: {str(e)}")
                continue
        
        # 중복 제거
        return self._deduplicate(all_articles)
    
    def _search_page(
        self,
        keyword: str,
        date_from: Optional[str],
        date_to: Optional[str],
        page: int
    ) -> List[NewsArticle]:
        """단일 페이지 검색"""
        url = self._build_url(keyword, date_from, date_to, page)
        logger.info(f"Crawling page {page}: {url}")
        
        response = self.request_handler.get(url)
        
        metadata = {
            'keyword': keyword,
            'date_from': date_from,
            'date_to': date_to
        }
        
        articles = self.parser.parse_search_results(response.text, metadata)
        logger.info(f"Found {len(articles)} articles on page {page}")
        
        return articles
    
    def _build_url(
        self,
        keyword: str,
        date_from: Optional[str],
        date_to: Optional[str],
        page: int
    ) -> str:
        """검색 URL 생성"""
        params = {
            "where": "news",
            "query": keyword,
            "sm": "tab_opt",
            "start": (page - 1) * 10 + 1,
        }
        
        # 날짜 필터 추가
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
        
        return f"{self.BASE_URL}?{urlencode(params, doseq=False)}"
    
    @staticmethod
    def _deduplicate(articles: List[NewsArticle]) -> List[NewsArticle]:
        """중복 제거"""
        seen = set()
        unique = []
        for article in articles:
            if article.link not in seen:
                seen.add(article.link)
                unique.append(article)
        return unique
    
    def close(self):
        """리소스 정리"""
        self.request_handler.close()