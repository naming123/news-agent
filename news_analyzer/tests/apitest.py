#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
pytest를 사용한 네이버 API 크롤러 테스트
실행: pytest test_pytest.py -v
"""

import pytest
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.news_collector.collector.APIcrawler import NaverAPINewsCrawler, search_news_api

# 픽스처 정의
@pytest.fixture(scope="session")
def api_key_check():
    """API 키 존재 여부 체크"""
    if not os.getenv('NAVER_CLIENT_ID'):
        pytest.skip("NAVER_CLIENT_ID 환경변수가 설정되지 않았습니다")

@pytest.fixture(scope="session")
def crawler(api_key_check):
    """크롤러 인스턴스 생성"""
    return NaverAPINewsCrawler()

@pytest.fixture(scope="session")
def sample_data(crawler):
    """테스트용 샘플 데이터"""
    result = crawler.search_news("파이썬", display=3)
    if result and 'items' in result:
        return result['items']
    return []

# 기본 테스트
def test_crawler_init(crawler):
    """크롤러 초기화 테스트"""
    assert crawler.client_id is not None
    assert crawler.client_secret is not None
    assert crawler.headers is not None
    assert 'X-Naver-Client-Id' in crawler.headers

def test_api_connection(crawler):
    """API 연결 테스트"""
    result = crawler.search_news("테스트", display=1)
    
    assert result is not None
    assert 'total' in result
    assert 'start' in result
    assert 'display' in result
    assert 'items' in result

def test_search_with_results(crawler):
    """검색 결과가 있는 경우 테스트"""
    result = crawler.search_news("뉴스", display=5)
    
    assert result is not None
    assert isinstance(result['items'], list)
    assert len(result['items']) <= 5
    
    if result['items']:
        item = result['items'][0]
        assert 'title' in item
        assert 'link' in item
        assert 'description' in item

def test_multiple_pages_search(crawler):
    """다중 페이지 검색 테스트"""
    items = crawler.search_news_multiple_pages("AI", max_results=15)
    
    assert isinstance(items, list)
    assert len(items) <= 15
    
    if items:
        # 모든 아이템이 필수 필드를 가지고 있는지 확인
        required_fields = ['title', 'link', 'description']
        for item in items:
            for field in required_fields:
                assert field in item

def test_data_formatting(crawler, sample_data):
    """데이터 포맷팅 테스트"""
    if not sample_data:
        pytest.skip("샘플 데이터가 없습니다")
    
    formatted = crawler.format_news_data(sample_data, "테스트키워드")
    
    assert isinstance(formatted, list)
    assert len(formatted) == len(sample_data)
    
    if formatted:
        item = formatted[0]
        required_fields = ['keyword', 'title', 'description', 'link', 'pub_date', 'crawl_time']
        
        for field in required_fields:
            assert field in item
            
        assert item['keyword'] == "테스트키워드"

def test_wrapper_function():
    """래퍼 함수 테스트"""
    if not os.getenv('NAVER_CLIENT_ID'):
        pytest.skip("API 키가 없습니다")
        
    items = search_news_api("개발", num_items=3)
    
    assert isinstance(items, list)
    assert len(items) <= 3
    
    if items:
        item = items[0]
        assert item['keyword'] == "개발"
        assert 'title' in item
        assert 'link' in item

def test_html_tag_removal(crawler):
    """HTML 태그 제거 테스트"""
    test_cases = [
        ("&lt;b&gt;테스트&lt;/b&gt;", "테스트"),
        ("&quot;뉴스&quot;", '"뉴스"'),
        ("A &amp; B", "A & B"),
        ("&lt;script&gt;alert()&lt;/script&gt;", "alert()"),
    ]
    
    for html_input, expected in test_cases:
        result = crawler._remove_html_tags(html_input)
        assert expected in result

def test_date_conversion(crawler):
    """날짜 변환 테스트"""
    test_date = "Mon, 23 Sep 2025 10:30:00 +0900"
    result = crawler._convert_date_format(test_date)
    
    # YYYY-MM-DD 형식 확인
    assert len(result) == 10
    assert result.count('-') == 2
    assert result.split('-')[0].isdigit()  # 연도
    assert result.split('-')[1].isdigit()  # 월
    assert result.split('-')[2].isdigit()  # 일

# 에러 처리 테스트
def test_invalid_api_key():
    """잘못된 API 키 테스트"""
    bad_crawler = NaverAPINewsCrawler(
        client_id="invalid",
        client_secret="invalid"
    )
    
    result = bad_crawler.search_news("테스트", display=1)
    assert result is None

def test_empty_search_results(crawler):
    """검색 결과가 없는 경우 테스트"""
    # 매우 특수한 검색어로 결과가 없을 가능성이 높은 케이스
    weird_keyword = "xyzabc123impossible999"
    result = crawler.search_news(weird_keyword, display=1)
    
    # API 호출은 성공하지만 결과가 0개일 수 있음
    if result:
        assert 'items' in result
        assert isinstance(result['items'], list)

# 파라미터화된 테스트
@pytest.mark.parametrize("keyword,expected_count", [
    ("AI", 5),
    ("Python", 3),
    ("뉴스", 1),
])
def test_multiple_keywords(keyword, expected_count):
    """여러 키워드로 테스트"""
    if not os.getenv('NAVER_CLIENT_ID'):
        pytest.skip("API 키가 없습니다")
    
    items = search_news_api(keyword, num_items=expected_count)
    
    assert isinstance(items, list)
    assert len(items) <= expected_count
    
    if items:
        assert all(item['keyword'] == keyword for item in items)

@pytest.mark.parametrize("display_count", [1, 5, 10, 50, 100])
def test_display_limits(crawler, display_count):
    """Display 제한 테스트"""
    result = crawler.search_news("테스트", display=display_count)
    
    if result and 'items' in result:
        assert len(result['items']) <= display_count

# 성능 관련 테스트
def test_response_time(crawler):
    """응답 시간 테스트"""
    import time
    
    start_time = time.time()
    result = crawler.search_news("빠른테스트", display=1)
    end_time = time.time()
    
    response_time = end_time - start_time
    
    # 5초 이내 응답 기대
    assert response_time < 5.0
    assert result is not None

# 마크 데코레이터를 사용한 그룹 테스트
@pytest.mark.slow
def test_large_data_collection(crawler):
    """대용량 데이터 수집 테스트 (느린 테스트)"""
    items = crawler.search_news_multiple_pages("뉴스", max_results=100)
    
    assert isinstance(items, list)
    assert len(items) <= 100

@pytest.mark.api_dependent
def test_api_rate_limit():
    """API Rate Limit 테스트"""
    if not os.getenv('NAVER_CLIENT_ID'):
        pytest.skip("API 키가 없습니다")
        
    crawler = NaverAPINewsCrawler()
    
    # 연속 요청으로 Rate Limit 확인
    success_count = 0
    for i in range(5):
        result = crawler.search_news(f"테스트{i}", display=1)
        if result:
            success_count += 1
    
    # 최소한 일부는 성공해야 함
    assert success_count > 0

if __name__ == "__main__":
    # pytest 실행
    pytest.main([__file__, "-v", "--tb=short"])