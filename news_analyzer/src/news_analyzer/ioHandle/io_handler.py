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

from typing import Dict, List, Optional
from datetime import datetime
import logging
import re

import pandas as pd
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils import get_column_letter

logger = logging.getLogger(__name__)

# 프로젝트 정의에 맞춰 실제 구현체 사용 (여기선 예시 타입용)
class NewsArticle:
    title: str
    press: Optional[str]
    date: Optional[datetime]   # 또는 str
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
        articles_by_keyword: Dict[str, List['NewsArticle']],
        filepath: str,
        summary_sheet: bool = True,
        separate_sheets: bool = True,
        datetime_format: str = "yyyy-mm-dd hh:mm:ss",
    ) -> None:
        """크롤링 결과를 엑셀로 저장"""
        try:
            with pd.ExcelWriter(filepath, engine="openpyxl", datetime_format=datetime_format) as writer:
                wb = writer.book

                # --- 보이는 시트 최소 1개 보장용 플레이스홀더 ---
                if "empty" in wb.sheetnames:
                    placeholder = wb["empty"]
                else:
                    placeholder = wb.create_sheet("empty")
                placeholder.sheet_state = "visible"
                real_sheet_created = False

                sheet_names_in_use = set()

                # 1) 요약 시트
                if summary_sheet:
                    rows = []
                    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    for keyword, articles in articles_by_keyword.items():
                        latest_title = ""
                        if articles:
                            latest = ExcelOutputHandler._pick_latest(articles)
                            latest_title = latest.title if latest else (articles[0].title or "")
                        press_count = len({a.press for a in articles if getattr(a, "press", None)})
                        rows.append({
                            "키워드": keyword,
                            "수집 기사 수": len(articles),
                            "수집 시각": now_str,
                            "언론사 수": press_count,
                            "최신 기사": latest_title,
                        })
                    if rows:
                        df = pd.DataFrame(rows)
                        df.to_excel(writer, sheet_name="요약", index=False)
                        real_sheet_created = True
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
                    preferred = ["검색_키워드", "title", "press", "date", "link", "crawled_at"]
                    cols = [c for c in preferred if c in all_df.columns] + [c for c in all_df.columns if c not in preferred]
                    all_df = all_df[cols]
                    all_df.to_excel(writer, sheet_name="전체_데이터", index=False)
                    real_sheet_created = True
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

                        base = ExcelOutputHandler._clean_sheet_name(keyword)
                        name = ExcelOutputHandler._dedupe_sheet_name(base, sheet_names_in_use)
                        sheet_names_in_use.add(name)

                        df.to_excel(writer, sheet_name=name, index=False)
                        real_sheet_created = True
                        ws = writer.sheets[name]
                        ExcelOutputHandler._autosize_columns(ws)
                        ExcelOutputHandler._freeze_and_filter(ws)

                # --- 저장 직전 정리 ---
                if real_sheet_created:
                    # 실제 시트가 하나라도 있으면 플레이스홀더 제거
                    try:
                        wb.remove(placeholder)
                    except Exception:
                        pass
                else:
                    # 실제 시트가 0개면 플레이스홀더에 간단 메시지 써서 저장
                    placeholder.cell(row=1, column=1, value="info")
                    placeholder.cell(row=1, column=2, value="no data")

            logger.info(f"Results saved to {filepath}")
        except Exception as e:
            logger.error(f"Error saving results to Excel: {str(e)}")
            raise

    # 레거시 호환: 기존 코드가 이 이름을 호출했을 가능성
    @staticmethod
    def save_company_results(
        articles_by_keyword: Dict[str, List['NewsArticle']],
        filepath: str,
        **kwargs,
    ) -> None:
        return ExcelOutputHandler.save_results(articles_by_keyword, filepath, **kwargs)

    # ----------------- 내부 유틸 -----------------
    @staticmethod
    def _pick_latest(articles: List['NewsArticle']) -> Optional['NewsArticle']:
        def to_dt(x):
            v = getattr(x, "date", None)
            if v is None:
                return None
            if isinstance(v, datetime):
                return v
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
        invalid = r'[\/\\\?\*\[\]\:]'
        safe = re.sub(invalid, "_", str(name)).strip()
        if len(safe) > max_length:
            safe = safe[: max_length - 3] + "..."
        return safe or "Sheet"

    @staticmethod
    def _dedupe_sheet_name(base: str, used: set, max_length: int = 31) -> str:
        if base not in used:
            return base
        i = 2
        while True:
            suffix = f"_{i}"
            cand = base if len(base) + len(suffix) <= max_length else base[: max_length - len(suffix)]
            cand += suffix
            if cand not in used:
                return cand
            i += 1

    @staticmethod
    def _apply_summary_style(ws) -> None:
        try:
            header_font = Font(bold=True, color="FFFFFF")
            header_fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
            header_alignment = Alignment(horizontal="center", vertical="center")
            for cell in next(ws.iter_rows(min_row=1, max_row=1)):
                cell.font = header_font
                cell.fill = header_fill
                cell.alignment = header_alignment
            ExcelOutputHandler._autosize_columns(ws, header_extra=2)
        except Exception as e:
            logger.warning(f"Could not apply styles: {str(e)}")

    @staticmethod
    def _freeze_and_filter(ws) -> None:
        try:
            ws.freeze_panes = "A2"
            last_col = get_column_letter(ws.max_column)
            ws.auto_filter.ref = f"A1:{last_col}{ws.max_row}"
        except Exception as e:
            logger.warning(f"Could not set freeze/filter: {str(e)}")

    @staticmethod
    def _autosize_columns(ws, header_extra: int = 0) -> None:
        """내용 길이에 따라 열 너비 자동 조정 (상한 50)"""
        try:
            for col_idx in range(1, ws.max_column + 1):
                letter = get_column_letter(col_idx)
                max_len = 0
                # iter_cols는 generator를 반환 → next(...)로 첫 컬럼 얻기
                col_cells = next(ws.iter_cols(
                    min_col=col_idx, max_col=col_idx,
                    min_row=1, max_row=ws.max_row
                ))
                for cell in col_cells:
                    text = "" if cell.value is None else str(cell.value)
                    if len(text) > max_len:
                        max_len = len(text)
                ws.column_dimensions[letter].width = min(max_len + 2 + header_extra, 50)
        except Exception as e:
            logger.warning(f"Could not autosize columns: {str(e)}")

# 15:26:26,323