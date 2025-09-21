"""
데이터 구조 정의 (NewsArticle, CrawlerConfig 클래스)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Any, Optional


@dataclass
class CrawlerConfig:
    """크롤러 설정"""
    max_retries: int = 3
    timeout: int = 10
    min_delay: float = 2.0
    max_delay: float = 4.0
    user_agents: List[str] = field(default_factory=lambda: [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    ])


@dataclass
class NewsArticle:
    """뉴스 기사 데이터 모델"""
    title: str
    link: str
    press: str = ""
    date: str = ""
    keyword: str = ""
    date_from: Optional[str] = None
    date_to: Optional[str] = None
    crawled_at: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        return {
            'title': self.title,
            'link': self.link,
            'press': self.press,
            'date': self.date,
            'keyword': self.keyword,
            'date_from': self.date_from,
            'date_to': self.date_to,
            'crawled_at': self.crawled_at
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'NewsArticle':
        """딕셔너리에서 생성"""
        return cls(**data)