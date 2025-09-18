# sentiment_analyzer.py
from __future__ import annotations
from typing import Dict, List

class SentimentAnalyzer:
    """
    Keyword-based sentiment analyzer for Korean text.
    Returns one of 긍정/부정/중립 with a confidence score in [0, 1].
    """
    def __init__(self, positive_words: List[str] | None = None, negative_words: List[str] | None = None):
        # 기본 키워드 세트 (간단 예시)
        self.positive_words = set(positive_words or [
            "좋다","좋은","상승","성장","개선","호재","강세","이익","흑자","신기록","호조","확대","호평","강화","혁신"
        ])
        self.negative_words = set(negative_words or [
            "나쁘다","나쁜","하락","손실","악화","악재","약세","적자","부진","감소","경고","축소","불만","취약","리콜"
        ])

    def _count_matches(self, text: str, vocab: set) -> int:
        cnt = 0
        for w in vocab:
            if w in text:
                cnt += text.count(w)
        return cnt

    def predict_sentiment(self, text: str) -> Dict:
        """
        Args:
            text (str): 입력 텍스트
        Returns:
            dict: {'sentiment': str, 'confidence': float, 'scores': dict}
        """
        if not isinstance(text, str) or len(text.strip()) == 0:
            # 빈 문자열은 에러 없이 중립 처리
            return {'sentiment': '중립', 'confidence': 0.0, 'scores': {'중립': 1.0}}

        text_norm = text.strip()
        pos = self._count_matches(text_norm, self.positive_words)
        neg = self._count_matches(text_norm, self.negative_words)

        if pos > neg:
            sentiment = '긍정'
            conf = pos / max(1, pos + neg)
        elif neg > pos:
            sentiment = '부정'
            conf = neg / max(1, pos + neg)
        else:
            sentiment = '중립'
            conf = 1.0 if (pos == 0 and neg == 0) else 0.5

        scores = {
            '긍정': pos / max(1, pos + neg),
            '부정': neg / max(1, pos + neg),
            '중립': 1.0 if (pos == 0 and neg == 0) else 0.0
        }
        return {'sentiment': sentiment, 'confidence': float(round(conf, 4)), 'scores': {k: float(round(v, 4)) for k, v in scores.items()}}


