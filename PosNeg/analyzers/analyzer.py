"""
analyzers/analyzer.py
단어 유사도 분석 엔진
"""

import numpy as np
from typing import Dict, List, Union


class WordSimilarityAnalyzer:
    """단어 유사도 분석 엔진"""
    
    def __init__(
        self,
        embeddings: np.ndarray,
        token2id: Dict,
        id2token: Dict,
        model_name: str,
        model_loader=None
    ):
        self.embeddings = embeddings
        self.token2id = token2id
        self.id2token = id2token
        self.model_name = model_name
        self.vocab_size = len(token2id) if token2id else 0
        self.model_loader = model_loader
    
    def search(
        self,
        query: Union[str, np.ndarray],
        metric_obj,
        top_k: int = 10,
        exclude_self: bool = True
    ):
        """유사 단어/문장 검색"""
        
        # Sentence Transformer 모델인 경우
        if self.model_loader and hasattr(self.model_loader, 'is_sentence_model') and self.model_loader.is_sentence_model:
            return self._search_sentence_model(query, metric_obj, top_k)
        
        # 기존 단어 기반 모델
        if isinstance(query, str):
            if query not in self.token2id:
                raise KeyError(f"'{query}'는 사전에 없습니다")
            query_vec = self.embeddings[self.token2id[query]]
            exclude_id = self.token2id[query] if exclude_self else None
            query_word = query
        else:
            query_vec = query
            exclude_id = None
            query_word = "custom_vector"
        
        # 유사도 계산
        scores = metric_obj.compute(query_vec)
        
        # 자기 자신 제외
        if exclude_id is not None:
            scores[exclude_id] = -np.inf
        
        # Top-K 추출
        k = min(top_k, self.vocab_size)
        top_indices = np.argpartition(-scores, k-1)[:k]
        top_indices = top_indices[np.argsort(-scores[top_indices])]
        
        neighbors = [(self.id2token[i], float(scores[i])) for i in top_indices]
        
        # SearchResult 반환
        from utils.result import SearchResult
        return SearchResult(
            query=query_word,
            model=self.model_name,
            metric=metric_obj.name,
            neighbors=neighbors
        )
    
    def _search_sentence_model(self, query: str, metric_obj, top_k: int):
        """Sentence Transformer용 검색"""
        from utils.result import SearchResult
        
        # 경고 메시지 반환
        return SearchResult(
            query=query,
            model=self.model_name,
            metric="cosine",
            neighbors=[("compare-sentences 명령어를 사용하세요", 0.0)]
        )
    
    def analogy(self, a: str, b: str, c: str, metric_obj, top_k: int = 5):
        """
        단어 유추: a - b + c = ?
        
        예: king - man + woman = queen
        """
        vec_a = self.embeddings[self.token2id[a]]
        vec_b = self.embeddings[self.token2id[b]]
        vec_c = self.embeddings[self.token2id[c]]
        
        result_vec = vec_a - vec_b + vec_c
        
        result = self.search(result_vec, metric_obj, top_k, exclude_self=False)
        result.query = f"{a} - {b} + {c}"
        
        return result