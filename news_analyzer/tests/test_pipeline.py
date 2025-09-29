# tests/test_pipeline.py
from news_analyzer.pipeline.news_pipeline import NewsAnalysisPipeline

def test_run_pipeline_smoke():
    p = NewsAnalysisPipeline()
    res = p.run_analysis(["삼성전자","LG화학"], "2024-01-01", "2024-01-31")
    assert isinstance(res, list) and len(res) > 0
    stats = p.get_summary_stats(res)
    assert "num_items" in stats and stats["num_items"] == len(res)
