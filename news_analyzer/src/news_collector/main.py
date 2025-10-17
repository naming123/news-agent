"""
네이버 뉴스 크롤러 실행 예제
"""
import argparse
from datetime import datetime, timedelta

from news_crawler import (
    create_crawler,
    TimeRangeCrawler,
    save_to_json,
    save_to_csv,
    get_statistics,
    setup_logging
)


def main():
    parser = argparse.ArgumentParser(description='네이버 뉴스 크롤러')
    parser.add_argument('keyword', help='검색 키워드')
    parser.add_argument('--pages', type=int, default=3, help='최대 페이지 수')
    parser.add_argument('--date-from', help='시작 날짜 (YYYY-MM-DD)')
    parser.add_argument('--date-to', help='종료 날짜 (YYYY-MM-DD)')
    parser.add_argument('--output', default='news.json', help='출력 파일')
    parser.add_argument('--format', choices=['json', 'csv'], default='json', help='출력 형식')
    parser.add_argument('--realtime', action='store_true', help='실시간 모드')
    parser.add_argument('--interval', type=int, default=30, help='실시간 모드 간격 (분)')
    parser.add_argument('--log-level', default='INFO', help='로그 레벨')
    
    args = parser.parse_args()
    
    # 로깅 설정
    setup_logging(level=getattr(logging, args.log_level))
    
    # 크롤러 생성
    crawler = create_crawler()
    
    if args.realtime:
        # 실시간 모드
        time_crawler = TimeRangeCrawler(crawler)
        print(f"실시간 크롤링 시작: {args.keyword} (간격: {args.interval}분)")
        
        for articles in time_crawler.crawl_realtime(args.keyword, args.interval):
            if articles:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"realtime_{args.keyword}_{timestamp}.{args.format}"
                
                if args.format == 'json':
                    save_to_json(articles, filename)
                else:
                    save_to_csv(articles, filename)
                
                print(f"수집: {len(articles)}개 -> {filename}")
            else:
                print("새로운 기사 없음")
    else:
        # 일반 검색 모드
        articles = crawler.search(
            keyword=args.keyword,
            date_from=args.date_from,
            date_to=args.date_to,
            max_pages=args.pages
        )
        
        if articles:
            # 저장
            if args.format == 'json':
                save_to_json(articles, args.output)
            else:
                save_to_csv(articles, args.output)
            
            # 통계 출력
            stats = get_statistics(articles)
            print(f"\n=== 크롤링 완료 ===")
            print(f"총 기사 수: {stats['total_count']}")
            print(f"언론사별 분포:")
            for press, count in list(stats['press_count'].items())[:5]:
                print(f"  - {press}: {count}개")
            if stats['date_range']:
                print(f"날짜 범위: {stats['date_range']['start']} ~ {stats['date_range']['end']}")
        else:
            print("수집된 기사가 없습니다.")
    
    # 리소스 정리
    crawler.close()


if __name__ == "__main__":
    import logging
    main()