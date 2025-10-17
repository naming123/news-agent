# scorer.py
import pandas as pd
import numpy as np
from pathlib import Path
from typing import List, Dict, Tuple

ESG_SHEET_NAME = "ESG"
OUTPUT_SHEET_NAME = "output"          # 기사가 저장된 시트
ESG_ISSUE_COL = "뉴스 키워드 후보"       # (=핵심이슈)
ESG_NEG_COL = "부정 ESG 키워드"         # 콤마로 구분된 키워드 문자열
DEFAULT_THRESHOLD = 0.5
MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"  # SBERT 다국어

TEXT_COL_CANDIDATES = ["title", "제목", "headline", "내용", "content", "본문", "요약",
                       "기사제목"]  # UI에서 크롤링 결과 컬럼명까지 포괄

def pick_text_col(df: pd.DataFrame, user_col: str | None) -> str:
    if user_col and user_col in df.columns:
        return user_col
    for c in TEXT_COL_CANDIDATES:
        if c in df.columns:
            return c
    raise ValueError(f"기사 텍스트 컬럼을 찾을 수 없습니다. 후보: {TEXT_COL_CANDIDATES} (또는 text_col로 지정)")

def load_issue_keyword_map(esg_path: str) -> Tuple[Dict[str, List[str]], Dict[str, str]]:
    """
    ESG 시트에서 이슈별 키워드 묶음 읽기.
    반환:
      - issue_to_kwlist: {이슈: [고유 키워드 리스트]}
      - issue_to_joined_original: {이슈: '원문 키워드(중복/순서 보존, 콤마)'}
    """
    esg = pd.read_excel(esg_path, sheet_name=ESG_SHEET_NAME)
    for col in (ESG_ISSUE_COL, ESG_NEG_COL):
        if col not in esg.columns:
            raise ValueError(f"ESG 시트에 '{col}' 컬럼이 없습니다.")

    issue_to_tokens_raw: Dict[str, List[str]] = {}
    for _, row in esg[[ESG_ISSUE_COL, ESG_NEG_COL]].dropna(subset=[ESG_ISSUE_COL, ESG_NEG_COL]).iterrows():
        issue = str(row[ESG_ISSUE_COL]).strip()
        tokens = [t.strip() for t in str(row[ESG_NEG_COL]).split(",") if str(t).strip()]
        if not tokens:
            continue
        issue_to_tokens_raw.setdefault(issue, []).extend(tokens)

    if not issue_to_tokens_raw:
        raise ValueError("ESG 시트에서 유효한 (이슈, 부정 ESG 키워드) 페어를 찾지 못했습니다.")

    issue_to_kwlist: Dict[str, List[str]] = {}
    issue_to_joined_original: Dict[str, str] = {}
    for issue, raw_list in issue_to_tokens_raw.items():
        issue_to_joined_original[issue] = ", ".join(raw_list)  # 보고/추적용 (중복/순서 보존)
        unique_sorted = sorted(set(raw_list))
        issue_to_kwlist[issue] = unique_sorted

    return issue_to_kwlist, issue_to_joined_original

def cosine_sim_mat(A: np.ndarray, B: np.ndarray) -> np.ndarray:
    # A: n x d (articles), B: m x d (keywords)
    A_norm = A / (np.linalg.norm(A, axis=1, keepdims=True) + 1e-12)
    B_norm = B / (np.linalg.norm(B, axis=1, keepdims=True) + 1e-12)
    return A_norm @ B_norm.T  # n x m

def score_esg(
    dedup_xlsx_path: str,
    esg_xlsx_path: str,
    text_col: str | None = None,
    threshold: float = DEFAULT_THRESHOLD,
    out_path: str | None = None,
    device: str = "cpu",
):
    """
    ESG 부정 키워드 기반 기사 부정점수 산정 (이슈 자동 선택)
    - dedup_xlsx_path: 크롤링 결과(또는 중복제거 결과) 엑셀 경로, 시트명 'output'
    - esg_xlsx_path: ESG 키워드 엑셀 경로, 시트명 'ESG'
    - text_col: 기사 텍스트 컬럼명 (없으면 자동 탐색)
    - threshold: 부정 임계치
    - out_path: 저장 경로 (없으면 *_scored.xlsx)
    - device: 'cpu' 권장
    반환: (result_df: pd.DataFrame, saved_path: str)
    """
    # 1) 기사 로드
    df_out = pd.read_excel(dedup_xlsx_path, sheet_name=OUTPUT_SHEET_NAME)
    text_col = pick_text_col(df_out, text_col)
    texts = df_out[text_col].astype(str).fillna("").tolist()

    # 2) ESG 이슈-키워드
    issue_to_kwlist, issue_to_joined_original = load_issue_keyword_map(esg_xlsx_path)
    issues = list(issue_to_kwlist.keys())

    # 3) 임베딩 모델
    from sentence_transformers import SentenceTransformer
    model = SentenceTransformer(MODEL_NAME, device=device)

    # 4) 기사/키워드 임베딩
    art_vecs = model.encode(texts, convert_to_numpy=True, batch_size=64, show_progress_bar=False)

    all_keywords = sorted(set(kw for lst in issue_to_kwlist.values() for kw in lst))
    if not all_keywords:
        raise ValueError("키워드가 비어 있습니다.")

    kw_vecs_all = model.encode(all_keywords, convert_to_numpy=True, batch_size=64, show_progress_bar=False)
    kw_to_vec: Dict[str, np.ndarray] = {k: v for k, v in zip(all_keywords, kw_vecs_all)}

    # 5) 이슈별 산정
    n = len(df_out)
    best_issue = [""] * n
    best_score = np.zeros(n, dtype=float)
    best_exceed_keywords = [""] * n
    best_issue_keywords_original = [""] * n  # 보고용

    for issue in issues:
        issue_keywords = issue_to_kwlist[issue]
        issue_kw_mat = np.stack([kw_to_vec[k] for k in issue_keywords], axis=0)  # K x d
        sim_issue = cosine_sim_mat(art_vecs, issue_kw_mat)  # n x K

        max_scores_issue = sim_issue.max(axis=1)

        exceed_keywords_issue: List[str] = []
        for i in range(n):
            idxs = np.where(sim_issue[i] > threshold)[0]
            if len(idxs):
                exceed_keywords_issue.append(", ".join([issue_keywords[j] for j in idxs]))
            else:
                exceed_keywords_issue.append("")

        better_mask = max_scores_issue > best_score
        if np.any(better_mask):
            for i in np.where(better_mask)[0]:
                best_issue[i] = issue
                best_score[i] = float(max_scores_issue[i])
                best_exceed_keywords[i] = exceed_keywords_issue[i]
                best_issue_keywords_original[i] = issue_to_joined_original[issue]

    # 6) 결과 병합
    result_df = df_out.copy()
    result_df["핵심이슈(자동)"] = best_issue
    result_df["부정 ESG 키워드"] = best_issue_keywords_original
    result_df["부정점수"] = best_score
    result_df["부정 초과 키워드"] = best_exceed_keywords
    result_df["부정 여부(>thr)"] = (best_score > threshold).astype(int)

    # 7) 저장
    out_path = out_path or str(Path(dedup_xlsx_path).with_name(Path(dedup_xlsx_path).stem + "_scored.xlsx"))
    with pd.ExcelWriter(out_path, engine="openpyxl") as w:
        result_df.to_excel(w, index=False, sheet_name=OUTPUT_SHEET_NAME)

    return result_df, out_path
