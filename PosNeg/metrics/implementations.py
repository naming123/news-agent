from .base import SimilarityMetric
import numpy as np


class CosineSimilarity(SimilarityMetric):
    """코사인 유사도"""
    
    def _preprocess(self):
        norms = np.linalg.norm(self.embeddings, axis=1, keepdims=True)
        self.norm_embeddings = self.embeddings / np.maximum(norms, 1e-12)
    
    def compute(self, query_vec: np.ndarray) -> np.ndarray:
        query_norm = query_vec / (np.linalg.norm(query_vec) + 1e-12)
        return self.norm_embeddings @ query_norm
    
    def is_distance(self) -> bool:
        return False
    
    @property
    def name(self) -> str:
        return "Cosine Similarity"


class EuclideanDistance(SimilarityMetric):
    """유클리드 거리"""
    
    def compute(self, query_vec: np.ndarray) -> np.ndarray:
        diff = self.embeddings - query_vec
        return -np.sqrt(np.sum(diff ** 2, axis=1))
    
    def is_distance(self) -> bool:
        return True
    
    @property
    def name(self) -> str:
        return "Euclidean Distance"


class ManhattanDistance(SimilarityMetric):
    """맨하탄 거리"""
    
    def compute(self, query_vec: np.ndarray) -> np.ndarray:
        return -np.sum(np.abs(self.embeddings - query_vec), axis=1)
    
    def is_distance(self) -> bool:
        return True
    
    @property
    def name(self) -> str:
        return "Manhattan Distance"


class DotProduct(SimilarityMetric):
    """내적"""
    
    def compute(self, query_vec: np.ndarray) -> np.ndarray:
        return self.embeddings @ query_vec
    
    def is_distance(self) -> bool:
        return False
    
    @property
    def name(self) -> str:
        return "Dot Product"


class CorrelationSimilarity(SimilarityMetric):
    """상관계수"""
    
    def compute(self, query_vec: np.ndarray) -> np.ndarray:
        embeddings_centered = self.embeddings - self.embeddings.mean(axis=1, keepdims=True)
        query_centered = query_vec - query_vec.mean()
        
        emb_std = np.std(embeddings_centered, axis=1)
        query_std = np.std(query_centered)
        
        corr = (embeddings_centered @ query_centered) / (emb_std * query_std * len(query_vec) + 1e-12)
        return corr
    
    def is_distance(self) -> bool:
        return False
    
    @property
    def name(self) -> str:
        return "Correlation"


class MetricFactory:
    """지표 팩토리"""
    
    METRICS = {
        'cosine': CosineSimilarity,
        'euclidean': EuclideanDistance,
        'manhattan': ManhattanDistance,
        'dot': DotProduct,
        'correlation': CorrelationSimilarity
    }
    
    @classmethod
    def create(cls, metric_name: str, embeddings: np.ndarray) -> SimilarityMetric:
        if metric_name not in cls.METRICS:
            raise ValueError(f"지원하지 않는 지표: {metric_name}")
        return cls.METRICS[metric_name](embeddings)
    
    @classmethod
    def list_metrics(cls):
        return list(cls.METRICS.keys())


