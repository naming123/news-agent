# tests/test_crawler_with_excel.py

import pandas as pd
from datetime import datetime
from news_analyzer.naver_crawler import NaverNewsCrawler

def main():
    crawler = NaverNewsCrawler()
    
    print("🚀 삼성전자 다중 페이지 크롤링 + 엑셀 저장 테스트")
    print("="*60)
    
    keyword = "삼성전자"
    max_pages = 100  # 3페이지까지 수집
    
    print(f"🔍 {keyword} 검색 중 ({max_pages}페이지)...")
    
    # 필터링할 불필요한 제목들
    exclude_titles = [
        "언론사 선정언론사가 선정한 주요기사 혹은 심층기획 기사입니다.네이버 메인에서 보고 싶은 언론사를 구독하세요.",
        "Keep에 저장",
        "Keep에 바로가기"
    ]
    
    try:
        # 다중 페이지 뉴스 검색
        items = crawler.search_news_html_multi_page(keyword, max_pages=max_pages)
        print(f"🎯 원본 수집: {len(items)}개")
        
        # 불필요한 제목 필터링
        filtered_items = []
        for item in items:
            title = item["title"]
            
            # 제외할 제목인지 체크
            should_exclude = False
            for exclude in exclude_titles:
                if exclude in title:
                    print(f"    ❌ EXCLUDED: {title[:60]}...")
                    should_exclude = True
                    break
            
            if not should_exclude:
                print(f"    ✅ INCLUDED: {title[:60]}...")
                filtered_items.append(item)
        
        print(f"✅ {keyword}: {len(filtered_items)}개 수집 완료 (필터링 후)")
        all_results = filtered_items
        
    except Exception as e:
        print(f"❌ {keyword} 검색 실패: {e}")
        all_results = []
    
    print(f"\n{'='*60}")
    print("📊 수집 결과 요약")
    print(f"{'='*60}")
    print(f"총 수집 뉴스: {len(all_results)}개")
    print(f"페이지 수: {max_pages}페이지")
    
    # 수집된 뉴스 제목들 미리보기
    if all_results:
        print(f"\n📋 수집된 뉴스 제목들:")
        for i, item in enumerate(all_results[:15], 1):  # 최대 15개만 표시
            print(f"  [{i:2d}] {item['title']}")
            if i >= 15 and len(all_results) > 15:
                print(f"  ... 외 {len(all_results)-15}개 더")
                break
    
    # 엑셀 저장 테스트
    if all_results:
        print(f"\n💾 엑셀 저장 테스트...")
        
        try:
            df = pd.DataFrame(all_results)
            print(f"✅ pandas 정상 작동")
            
            # 파일명 생성
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"samsung_news_multipage_{timestamp}.xlsx"
            
            # 엑셀 저장
            df.to_excel(filename, index=False, engine='openpyxl')
            print(f"✅ 엑셀 저장 성공: {filename}")
            
            # 파일 정보
            import os
            if os.path.exists(filename):
                size = os.path.getsize(filename)
                print(f"📁 파일 크기: {size:,} bytes")
                print(f"📋 컬럼: {list(df.columns)}")
                
                # 데이터 상세 정보
                print(f"📊 데이터 상세:")
                print(f"  - 총 행 수: {len(df)}")
                print(f"  - 평균 제목 길이: {df['title'].str.len().mean():.1f}자")
                
                # source별 통계
                if 'source' in df.columns:
                    source_counts = df['source'].value_counts()
                    print(f"  - 소스별 분포: {dict(source_counts)}")
                
                # 샘플 데이터
                print(f"\n📄 샘플 데이터:")
                for idx, row in df.head(3).iterrows():
                    print(f"  제목: {row['title'][:50]}...")
                    print(f"  링크: {row['link'][:80]}...")
                    if 'crawl_time' in row:
                        print(f"  시간: {row['crawl_time']}")
                    print()
            
        except ImportError as e:
            print(f"❌ 라이브러리 누락: {e}")
            print("💡 설치 명령어: pip install pandas openpyxl")
            
        except Exception as e:
            print(f"❌ 엑셀 저장 실패: {e}")
            
    else:
        print("❌ 저장할 데이터가 없습니다")
    
    print(f"\n🎉 다중 페이지 크롤링 테스트 완료!")
    print(f"스크롤 효과 시뮬레이션으로 {len(all_results)}개 뉴스 수집됨")

if __name__ == "__main__":
    main()