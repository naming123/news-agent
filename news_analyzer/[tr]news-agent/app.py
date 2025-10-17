# app.py
import streamlit as st
import pandas as pd
from pathlib import Path
import datetime as dt
import os
import sys

from batch_crawler import BatchCrawler
from utils.excel_handler import ExcelOutputHandler

class NewsAgentApp:
    """뉴스 에이전트 UI 컨트롤러"""
    
    def __init__(self):
        self.crawler = BatchCrawler()
        self.excel_handler = ExcelOutputHandler()
        self.setup_directories()
        
    def setup_directories(self):
        """필요한 디렉토리 생성"""
        self.output_dir = Path("outputs")
        self.output_dir.mkdir(exist_ok=True)
        
    def run(self):
        st.set_page_config(page_title="News Agent", layout="wide")
        
        # 사이드바 입력
        with st.sidebar:
            st.header("🔍 검색 설정")
            
            keyword = st.text_input("키워드", value="AI")
            
            # 날짜 입력 - 1990년부터 가능하도록 수정
            c1, c2 = st.columns(2)
            with c1:
                start_date = st.date_input(
                    "시작일",
                    value=dt.date(2010, 1, 1),
                    min_value=dt.date(1990, 1, 1),   # 1990년부터 가능
                    max_value=dt.date.today(),
                    key="opt_start_date"
                )
            with c2:
                end_date = st.date_input(
                    "마감일",
                    value=dt.date.today(),
                    min_value=dt.date(1990, 1, 1),   # 1990년부터 가능
                    max_value=dt.date.today(),
                    key="opt_end_date"
                )
            
            # 날짜 유효성 검증
            if start_date > end_date:
                st.error("❌ 시작일이 종료일보다 늦을 수 없습니다")
            else:
                st.success(f"✅ 검색 기간: {start_date.strftime('%Y.%m.%d')} ~ {end_date.strftime('%Y.%m.%d')}")
            
            st.info("📌 검색 결과 끝까지 모든 기사를 수집합니다")
            
            # 파일명 설정
            default_name = f"news_{keyword}_{dt.datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
            output_filename = st.text_input("저장 파일명", value=default_name)
            
            # 크롤링 실행 버튼
            if st.button("🚀 뉴스 수집 시작", type="primary"):
                if start_date <= end_date:  # 날짜 유효성 재확인
                    self._run_crawling(
                        keyword=keyword,
                        date_from=start_date.strftime("%Y.%m.%d"),
                        date_to=end_date.strftime("%Y.%m.%d"),
                        output_filename=output_filename
                    )
                else:
                    st.error("날짜를 확인해주세요")
        
        # 메인 화면
        self._display_results()
        
    def _run_crawling(self, keyword, date_from, date_to, output_filename):
        """크롤링 실행 및 상태 관리"""
        output_path = self.output_dir / output_filename
        
        with st.spinner(f"'{keyword}' 뉴스 수집 중..."):
            try:
                # 크롤링 실행 (excel 저장 포함)
                results = self.crawler.run_batch(
                    keyword=keyword,
                    date_from=date_from,
                    date_to=date_to,
                    output_path=str(output_path)
                )
                
                # 세션에 결과 저장
                st.session_state['last_results'] = results
                st.session_state['last_file'] = str(output_path)
                st.success(f"✅ 수집 완료: {output_path.name}")
                
            except Exception as e:
                st.error(f"❌ 크롤링 실패: {e}")
    
    def _display_results(self):
        """결과 화면 표시"""
        st.header("📊 수집 결과")
        
        if 'last_file' not in st.session_state:
            st.info("👈 왼쪽 사이드바에서 뉴스 수집을 시작하세요")
            return
            
        # 엑셀 파일 읽기
        file_path = st.session_state['last_file']
        if Path(file_path).exists():
            try:
                # 첫 번째 데이터 시트 읽기 (meta 시트가 아닌)
                xl_file = pd.ExcelFile(file_path)
                sheet_names = [s for s in xl_file.sheet_names if s != 'meta']
                
                if sheet_names:
                    df = pd.read_excel(file_path, sheet_name=sheet_names[0])
                    
                    # 통계
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("총 기사 수", len(df))
                    with col2:
                        st.metric("언론사 수", df['언론사'].nunique() if '언론사' in df.columns else 0)
                    with col3:
                        st.metric("파일 크기", f"{Path(file_path).stat().st_size / 1024:.1f} KB")
                    
                    # 데이터 표시
                    st.dataframe(df, use_container_width=True)
                    
                    # 다운로드 버튼
                    with open(file_path, 'rb') as f:
                        st.download_button(
                            label="📥 엑셀 다운로드",
                            data=f,
                            file_name=Path(file_path).name,
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                        )
                else:
                    st.warning("데이터 시트를 찾을 수 없습니다")
                    
            except Exception as e:
                st.error(f"파일 읽기 실패: {e}")

# Streamlit 직접 실행 지원
if __name__ == "__main__":
    if "streamlit" not in sys.modules:
        import streamlit.web.cli as stcli
        sys.argv = ["streamlit", "run", sys.argv[0]]
        sys.exit(stcli.main())
    else:
        app = NewsAgentApp()
        app.run()