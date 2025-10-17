"""
HTTP 요청 처리 (네이버 접속, 헤더 로테이션, 재시도)
"""
# news_analyzer/http/request_handler.py
import logging, random, time
import requests
from urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter
from typing import Optional

logger = logging.getLogger(__name__)

UA_LIST = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:126.0) Gecko/20100101 Firefox/126.0",
]

class RequestHandler:
    def __init__(self, config):
        self.timeout    = int(getattr(config, "timeout", 10))
        self.min_delay  = float(getattr(config, "min_delay", 2.0))
        self.max_delay  = float(getattr(config, "max_delay", 4.0))
        retries         = int(getattr(config, "max_retries", 3))

        self.session = requests.Session()
        retry = Retry(
            total=retries, connect=retries, read=retries, status=retries,
            backoff_factor=1.5, status_forcelist=[403,429,500,502,503,504],
            allowed_methods=["GET","HEAD"], raise_on_status=False
        )
        self.session.mount("https://", HTTPAdapter(max_retries=retry))
        self.session.mount("http://", HTTPAdapter(max_retries=retry))

        # 쿠키/헤더 워밍업
        try:
            self.session.get("https://search.naver.com/", headers=self._headers(), timeout=self.timeout)
        except Exception as e:
            logger.debug(f"Warmup failed (ignored): {e}")

    def _headers(self, referer=None):
        return {
            "User-Agent": random.choice(UA_LIST),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
            "Referer": referer or "https://search.naver.com/",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
            "Connection": "keep-alive",
        }

    def page_delay(self):
        time.sleep(random.uniform(self.min_delay, self.max_delay))

    def get(self, url: str, referer: Optional[str] = None):
        """403/429 시 짧게 쉬고 UA 교체 후 1회 재시도. 그래도 403이면 호출측에서 중단 판단."""
        headers = {"User-Agent": "...", "Referer": referer or "https://search.naver.com/"}
        try:
            resp = self.session.get(url, headers=self._headers(referer), timeout=self.timeout)
        except Exception as e:
            logger.error(f"Request failed: {url} - {e}")
            raise

        if resp.status_code in (403, 429):
            logger.warning(f"Blocked {resp.status_code}. Sleep & rotate UA... {url}")
            time.sleep(random.uniform(4.0, 8.0))
            try:
                self.session.cookies.clear()
            except Exception:
                pass
            resp = self.session.get(url, headers=headers, timeout=self.timeout)
            return resp

        if resp.status_code >= 400:
            # 상위에서 처리할 수 있도록 예외
            try:
                resp.raise_for_status()
            except Exception as e:
                logger.error(f"Request failed: {url} - {e}")
                raise

        return resp
