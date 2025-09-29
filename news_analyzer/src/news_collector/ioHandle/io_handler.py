"""
엑셀 기반 입출력 처리 모듈
"""
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional
import re

import pandas as pd
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils import get_column_letter

from ..config.models import NewsArticle

logger = logging.getLogger(__name__)

def _article_to_row(a: Any, fallback_keyword: str = "") -> dict:
    """
    NewsArticle(객체)든 dict든 안전하게 행으로 변환.
    프로젝트마다 필드명이 다를 수 있어 최대한 넓게 커버.
    """
    # dict/객체 양쪽 케이스 방어
    def g(obj, name, default=""):
        if isinstance(obj, dict):
            return obj.get(name, default)
        return getattr(obj, name, default)

    return {
        "회사":           g(a, "company"),
        "키워드":         g(a, "keyword", fallback_keyword),
        "그룹":           g(a, "group"),
        "제목":           g(a, "title"),
        "링크":           g(a, "link") or g(a, "url"),
        "원문링크":       g(a, "original_link") or g(a, "originallink"),
        "언론사":         g(a, "press") or g(a, "source"),
        "날짜":           g(a, "date") or g(a, "pub_date") or g(a, "pubDate"),
        "요약":           g(a, "summary") or g(a, "description"),
        "검색쿼리":       g(a, "search_query"),
        "수집시각":       g(a, "crawl_time") or datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "date_from":      g(a, "date_from", ""),
        "date_to":        g(a, "date_to", ""),
    }

class ExcelInputHandler:
    """엑셀 입력 처리"""

    @staticmethod
    def read_companies(filepath: str, sheet_name: str = "Company", column: str = "A", start_row: int = 2) -> List[str]:
        df = pd.read_excel(filepath, sheet_name=sheet_name, header=None)
        col_idx = ord(column.upper()) - ord("A")
        return [str(v).strip() for v in df.iloc[start_row - 1:, col_idx].dropna() if str(v).strip()]

    @staticmethod
    def read_keywords(filepath: str, sheet_name: str = "ESG", base_col: str = "C", cand_col: str = "D", start_row: int = 2) -> List[Dict[str, Any]]:
        df = pd.read_excel(filepath, sheet_name=sheet_name, header=None)
        base_idx = ord(base_col.upper()) - ord("A")
        cand_idx = ord(cand_col.upper()) - ord("A")

        rows = df.iloc[start_row - 1:, [base_idx, cand_idx]].dropna(how="all")
        out = []
        for _, (base_val, cand_val) in rows.iterrows():
            base = str(base_val).strip() if pd.notna(base_val) else ""
            cands = str(cand_val).split(",") if pd.notna(cand_val) else []
            for kw in (k.strip() for k in cands):
                if kw:
                    out.append({"group": base, "keyword": kw, "company": ""})
        return out

    @staticmethod
    def read_config(filepath: str, sheet_name: str = "Config") -> Dict[str, Any]:
        defaults = {"max_pages": 3, "min_delay": 1.0, "max_delay": 2.0}
        try:
            df = pd.read_excel(filepath, sheet_name=sheet_name)
            config = {}
            for _, row in df.iterrows():
                if "parameter" in df.columns and "value" in df.columns:
                    param = str(row["parameter"]).strip()
                    value = row["value"]
                    if "type" in df.columns:
                        t = str(row.get("type", "str")).lower()
                        if t == "int": value = int(value)
                        elif t == "float": value = float(value)
                        elif t == "bool": value = str(value).lower() in ["true", "1", "yes"]
                    config[param] = value

            # 연 단위 기간 처리
            if "date_from" not in config and "date_to" not in config:
                if "year" in config:
                    y = int(config["year"])
                    config["date_from"] = f"{y}.01.01"
                    config["date_to"] = f"{y}.12.31"
                elif "start_year" in config and "end_year" in config:
                    sy, ey = int(config["start_year"]), int(config["end_year"])
                    config["date_from"] = f"{sy}.01.01"
                    config["date_to"] = f"{ey}.12.31"
            for k, v in defaults.items():
                config.setdefault(k, v)
            return config
        except Exception as e:
            logger.warning(f"Config sheet not found, using defaults: {e}")
            return defaults


