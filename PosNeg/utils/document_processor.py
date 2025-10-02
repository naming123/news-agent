"""
utils/document_processor.py
문장/문서를 벡터로 변환
"""

import numpy as np
from typing import List, Tuple, Dict


class DocumentProcessor:
    """문장/문서 처리기"""
    
    def __init__(self, embeddings: np.ndarray, token2id: Dict):
        self.embeddings = embeddings
        self.token2id = token2id
    
    def sentence_to_vector(self, sentence: str) -> np.ndarray:
        """
        문장을 벡터로 변환 (평균 임베딩)
        
        예: "경제가 어렵다" 
        → [경제, 어렵다] 두 단어의 벡터 평균
        """
        # 간단한 토큰화 (공백 기준)
        words = sentence.lower().strip().split()
        
        vectors = []
        found_words = []
        
        for word in words:
            # 구두점 제거
            word = word.strip('.,!?;:')
            
            if word in self.token2id:
                vectors.append(self.embeddings[self.token2id[word]])
                found_words.append(word)
        
        if vectors:
            # 평균 벡터 반환
            return np.mean(vectors, axis=0), found_words
        else:
            return None, []
    
    def compare_word_with_sentences(
        self,
        query_word: str,
        sentences: List[str],
        metric_obj
    ) -> List[Tuple[int, str, float, List[str]]]:
        """
        단어와 여러 문장 비교
        
        Args:
            query_word: 기준 단어 (예: "부정")
            sentences: 문장 리스트
            metric_obj: 유사도 지표 객체
        
        Returns:
            [(인덱스, 문장, 유사도 점수, 인식된 단어들), ...]
        """
        if query_word not in self.token2id:
            raise KeyError(f"'{query_word}'는 사전에 없습니다")
        
        # 기준 단어 벡터
        query_vec = self.embeddings[self.token2id[query_word]]
        
        results = []
        
        for idx, sentence in enumerate(sentences):
            sentence_vec, found_words = self.sentence_to_vector(sentence)
            
            if sentence_vec is not None:
                # 유사도 계산 (코사인)
                query_norm = query_vec / (np.linalg.norm(query_vec) + 1e-12)
                sent_norm = sentence_vec / (np.linalg.norm(sentence_vec) + 1e-12)
                similarity = float(np.dot(query_norm, sent_norm))
                
                results.append((idx + 1, sentence, similarity, found_words))
            else:
                # 인식된 단어가 없는 경우
                results.append((idx + 1, sentence, 0.0, []))
        
        # 유사도 내림차순 정렬
        results.sort(key=lambda x: x[2], reverse=True)
        
        return results