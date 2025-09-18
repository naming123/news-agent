"""
엑셀 기반 배치 뉴스 크롤러
"""
import logging
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
from collections import defaultdict

from news_analyzer.config.models import CrawlerConfig, NewsArticle
from news_analyzer.collector.crawler import NaverNewsCrawler
from news_analyzer.ioHandle.io_handler import ExcelInputHandler, ExcelOutputHandler
from news_analyzer.utils.util import setup_logging


logger = logging.getLogger(__name__)  # <-- 전역 로거 핸들

class BatchNewsCrawler:
    """배치 뉴스 크롤러"""
    
    def __init__(
        self,
        input_file: str,
        output_dir: str = "./output",
        config: Optional[CrawlerConfig] = None
    ):
        """
        Args:
            input_file: 입력 엑셀 파일 경로
            output_dir: 출력 디렉토리
            config: 크롤러 설정
        """
        self.input_file = input_file
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # 설정 로드
        self.excel_config = ExcelInputHandler.read_config(input_file)
        self.crawler_config = config or self._create_config_from_excel()
        
        # 크롤러 초기화
        self.crawler = NaverNewsCrawler(self.crawler_config)
        
        # 결과 저장
        self.results_by_keyword = {}
        self.results_by_company = defaultdict(dict)
    
    def _create_config_from_excel(self) -> CrawlerConfig:
        """엑셀 설정으로부터 CrawlerConfig 생성"""
        return CrawlerConfig(
            max_retries=self.excel_config.get('max_retries', 3),
            timeout=self.excel_config.get('timeout', 10),
            min_delay=self.excel_config.get('min_delay', 1.0),
            max_delay=self.excel_config.get('max_delay', 2.0)
        )
    
    def run(self) -> Dict[str, List[NewsArticle]]:
        """
        배치 크롤링 실행
        
        Returns:
            키워드별 기사 딕셔너리
        """
        # 키워드 로드
        keywords_info = ExcelInputHandler.read_keywords(self.input_file)
        
        if not keywords_info:
            logger.warning("No keywords found in input file")
            return {}
        
        logger.info(f"Starting batch crawl for {len(keywords_info)} keywords")
        
        # 크롤링 파라미터
        max_pages = self.excel_config.get('max_pages', 3)
        date_from = self.excel_config.get('date_from')
        date_to = self.excel_config.get('date_to')
        
        # 키워드별 크롤링
        for idx, info in enumerate(keywords_info, 1):
            keyword = info['keyword']
            company = info['company']
            
            logger.info(f"[{idx}/{len(keywords_info)}] Crawling: {company} - {keyword}")
            
            try:
                articles = self.crawler.search(
                    keyword=keyword,
                    date_from=date_from,
                    date_to=date_to,
                    max_pages=max_pages
                )
                
                # 회사 정보 추가
                for article in articles:
                    article.company = company
                
                # 결과 저장
                self.results_by_keyword[keyword] = articles
                self.results_by_company[company][keyword] = articles
                
                logger.info(f"  -> Found {len(articles)} articles")
                
                # 다음 키워드 전 대기 (마지막 제외)
                if idx < len(keywords_info):
                    delay = self.crawler_config.min_delay
                    time.sleep(delay)
                    
            except Exception as e:
                logger.error(f"  -> Error: {str(e)}")
                self.results_by_keyword[keyword] = []
                self.results_by_company[company][keyword] = []
        
        # 결과 저장
        self._save_results()
        
        return self.results_by_keyword
    
    def _save_results(self):
        """결과를 엑셀 파일로 저장"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # 1. 키워드별 결과
        if self.results_by_keyword:
            keyword_output = self.output_dir / f"keyword_results_{timestamp}.xlsx"
            ExcelOutputHandler.save_results(
                self.results_by_keyword,
                str(keyword_output),
                summary_sheet=True,
                separate_sheets=True
            )
            logger.info(f"Keyword results saved: {keyword_output}")
        
        # 2. 회사별 결과
        if self.results_by_company:
            company_output = self.output_dir / f"company_results_{timestamp}.xlsx"
            ExcelOutputHandler.save_company_results(
                dict(self.results_by_company),
                str(company_output)
            )
            logger.info(f"Company results saved: {company_output}")
    
    def get_statistics(self) -> Dict:
        """크롤링 통계 반환"""
        stats = {
            'total_keywords': len(self.results_by_keyword),
            'total_companies': len(self.results_by_company),
            'total_articles': sum(len(articles) for articles in self.results_by_keyword.values()),
            'by_company': {},
            'by_keyword': {}
        }
        
        # 회사별 통계
        for company, keyword_articles in self.results_by_company.items():
            stats['by_company'][company] = {
                'keywords': len(keyword_articles),
                'articles': sum(len(articles) for articles in keyword_articles.values())
            }
        
        # 키워드별 통계
        for keyword, articles in self.results_by_keyword.items():
            stats['by_keyword'][keyword] = len(articles)
        
        return stats
    
    def close(self):
        """리소스 정리"""
        if self.crawler:
            self.crawler.close()


def main():
    """메인 실행 함수"""
    import argparse
    
    parser = argparse.ArgumentParser(description='엑셀 기반 배치 뉴스 크롤러')
    parser.add_argument('input', help='입력 엑셀 파일')
    parser.add_argument('--output-dir', default='./output', help='출력 디렉토리')
    parser.add_argument('--create-template', action='store_true', help='템플릿 생성')
    parser.add_argument('--log-level', default='INFO', help='로그 레벨')
    parser.add_argument('--log-file', help='로그 파일')
    
    args = parser.parse_args()
    
    # 로깅 설정
    setup_logging(
        level=getattr(logging, args.log_level),
        log_file=args.log_file
    )
    

    
    # 배치 크롤링 실행
    print(f"배치 크롤링 시작: {args.input}")
    print(f"출력 디렉토리: {args.output_dir}")
    
    batch_crawler = BatchNewsCrawler(
        input_file=args.input,
        output_dir=args.output_dir
    )
    
    try:
        results = batch_crawler.run()
        
        # 통계 출력
        stats = batch_crawler.get_statistics()
        print("\n=== 크롤링 완료 ===")
        print(f"총 키워드: {stats['total_keywords']}개")
        print(f"총 회사: {stats['total_companies']}개")
        print(f"총 기사: {stats['total_articles']}개")
        
        print("\n회사별 결과:")
        for company, company_stats in stats['by_company'].items():
            print(f"  {company}: {company_stats['keywords']}개 키워드, {company_stats['articles']}개 기사")
        
    except Exception as e:
        logger.error(f"Batch crawling failed: {str(e)}")
        print(f"오류 발생: {str(e)}")
    finally:
        batch_crawler.close()


if __name__ == "__main__":
    main()