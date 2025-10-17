import re, unicodedata
import pandas as pd
from pandas import DataFrame, Timestamp
from typing import Optional, Literal

COMPANY_COL = "회사명"
KW_CANDIDATES = ("뉴스 키워드 후보", "Key Issue (핵심 이슈)")
DATE_PREFS = ("뉴스 보도날짜(YYYYMMDD)", "뉴스 보도날짜")
URL_COL, TITLE_COL, SCORE_COL = "기사 URL", "기사제목", "부정점수"

def _canon(s: str) -> str:
    if pd.isna(s): return s
    s = unicodedata.normalize("NFKC", str(s))
    s = s.replace("\u00A0"," ").replace("\u200B","").replace("\uFEFF","")
    s = re.sub(r"\s+"," ", s).strip()
    return s

def _pick_kw_col(df: DataFrame) -> str:
    for c in KW_CANDIDATES:
        if c in df.columns: return c
    raise KeyError(f"키워드 컬럼 없음. 후보={KW_CANDIDATES}, 실제={list(df.columns)}")

def _pick_date_col(df: DataFrame) -> str:
    for c in DATE_PREFS:
        if c in df.columns: return c
    cand = [c for c in df.columns if "보도날짜" in str(c)]
    if not cand: raise KeyError("날짜 컬럼을 찾을 수 없습니다.")
    return cand[0]

def deduplicate_news(
    input_xlsx_path: str,
    output_xlsx_path: Optional[str] = None,
    sheet_name: Optional[str | int] = 0,
    mode: Literal["rolling30","calendar_month"] = "rolling30",
    window_days: int = 30,
    pick_strategy: Literal["earliest","highest_score"] = "earliest",
):
    df = pd.read_excel(input_xlsx_path, sheet_name=sheet_name)
    if COMPANY_COL not in df.columns:
        raise KeyError(f"회사 컬럼 '{COMPANY_COL}' 없음.")
    kw_col   = _pick_kw_col(df)
    date_col = _pick_date_col(df)

    # 1) 날짜: 8자리만 안전 추출 → 파싱
    s = df[date_col].astype(str).str.extract(r"(\d{8})")[0]
    df["_dt"] = pd.to_datetime(s, format="%Y%m%d", errors="coerce")
    df = df.dropna(subset=["_dt"]).copy()

    # 2) 키 정규화(그룹용 보조 컬럼)
    df["_comp_norm"] = df[COMPANY_COL].map(_canon)
    df["_kw_norm"]   = df[kw_col].map(_canon)

    # (선택) 정규화로 값이 바뀐 행을 로그로 확인하고 싶다면:
    changed = df[(df["_comp_norm"] != df[COMPANY_COL]) | (df["_kw_norm"] != df[kw_col])]
    if not changed.empty:
        # 필요 시 Streamlit에 표시하거나 파일로 저장해서 확인
        print("[DEBUG] 정규화로 달라진 키 샘플:")
        print(changed[[COMPANY_COL, "_comp_norm", kw_col, "_kw_norm"]].head(10).to_string(index=False))

    # 3) URL/제목 완전중복 1차 제거
    base_sort = ["_comp_norm","_kw_norm","_dt"]
    if URL_COL in df.columns:
        df = df.sort_values(base_sort).drop_duplicates(["_comp_norm","_kw_norm",URL_COL], keep="first")
    if TITLE_COL in df.columns:
        df = df.sort_values(base_sort).drop_duplicates(["_comp_norm","_kw_norm",TITLE_COL], keep="first")

    # 4) 30일 창 대표 선택
    if mode == "calendar_month":
        df["_ym"] = df["_dt"].dt.to_period("M")
        def pick_one(g: DataFrame) -> DataFrame:
            if pick_strategy=="highest_score" and (SCORE_COL in g.columns):
                idx = pd.to_numeric(g[SCORE_COL], errors="coerce").fillna(float("-inf")).idxmax()
                return g.loc[[idx]]
            return g.nsmallest(1, "_dt")
        kept = (df.sort_values(base_sort)
                  .groupby(["_comp_norm","_kw_norm","_ym"], group_keys=False)
                  .apply(pick_one))
    else:
        kept_rows = []
        for _, g in df.sort_values(base_sort).groupby(["_comp_norm","_kw_norm"], sort=False):
            last_keep: Optional[Timestamp] = None
            buf = []
            def flush():
                nonlocal buf, kept_rows
                if not buf: return
                if pick_strategy=="highest_score" and (SCORE_COL in df.columns):
                    pick = max(buf, key=lambda r: pd.to_numeric(r.get(SCORE_COL), errors="coerce")
                                           if r.get(SCORE_COL) is not None else float("-inf"))
                else:
                    pick = min(buf, key=lambda r: r["_dt"])
                kept_rows.append(pick); buf.clear()
            for _, row in g.iterrows():
                if last_keep is None:
                    buf.append(row.to_dict()); flush(); last_keep = row["_dt"]
                else:
                    gap = (row["_dt"] - last_keep).days
                    if gap >= window_days:
                        flush(); buf.append(row.to_dict()); flush(); last_keep = row["_dt"]
                    else:
                        buf.append(row.to_dict())
            flush()
        kept = pd.DataFrame(kept_rows)

    # 5) 출력 정리: 날짜 컬럼 충돌 방지
    if date_col in kept.columns and "_dt" in kept.columns:
        kept.drop(columns=[date_col], inplace=True)
    kept.rename(columns={"_dt": date_col}, inplace=True)

    # 보조 norm 컬럼 제거
    kept = kept.drop(columns=[c for c in ["_comp_norm","_kw_norm","_ym"] if c in kept.columns])
    kept = kept.sort_values([COMPANY_COL, kw_col, date_col]).reset_index(drop=True)

    # 규칙 위반 후보(정보용): 같은 그룹에서 30일 미만 간격
    vio = (df.sort_values(base_sort)
             .assign(_prev=lambda x: x.groupby(["_comp_norm","_kw_norm"])["_dt"].shift(1))
             .assign(_gap=lambda x: (x["_dt"] - x["_prev"]).dt.days))
    vio = vio[vio["_gap"].notna() & (vio["_gap"] < 30)]
    if not vio.empty:
        vio = vio[[COMPANY_COL, kw_col, "_dt", "_prev", "_gap"] + [c for c in [TITLE_COL, URL_COL] if c in df.columns]]

    kept.to_excel(output_xlsx_path, index=False)
    return kept, output_xlsx_path, vio

