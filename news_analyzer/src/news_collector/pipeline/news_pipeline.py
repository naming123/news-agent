# news_pipeline.py
from __future__ import annotations
from typing import List, Dict, Any
import csv, json, os
from news_analyzer.sentiment_analyzer import SentimentAnalyzer
from news_analyzer.company_identifier import CompanyIdentifier
from news_analyzer.naver_crawler import NaverNewsCrawler

class NewsAnalysisPipeline:
    def __init__(self):
        self.sa = SentimentAnalyzer()
        self.ci = CompanyIdentifier()
        self.crawler = NaverNewsCrawler()

    def run_analysis(self, keywords: List[str], start_date: str, end_date: str) -> List[Dict[str, Any]]:
        results: List[Dict[str, Any]] = []
        for kw in keywords:
            items = self.crawler.search_news_mock(kw.strip(), start_date, end_date)
            for it in items:
                text_for_sent = f"{it.get('title','')} {it.get('summary','')}"
                sent = self.sa.predict_sentiment(text_for_sent)
                comps = self.ci.identify_companies(text_for_sent)
                results.append({
                    "keyword": kw,
                    "title": it.get("title"),
                    "summary": it.get("summary"),
                    "link": it.get("link"),
                    "media": it.get("media"),
                    "date": it.get("date"),
                    "sentiment": sent["sentiment"],
                    "confidence": sent["confidence"],
                    "scores": sent["scores"],
                    "companies": comps
                })
        return results

    def save_results(self, results: List[Dict[str, Any]], fmt: str = "csv", out_path: str | None = None) -> str:
        fmt = fmt.lower()
        out_path = out_path or f"news_results.{fmt}"
        if fmt == "csv":
            # 평탄화하여 저장
            fieldnames = ["keyword","title","summary","link","media","date","sentiment","confidence","companies","scores"]
            with open(out_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                for r in results:
                    row = r.copy()
                    row["companies"] = ";".join(r.get("companies", []))
                    row["scores"] = json.dumps(r.get("scores", {}), ensure_ascii=False)
                    writer.writerow(row)
        elif fmt == "json":
            with open(out_path, "w", encoding="utf-8") as f:
                json.dump(results, f, ensure_ascii=False, indent=2)
        else:
            raise ValueError("Unsupported format. Use 'csv' or 'json'.")
        return os.path.abspath(out_path)

    def get_summary_stats(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        from collections import Counter, defaultdict
        sentiments = Counter(r["sentiment"] for r in results)
        company_counts = Counter()
        by_keyword = defaultdict(int)
        for r in results:
            by_keyword[r["keyword"]] += 1
            for c in r.get("companies", []):
                company_counts[c] += 1
        return {
            "num_items": len(results),
            "sentiments": dict(sentiments),
            "top_companies": company_counts.most_common(10),
            "items_by_keyword": dict(by_keyword)
        }

