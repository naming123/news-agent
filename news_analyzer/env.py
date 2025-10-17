# C:\Users\user\yalco-Docker\data_project\news_analyzer\env.py
# 목적: .env 로딩 확인, NAVER 키 진단, 임포트/요청 검증

import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent              # .../news_analyzer
SRC  = HERE / "src"                                 # .../news_analyzer/src
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))                    # src를 최우선 모듈 경로에 추가

# --- .env 로딩 (news_analyzer/.env 우선) ---
try:
    from dotenv import load_dotenv, find_dotenv     # type: ignore
    dotenv_path = find_dotenv(filename=".env", usecwd=True)
    if not dotenv_path:
        cand = HERE / ".env"
        if cand.exists():
            dotenv_path = str(cand)
    if dotenv_path:
        load_dotenv(dotenv_path=dotenv_path, override=True)
        print(f"[dotenv] loaded: {dotenv_path}")
    else:
        print("[dotenv] .env not found (continue)")
except Exception as e:
    print(f"[dotenv] skipped: {e}")

# --- 올바른 임포트 (당신 구조에 맞춤) ---
try:
    from src.news_collector.collector.crawler import NaverNewsCrawler
    print("[import] news_collector.collector.crawler.NaverNewsCrawler")
except Exception as e:
    print("[import] FAILED:", repr(e))
    sys.exit(1)

# --- ENV 값 진단 ---
cid = (os.getenv("NAVER_CLIENT_ID") or "").strip()
csc = (os.getenv("NAVER_CLIENT_SECRET") or "").strip()
print("ID  :", repr(cid), "LEN:", len(cid))
print("SEC :", repr(csc), "LEN:", len(csc))
if not cid or not csc:
    print("!! ENV missing: NAVER_CLIENT_ID / NAVER_CLIENT_SECRET (UTF-8, BOM 없음, 공백/따옴표 X)")
    # 여기서도 진행해 보되, 생성자에서 막히면 종료

# --- 크롤러 생성 + 헤더 확인 ---
try:
    crawler = NaverNewsCrawler(client_id=cid, client_secret=csc)  # 명시 주입으로 경로 문제 차단
    print("HEADERS:", crawler.headers)
except Exception as e:
    print("!! Crawler init failed:", repr(e))
    sys.exit(1)

# --- 실제 호출 테스트 (요청/응답/URL 확인) ---
import requests
try:
    r = crawler.session.get(
        crawler.BASE_URL,
        headers=crawler.headers,
        params={"query": "삼성전자 ESG", "start": 1, "display": 10, "sort": "date"},
        timeout=10,
    )
    print("HTTP :", r.status_code)
    print("URL  :", r.url)
    print("BODY :", r.text[:300])
    if r.status_code != 200:
        print("!! Non-200 response, check body above.")
except requests.exceptions.RequestException as e:
    print("!! Request failed:", repr(e))