class ExcelOutputHandler:
    """엑셀 출력 처리"""

    @staticmethod
    def save_results(articles_by_keyword: Dict[str, List[Any]], filepath: str):
        Path(filepath).parent.mkdir(parents=True, exist_ok=True)
        with pd.ExcelWriter(filepath, engine="openpyxl") as writer:
            all_articles = []
            for kw, articles in articles_by_keyword.items():
                for a in articles:
                    row = a.to_dict() if hasattr(a, "to_dict") else {}
                    row["검색_회사"]  = getattr(a, "company", "")
                    row["기준키워드"] = getattr(a, "group", "")
                    row["후보키워드"] = getattr(a, "keyword", "")
                    row["검색_쿼리"]  = getattr(a, "search_query", "")
                    row["기간_from"] = getattr(a, "date_from", "")
                    row["기간_to"]   = getattr(a, "date_to", "")
                    all_articles.append(row)

            df = pd.DataFrame(all_articles)
            df.to_excel(writer, sheet_name="전체_데이터", index=False)

            # 스타일 적용
            try:
                ws = writer.sheets["전체_데이터"]
                ExcelOutputHandler._autosize_columns(ws)
            except Exception as e:
                logger.error(f"[save_results] 컬럼 자동 너비 조정 실패: {e}", exc_info=True)

    @staticmethod
    def save_company_results(
        results_by_company: Dict[str, Dict[str, List[NewsArticle]]],
        filepath: str
    ) -> None:
        """회사별 결과 저장 (호환성 유지)"""
        # 회사별 → 키워드별로 flatten
        all_articles = {}
        for company, keyword_articles in results_by_company.items():
            for keyword, articles in keyword_articles.items():
                key = f"{company}_{keyword}" if company else keyword
                all_articles[key] = articles
        
        ExcelOutputHandler.save_results(all_articles, filepath)

    @staticmethod
    def _clean_sheet_name(name: str, max_length: int = 31) -> str:
        """엑셀 시트명 정리"""
        # 특수문자 제거
        invalid = r'[\/\\\?\*\[\]\:]'
        safe = re.sub(invalid, "_", str(name)).strip()
        
        # 길이 제한
        if len(safe) > max_length:
            safe = safe[:max_length - 3] + "..."
        
        return safe or "Sheet"

    @staticmethod
    def _dedupe_sheet_name(base: str, used: set, max_length: int = 31) -> str:
        """중복 시트명 처리"""
        if base not in used:
            return base
        
        i = 2
        while True:
            suffix = f"_{i}"
            # 충분한 공간 확보
            if len(base) + len(suffix) <= max_length:
                candidate = base + suffix
            else:
                candidate = base[:max_length - len(suffix)] + suffix
            
            if candidate not in used:
                return candidate
            i += 1

    @staticmethod
    def _apply_summary_style(ws) -> None:
        """요약 시트 스타일 적용"""
        try:
            header_font = Font(bold=True, color="FFFFFF")
            header_fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
            header_alignment = Alignment(horizontal="center", vertical="center")
            
            # 헤더 행 스타일
            for cell in ws[1]:
                cell.font = header_font
                cell.fill = header_fill
                cell.alignment = header_alignment
            
            ExcelOutputHandler._autosize_columns(ws)
            
        except Exception as e:
            logger.warning(f"Could not apply styles: {str(e)}")
    @staticmethod
    def save_results_to_sheet(results_by_keyword: dict, file_path: str, sheet_name: str = "output", replace: bool = True):
        """키워드별 결과를 단일 시트로 합쳐 input.xlsx의 특정 시트를 교체 저장."""
        # (1) dict -> DataFrame 풀기 (필요에 따라 정렬/칼럼 순서 조정)
        rows = []
        for kw, articles in results_by_keyword.items():
            for a in articles:
                rows.append({
                    "회사": getattr(a, "company", ""),
                    "키워드": getattr(a, "keyword", kw),
                    "그룹": getattr(a, "group", ""),
                    "제목": a.title,
                    "링크": a.link,
                    "언론사": a.press,
                    "날짜": a.date,
                    "요약": a.summary,
                    "검색쿼리": getattr(a, "search_query", ""),
                    "date_from": getattr(a, "date_from", None),
                    "date_to": getattr(a, "date_to", None),
                })
        df = pd.DataFrame(rows)

        # (2) 기존 파일 열어서 시트 교체
        try:
            book = load_workbook(file_path)
            if sheet_name in book.sheetnames and replace:
                std = book[sheet_name]
                book.remove(std)
            with pd.ExcelWriter(file_path, engine="openpyxl", mode="a" if sheet_name not in book.sheetnames else "a") as writer:
                writer.book = book
                df.to_excel(writer, index=False, sheet_name=sheet_name)
                writer.save()
        except FileNotFoundError:
            # 파일이 없으면 새로 생성
            with pd.ExcelWriter(file_path, engine="openpyxl") as writer:
                df.to_excel(writer, index=False, sheet_name=sheet_name)

    @staticmethod
    def _autosize_columns(ws, max_width: int = 50):
        for column in ws.columns:
            length = max((len(str(cell.value)) if cell.value else 0) for cell in column)
            col_letter = column[0].column_letter
            ws.column_dimensions[col_letter].width = min(length + 2, max_width)


    def save_keyword_results(
        articles_by_keyword: Dict[str, List[NewsArticle]], 
        output_dir: str, 
        filename_prefix: str = "keyword_results"
    ) -> str:
        """
        크롤링 결과를 엑셀로 저장하고 경로 반환
        """
        # 출력 디렉토리 생성
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # 파일명 생성
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filepath = output_path / f"{filename_prefix}_{timestamp}.xlsx"
        
        # 저장
        ExcelOutputHandler.save_results(
            articles_by_keyword=articles_by_keyword,
            filepath=str(filepath),
            summary_sheet=True,
            separate_sheets=True
        )
        
        return str(filepath)