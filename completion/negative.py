import pandas as pd
import numpy as np
from pathlib import Path
from typing import List, Dict, Tuple
import argparse

# ====== 설정 ======
ESG_SHEET_NAME = "ESG"
OUTPUT_SHEET_NAME = "output"          # 기사가 저장된 시트
ESG_ISSUE_COL = "뉴스 키워드 후보"       # (=핵심이슈)
ESG_NEG_COL = "부정 ESG 키워드"         # 콤마로 구분된 키워드 문자열
TEXT_COL_CANDIDATES = ["title", "제목", "headline", "내용", "content", "본문", "요약"]
THRESHOLD = 0.5
MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"  # SBERT 다국어

def pick_text_col(df: pd.DataFrame, user_col: str | None) -> str:
    if user_col and user_col in df.columns:
        return user_col
    for c in TEXT_COL_CANDIDATES:
        if c in df.columns:
            return c
    raise ValueError(f"기사 텍스트 컬럼을 찾을 수 없습니다. 후보: {TEXT_COL_CANDIDATES} (또는 --text-col 로 지정)")

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

def main():
    parser = argparse.ArgumentParser(description="ESG 부정 키워드 기반 기사 부정점수 산정 (이슈 자동 선택)")
    parser.add_argument("--dedup", required=True, help="중복제거 기사 엑셀 경로 (output 시트 사용)")
    parser.add_argument("--esg", required=True, help="ESG 키워드 엑셀 경로 (시트 'ESG')")
    parser.add_argument("--text-col", default=None, help="기사 텍스트 컬럼명 (미지정 시 자동 탐색)")
    parser.add_argument("--threshold", type=float, default=THRESHOLD, help="부정 임계치 (기본 0.5)")
    parser.add_argument("--out", default=None, help="출력 파일 경로(미지정 시 dedup 파일명에 _scored 부여)")
    args = parser.parse_args()

    # 1) 기사 로드 (output 시트)
    df_out = pd.read_excel(args.dedup, sheet_name=OUTPUT_SHEET_NAME)
    text_col = pick_text_col(df_out, args.text_col)
    texts = df_out[text_col].astype(str).fillna("").tolist()

    # 2) ESG 이슈-키워드 매핑 로드 (이슈 자동)
    issue_to_kwlist, issue_to_joined_original = load_issue_keyword_map(args.esg)
    issues = list(issue_to_kwlist.keys())

    # 3) 임베딩 모델
    from sentence_transformers import SentenceTransformer
    model = SentenceTransformer(MODEL_NAME, device="cpu")

    # 4) 기사/키워드 임베딩
    print(f"임베딩 계산 중... (기사 {len(texts)}건, 이슈 {len(issues)}개)")
    art_vecs = model.encode(texts, convert_to_numpy=True, batch_size=64, show_progress_bar=True)

    # 키워드 전체 집합을 한 번에 임베딩하여 캐시
    all_keywords = sorted(set(kw for lst in issue_to_kwlist.values() for kw in lst))
    kw_to_vec: Dict[str, np.ndarray] = {}
    if all_keywords:
        kw_vecs_all = model.encode(all_keywords, convert_to_numpy=True, batch_size=64, show_progress_bar=True)
        for k, v in zip(all_keywords, kw_vecs_all):
            kw_to_vec[k] = v
    else:
        raise ValueError("키워드가 비어 있습니다.")

    # 5) 이슈별 유사도(기사 x 키워드)에서 기사별 최대점수/초과키워드 계산
    n = len(df_out)
    best_issue = [""] * n
    best_score = np.zeros(n, dtype=float)
    best_exceed_keywords = [""] * n
    best_issue_keywords_original = [""] * n  # 보고용: 해당 이슈의 원문 키워드 문자열

    for issue in issues:
        issue_keywords = issue_to_kwlist[issue]
        # 이슈에 해당하는 키워드 벡터들
        K = len(issue_keywords)
        mat = np.zeros((n, K), dtype=float)
        # 키워드 행렬 구성
        issue_kw_mat = np.stack([kw_to_vec[k] for k in issue_keywords], axis=0)  # K x d
        # 기사 x 키워드 유사도
        sim_issue = cosine_sim_mat(art_vecs, issue_kw_mat)  # n x K

        # 기사별 최대 점수
        max_scores_issue = sim_issue.max(axis=1)

        # 임계 초과 키워드 문자열 만들기
        exceed_keywords_issue: List[str] = []
        for i in range(n):
            idxs = np.where(sim_issue[i] > args.threshold)[0]
            if len(idxs):
                exceed_keywords_issue.append(", ".join([issue_keywords[j] for j in idxs]))
            else:
                exceed_keywords_issue.append("")

        # 현재 이슈가 기존 best보다 좋은 곳 갱신
        better_mask = max_scores_issue > best_score
        if np.any(better_mask):
            # 갱신
            for i in np.where(better_mask)[0]:
                best_issue[i] = issue
                best_score[i] = float(max_scores_issue[i])
                best_exceed_keywords[i] = exceed_keywords_issue[i]
                best_issue_keywords_original[i] = issue_to_joined_original[issue]

    # 6) 결과 덧붙이기 (output 시트 형식 유지)
    result_df = df_out.copy()
    result_df["핵심이슈(자동)"] = best_issue
    result_df["부정 ESG 키워드"] = best_issue_keywords_original            # 해당 이슈의 원문 키워드(중복/순서 보존)
    result_df["부정점수"] = best_score                                     # 해당 이슈 내 키워드와의 최대값
    result_df["부정 초과 키워드"] = best_exceed_keywords                   # 임계치 초과 키워드(해당 이슈 한정)
    result_df["부정 여부(>thr)"] = (best_score > args.threshold).astype(int)

    # 7) 저장
    out_path = args.out or str(Path(args.dedup).with_name(Path(args.dedup).stem + "_scored.xlsx"))
    # output 시트만 저장(원본 형식 유지)
    with pd.ExcelWriter(out_path, engine="openpyxl") as w:
        result_df.to_excel(w, index=False, sheet_name=OUTPUT_SHEET_NAME)

    print(f"✓ 저장 완료: {out_path}")
    print(f"임계치 {args.threshold} 초과 기사 수: {(best_score > args.threshold).sum()} / {len(result_df)}")

if __name__ == "__main__":
    main()
