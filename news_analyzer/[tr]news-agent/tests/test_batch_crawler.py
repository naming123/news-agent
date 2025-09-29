# tests/test_batch_crawler.py
import unittest
from unittest.mock import Mock, patch
from datetime import datetime
from batch_crawler import BatchCrawler
from crawler import NewsArticle

class TestBatchCrawler(unittest.TestCase):
    """배치 크롤러 테스트"""
    
    def setUp(self):
        """테스트 초기화"""
        self.mock_crawler = Mock()
        self.batch_crawler = BatchCrawler(crawler=self.mock_crawler)
    
    def test_run_batch_success(self):
        """정상 크롤링 테스트"""
        # Given
        mock_articles = [
            NewsArticle(
                title="테스트 기사",
                link="http://test.com",
                press="테스트 언론사",
                date="2024.01.01",
                summary="테스트 요약"
            )
        ]
        self.mock_crawler.fetch_news_data.return_value = [
            article.to_dict() for article in mock_articles
        ]
        
        # When
        result = self.batch_crawler.run_batch(
            keyword="AI",
            date_from="2024.01.01",
            date_to="2024.01.31",
            max_articles=10
        )
        
        # Then
        self.assertEqual(len(result), 1)
        self.assertIn("AI", result)
        self.assertEqual(len(result["AI"]), 1)
        
    @patch('batch_crawler.ExcelOutputHandler')
    def test_save_results(self, mock_excel_handler):
        """엑셀 저장 테스트"""
        # Given
        articles = {"AI": [{"title": "test"}]}
        
        # When
        self.batch_crawler._save_results(
            articles_by_keyword=articles,
            output_path="test.xlsx",
            date_from="2024.01.01",
            date_to="2024.01.31"
        )
        
        # Then
        mock_excel_handler.return_value.save_results.assert_called_once()

if __name__ == '__main__':
    unittest.main()