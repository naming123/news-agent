from abc import ABC, abstractmethod
import numpy as np


class SimilarityMetric(ABC):
    """유사도 지표 추상 클래스"""
    
    def __init__(self, embeddings: np.ndarray):
        self.embeddings = embeddings
        self._preprocess()
    
    def _preprocess(self):
        """전처리 (하위 클래스에서 필요시 오버라이드)"""
        pass
    
    @abstractmethod
    def compute(self, query_vec: np.ndarray) -> np.ndarray:
        """유사도 계산"""
        pass
    
    @abstractmethod
    def is_distance(self) -> bool:
        """거리 지표 여부"""
        pass
    
    @property
    @abstractmethod
    def name(self) -> str:
        """지표 이름"""
        pass