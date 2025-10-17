# app.py
import os
import tempfile
from pathlib import Path

import streamlit as st
import pandas as pd

# 크롤러/스코어러 모듈
from scorer import score_esg, OUTPUT_SHEET_NAME
from crawl import NewsCrawlerApp
from dedup import deduplicate_news  # (회사명, 뉴스 키워드 후보)×30일 규칙

st.set_page_config(page_title="Naver ESG News Pipeline", layout="wide")
st.title("📰 Naver ESG News Pipeline (Crawler + Scorer)")
st.caption("엑셀 입력 → 네이버 뉴스 크롤링 → (저장) → [버튼] 중복 제거 → ESG 스코어 산정")

# --- 좌측: 설정 ---
with st.sidebar:
    st.header("🔑 API 설정")
    use_env = st.toggle("`.env` 사용 (NAVER_CLIENT_ID/SECRET)", value=True)
    client_id = st.text_input("NAVER_CLIENT_ID", value="" if use_env else os.getenv("NAVER_CLIENT_ID", ""))
    client_secret = st.text_input("NAVER_CLIENT_SECRET", value="" if use_env else os.getenv("NAVER_CLIENT_SECRET", ""), type="password")
    st.info("`.env`를 사용할 경우 sidebar의 입력은 무시됩니다.", icon="ℹ️")

    st.header("⚙️ 스코어 옵션")
    threshold = st.slider("부정 임계치", 0.0, 1.0, 0.5, 0.05)
    text_col_override = st.text_input("기사 텍스트 컬럼명(선택)", help="미지정 시 자동 탐색합니다.")

# --- 탭 ---
tab1, tab2 = st.tabs(["① 크롤링/저장", "② 중복 제거 ▶ 스코어링"])

# 상태
if "raw_outfile" not in st.session_state:
    st.session_state.raw_outfile = None  # 크롤 원본 파일
if "crawl_outfile" not in st.session_state:
    st.session_state.crawl_outfile = None  # dedup 결과 파일
if "scored_outfile" not in st.session_state:
    st.session_state.scored_outfile = None

