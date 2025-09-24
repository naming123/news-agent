import os
import random
import time
import json
from typing import List, Dict
from datetime import datetime
import requests

class NaverNewsCrawler:
    """네이버 Open API를 사용한 뉴스 검색 크롤러"""
    
    def __init__(self, client_id: str = None, client_secret: str = None):
        # 환경 변수에서 API 키 로드
        from dotenv import load_dotenv
        load_dotenv()
        
        self.client_id = client_id or os.getenv('NAVER_CLIENT_ID')
        self.client_secret = client_secret or os.getenv('NAVER_CLIENT_SECRET')
        self.session = requests.Session()
        # self.config = config
        
        if not self.client_id or not self.client_secret:
            raise ValueError(
                "네이버 API 키가 없습니다. "
                ".env 파일에 NAVER_CLIENT_ID와 NAVER_CLIENT_SECRET을 설정하거나 "
                "생성자 파라미터로 직접 전달하세요."
            )
        self.base_url = "https://openapi.naver.com/v1/search/news.json"
        
        # API 요청 헤더
        self.headers = {
            "X-Naver-Client-Id": self.client_id,
            "X-Naver-Client-Secret": self.client_secret,
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
    def close(self):
        self.session.close() 
    def search_news(self, query: str, start: int = 1, display: int = 10, sort: str = "date") -> Dict:
        """
        네이버 뉴스 API 검색
        
        Args:
            query: 검색어
            start: 검색 시작 위치 (1~1000)
            display: 출력 건수 (1~100)
            sort: 정렬 옵션 (sim: 정확도, date: 날짜)
        
        Returns:
            API 응답 JSON
        """
        params = {
            "query": query,
            "start": start,
            "display": display,
            "sort": sort
        }
        
        try:
            response = requests.get(
                self.base_url,
                headers=self.headers,
                params=params,
                timeout=10
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                print(f"API 요청 실패: {response.status_code}")
                print(f"응답: {response.text}")
                return None
                
        except requests.exceptions.RequestException as e:
            print(f"요청 중 오류 발생: {e}")
            return None
    
    def search_news_multiple_pages(self, query: str, max_results: int = 100) -> List[Dict]:
        """
        여러 페이지에 걸쳐 뉴스 검색
        
        Args:
            query: 검색어
            max_results: 최대 결과 수
            
        Returns:
            뉴스 아이템 리스트
        """
        all_items = []
        page_size = 100  # API 최대 출력 건수
        current_start = 1
        
        while len(all_items) < max_results and current_start <= 1000:  # API 최대 1000건
            display_count = min(page_size, max_results - len(all_items), 1000 - current_start + 1)
            
            print(f"페이지 요청: start={current_start}, display={display_count}")
            
            result = self.search_news(
                query=query,
                start=current_start,
                display=display_count,
                sort="date"
            )
            
            if result and "items" in result:
                items = result["items"]
                if not items:  # 더 이상 결과가 없으면 중단
                    break
                    
                all_items.extend(items)
                current_start += len(items)
                
                print(f"수집된 뉴스: {len(all_items)}개")
                
                # API 호출 간격 조절 (Rate Limit 방지)
                time.sleep(random.uniform(0.1, 0.3))
            else:
                break
        
        return all_items[:max_results]
    
    def format_news_data(self, items: List[Dict], keyword: str) -> List[Dict]:
        """
        API 응답을 기존 크롤러 형식으로 변환
        
        Args:
            items: API 응답 아이템 리스트
            keyword: 검색 키워드
            
        Returns:
            포맷된 뉴스 데이터 리스트
        """
        formatted_items = []
        
        for item in items:
            # HTML 태그 제거
            title = self._remove_html_tags(item.get("title", ""))
            description = self._remove_html_tags(item.get("description", ""))
            
            # 날짜 포맷 변환 (YYYYMMDD -> YYYY-MM-DD)
            pub_date = item.get("pubDate", "")
            formatted_date = self._convert_date_format(pub_date)
            
            formatted_item = {
                "keyword": keyword,
                "title": title,
                "description": description,
                "link": item.get("link", ""),
                "pub_date": formatted_date,
                "original_link": item.get("originallink", ""),
                "crawl_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            
            formatted_items.append(formatted_item)
        
        return formatted_items
    
    def _remove_html_tags(self, text: str) -> str:
        """HTML 태그 제거"""
        import re
        clean_text = re.sub(r'<[^>]+>', '', text)
        return clean_text.replace("&quot;", '"').replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
    
    def _convert_date_format(self, pub_date: str) -> str:
        """
        네이버 API 날짜 형식을 YYYY-MM-DD로 변환
        예: 'Mon, 23 Sep 2025 10:30:00 +0900' -> '2025-09-23'
        """
        try:
            # RFC 2822 형식 파싱
            from datetime import datetime
            dt = datetime.strptime(pub_date, '%a, %d %b %Y %H:%M:%S %z')
            return dt.strftime('%Y-%m-%d')
        except:
            # 파싱 실패시 현재 날짜 반환
            return datetime.now().strftime('%Y-%m-%d')

# 기존 코드와의 호환성을 위한 래퍼 함수
def search_news_api(keyword: str, num_items: int = 100) -> List[Dict]:
    """
    기존 search_news_html 함수와 호환되는 API 버전
    
    Args:
        keyword: 검색 키워드
        num_items: 수집할 뉴스 개수
        
    Returns:
        뉴스 아이템 리스트
    """
    crawler = NaverNewsCrawler()
    
    # API로 뉴스 검색
    raw_items = crawler.search_news_multiple_pages(keyword, num_items)
    
    # 기존 형식으로 변환
    formatted_items = crawler.format_news_data(raw_items, keyword)
    
    return formatted_items

# 테스트 코드
if __name__ == "__main__":
    # 기본 테스트
    crawler = NaverNewsCrawler()
    
    # 단일 페이지 검색 테스트
    result = crawler.search_news("삼성전자", display=5)
    if result:
        print("=== API 응답 샘플 ===")
        print(json.dumps(result, indent=2, ensure_ascii=False))
    
    # 다중 페이지 검색 테스트
    print("\n=== 포맷된 뉴스 데이터 ===")
    news_items = search_news_api("삼성전자", num_items=10)
    
    for i, item in enumerate(news_items, 1):
        print(f"\n{i}. {item['title']}")
        print(f"   링크: {item['link']}")
        print(f"   날짜: {item['pub_date']}")
        print(f"   설명: {item['description'][:100]}...")