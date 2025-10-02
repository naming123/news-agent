"""
utils/importer.py
엑셀/CSV 파일에서 단어 읽기
"""

import pandas as pd
from pathlib import Path
from typing import List


class WordImporter:
    """엑셀/CSV에서 단어 리스트 불러오기"""
    
    @staticmethod
    def load_from_excel(filepath: str, column: str = None) -> List[str]:
        """
        엑셀에서 단어 리스트 로드
        
        Args:
            filepath: 엑셀 파일 경로
            column: 읽을 컬럼명 (None이면 첫 번째 컬럼)
        
        Returns:
            단어 리스트
            
        엑셀 형식:
        | 단어    |
        |---------|
        | king    |
        | queen   |
        | prince  |
        """
        df = pd.read_excel(filepath)
        
        if column is None:
            # 첫 번째 컬럼 사용
            words = df.iloc[:, 0].dropna().tolist()
        else:
            words = df[column].dropna().tolist()
        
        # 문자열로 변환
        words = [str(word).strip() for word in words]
        
        print(f"✓ 엑셀에서 {len(words)}개 단어 로드: {filepath}")
        return words
    
    @staticmethod
    def load_from_csv(filepath: str, column: str = None) -> List[str]:
        """CSV에서 단어 리스트 로드"""
        df = pd.read_csv(filepath)
        
        if column is None:
            words = df.iloc[:, 0].dropna().tolist()
        else:
            words = df[column].dropna().tolist()
        
        words = [str(word).strip() for word in words]
        
        print(f"✓ CSV에서 {len(words)}개 단어 로드: {filepath}")
        return words
    
    
    @staticmethod
    def load_sentences_from_excel(
        filepath: str, 
        sentence_column: str = None
    ) -> List[str]:
        """
        엑셀에서 문장 리스트 로드
        
        Args:
            filepath: 엑셀 파일 경로
            sentence_column: 문장이 있는 컬럼명 (None이면 첫 번째)
        
        엑셀 형식:
        | 문장 |
        |------|
        | 경제가 침체되고 어렵다 |
        | 주가가 급락했다 |
        """
        df = pd.read_excel(filepath)
        
        if sentence_column is None:
            sentences = df.iloc[:, 0].dropna().tolist()
        else:
            sentences = df[sentence_column].dropna().tolist()
        
        # 문자열로 변환
        sentences = [str(sent).strip() for sent in sentences]
        
        print(f"✓ 엑셀에서 {len(sentences)}개 문장 로드: {filepath}")
        return sentences