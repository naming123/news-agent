"""
시간 기반 크롤링 (날짜 범위, 실시간 모니터링)
"""
import time
import random
import logging
from datetime import datetime, timedelta
from typing import List, Optional, Generator

from ..collector.crawler import NaverNewsCrawler
from ..config.models import CrawlerConfig, NewsArticle

logger = logging.getLogger(__name__)


class TimeRangeCrawler:
    """시간 범위 기반 크롤러"""
    
    def __init__(self, crawler: Optional[NaverNewsCrawler] = None):
        self.crawler = crawler or NaverNewsCrawler()
    
    def crawl_date_range(
        self,
        keyword: str,
        start_date: datetime,
        end_date: datetime,
        interval_days: int = 1,
        max_pages_per_interval: int = 1
    ) -> List[NewsArticle]:
        """
        날짜 범위를 간격으로 나누어 크롤링
        
        Args:
            keyword: 검색 키워드
            start_date: 시작 날짜
            end_date: 종료 날짜
            interval_days: 크롤링 간격 (일)
            max_pages_per_interval: 간격당 최대 페이지
            
        Returns:
            List[NewsArticle]: 전체 수집된 기사
        """
        all_articles = []
        current_date = start_date
        
        while current_date < end_date:
            interval_end = min(
                current_date + timedelta(days=interval_days),
                end_date
            )
            
            date_from = current_date.strftime("%Y-%m-%d")
            date_to = interval_end.strftime("%Y-%m-%d")
            
            logger.info(f"Crawling {date_from} to {date_to}")
            
            articles = self.crawler.search(
                keyword=keyword,
                date_from=date_from,
                date_to=date_to,
                max_pages=max_pages_per_interval
            )
            
            all_articles.extend(articles)
            current_date = interval_end
            
            # 다음 간격 전 대기
            if current_date < end_date:
                time.sleep(random.uniform(2, 4))
        
        return NaverNewsCrawler._deduplicate(all_articles)
    
    def crawl_realtime(
        self,
        keyword: str,
        interval_minutes: int = 30,
        max_iterations: Optional[int] = None
    ) -> Generator[List[NewsArticle], None, None]:
        """
        실시간 크롤링
        
        Args:
            keyword: 검색 키워드
            interval_minutes: 크롤링 간격 (분)
            max_iterations: 최대 반복 횟수 (None이면 무한)
            
        Yields:
            List[NewsArticle]: 각 반복마다 수집된 기사
        """
        iteration = 0
        
        while max_iterations is None or iteration < max_iterations:
            now = datetime.now()
            date_str = now.strftime("%Y-%m-%d")
            
            logger.info(f"Realtime crawling iteration {iteration + 1}")
            
            articles = self.crawler.search(
                keyword=keyword,
                date_from=date_str,
                date_to=date_str,
                max_pages=1
            )
            
            yield articles
            
            iteration += 1
            if max_iterations is None or iteration < max_iterations:
                time.sleep(interval_minutes * 60)
    
    def crawl_recent_hours(
        self,
        keyword: str,
        hours: int = 24,
        max_pages: int = 3
    ) -> List[NewsArticle]:
        """
        최근 N시간 내 기사 크롤링
        
        Args:
            keyword: 검색 키워드
            hours: 최근 시간 수
            max_pages: 최대 페이지 수
            
        Returns:
            List[NewsArticle]: 수집된 기사
        """
        end_date = datetime.now()
        start_date = end_date - timedelta(hours=hours)
        
        return self.crawler.search(
            keyword=keyword,
            date_from=start_date.strftime("%Y-%m-%d"),
            date_to=end_date.strftime("%Y-%m-%d"),
            max_pages=max_pages
        )