# ① 크롤링/저장
with tab1:
    st.subheader("엑셀 업로드 (Company/ESG 시트 포함)")
    uploaded = st.file_uploader("input.xlsx 업로드", type=["xlsx"], accept_multiple_files=False)
    out_dir = st.text_input("출력 디렉토리", value="./output")

    c1, c2 = st.columns(2)
    with c1:
        run_btn = st.button("🚀 크롤링 실행 (원본 저장)", use_container_width=True, type="primary")
    with c2:
        st.write(" ")

    if run_btn:
        if not uploaded:
            st.error("input.xlsx를 업로드해 주세요.")
        else:
            # 임시 저장
            tmp_dir = tempfile.mkdtemp(prefix="esg_crawl_")
            input_path = Path(tmp_dir) / "input.xlsx"
            with open(input_path, "wb") as f:
                f.write(uploaded.read())

            # .env 미사용 시 환경변수 주입
            if not use_env:
                os.environ["NAVER_CLIENT_ID"] = client_id.strip()
                os.environ["NAVER_CLIENT_SECRET"] = client_secret.strip()

            st.info("크롤링 시작…")
            try:
                app = NewsCrawlerApp(str(input_path), output_dir=out_dir.strip() or "./output")
                app.run()  # ★ 파일 먼저 저장

                # 최신 원본 결과
                out_dir_path = Path(out_dir)
                latest = max(out_dir_path.glob("news_output_*.xlsx"), key=lambda p: p.stat().st_mtime)
                st.session_state.raw_outfile = str(latest)  # ✅ 원본만 기록
                st.session_state.crawl_outfile = None       # dedup 아직 안 함

                st.success(f"크롤링 완료 (원본 저장됨): {latest.name}")
                with open(latest, "rb") as f:
                    st.download_button("⬇️ 원본 결과 다운로드", f, file_name=latest.name,
                                       mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

                # 원본 미리보기
                df_preview = pd.read_excel(latest, sheet_name=OUTPUT_SHEET_NAME).head(50)
                st.dataframe(df_preview, use_container_width=True, height=400)

            except Exception as e:
                st.error(f"크롤링 중 오류: {e}")

# ② 중복 제거 ▶ 스코어링
with tab2:
    st.subheader("🧹 저장된 파일 기반 중복 제거")
    if not st.session_state.raw_outfile:
        st.info("먼저 ① 탭에서 크롤링을 실행해 원본 파일을 생성하세요.")
    else:
        st.caption(f"원본 파일: {Path(st.session_state.raw_outfile).name}")
        dedup_btn = st.button("중복 제거 실행", type="primary", use_container_width=True)

        if dedup_btn:
            try:
                raw_path = Path(st.session_state.raw_outfile)
                dedup_path = raw_path.with_name(f"{raw_path.stem}_dedup.xlsx")

                filtered_df, saved_path, vio = deduplicate_news(
                    input_xlsx_path=str(raw_path),
                    output_xlsx_path=str(dedup_path),
                    sheet_name=OUTPUT_SHEET_NAME,
                    mode="rolling30",          # 30일 롤링 창 내 1건 유지
                    pick_strategy="earliest",  # 같은 창에서 가장 이른 기사 선택
                )

                st.session_state.crawl_outfile = saved_path  # ⬅️ 스코어링 입력으로 사용
                # 카운트 표시
                n_raw = len(pd.read_excel(raw_path, sheet_name=OUTPUT_SHEET_NAME))
                st.success(f"중복 제거 완료: {Path(saved_path).name}  (입력 {n_raw} → 결과 {len(filtered_df)})")

                # 다운로드
                with open(saved_path, "rb") as f:
                    st.download_button("⬇️ 중복 제거 후 결과 다운로드", f,
                        file_name=Path(saved_path).name,
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

                # 결과 미리보기 + 위반 후보(정보용)
                c1, c2 = st.columns(2)
                with c1:
                    st.caption("원본 미리보기")
                    st.dataframe(pd.read_excel(raw_path, sheet_name=OUTPUT_SHEET_NAME).head(30),
                                 use_container_width=True, height=300)
                with c2:
                    st.caption("Dedup 결과 미리보기")
                    st.dataframe(filtered_df.head(30), use_container_width=True, height=300)

                if not vio.empty:
                    st.warning(f"30일 간격 위반 후보 {len(vio)}건 (정보용)")
                    st.dataframe(vio.head(50), use_container_width=True, height=260)

            except Exception as e:
                st.error(f"중복 제거 중 오류: {e}")

    st.divider()
    st.subheader("🧮 스코어링")
    st.markdown("- 위의 **중복 제거 결과 파일**을 기본 입력으로 사용하거나, 직접 업로드할 수 있습니다.")

    col1, col2 = st.columns(2)
    with col1:
        use_crawl_output = st.toggle("중복 제거 결과 사용", value=bool(st.session_state.crawl_outfile))
        if use_crawl_output and st.session_state.crawl_outfile:
            st.success(f"선택됨: {Path(st.session_state.crawl_outfile).name}")
    with col2:
        custom_dedup = st.file_uploader("직접 업로드 (대신 사용)", type=["xlsx"], accept_multiple_files=False)

    esg_file = st.file_uploader("ESG 키워드 엑셀 (시트명 'ESG')", type=["xlsx"], accept_multiple_files=False, key="esg")

    run_score = st.button("스코어링 실행", type="primary", use_container_width=True)

    if run_score:
        if custom_dedup is None and not (use_crawl_output and st.session_state.crawl_outfile):
            st.error("중복 제거 결과를 선택하거나, 직접 업로드해 주세요.")
        elif esg_file is None:
            st.error("ESG 키워드 엑셀을 업로드해 주세요.")
        else:
            tmp_dir = tempfile.mkdtemp(prefix="esg_score_")

            # dedup(=크롤링 결과) 파일 경로
            if custom_dedup:
                dedup_path = Path(tmp_dir) / "dedup.xlsx"
                with open(dedup_path, "wb") as f:
                    f.write(custom_dedup.read())
            else:
                dedup_path = Path(st.session_state.crawl_outfile)

            # ESG 파일 경로
            esg_path = Path(tmp_dir) / "esg.xlsx"
            with open(esg_path, "wb") as f:
                f.write(esg_file.read())

            st.info("임베딩 및 스코어 계산 중… (CPU 기준)")
            try:
                result_df, saved_path = score_esg(
                    dedup_xlsx_path=str(dedup_path),
                    esg_xlsx_path=str(esg_path),
                    text_col=text_col_override.strip() or None,
                    threshold=threshold,
                    device="cpu",
                )
                st.session_state.scored_outfile = saved_path
                st.success(f"스코어링 완료: {Path(saved_path).name}")

                with open(saved_path, "rb") as f:
                    st.download_button(
                        "⬇️ 스코어 결과 다운로드",
                        f,
                        file_name=Path(saved_path).name,
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    )

                st.dataframe(result_df.head(100), use_container_width=True, height=500)

            except Exception as e:
                st.error(f"스코어링 오류: {e}")
