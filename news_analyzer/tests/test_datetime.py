# test_simple_crawler.py
import sys
import os
import pandas as pd
from datetime import datetime

# 경로 추가
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from news_analyzer.naver_crawler_time import NaverNewsCrawler

def test_basic_search():
    """기본 검색 테스트"""
    print("=== 기본 검색 테스트 ===")
    
    crawler = NaverNewsCrawler()
    results = crawler.search_news_html("삼성전자")
    
    print(f"결과: {len(results)}개")
    if results:
        print(f"첫 번째: {results[0]['title']}")
    return results

def test_date_filtered_search():
    """날짜 필터링 검색 테스트"""
    print("\n=== 날짜 필터링 검색 테스트 ===")
    
    crawler = NaverNewsCrawler()
    results = crawler.search_news_html(
        keyword="삼성전자",
        date_from="2024.09.01", 
        date_to="2024.09.13"
    )
    
    print(f"결과: {len(results)}개")
    if results:
        for i, item in enumerate(results[:3], 1):
            print(f"{i}. {item['title'][:50]}...")
    return results

def test_multi_page():
    """다중 페이지 테스트"""
    print("\n=== 다중 페이지 테스트 ===")
    
    crawler = NaverNewsCrawler()
    results = crawler.search_news_html_multi_page(
        keyword="삼성전자",
        date_from="2024.09.01",
        date_to="2024.09.13", 
        max_pages=2
    )
    
    print(f"결과: {len(results)}개")
    return results

def test_custom_url():
    """사용자 정의 URL 테스트"""
    print("\n=== 사용자 정의 URL 테스트 ===")
    
    # 직접 네이버 뉴스 URL 입력
    custom_url = input("네이버 뉴스 URL을 입력하세요 (엔터시 기본값 사용): ").strip()
    
    if not custom_url:
        custom_url = "https://search.naver.com/search.naver?where=news&query=삼성전자&start=1&pd=3&ds=2024.09.01&de=2024.09.13"
        print(f"기본값 사용: {custom_url}")
    
    crawler = NaverNewsCrawler()
    results = crawler.search_news_html("", custom_url=custom_url)
    
    print(f"결과: {len(results)}개")
    return results

def save_to_excel(results, filename=None):
    """엑셀로 저장"""
    if not results:
        print("저장할 데이터가 없습니다")
        return
    
    if not filename:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"naver_news_{timestamp}.xlsx"
    
    try:
        df = pd.DataFrame(results)
        df.to_excel(filename, index=False, engine='openpyxl')
        print(f"엑셀 저장 완료: {filename}")
        return filename
    except Exception as e:
        print(f"엑셀 저장 실패: {e}")
        # CSV로 백업 저장
        try:
            csv_filename = filename.replace('.xlsx', '.csv')
            df.to_csv(csv_filename, index=False, encoding='utf-8-sig')
            print(f"CSV 저장 완료: {csv_filename}")
        except:
            print("CSV 저장도 실패")

def main():
    """메인 테스트"""
    print("네이버 뉴스 크롤러 테스트")
    print("=" * 40)
    
    while True:
        print("\n메뉴:")
        print("1. 기본 검색")
        print("2. 날짜 필터링 검색") 
        print("3. 다중 페이지 검색")
        print("4. 사용자 정의 URL")
        print("5. 종료")
        
        choice = input("선택하세요 (1-5): ").strip()
        results = []
        
        if choice == "1":
            results = test_basic_search()
        elif choice == "2":
            results = test_date_filtered_search()
        elif choice == "3":
            results = test_multi_page()
        elif choice == "4":
            results = test_custom_url()
        elif choice == "5":
            break
        else:
            print("잘못된 선택입니다")
            continue
        
        # 결과가 있으면 엑셀 저장 여부 확인
        if results:
            save_choice = input("엑셀로 저장하시겠습니까? (y/n): ").strip().lower()
            if save_choice == 'y':
                save_to_excel(results)

if __name__ == "__main__":
    main()