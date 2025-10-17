@echo off
REM ===== 프로젝트 경로로 이동 =====
cd /d C:\Users\LEE

REM ===== 가상환경 존재 여부 확인 및 생성 =====
IF NOT EXIST data1 (
    echo Creating virtual environment...
    python -m venv data1
)

REM ===== 가상환경 활성화 =====
call data1\Scripts\activate

REM ===== requirements.txt 설치 =====
IF EXIST requirements.txt (
    echo Installing dependencies from requirements.txt...
    pip install --upgrade pip
    pip install -r requirements.txt
) ELSE (
    echo No requirements.txt found. Skipping installation.
)

REM ===== Streamlit 실행 =====
echo Starting Streamlit app...
streamlit run app.py

REM ===== 콘솔 유지 =====
pause
