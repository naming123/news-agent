"""
보조 함수 (JSON/CSV 저장, 통계, 필터링)
"""
import json
import csv
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Optional, Dict, Any

from ..config.models import NewsArticle, CrawlerConfig
from ..collector.crawler import NaverNewsCrawler

logger = logging.getLogger(__name__)


def create_crawler(
    max_retries: int = 3,
    timeout: int = 10,
    min_delay: float = 1.0,
    max_delay: float = 2.0
) -> NaverNewsCrawler:
    """크롤러 인스턴스 생성 헬퍼"""
    config = CrawlerConfig(
        max_retries=max_retries,
        timeout=timeout,
        min_delay=min_delay,
        max_delay=max_delay
    )
    return NaverNewsCrawler(config)


def save_to_json(
    articles: List[NewsArticle],
    filepath: str,
    encoding: str = 'utf-8'
) -> None:
    """기사 목록을 JSON 파일로 저장"""
    try:
        data = [article.to_dict() for article in articles]
        with open(filepath, 'w', encoding=encoding) as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        logger.info(f"Saved {len(articles)} articles to {filepath}")
    except Exception as e:
        logger.error(f"Error saving to JSON: {str(e)}")
        raise


def save_to_csv(
    articles: List[NewsArticle],
    filepath: str,
    encoding: str = 'utf-8-sig'
) -> None:
    """기사 목록을 CSV 파일로 저장"""
    try:
        if not articles:
            logger.warning("No articles to save")
            return
            
        fieldnames = articles[0].to_dict().keys()
        
        with open(filepath, 'w', newline='', encoding=encoding) as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for article in articles:
                writer.writerow(article.to_dict())
        
        logger.info(f"Saved {len(articles)} articles to {filepath}")
    except Exception as e:
        logger.error(f"Error saving to CSV: {str(e)}")
        raise


def load_from_json(filepath: str) -> List[NewsArticle]:
    """JSON 파일에서 기사 목록 로드"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        articles = [NewsArticle.from_dict(item) for item in data]
        logger.info(f"Loaded {len(articles)} articles from {filepath}")
        return articles
    except Exception as e:
        logger.error(f"Error loading from JSON: {str(e)}")
        raise


def filter_by_date(
    articles: List[NewsArticle],
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None
) -> List[NewsArticle]:
    """날짜로 기사 필터링"""
    filtered = []
    
    for article in articles:
        try:
            # crawled_at 기준으로 필터링
            article_date = datetime.fromisoformat(article.crawled_at)
            
            if start_date and article_date < start_date:
                continue
            if end_date and article_date > end_date:
                continue
                
            filtered.append(article)
        except Exception as e:
            logger.warning(f"Error filtering article: {str(e)}")
            continue
    
    return filtered


def filter_by_press(
    articles: List[NewsArticle],
    press_list: List[str],
    exclude: bool = False
) -> List[NewsArticle]:
    """언론사로 기사 필터링"""
    filtered = []
    
    for article in articles:
        if exclude:
            if article.press not in press_list:
                filtered.append(article)
        else:
            if article.press in press_list:
                filtered.append(article)
    
    return filtered


def get_statistics(articles: List[NewsArticle]) -> Dict[str, Any]:
    """기사 통계 정보 생성"""
    if not articles:
        return {
            'total_count': 0,
            'press_count': {},
            'date_range': None,
            'keywords': []
        }
    
    press_count = {}
    keywords = set()
    dates = []
    
    for article in articles:
        # 언론사별 카운트
        if article.press:
            press_count[article.press] = press_count.get(article.press, 0) + 1
        
        # 키워드 수집
        if article.keyword:
            keywords.add(article.keyword)
        
        # 날짜 수집
        try:
            dates.append(datetime.fromisoformat(article.crawled_at))
        except:
            continue
    
    date_range = None
    if dates:
        date_range = {
            'start': min(dates).isoformat(),
            'end': max(dates).isoformat()
        }
    
    return {
        'total_count': len(articles),
        'press_count': dict(sorted(press_count.items(), key=lambda x: x[1], reverse=True)),
        'date_range': date_range,
        'keywords': list(keywords)
    }


def setup_logging(
    level: int = logging.INFO,
    log_file: Optional[str] = None
) -> None:
    """로깅 설정"""
    handlers = [logging.StreamHandler()]
    
    if log_file:
        handlers.append(logging.FileHandler(log_file, encoding='utf-8'))
    
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=handlers
    )