# batch_crawler.py
from typing import Dict, List, Optional
from datetime import datetime
import logging
from pathlib import Path

# excel_handler import 추가
from utils.excel_handler import ExcelOutputHandler

logger = logging.getLogger(__name__)

class BatchCrawler:
    """뉴스 배치 크롤링 핵심 로직"""
    
    def __init__(self, crawler=None):
        self.crawler = crawler or self._get_default_crawler()
        self.excel_handler = ExcelOutputHandler()  # 추가
        
    def _get_default_crawler(self):
        """크롤러 인스턴스 생성"""
        from crawler import NewsCrawler  
        return NewsCrawler()
    
    def run_batch(
            self, 
            keyword: str,
            date_from: str,  # "2024.01.01" 형식
            date_to: str,     # "2024.01.31" 형식
            output_path: Optional[str] = None
        ) -> Dict[str, List]:
            """배치 크롤링 실행"""
            
            # 날짜 유효성 검증
            try:
                # 날짜 파싱
                start = datetime.strptime(date_from, "%Y.%m.%d")
                end = datetime.strptime(date_to, "%Y.%m.%d")
                
                # 1990년 이전 체크 (네이버 뉴스 한계)
                min_date = datetime(1990, 1, 1)
                if start < min_date:
                    raise ValueError(f"시작 날짜는 1990.01.01 이후여야 합니다. 입력된 날짜: {date_from}")
                
                if start > end:
                    raise ValueError(f"시작일({date_from})이 종료일({date_to})보다 늦습니다")
                    
                # 미래 날짜 체크
                if end > datetime.now():
                    logger.warning(f"종료일이 미래입니다: {date_to}")
                    
            except ValueError as e:
                logger.error(f"날짜 형식 오류: {e}")
                raise
            
            logger.info(f"크롤링 시작 - 키워드: {keyword}, 기간: {date_from} ~ {date_to}")
    
    def _save_results(
        self,
        articles_by_keyword: Dict[str, List],
        output_path: str,
        date_from: str,
        date_to: str
    ):
        """엑셀 저장"""
        self.excel_handler.save_results(
            results_by_keyword=articles_by_keyword,
            file_path=output_path,
            date_from=date_from,
            date_to=date_to
        )