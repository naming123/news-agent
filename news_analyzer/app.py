# news_analyzer/app.py
from __future__ import annotations
import datetime as dt
import os
import sys
import platform
import subprocess
from io import BytesIO
from pathlib import Path
from datetime import datetime
from typing import Dict, Tuple, Optional, List

import pandas as pd
import matplotlib.pyplot as plt
import plotly.express as px
import streamlit as st
from wordcloud import WordCloud
from datetime import datetime
from zoneinfo import ZoneInfo  # Python 3.9+
def now_kst(fmt="%Y-%m-%d %H:%M:%S"):
    return datetime.now(ZoneInfo("Asia/Seoul")).strftime(fmt)

# =========================
# Infra / Utilities
# =========================
def get_base_dir() -> Path:
    try:
        return Path(__file__).parent
    except NameError:
        return Path.cwd()


def get_korean_font() -> Optional[str]:
    system = platform.system()
    candidates: List[str] = []
    if system == "Windows":
        candidates = [
            r"C:\Windows\Fonts\malgun.ttf",
            r"C:\Windows\Fonts\malgunbd.ttf",
        ]
    elif system == "Darwin":
        candidates = [
            "/System/Library/Fonts/AppleGothic.ttf",
            "/System/Library/Fonts/Supplemental/AppleGothic.ttf",
        ]
    else:  # Linux
        candidates = [
            "/usr/share/fonts/truetype/nanum/NanumGothic.ttf",
            "/usr/share/fonts/truetype/nanum/NanumGothicCoding.ttf",
        ]
    for p in candidates:
        if os.path.exists(p):
            return p
    return None


# =========================
# Data / Crawler Layer
# =========================
class DataManager:
    def __init__(self, base_dir: Path):
        self.base_dir = base_dir
        self.input_dir = (self.base_dir / "input")
        self.input_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    @st.cache_data
    def _load_excel_cached(file_path: str) -> Dict[str, pd.DataFrame]:
        excel_file = pd.ExcelFile(file_path)
        sheets: Dict[str, pd.DataFrame] = {}
        for sheet_name in excel_file.sheet_names:
            df = pd.read_excel(file_path, sheet_name=sheet_name)
            sheets[sheet_name] = df
        return sheets

    def load_excel(self, file_path: Path) -> Optional[Dict[str, pd.DataFrame]]:
        try:
            return self._load_excel_cached(str(file_path))
        except Exception as e:
            st.error(f"파일 로드 중 오류: {e}")
            return None

    def clear_cache(self):
        self._load_excel_cached.clear()

    def available_excels(self) -> List[Path]:
        files = list(self.input_dir.glob("*.xlsx")) + list(self.input_dir.glob("*.xls"))
        return sorted(files, key=lambda x: x.stat().st_mtime, reverse=True)

    # app.py 내부 DataManager 클래스의 run_crawler 교체

    def run_crawler(
        self,
        input: Path,
        *,
        companies: list[str] | None = None,
        keywords: list[str] | None = None,
        start: str | None = None,
        end: str | None = None,
        output_sheet: str | None = None,
        extra_args: list[str] | None = None,
    ) -> tuple[bool, str]:
        
        try:
            # 실행 기준 디렉토리: news_analyzer/src (없으면 news_analyzer)
            crawler_cwd = self.base_dir / "src"
            
            if not crawler_cwd.exists():
                crawler_cwd = self.base_dir

            # 크롤러 기준의 상대경로 계산 (실패 시 절대경로 fallback)
            
            try:
                
                rel_path = input.resolve().relative_to(crawler_cwd.parent.resolve())
            except Exception:
                
                rel_path = input.resolve()
            # breakpoint()
            # python -m news_collector.ioHandle.batch_crawler <상대(or 절대)경로>
            cmd = [sys.executable, "-m", "news_collector.ioHandle.batch_crawler", "--input", str(rel_path)]
            
            # 옵션들
    
            if companies is not None: cmd += ["--companies", ",".join(companies)]
            if keywords  is not None: cmd += ["--keywords",  ",".join(keywords)]

            if start:
                cmd += ["--start", start]
            if end:
                cmd += ["--end", end]
            if output_sheet:
                cmd += ["--output-sheet", output_sheet]

            # 항상 인플레이스 저장
            cmd += ["--inplace"]
            
            if extra_args:
                cmd += extra_args
            # breakpoint()
            completed = subprocess.run(
                cmd,
                cwd=str(crawler_cwd),             # ← 여기서 상대경로가 유효해짐
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                check=False,
            )
            
            ok = (completed.returncode == 0)
            msg = (completed.stdout or "") + ("\n" + (completed.stderr or ""))
            return ok, msg.strip()
        except Exception as e:
            return False, f"크롤러 실행 중 예외: {e}"





