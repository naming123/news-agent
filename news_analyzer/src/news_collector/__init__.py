# news_analyzer package
'''
패키지 초기화 (import 할 수 있게 만드는 파일)
'''


from .config.models import CrawlerConfig, NewsArticle
from .collector.crawler import NaverNewsCrawler
from .ioHandle.io_handler import ExcelInputHandler, ExcelOutputHandler
from .utils.util import setup_logging
from .config.models import CrawlerConfig, NewsArticle
from .collector.crawler import NaverNewsCrawler
from .collector.time_crawler import TimeRangeCrawler
from .utils.util import (
    create_crawler,
    save_to_json,
    save_to_csv,
    load_from_json,
    filter_by_date,
    filter_by_press,
    get_statistics,
    setup_logging
)

__version__ = "1.0.0"

__all__ = [
    # 모델
    'CrawlerConfig',
    'NewsArticle',
    
    # 크롤러
    'NaverNewsCrawler',
    'TimeRangeCrawler',
    
    # 유틸리티
    'create_crawler',
    'save_to_json',
    'save_to_csv',
    'load_from_json',
    'filter_by_date',
    'filter_by_press',
    'get_statistics',
    'setup_logging',
]