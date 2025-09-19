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

from __future__ import annotations
from typing import Dict, List, Optional
from datetime import datetime
import pandas as pd
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils import get_column_letter
import re
import logging

logger = logging.getLogger(__name__)

# 예시: NewsArticle 타입 힌트(프로젝트 정의에 맞춰 조정)
class NewsArticle:
    title: str
    press: Optional[str]
    date: Optional[datetime]  # 또는 str
    link: str
    crawled_at: Optional[datetime]

    def to_dict(self) -> dict:
        return {
            "title": self.title,
            "press": self.press,
            "date": self.date,
            "link": self.link,
            "crawled_at": self.crawled_at,
        }


class ExcelOutputHandler:
    """엑셀 출력 처리"""

    @staticmethod
    def save_results(
        articles_by_keyword: Dict[str, List[NewsArticle]],
        filepath: str,
        summary_sheet: bool = True,
        separate_sheets: bool = True,
        datetime_format: str = "yyyy-mm-dd hh:mm:ss",
    ) -> None:
        """크롤링 결과를 엑셀로 저장"""
        try:
            with pd.ExcelWriter(filepath, engine="openpyxl", datetime_format=datetime_format) as writer:
                sheet_names_in_use = set()

                # 1) 요약 시트
                if summary_sheet:
                    summary_rows = []
                    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                    for keyword, articles in articles_by_keyword.items():
                        latest_title = ""
                        if articles:
                            # date가 있으면 최신으로, 없으면 입력 순서 유지
                            latest = ExcelOutputHandler._pick_latest(articles)
                            latest_title = latest.title if latest else (articles[0].title or "")

                        press_count = len({a.press for a in articles if getattr(a, "press", None)})
                        summary_rows.append(
                            {
                                "키워드": keyword,
                                "수집 기사 수": len(articles),
                                "수집 시각": now_str,
                                "언론사 수": press_count,
                                "최신 기사": latest_title,
                            }
                        )

                    if summary_rows:
                        df = pd.DataFrame(summary_rows)
                        df.to_excel(writer, sheet_name="요약", index=False)
                        ws = writer.sheets["요약"]
                        ExcelOutputHandler._apply_summary_style(ws)
                        ExcelOutputHandler._freeze_and_filter(ws)

                # 2) 전체 데이터 시트
                all_rows = []
                for keyword, articles in articles_by_keyword.items():
                    for art in articles:
                        row = art.to_dict()
                        row["검색_키워드"] = keyword
                        all_rows.append(row)

                if all_rows:
                    all_df = pd.DataFrame(all_rows)

                    # 칼럼 정렬(있는 것만 유지)
                    preferred = ["검색_키워드", "title", "press", "date", "link", "crawled_at"]
                    cols = [c for c in preferred if c in all_df.columns] + [c for c in all_df.columns if c not in preferred]
                    all_df = all_df[cols]

                    all_df.to_excel(writer, sheet_name="전체_데이터", index=False)
                    ws_all = writer.sheets["전체_데이터"]
                    ExcelOutputHandler._autosize_columns(ws_all)
                    ExcelOutputHandler._freeze_and_filter(ws_all)

                # 3) 키워드별 개별 시트
                if separate_sheets:
                    for keyword, articles in articles_by_keyword.items():
                        if not articles:
                            continue
                        df = pd.DataFrame([a.to_dict() for a in articles])

                        preferred = ["title", "press", "date", "link", "crawled_at"]
                        cols = [c for c in preferred if c in df.columns] + [c for c in df.columns if c not in preferred]
                        df = df[cols]

                        # 시트명 생성(충돌/길이/금지문자 처리)
                        base_name = ExcelOutputHandler._clean_sheet_name(keyword)
                        sheet_name = ExcelOutputHandler._dedupe_sheet_name(base_name, sheet_names_in_use)
                        sheet_names_in_use.add(sheet_name)

                        df.to_excel(writer, sheet_name=sheet_name, index=False)
                        ws = writer.sheets[sheet_name]
                        ExcelOutputHandler._autosize_columns(ws)
                        ExcelOutputHandler._freeze_and_filter(ws)

            logger.info(f"Results saved to {filepath}")
        except Exception as e:
            logger.error(f"Error saving results to Excel: {str(e)}")
            raise

    # ▶ 레거시 호환용: 기존 호출 경로가 이 이름을 찾고 있었습니다.
    @staticmethod
    def save_company_results(
        articles_by_keyword: Dict[str, List[NewsArticle]],
        filepath: str,
        **kwargs,
    ) -> None:
        """
        레거시 코드 호환을 위한 래퍼.
        내부적으로 save_results를 호출합니다.
        """
        return ExcelOutputHandler.save_results(articles_by_keyword, filepath, **kwargs)

    # -----------------------
    # 내부 유틸
    # -----------------------
    @staticmethod
    def _pick_latest(articles: List[NewsArticle]) -> Optional[NewsArticle]:
        """date가 존재하고 비교 가능한 경우 최신 기사 선택."""
        def to_dt(x):
            v = getattr(x, "date", None)
            if v is None:
                return None
            if isinstance(v, datetime):
                return v
            # str -> datetime 파싱 시도(프로젝트 포맷에 맞춰 필요시 커스터마이즈)
            try:
                return datetime.fromisoformat(str(v))
            except Exception:
                return None

        dated = [(to_dt(a), a) for a in articles]
        dated = [t for t in dated if t[0] is not None]
        if not dated:
            return None
        return max(dated, key=lambda t: t[0])[1]

    @staticmethod
    def _clean_sheet_name(name: str, max_length: int = 31) -> str:
        """금지문자 제거 + 길이 제한."""
        invalid_chars = r'[\/\\\?\*\[\]\:]'
        safe = re.sub(invalid_chars, "_", str(name)).strip()
        if len(safe) > max_length:
            safe = safe[: max_length - 3] + "..."
        # 빈 문자열 방지
        return safe or "Sheet"

    @staticmethod
    def _dedupe_sheet_name(base: str, used: set, max_length: int = 31) -> str:
        """시트명 충돌 시 뒤에 _2, _3 ...로 부여 (길이 제한 유지)"""
        if base not in used:
            return base
        i = 2
        while True:
            suffix = f"_{i}"
            candidate = base
            if len(candidate) + len(suffix) > max_length:
                candidate = candidate[: max_length - len(suffix)]
            candidate += suffix
            if candidate not in used:
                return candidate
            i += 1

    @staticmethod
    def _apply_summary_style(worksheet) -> None:
        try:
            header_font = Font(bold=True, color="FFFFFF")
            header_fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
            header_alignment = Alignment(horizontal="center", vertical="center")

            # 1행 헤더 스타일
            for cell in next(worksheet.iter_rows(min_row=1, max_row=1)):
                cell.font = header_font
                cell.fill = header_fill
                cell.alignment = header_alignment

            ExcelOutputHandler._autosize_columns(worksheet, header_extra=2)
        except Exception as e:
            logger.warning(f"Could not apply styles: {str(e)}")

    @staticmethod
    def _freeze_and_filter(worksheet) -> None:
        """헤더 고정 + 오토필터"""
        try:
            worksheet.freeze_panes = "A2"
            # 유효한 데이터 범위로 자동 필터 설정
            max_col = worksheet.max_column
            max_row = worksheet.max_row
            if max_col and max_row and max_row >= 1:
                last_col = get_column_letter(max_col)
                worksheet.auto_filter.ref = f"A1:{last_col}{max_row}"
        except Exception as e:
            logger.warning(f"Could not set freeze/filter: {str(e)}")

    @staticmethod
    def _autosize_columns(worksheet, header_extra: int = 0) -> None:
        """내용 길이에 따라 열 너비 자동 조정 (상한 50)"""
        try:
            for col_idx in range(1, worksheet.max_column + 1):
                letter = get_column_letter(col_idx)
                max_len = 0
                for cell in worksheet.iter_cols(min_col=col_idx, max_col=col_idx, min_row=1, max_row=worksheet.max_row)[0]:
                    text = str(cell.value) if cell.value is not None else ""
                    if len(text) > max_len:
                        max_len = len(text)
                worksheet.column_dimensions[letter].width = min(max_len + 2 + header_extra, 50)
        except Exception as e:
            logger.warning(f"Could not autosize columns: {str(e)}")

