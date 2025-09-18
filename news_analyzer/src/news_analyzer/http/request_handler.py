"""
HTTP 요청 처리 (네이버 접속, 헤더 로테이션, 재시도)
"""
import logging
from typing import Dict

import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

from news_analyzer.config.models import CrawlerConfig

logger = logging.getLogger(__name__)


class RequestHandler:
    """HTTP 요청 처리"""
    
    def __init__(self, config: CrawlerConfig):
        self.config = config
        self.session = self._create_session()
        self._ua_index = 0
        
    def _create_session(self) -> requests.Session:
        """세션 생성 with retry strategy"""
        session = requests.Session()
        retry_strategy = Retry(
            total=self.config.max_retries,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        return session
    
    def get_headers(self) -> Dict[str, str]:
        """로테이션 헤더 반환"""
        ua = self.config.user_agents[self._ua_index % len(self.config.user_agents)]
        self._ua_index += 1
        return {"User-Agent": ua}
    
    def get(self, url: str) -> requests.Response:
        """GET 요청 with error handling"""
        try:
            response = self.session.get(
                url, 
                headers=self.get_headers(), 
                timeout=self.config.timeout
            )
            response.raise_for_status()
            return response
        except requests.RequestException as e:
            logger.error(f"Request failed: {url} - {str(e)}")
            raise
    
    def close(self):
        """세션 종료"""
        if self.session:
            self.session.close()