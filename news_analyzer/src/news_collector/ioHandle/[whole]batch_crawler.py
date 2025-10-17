"""
배치 뉴스 크롤러
"""
import logging, time
from pathlib import Path
from datetime import datetime
from collections import defaultdict
from typing import Dict, List, Optional

from ..config.models import CrawlerConfig, NewsArticle
from ..collector.crawler import NaverNewsCrawler
from ..ioHandle.io_handler import ExcelInputHandler, ExcelOutputHandler
from ..utils.util import setup_logging

logger = logging.getLogger(__name__)

class BatchNewsCrawler:
    def __init__(self, input_file: str, output_dir: str = "./output", config: Optional[CrawlerConfig] = None):
        self.input_file = input_file
        self.output_dir = Path(output_dir); self.output_dir.mkdir(parents=True, exist_ok=True)
        self.excel_config = ExcelInputHandler.read_config(input_file)
        self.crawler_config = config or CrawlerConfig(
            max_retries=self.excel_config.get("max_retries", 3),
            timeout=self.excel_config.get("timeout", 10),
            min_delay=self.excel_config.get("min_delay", 1.0),
            max_delay=self.excel_config.get("max_delay", 2.0),
        )
        self.crawler = NaverNewsCrawler()
        self.results_by_keyword = {}
        self.results_by_company = defaultdict(dict)

    def run(self) -> Dict[str, List[NewsArticle]]:
        companies = ExcelInputHandler.read_companies(self.input_file)
        key_specs = ExcelInputHandler.read_keywords(self.input_file)
        date_from, date_to = self.excel_config.get("date_from"), self.excel_config.get("date_to")
        max_pages = self.excel_config.get("max_pages", 10)


        for company in companies:
            for spec in key_specs:
                group, kw = spec["group"], spec["keyword"]
                query = f"{company} {kw}".strip()
                try:
                    # API는 날짜 필터링 안됨, max_pages 대신 개수로 제한
                    max_items = max_pages * 100  # 페이지당 10개 가정
                    raw_items = self.crawler.search_news_multiple_pages(query, max_results=max_items)
                    articles = self.crawler.format_news_data(raw_items, query)
                    # NewsArticle 객체로 변환
                    articles = [NewsArticle(**item) for item in articles]
                    for a in articles:
                        a.company = company; a.keyword = kw; a.group = group
                        a.search_query = query; a.date_from = date_from; a.date_to = date_to
                    self.results_by_keyword.setdefault(kw, []).extend(articles)
                    self.results_by_company.setdefault(company, {}).setdefault(kw, []).extend(articles)
                except Exception as e:
                    logger.error(f"[{company}] {group}/{kw} 에러: {e}")
        self._save_results()
        return self.results_by_keyword

    def _save_results(self):
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        output = self.output_dir / f"results_{ts}.xlsx"
        ExcelOutputHandler.save_results(self.results_by_keyword, str(output))
        logger.info(f"저장 완료: {output}")

    def close(self):
        if self.crawler: self.crawler.close()

def main():
    import argparse
    parser = argparse.ArgumentParser(description="엑셀 기반 배치 뉴스 크롤러")
    parser.add_argument("input", help="입력 엑셀 파일")
    parser.add_argument("--output-dir", default="./output")
    args = parser.parse_args()
    setup_logging(level=logging.INFO)

    crawler = BatchNewsCrawler(input_file=args.input, output_dir=args.output_dir)
    try:
        crawler.run()
    finally:
        crawler.close()

if __name__ == "__main__":
    main()
