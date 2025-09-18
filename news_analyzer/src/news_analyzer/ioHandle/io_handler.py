"""
엑셀 기반 입출력 처리 모듈
"""
import logging
from datetime import datetime
from typing import List, Dict, Any

import pandas as pd
from openpyxl.styles import Font, PatternFill, Alignment

from news_analyzer.config.models import NewsArticle

logger = logging.getLogger(__name__)


class ExcelInputHandler:
    """엑셀 입력 처리"""

    @staticmethod
    def read_keywords(
        filepath: str,
        sheet_name: str = 'ESG',
        column: str = 'D',
        start_row: int = 2
    ) -> List[Dict[str, Any]]:
        """
        ESG 시트에서 키워드 읽기 (D열, 2행부터, 콤마로 분리)

        Args:
            filepath: 엑셀 파일 경로
            sheet_name: 읽을 시트 이름 (기본 ESG)
            column: 키워드가 있는 열 (기본 D)
            start_row: 키워드가 시작되는 행 번호 (기본 2)

        Returns:
            [{'keyword': 키워드, 'company': '', 'metadata': {}}]
        """
        try:
            df = pd.read_excel(filepath, sheet_name=sheet_name, header=None)

            # D열만 추출 (Excel D → pandas index 3)
            col_idx = ord(column.upper()) - ord('A')
            keywords_raw = df.iloc[start_row - 1:, col_idx].dropna()

            keywords = []
            for cell in keywords_raw:
                for kw in str(cell).split(','):
                    kw = kw.strip()
                    if kw:
                        keywords.append({
                            'keyword': kw,
                            'company': '',  # 회사명 없음
                            'metadata': {}
                        })

            logger.info(f"Loaded {len(keywords)} keywords from {filepath} [{sheet_name}!{column}{start_row}:]")
            return keywords

        except Exception as e:
            logger.error(f"Error reading ESG keywords: {str(e)}")
            raise

    @staticmethod
    def read_config(filepath: str, sheet_name: str = 'Config') -> Dict[str, Any]:
        """Config 시트에서 설정 읽기 (없으면 기본값 반환)"""
        try:
            df = pd.read_excel(filepath, sheet_name=sheet_name)
            config = {}
            for _, row in df.iterrows():
                if 'parameter' in df.columns and 'value' in df.columns:
                    param = str(row['parameter']).strip()
                    value = row['value']

                    if 'type' in df.columns:
                        type_str = str(row.get('type', 'str')).lower()
                        if type_str == 'int':
                            value = int(value)
                        elif type_str == 'float':
                            value = float(value)
                        elif type_str == 'bool':
                            value = str(value).lower() in ['true', '1', 'yes']

                    config[param] = value
            return config
        except Exception as e:
            logger.warning(f"Config sheet not found or error reading: {str(e)}")
            return {'max_pages': 3, 'min_delay': 1.0, 'max_delay': 2.0}


class ExcelOutputHandler:
    """엑셀 출력 처리"""

    @staticmethod
    def save_results(
        articles_by_keyword: Dict[str, List[NewsArticle]],
        filepath: str,
        summary_sheet: bool = True,
        separate_sheets: bool = True
    ) -> None:
        """크롤링 결과를 엑셀로 저장"""
        try:
            with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
                # 1. 요약 시트
                if summary_sheet:
                    summary_data = []
                    for keyword, articles in articles_by_keyword.items():
                        summary_data.append({
                            '키워드': keyword,
                            '수집 기사 수': len(articles),
                            '수집 시각': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                            '언론사 수': len(set(a.press for a in articles if a.press)),
                            '최신 기사': articles[0].title if articles else '',
                        })
                    if summary_data:
                        summary_df = pd.DataFrame(summary_data)
                        summary_df.to_excel(writer, sheet_name='요약', index=False)
                        ExcelOutputHandler._apply_summary_style(writer.sheets['요약'], len(summary_data))

                # 2. 전체 데이터 시트
                all_articles = []
                for keyword, articles in articles_by_keyword.items():
                    for article in articles:
                        article_dict = article.to_dict()
                        article_dict['검색_키워드'] = keyword
                        all_articles.append(article_dict)
                if all_articles:
                    all_df = pd.DataFrame(all_articles)
                    cols = ['검색_키워드', 'title', 'press', 'date', 'link', 'crawled_at']
                    cols = [c for c in cols if c in all_df.columns]
                    all_df = all_df[cols]
                    all_df.to_excel(writer, sheet_name='전체_데이터', index=False)

                # 3. 키워드별 개별 시트
                if separate_sheets:
                    for keyword, articles in articles_by_keyword.items():
                        if articles:
                            sheet_name = ExcelOutputHandler._clean_sheet_name(keyword)
                            df = pd.DataFrame([a.to_dict() for a in articles])
                            cols = ['title', 'press', 'date', 'link', 'crawled_at']
                            cols = [c for c in cols if c in df.columns]
                            df = df[cols]
                            df.to_excel(writer, sheet_name=sheet_name, index=False)

            logger.info(f"Results saved to {filepath}")
        except Exception as e:
            logger.error(f"Error saving results to Excel: {str(e)}")
            raise

    @staticmethod
    def _clean_sheet_name(name: str, max_length: int = 31) -> str:
        invalid_chars = ['/', '\\', '?', '*', '[', ']', ':']
        for char in invalid_chars:
            name = name.replace(char, '_')
        if len(name) > max_length:
            name = name[:max_length - 3] + '...'
        return name.strip()

    @staticmethod
    def _apply_summary_style(worksheet, row_count: int):
        try:
            header_font = Font(bold=True, color="FFFFFF")
            header_fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
            header_alignment = Alignment(horizontal="center", vertical="center")
            for cell in worksheet[1]:
                cell.font = header_font
                cell.fill = header_fill
                cell.alignment = header_alignment
            for column in worksheet.columns:
                max_length = 0
                column_letter = column[0].column_letter
                for cell in column:
                    try:
                        if len(str(cell.value)) > max_length:
                            max_length = len(str(cell.value))
                    except:
                        pass
                worksheet.column_dimensions[column_letter].width = min(max_length + 2, 50)
        except Exception as e:
            logger.warning(f"Could not apply styles: {str(e)}")
