

from news_analyzer.naver_crawler import NaverNewsCrawler

def main():
    crawler = NaverNewsCrawler()
    
    for kw in ["삼성전자", "LG화학", "현대차"]:
        # search_news_html은 keyword와 start만 받으므로 인자 수정
        items = crawler.search_news_html(kw, start=1)
        
        # 각 아이템에 keyword가 올바르게 설정되었는지 확인
        assert all(i["keyword"] == kw for i in items)
        print(f"{kw}: {len(items)} items OK")
    
    print("SAFE ✅ HTML parsing executed.")

if __name__ == "__main__":
    main()

