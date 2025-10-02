# 추가 설치 필요
# pip install sentence-transformers

# models/sentence_loader.py (새 파일)

from sentence_transformers import SentenceTransformer
import numpy as np
from typing import Dict, Tuple


class MultilingualLoader:
    """다국어 Sentence Transformer 모델"""
    
    def __init__(self):
        self.model = None
        self.vocab = None
        self.embeddings = None
    
    def load(self, model_name: str = 'paraphrase-multilingual-MiniLM-L12-v2'):
        """
        다국어 모델 로드
        
        지원 모델:
        - paraphrase-multilingual-MiniLM-L12-v2 (50+ 언어)
        - distiluse-base-multilingual-cased-v2
        """
        print(f"\n{'='*60}")
        print(f"다국어 모델 로드: {model_name}")
        print(f"{'='*60}")
        print("※ 한국어, 영어 등 50개 언어 지원")
        
        self.model = SentenceTransformer(model_name)
        
        print(f"✓ 로드 완료!\n")
    
    def encode_words(self, words: list) -> np.ndarray:
        """단어 리스트를 벡터로 변환"""
        return self.model.encode(words)
    
    def encode_sentences(self, sentences: list) -> np.ndarray:
        """문장 리스트를 벡터로 변환"""
        return self.model.encode(sentences)