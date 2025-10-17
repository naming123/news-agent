"""
HTML 파싱 (뉴스 제목, 링크, 언론사 추출)
"""
import logging
from typing import List, Dict, Any, Optional

from bs4 import BeautifulSoup

from news_collector.config.models import NewsArticle

logger = logging.getLogger(__name__)


class NewsParser:
    """뉴스 HTML 파싱"""
    
    @staticmethod
    def parse_search_results(html: str, metadata: Dict[str, Any]) -> List[NewsArticle]:
        """검색 결과 페이지 파싱"""
        soup = BeautifulSoup(html, "html.parser")
        articles = []
        
        # 메인 셀렉터로 파싱
        for item in soup.select("ul.list_news > li"):
            article = NewsParser._parse_news_item(item, metadata)
            if article:
                articles.append(article)
        
        # 결과가 없으면 대체 셀렉터 시도
        if not articles:
            logger.debug("Main selector failed, trying fallback")
            articles = NewsParser._parse_fallback(soup, metadata)
            
        return articles
    
    @staticmethod
    def _parse_news_item(item, metadata: Dict[str, Any]) -> Optional[NewsArticle]:
        """개별 뉴스 아이템 파싱"""
        try:
            title_elem = item.select_one("a.news_tit")
            if not title_elem:
                return None
                
            title = title_elem.get("title") or title_elem.get_text(strip=True)
            link = title_elem.get("href")
            
            if not (title and link):
                return None
                
            press_elem = item.select_one("a.info.press")
            press = press_elem.get_text(strip=True) if press_elem else ""
            
            date_elem = item.select_one("span.info")
            date_text = date_elem.get_text(strip=True) if date_elem else ""
            
            return NewsArticle(
                title=title,
                link=link,
                press=press,
                date=date_text,
                **metadata
            )
        except Exception as e:
            logger.error(f"Error parsing news item: {str(e)}")
            return None
    
    @staticmethod
    def _parse_fallback(soup: BeautifulSoup, metadata: Dict[str, Any]) -> List[NewsArticle]:
        """대체 파싱 로직"""
        articles = []
        
        for elem in soup.select("a.news_tit, a[href*='n.news.naver.com']"):
            try:
                title = elem.get("title") or elem.get_text(strip=True)
                link = elem.get("href")
                
                if title and link:
                    articles.append(NewsArticle(
                        title=title,
                        link=link,
                        **metadata
                    ))
            except Exception as e:
                logger.error(f"Error in fallback parsing: {str(e)}")
                continue
                
        return articles