# =========================
# App (UI) Layer
# =========================
class ESGNewsApp:
    def __init__(self):
        st.set_page_config(page_title="ESG 뉴스 분석기", layout="wide")

        self.base_dir = get_base_dir()           # news_analyzer/
        self.dm = DataManager(self.base_dir)     # news_analyzer/input

        self.font_path = get_korean_font()

        # state
        self.selected_file: Optional[Path] = None
        self.sheets: Optional[Dict[str, pd.DataFrame]] = None
        self.df: Optional[pd.DataFrame] = None
        self.save_filename: str = f"ESG_분석_{datetime.now().strftime('%Y%m%d')}"

    # ---------- Sidebar ----------
    def render_sidebar(self):
        with st.sidebar:
            st.header("📂 데이터 파일 선택")
            excel_files = self.dm.available_excels()
            if not excel_files:
                st.error("❌ input 폴더가 비어있습니다!")
                st.info(f"📍 폴더 경로:\n{self.dm.input_dir.absolute()}")

                with st.expander("💡 파일 추가 방법", expanded=True):
                    st.markdown("엑셀 파일을 아래 경로에 넣어주세요:")
                    st.code(str(self.dm.input_dir.absolute()))
                    st.markdown("또는 크롤링으로 생성:")
                    st.code(
                        "cd news_analyzer/src\n"
                        "python -m news_collector.ioHandle.batch_crawler ../input/input.xlsx"
                    )
                st.stop()

            file_names = [f.name for f in excel_files]
            selected_name = st.selectbox(
                "엑셀 파일 선택", file_names, help="최신 파일이 맨 위에 표시됩니다"
            )
            self.selected_file = self.dm.input_dir / selected_name

            # file info
            stat = self.selected_file.stat()
            st.info(
                f"📊 파일 정보\n"
                f"크기: {stat.st_size/1024:.1f} KB\n"
                f"수정일: {datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M')}"
            )

            st.markdown("---")
            st.subheader("🕷️ 크롤링 옵션")

            # 회사 / 키워드
            company_str = st.text_input(
                "회사(쉼표로 구분)",
                value="",
                placeholder="삼성전자, LG에너지솔루션",
                key="opt_companies"
            )
            kw_str = st.text_input(
                "키워드(쉼표로 구분)",
                value="",
                placeholder="ESG, 탄소중립",
                key="opt_keywords"
            )

            # 기간 (시작/마감 분리)
            MAX_RANGE_DAYS = 365 * 5 # 권장 최대 범위(일)
            c1, c2 = st.columns(2)
            with c1:
                start_date = st.date_input(
                    "시작일",
                    value=dt.date(2010, 1, 1),
                    min_value=dt.date(1990, 1, 1),   # ← 여기 지정해야 2015년 이전 가능
                    max_value=dt.date.today(),
                    key="opt_start_date"
                )
            with c2:
                end_date = st.date_input(
                    "마감일",
                    value=dt.date.today(),
                    min_value=dt.date(1990, 1, 1),   # ← 동일하게 지정
                    max_value=dt.date.today(),
                    key="opt_end_date"
                )

            out_sheet = st.text_input(
                "출력 시트명",
                value="output",
                help="크롤러가 쓸 시트명 (기본: output)",
                key="opt_output_sheet"
            )


            # 파라미터 가공
            companies = [s.strip() for s in company_str.split(",") if s.strip()] or None
            keywords  = [s.strip() for s in kw_str.split(",") if s.strip()] or None
            start = start_date.strftime("%Y-%m-%d") if start_date else None
            end   = end_date.strftime("%Y-%m-%d")   if end_date   else None

            # 유효성 검사
            invalid = False
            if start and end and start > end:
                st.error("시작일이 마감일보다 늦습니다. 날짜를 확인해주세요.")
                invalid = True
            if start and end and MAX_RANGE_DAYS:
                from datetime import datetime as _dt
                try:
                    days = (_dt.strptime(end, "%Y-%m-%d") - _dt.strptime(start, "%Y-%m-%d")).days
                    if days > MAX_RANGE_DAYS:
                        st.warning(f"기간이 {days}일입니다. 권장 최대 {MAX_RANGE_DAYS}일을 초과했어요.")
                except Exception:
                    pass
            # 실행 대상 파일 = 사이드바에서 고른 파일(없으면 input.xlsx)
            target_path = self.selected_file or (self.dm.input_dir / "input.xlsx")

            # 크롤러 기준 상대경로 미리 표시 (사용자 안내용)
            crawler_cwd = (self.dm.base_dir / "src") if (self.dm.base_dir / "src").exists() else self.dm.base_dir
            try:
                rel_for_user = target_path.resolve().relative_to(crawler_cwd.parent.resolve())
            except Exception:
                rel_for_user = target_path.resolve()

            st.info(
                "🗂️ **크롤링 결과 저장 위치(인플레이스):**\n\n"
                f"- 파일: `{rel_for_user}`\n"
                f"- 시트: `{out_sheet or 'output'}`\n\n"
                "※ 실행하면 위 파일의 해당 시트가 **덮어쓰기** 됩니다."
            )

            st.markdown("---")
            st.subheader("크롤링 실행")
            
            if st.button("🚀 실행 (입력값으로 크롤링)", use_container_width=True, type="primary") and not invalid:
                with st.spinner("크롤링 중..."):
                    ok, log = self.dm.run_crawler(

                        input=target_path,                       # ← 선택 파일을 실행 대상으로
                        companies=companies,
                        keywords=keywords,
                        start=start,
                        end=end,
                        output_sheet=out_sheet or None,
                    )
                
                if ok:
                    st.success(f"✅ 크롤링 완료! `{out_sheet or 'output'}` 시트가 갱신되었습니다.")
                    self.dm.clear_cache()
                    import time as _t; _t.sleep(0.25)      # 윈도우 파일락 회피용 아주 짧은 지연
                    st.rerun()
                else:
                    st.error("❌ 크롤링 실패")
                    with st.expander("로그 보기"):
                        st.code(log or "(로그 없음)")


    # ---------- Data ----------
    def load_data(self):
        assert self.selected_file is not None
        sheets = self.dm.load_excel(self.selected_file)
        if not sheets:
            st.error("❌ 파일을 로드할 수 없습니다.")
            st.stop()
        self.sheets = sheets
        st.success(f"✅ 로드 완료! 시트: {len(sheets)}개")

    # ---------- Header + Save Name ----------
    def render_header_and_save_name(self):
        st.title("🔍 ESG 뉴스 분석기")
        st.markdown("---")
        st.header("💾 저장 설정")
        self.save_filename = st.text_input(
            "저장 파일명",
            value=self.save_filename,
            help="파일명만 입력 (확장자 제외)",
        )
        st.markdown("---")

    # ---------- Sheet Select ----------
    def render_sheet_select(self):
        assert self.sheets is not None
        st.header("📋 데이터 선택")
        col1, col2, col3 = st.columns([2, 1, 1])

        with col1:
            names = list(self.sheets.keys())
            default_idx = names.index("output") if "output" in names else 0
            selected_sheet = st.selectbox(
                "시트 선택", names, index=default_idx,
                help="분석할 시트를 선택하세요 (output 시트 권장)"
            )
            self.df = self.sheets[selected_sheet].copy()

        # --- 새 스키마 → 표준 컬럼명 매핑 ---
        # 새 스키마 열: 뉴스 보도날짜(YYYYMMDD), 기사제목, 기사 URL, 뉴스 키워드 후보, 회사명, 언론사, esg, Theme (주제) ...
        colmap = {
            "뉴스 보도날짜(YYYYMMDD)": "날짜",
            "기사제목": "제목",
            "기사 URL": "링크",
            "뉴스 키워드 후보": "키워드",
            "회사명": "회사",
            # "언론사"는 동일
        }
        for old, new in colmap.items():
            if old in self.df.columns and new not in self.df.columns:
                self.df[new] = self.df[old]

        # 날짜 파싱 (YYYYMMDD 우선, 안 되면 자동 파싱)
        if "날짜" in self.df.columns:
            s = self.df["날짜"].astype(str)
            # 우선 YYYYMMDD 시도
            parsed = pd.to_datetime(s, format="%Y%m%d", errors="coerce")
            # 실패분 자동 파싱 보강
            if parsed.isna().any():
                fallback = pd.to_datetime(s[parsed.isna()], errors="coerce")
                parsed.loc[parsed.isna()] = fallback
            self.df["날짜"] = parsed

            # 파생열
            self.df["연도"] = self.df["날짜"].dt.year
            self.df["년월"] = self.df["날짜"].dt.to_period("M").astype(str)

        # ESG 정규화 (E/S/G/F만 허용)
        if "esg" in self.df.columns:
            def _norm_esg(x):
                s = (str(x) if pd.notna(x) else "").strip().upper()
                return s if s in {"E", "S", "G", "F"} else ""
            self.df["esg"] = self.df["esg"].map(_norm_esg)

        with col2:
            st.metric("총 기사 수", f"{len(self.df):,}개")

        with col3:
            st.metric("컬럼 수", f"{len(self.df.columns)}개")


    # ---------- Filters ----------
    def render_filters(self):
        assert self.df is not None
        st.subheader("🔍 필터 설정")
        c1, c2, c3, c4 = st.columns(4)

        # 1) 날짜 범위
        with c1:
            if "날짜" in self.df.columns and self.df["날짜"].notna().any():
                mind = self.df["날짜"].min().date()
                maxd = self.df["날짜"].max().date()
                dr = st.date_input("날짜 범위", value=(mind, maxd), min_value=mind, max_value=maxd)
                if isinstance(dr, tuple) and len(dr) == 2:
                    self.df = self.df[
                        (self.df["날짜"].dt.date >= dr[0]) & (self.df["날짜"].dt.date <= dr[1])
                    ]

        # 2) ESG (E/S/G/F)
        with c2:
            if "esg" in self.df.columns:
                esg_vals = [x for x in self.df["esg"].dropna().unique() if x]
                esg_sel = st.multiselect("ESG 대분류", esg_vals, default=esg_vals)
                if esg_sel:
                    self.df = self.df[self.df["esg"].isin(esg_sel)]

        # 3) Theme (주제)
        with c3:
            col = "Theme (주제)"
            if col in self.df.columns:
                opts = self.df[col].dropna().astype(str).unique().tolist()
                default = opts if len(opts) <= 12 else opts[:12]
                theme_sel = st.multiselect("Theme(주제)", opts, default=default)
                if theme_sel:
                    self.df = self.df[self.df[col].astype(str).isin(theme_sel)]

        # 4) 회사명
        with c4:
            if "회사" in self.df.columns:  # ← 표준명(회사)로 필터
                comps = self.df["회사"].dropna().astype(str).unique().tolist()
                default = comps if len(comps) <= 12 else comps[:12]
                comp_sel = st.multiselect("회사명", comps, default=default)
                if comp_sel:
                    self.df = self.df[self.df["회사"].astype(str).isin(comp_sel)]

        st.info(f"🔎 필터링 결과: {len(self.df):,}개 기사")



    # ---------- Preview ----------
    def render_preview(self):
        assert self.df is not None
        st.subheader("📋 기사 목록")
        n = st.slider("표시할 행 수", 10, 200, 50)
        with st.expander("📊 데이터 미리보기", expanded=True):
            st.dataframe(self.df.head(n), use_container_width=True, height=350)

    # ---------- Visualizations ----------
    def render_viz(self):
        assert self.df is not None
        st.markdown("---")
        st.header("📊 시각화")
        viz_opts = st.multiselect(
            "시각화 선택 (다중 선택 가능)",
            ["📅 년도별 추이", "🔑 키워드별 분포", "📆 월별 추이", "📰 언론사별 분포", "☁️ 워드클라우드"],
            # default=["📅 년도별 추이", "☁️ 워드클라우드"],
            default=["📅 년도별 추이", "☁️ 워드클라우드"],
        )

        # 년도별
        if "📅 년도별 추이" in viz_opts and "날짜" in self.df.columns and self.df["날짜"].notna().any():
            st.markdown("### 📅 년도별 기사 추이")
            d = self.df.copy()
            d["연도"] = d["날짜"].dt.year
            yearly = d.groupby("연도").size().reset_index(name="기사수")
            fig = px.bar(
                yearly, x="연도", y="기사수", text="기사수",
                color="기사수", color_continuous_scale="Blues",
                title="년도별 기사 추이",
            )
            fig.update_traces(textposition="outside")
            fig.update_layout(height=400, showlegend=False)
            st.plotly_chart(fig, use_container_width=True)

        # 키워드별
        if "🔑 키워드별 분포" in viz_opts and "키워드" in self.df.columns and not self.df["키워드"].dropna().empty:
            st.markdown("### 🔑 키워드별 기사 분포")
            kc = self.df["키워드"].value_counts().reset_index()
            kc.columns = ["키워드", "기사수"]
            fig = px.pie(kc, values="기사수", names="키워드", title="키워드별 비율", hole=0.4)
            fig.update_traces(textposition="inside", textinfo="percent+label")
            fig.update_layout(height=400)
            st.plotly_chart(fig, use_container_width=True)

        # 월별
        if "📆 월별 추이" in viz_opts and "날짜" in self.df.columns and self.df["날짜"].notna().any():
            st.markdown("### 📆 월별 기사 추이")
            d = self.df.copy()
            d["년월"] = d["날짜"].dt.to_period("M").astype(str)
            monthly = d.groupby("년월").size().reset_index(name="기사수")
            fig = px.line(monthly, x="년월", y="기사수", markers=True, title="월별 기사 추이")
            fig.update_traces(line_color="#1f77b4", line_width=3)
            fig.update_layout(height=400)
            st.plotly_chart(fig, use_container_width=True)

        # 언론사별
        if "📰 언론사별 분포" in viz_opts and "언론사" in self.df.columns and not self.df["언론사"].dropna().empty:
            st.markdown("### 📰 언론사별 기사 분포")
            top_n = st.slider("표시할 언론사 수", 5, 50, 15, key="source_top_n")
            sc = self.df["언론사"].value_counts().head(top_n).reset_index()
            sc.columns = ["언론사", "기사수"]
            sc = sc.sort_values("기사수", ascending=True)
            fig = px.bar(
                sc, x="기사수", y="언론사", orientation="h", text="기사수",
                color="기사수", color_continuous_scale="Greens",
                title=f"언론사별 기사 수 (상위 {top_n}개)",
            )
            fig.update_traces(textposition="outside")
            fig.update_layout(height=max(400, top_n * 25), showlegend=False)
            st.plotly_chart(fig, use_container_width=True)

        # 워드클라우드
        if "☁️ 워드클라우드" in viz_opts and "제목" in self.df.columns:
            st.markdown("### ☁️ 제목 워드클라우드")
            try:
                text = " ".join(self.df["제목"].dropna().astype(str))
                if text.strip():
                    ctrl, _ = st.columns([1, 3])
                    with ctrl:
                        max_words = st.slider("최대 단어 수", 50, 300, 150, key="wc_max_words")
                        colormap = st.selectbox(
                            "색상 테마",
                            ["viridis", "plasma", "inferno", "magma", "cividis", "Spectral", "coolwarm"],
                            index=0
                        )
                    wc = WordCloud(
                        font_path=self.font_path,
                        width=1200, height=600,
                        background_color="white",
                        colormap=colormap,
                        max_words=max_words,
                        relative_scaling=0.5,
                        min_font_size=10,
                    ).generate(text)
                    fig, ax = plt.subplots(figsize=(15, 7))
                    ax.imshow(wc, interpolation="bilinear")
                    ax.axis("off")
                    ax.set_title("기사 제목 워드클라우드", fontsize=20, pad=20)
                    st.pyplot(fig)
                    plt.close()
                else:
                    st.warning("⚠️ 워드클라우드 생성할 텍스트가 없습니다.")
            except Exception as e:
                st.error(f"❌ 워드클라우드 생성 실패: {e}")

    # ---------- Stats ----------
    def render_stats(self):
        assert self.df is not None
        st.markdown("---")
        st.header("📈 통계 요약")
        c1, c2, c3, c4 = st.columns(4)

        with c1:
            st.metric("총 기사 수", f"{len(self.df):,}개")

        with c2:
            if "날짜" in self.df.columns and self.df["날짜"].notna().any():
                days = (self.df["날짜"].max() - self.df["날짜"].min()).days
                st.metric("기간", f"{days}일")
            else:
                st.metric("기간", "-")

        with c3:
            if "날짜" in self.df.columns and self.df["날짜"].notna().any():
                days = (self.df["날짜"].max() - self.df["날짜"].min()).days
                avg_per_day = len(self.df) / max(days, 1)
                st.metric("일평균 기사", f"{avg_per_day:.1f}개")
            else:
                st.metric("일평균 기사", "-")

        with c4:
            if "언론사" in self.df.columns:
                st.metric("언론사 수", f"{self.df['언론사'].nunique()}개")
            else:
                st.metric("언론사 수", "-")

    # ---------- Save ----------
    def render_save(self):
        assert self.df is not None
        st.markdown("---")
        st.header("💾 결과 저장")
        c1, c2 = st.columns(2)

        # 메모리 버퍼
        output = BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            self.df.to_excel(writer, index=False, sheet_name="필터링결과")
        excel_data = output.getvalue()
        csv_data = self.df.to_csv(index=False, encoding="utf-8-sig")

        with c1:
            st.subheader("📥 브라우저 다운로드")
            dl1, dl2 = st.columns(2)
            with dl1:
                st.download_button(
                    label="📥 Excel 다운로드",
                    data=excel_data,
                    file_name=f"{self.save_filename}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True,
                )
            with dl2:
                st.download_button(
                    label="📥 CSV 다운로드",
                    data=csv_data,
                    file_name=f"{self.save_filename}.csv",
                    mime="text/csv",
                    use_container_width=True,
                )

        with c2:
            st.subheader("💾 input 폴더에 저장")
            if st.button("📂 input 폴더에 저장하기", use_container_width=True, type="primary"):
                try:
                    excel_path = self.dm.input_dir / f"{self.save_filename}.xlsx"
                    with pd.ExcelWriter(excel_path, engine="openpyxl") as writer:
                        self.df.to_excel(writer, index=False, sheet_name="필터링결과")

                    csv_path = self.dm.input_dir / f"{self.save_filename}.csv"
                    self.df.to_csv(csv_path, index=False, encoding="utf-8-sig")

                    st.success(
                        "✅ 저장 완료!\n\n"
                        f"📁 저장 위치:\n"
                        f"Excel: {excel_path.name}\n"
                        f"CSV: {csv_path.name}\n\n"
                        f"💡 경로: {self.dm.input_dir.absolute()}"
                    )
                except Exception as e:
                    st.error(f"❌ 저장 실패: {e}")

        st.caption(f"📂 현재 작업 폴더: {self.dm.input_dir.absolute()}")

    # ---------- Orchestration ----------
    def run(self):
        self.render_sidebar()
        self.render_header_and_save_name()
        self.load_data()
        self.render_sheet_select()
        self.render_filters()
        self.render_preview()
        self.render_viz()
        self.render_stats()
        self.render_save()


# =========================
# Entry
# =========================
if __name__ == "__main__":
    print("app start: "+now_kst())                 # 2025-09-30 18:27:12
    ESGNewsApp().run()

