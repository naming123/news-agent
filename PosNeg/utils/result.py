from dataclasses import dataclass
from typing import List, Tuple, Dict
from datetime import datetime


@dataclass
class SearchResult:
    """검색 결과"""
    query: str
    model: str
    metric: str
    neighbors: List[Tuple[str, float]]
    timestamp: str = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    def display(self, show_bar: bool = True):
        """콘솔 출력"""
        print(f"\n{'='*70}")
        print(f"쿼리: '{self.query}' | 모델: {self.model} | 지표: {self.metric}")
        print(f"시간: {self.timestamp}")
        print(f"{'='*70}")
        
        for rank, (word, score) in enumerate(self.neighbors, 1):
            if show_bar:
                bar_len = max(0, min(40, int(abs(score) * 40)))
                bar = '█' * bar_len
                print(f"{rank:2d}. {word:20s} {score:7.4f} {bar}")
            else:
                print(f"{rank:2d}. {word:20s} {score:.4f}")
        print()
    
    def to_dict(self) -> Dict:
        """딕셔너리 변환"""
        return {
            'query': self.query,
            'model': self.model,
            'metric': self.metric,
            'timestamp': self.timestamp,
            'neighbors': self.neighbors
        }