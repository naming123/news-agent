# main.py
from __future__ import annotations
from news_analyzer.pipeline.news_pipeline import NewsAnalysisPipeline

def prompt_menu() -> str:
    print("\n=== 뉴스 분석 도구 ===")
    print("1) 분석 실행")
    print("2) 모듈 테스트 (샘플)")
    print("3) 종료")
    return input("메뉴 선택: ").strip()

def run_analysis_ui():
    keywords = input("키워드(쉼표 구분): ").strip()
    start_date = input("시작날짜(YYYY-MM-DD): ").strip()
    end_date = input("종료날짜(YYYY-MM-DD): ").strip()
    fmt = input("저장형식(csv/json): ").strip().lower()
    if fmt not in {"csv","json"}:
        print("형식이 올바르지 않아 csv로 저장합니다.")
        fmt = "csv"
    kws = [k.strip() for k in keywords.split(",") if k.strip()]
    pipeline = NewsAnalysisPipeline()
    results = pipeline.run_analysis(kws, start_date, end_date)
    stats = pipeline.get_summary_stats(results)
    print("\n--- 요약 ---")
    print(f"수집 건수: {stats['num_items']}")
    print(f"감정 분포: {stats['sentiments']}")
    print(f"키워드별 수집 건수: {stats['items_by_keyword']}")
    if stats["top_companies"]:
        print(f"상위 기업: {stats['top_companies']}")
    out_path = pipeline.save_results(results, fmt, f"news_results.{fmt}")
    print(f"파일 저장 완료: {out_path}")

def run_tests():
    print("샘플 실행을 시작합니다...")
    pipeline = NewsAnalysisPipeline()
    results = pipeline.run_analysis(["삼성전자","LG화학"], "2024-01-01", "2024-01-31")
    print(f"샘플 결과 {len(results)}건 중 2건 미리보기:")
    for r in results[:2]:
        print({k: r[k] for k in ['keyword','title','sentiment','confidence','companies']})
    out_path = pipeline.save_results(results, "csv", "sample_results.csv")
    print(f"샘플 CSV 저장: {out_path}")

if __name__ == "__main__":
    while True:
        choice = prompt_menu()
        if choice == "1":
            run_analysis_ui()
        elif choice == "2":
            run_tests()
        elif choice == "3":
            print("종료합니다.")
            break
        else:
            print("올바른 번호를 선택하세요.")
