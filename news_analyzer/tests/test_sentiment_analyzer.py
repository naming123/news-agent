# tests/test_sentiment_analyzer.py
from news_analyzer.sentiment_analyzer import SentimentAnalyzer

def test_basic_cases():
    sa = SentimentAnalyzer()
    assert sa.predict_sentiment("좋은 상승 성장")["sentiment"] == "긍정"
    assert sa.predict_sentiment("나쁜 하락 손실")["sentiment"] == "부정"
    assert sa.predict_sentiment("보통의 내용")["sentiment"] == "중립"
    assert sa.predict_sentiment("")["sentiment"] == "중립"
