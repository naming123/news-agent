import pandas as pd
from pathlib import Path
from typing import List, Union
from .result import SearchResult


class ResultExporter:
    """결과 출력기 (엑셀, CSV)"""
    
    def __init__(self, output_dir: str = './results/'):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True, parents=True)
    
    def export_to_excel(
        self,
        results: Union[SearchResult, List[SearchResult]],
        filename: str = None,
        include_summary: bool = True
    ) -> str:
        """
        엑셀로 출력
        
        Args:
            results: 검색 결과 (단일 또는 리스트)
            filename: 출력 파일명
            include_summary: 요약 시트 포함 여부
        """
        if not isinstance(results, list):
            results = [results]
        
        if filename is None:
            timestamp = pd.Timestamp.now().strftime("%Y%m%d_%H%M%S")
            filename = f"similarity_results_{timestamp}.xlsx"
        
        filepath = self.output_dir / filename
        
        with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
            # 각 쿼리마다 시트 생성
            for idx, result in enumerate(results, 1):
                df = self._result_to_dataframe(result)
                sheet_name = f"{idx}_{result.query[:20]}"  # 시트명 길이 제한
                df.to_excel(writer, sheet_name=sheet_name, index=False)
            
            # 요약 시트
            if include_summary and len(results) > 1:
                summary_df = self._create_summary(results)
                summary_df.to_excel(writer, sheet_name='Summary', index=False)
        
        print(f"✓ 엑셀 파일 저장: {filepath}")
        return str(filepath)
    
    def export_to_csv(
        self,
        results: Union[SearchResult, List[SearchResult]],
        filename: str = None
    ) -> str:
        """CSV로 출력"""
        if not isinstance(results, list):
            results = [results]
        
        if filename is None:
            timestamp = pd.Timestamp.now().strftime("%Y%m%d_%H%M%S")
            filename = f"similarity_results_{timestamp}.csv"
        
        filepath = self.output_dir / filename
        
        # 모든 결과를 하나의 DataFrame으로
        all_data = []
        for result in results:
            df = self._result_to_dataframe(result)
            all_data.append(df)
        
        combined_df = pd.concat(all_data, ignore_index=True)
        combined_df.to_csv(filepath, index=False, encoding='utf-8-sig')
        
        print(f"✓ CSV 파일 저장: {filepath}")
        return str(filepath)
    
    def _result_to_dataframe(self, result: SearchResult) -> pd.DataFrame:
        """SearchResult를 DataFrame으로 변환"""
        data = {
            'Query': [result.query] * len(result.neighbors),
            'Model': [result.model] * len(result.neighbors),
            'Metric': [result.metric] * len(result.neighbors),
            'Rank': list(range(1, len(result.neighbors) + 1)),
            'Word': [word for word, _ in result.neighbors],
            'Score': [score for _, score in result.neighbors],
            'Timestamp': [result.timestamp] * len(result.neighbors)
        }
        return pd.DataFrame(data)
    
    def _create_summary(self, results: List[SearchResult]) -> pd.DataFrame:
        """요약 DataFrame 생성"""
        summary_data = {
            'Query': [r.query for r in results],
            'Model': [r.model for r in results],
            'Metric': [r.metric for r in results],
            'Top1_Word': [r.neighbors[0][0] if r.neighbors else '' for r in results],
            'Top1_Score': [r.neighbors[0][1] if r.neighbors else 0 for r in results],
            'Num_Results': [len(r.neighbors) for r in results],
            'Timestamp': [r.timestamp for r in results]
        }
        return pd.DataFrame(summary_data)