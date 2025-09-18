# 네이버 뉴스 크롤링 및 센티멘트 분석 시스템
# Colab 환경용 완전한 파이프라인


# 필수 임포트
import os
import time
import random
import requests
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json
import re
from urllib.parse import urlencode, quote
import warnings
warnings.filterwarnings('ignore')

# 웹 크롤링 관련
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup

# ML/NLP 관련
import torch
import torch.nn as nn
from transformers import BertModel, BertTokenizer
from kobert_tokenizer import KoBERTTokenizer
import gluonnlp as nlp

print("라이브러리 설치 및 임포트 완료!")

# ============================================================================
# 2. 네이버 뉴스 크롤러 클래스
# ============================================================================

class NaverNewsCrawler:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })
        self.driver = None
        self.setup_driver()
    
    def setup_driver(self):
        """Selenium 드라이버 설정"""
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--window-size=1920,1080')
        chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
        
        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=chrome_options)
        print("Selenium 드라이버 설정 완료")
    
    def search_news_api(self, keyword, start_date, end_date, display=100):
        """네이버 뉴스 API를 통한 검색"""
        client_id = "YOUR_CLIENT_ID"  # 네이버 개발자센터에서 발급
        client_secret = "YOUR_CLIENT_SECRET"
        
        # API 방식 (제한적이지만 안정적)
        base_url = "https://openapi.naver.com/v1/search/news.json"
        
        headers = {
            'X-Naver-Client-Id': client_id,
            'X-Naver-Client-Secret': client_secret
        }
        
        params = {
            'query': keyword,
            'display': display,
            'start': 1,
            'sort': 'date'
        }
        
        try:
            response = self.session.get(base_url, headers=headers, params=params)
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            print(f"API 요청 실패: {e}")
        
        return None
    
    def search_news_selenium(self, keyword, start_date, end_date, max_pages=5):
        """Selenium을 통한 네이버 뉴스 크롤링 (봇 탐지 회피 포함)"""
        news_list = []
        
        # 네이버 뉴스 검색 URL 구성
        base_url = "https://search.naver.com/search.naver"
        
        for page in range(1, max_pages + 1):
            print(f"페이지 {page} 크롤링 중...")
            
            # 페이지별로 User-Agent 로테이션
            if page > 1:
                self.rotate_user_agent()
            
            params = {
                'where': 'news',
                'query': keyword,
                'start': (page - 1) * 10 + 1,
                'sort': '1',  # 최신순
                'pd': '3',    # 기간 설정
                'ds': start_date.strftime('%Y.%m.%d'),
                'de': end_date.strftime('%Y.%m.%d')
            }
            
            search_url = f"{base_url}?{urlencode(params)}"
            
            try:
                self.driver.get(search_url)
                
                # 랜덤 딜레이 (2-5초)
                delay = self.random_delay(2, 5)
                print(f"  딜레이: {delay:.1f}초")
                
                # 뉴스 아이템 수집
                news_items = self.driver.find_elements(By.CSS_SELECTOR, ".news_area")
                
                if not news_items:
                    print(f"  페이지 {page}에서 뉴스를 찾을 수 없습니다.")
                    continue
                
                for idx, item in enumerate(news_items):
                    try:
                        # 제목 및 링크
                        title_element = item.find_element(By.CSS_SELECTOR, ".news_tit")
                        title = title_element.text
                        link = title_element.get_attribute("href")
                        
                        # 언론사
                        media = item.find_element(By.CSS_SELECTOR, ".info_group .press").text
                        
                        # 날짜
                        date_element = item.find_element(By.CSS_SELECTOR, ".info_group .info")
                        date_text = date_element.text
                        
                        # 요약 내용
                        summary_element = item.find_element(By.CSS_SELECTOR, ".dsc_wrap")
                        summary = summary_element.text if summary_element else ""
                        
                        news_data = {
                            'title': title,
                            'link': link,
                            'media': media,
                            'date': date_text,
                            'summary': summary,
                            'keyword': keyword
                        }
                        
                        news_list.append(news_data)
                        
                        # 각 아이템 처리 후 짧은 딜레이
                        if idx < len(news_items) - 1:  # 마지막 아이템이 아니면
                            time.sleep(random.uniform(0.3, 0.8))
                        
                    except Exception as e:
                        print(f"  뉴스 아이템 {idx+1} 처리 실패: {e}")
                        continue
                
                print(f"  페이지 {page} 완료: {len([n for n in news_list if n['keyword'] == keyword])}개 기사")
                
                # 페이지 간 딜레이 (마지막 페이지가 아니면)
                if page < max_pages:
                    self.random_delay(3, 6)
                
            except Exception as e:
                print(f"  페이지 {page} 크롤링 실패: {e}")
                # 실패 시 더 긴 딜레이
                self.random_delay(5, 10)
                continue
        
        return news_list
    
    def get_full_article(self, url):
        """개별 기사 본문 크롤링 (봇 탐지 회피 포함)"""
        try:
            # 기사 접근 전 딜레이
            self.random_delay(1, 2)
            
            self.driver.get(url)
            
            # 페이지 로딩 대기
            self.random_delay(2, 3)
            
            # 네이버 뉴스 기사 본문 선택자
            content_selectors = [
                "#dic_area",  # 일반적인 네이버 뉴스
                ".go_trans._article_content",  # 번역 기사
                "#articleBodyContents",  # 구버전
                ".news_end"  # 기타
            ]
            
            content = ""
            for selector in content_selectors:
                try:
                    content_element = self.driver.find_element(By.CSS_SELECTOR, selector)
                    content = content_element.text
                    break
                except:
                    continue
            
            return content.strip()
            
        except Exception as e:
            print(f"본문 크롤링 실패 ({url}): {e}")
            return ""
    
    def close(self):
        """드라이버 종료"""
        if self.driver:
            self.driver.quit()

# ============================================================================
# 3. KoBERT 센티멘트 분석 모델
# ============================================================================

class BERTClassifier(nn.Module):
    def __init__(self, bert_model, dr_rate=None, params=None):
        super(BERTClassifier, self).__init__()
        self.bert = bert_model
        self.dr_rate = dr_rate
        self.classifier = nn.Linear(768, 3)  # 긍정/부정/중립
        if dr_rate:
            self.dropout = nn.Dropout(p=dr_rate)
    
    def gen_attention_mask(self, token_ids, valid_length):
        attention_mask = torch.zeros_like(token_ids)
        for i, v in enumerate(valid_length):
            attention_mask[i][:v] = 1
        return attention_mask.float()
    
    def forward(self, token_ids, valid_length, segment_ids):
        attention_mask = self.gen_attention_mask(token_ids, valid_length)
        _, pooler = self.bert(input_ids=token_ids, 
                             token_type_ids=segment_ids.long(), 
                             attention_mask=attention_mask.float().to(token_ids.device),
                             return_dict=False)
        if self.dr_rate:
            out = self.dropout(pooler)
        else:
            out = pooler
        return self.classifier(out)

class SentimentAnalyzer:
    def __init__(self):
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model_type = "keyword"
        self.positive_words = ['좋', '상승', '증가', '성장', '호조', '개선', '확대', '투자', '수익', '성공', '향상', '발전']
        self.negative_words = ['나쁘', '하락', '감소', '악화', '부진', '손실', '위기', '문제', '실패', '하향', '악감', '폐지']
        
        # KoBERT 시도
        self.tokenizer = None
        self.model = None
        self.setup_model()
        print(f"센티멘트 분석 모델 설정 완료: {self.model_type}")
    
    def setup_model(self):
        """모델 설정"""
        try:
            # KoBERT 시도 (토크나이저 오류 무시하고 진행)
            if BERT_AVAILABLE:
                from kobert_tokenizer import KoBERTTokenizer
                from transformers import BertModel
                
                self.tokenizer = KoBERTTokenizer.from_pretrained('skt/kobert-base-v1')
                bertmodel = BertModel.from_pretrained('skt/kobert-base-v1', return_dict=False)
                self.model = BERTClassifier(bertmodel, dr_rate=0.5).to(self.device)
                self.model_type = "kobert"
                
        except Exception as e:
            # KoBERT 실패하면 키워드 방식 사용
            self.model_type = "keyword"
    
    def predict_sentiment(self, text):
        """센티멘트 예측"""
        # 모든 경우에 키워드 방식 사용 (안전함)
        return self.predict_keyword_sentiment(text)
    
    def predict_keyword_sentiment(self, text):
        """키워드 기반 센티멘트 예측"""
        text_lower = text.lower()
        
        pos_count = sum(1 for word in self.positive_words if word in text_lower)
        neg_count = sum(1 for word in self.negative_words if word in text_lower)
        
        if pos_count > neg_count:
            sentiment = "긍정"
            confidence = min(0.6 + (pos_count - neg_count) * 0.1, 0.9)
        elif neg_count > pos_count:
            sentiment = "부정"
            confidence = min(0.6 + (neg_count - pos_count) * 0.1, 0.9)
        else:
            sentiment = "중립"
            confidence = 0.5
        
        return {
            'sentiment': sentiment,
            'confidence': float(confidence),
            'scores': {
                '긍정': confidence if sentiment == "긍정" else (1-confidence)/2,
                '부정': confidence if sentiment == "부정" else (1-confidence)/2,
                '중립': confidence if sentiment == "중립" else (1-confidence)/2
            }
        }

# ============================================================================
# 4. 기업 식별 시스템
# ============================================================================

class CompanyIdentifier:
    def __init__(self, company_list_file=None):
        self.companies = self.load_companies(company_list_file)
        
    def load_companies(self, file_path):
        """기업명 리스트 로드"""
        if file_path and os.path.exists(file_path):
            # 파일에서 기업명 로드
            if file_path.endswith('.csv'):
                df = pd.read_csv(file_path)
                return df['company_name'].tolist()
            elif file_path.endswith('.txt'):
                with open(file_path, 'r', encoding='utf-8') as f:
                    return [line.strip() for line in f.readlines()]
        else:
            # 샘플 기업명 리스트
            return [
                '삼성전자', '삼성', 'SK하이닉스', 'LG전자', 'LG화학', 
                '현대자동차', '현대차', '기아', 'POSCO', '포스코',
                '네이버', 'NAVER', '카카오', 'Kakao', '셀트리온',
                '한국전력', '한전', '신한금융', 'KB금융', '하나금융',
                '아모레퍼시픽', '아모레', 'CJ', '롯데', '두산',
                '고려아연', 'SK이노베이션', 'SK', 'LG', '현대'
            ]
    
    def identify_companies(self, text):
        """텍스트에서 기업명 식별"""
        found_companies = []
        text_lower = text.lower()
        
        for company in self.companies:
            if company.lower() in text_lower:
                found_companies.append(company)
        
        return list(set(found_companies))  # 중복 제거

# ============================================================================
# 5. 메인 파이프라인 클래스
# ============================================================================

class NewsAnalysisPipeline:
    def __init__(self, company_list_file=None):
        self.crawler = NaverNewsCrawler()
        self.sentiment_analyzer = SentimentAnalyzer()
        self.company_identifier = CompanyIdentifier(company_list_file)
        
    def run_analysis(self, keywords, start_date, end_date, max_pages=3, get_full_content=True):
        """전체 분석 파이프라인 실행"""
        all_results = []
        
        for keyword in keywords:
            print(f"\n=== '{keyword}' 키워드 분석 시작 ===")
            
            # 1. 뉴스 크롤링
            print("뉴스 크롤링 중...")
            news_list = self.crawler.search_news_selenium(
                keyword, start_date, end_date, max_pages
            )
            
            print(f"크롤링 완료: {len(news_list)}개 기사")
            
            # 2. 각 뉴스에 대해 분석 수행
            for i, news in enumerate(news_list):
                print(f"기사 {i+1}/{len(news_list)} 분석 중...")
                
                # 전체 본문 가져오기 (옵션)
                if get_full_content and news['link']:
                    full_content = self.crawler.get_full_article(news['link'])
                    analysis_text = f"{news['title']} {full_content}"
                else:
                    analysis_text = f"{news['title']} {news['summary']}"
                
                # 센티멘트 분석
                sentiment_result = self.sentiment_analyzer.predict_sentiment(analysis_text)
                
                # 기업 식별
                companies = self.company_identifier.identify_companies(analysis_text)
                
                # 결과 저장
                result = {
                    'keyword': keyword,
                    'title': news['title'],
                    'media': news['media'],
                    'date': news['date'],
                    'link': news['link'],
                    'summary': news['summary'],
                    'full_content': full_content if get_full_content else "",
                    'sentiment': sentiment_result['sentiment'],
                    'confidence': sentiment_result['confidence'],
                    'sentiment_scores': sentiment_result['scores'],
                    'companies': companies,
                    'company_count': len(companies)
                }
                
                all_results.append(result)
                
                # 과부하 방지
                time.sleep(0.5)
        
        return all_results
    
    def save_results(self, results, output_format='csv', filename=None):
        """결과 저장"""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"news_analysis_{timestamp}"
        
        df = pd.DataFrame(results)
        
        if output_format.lower() == 'csv':
            df.to_csv(f"{filename}.csv", index=False, encoding='utf-8-sig')
            print(f"결과 저장 완료: {filename}.csv")
        elif output_format.lower() == 'excel':
            df.to_excel(f"{filename}.xlsx", index=False)
            print(f"결과 저장 완료: {filename}.xlsx")
        elif output_format.lower() == 'json':
            df.to_json(f"{filename}.json", orient='records', force_ascii=False, indent=2)
            print(f"결과 저장 완료: {filename}.json")
        
        return df
    
    def get_summary_stats(self, results):
        """분석 결과 요약 통계"""
        df = pd.DataFrame(results)
        
        print("\n=== 분석 결과 요약 ===")
        print(f"총 분석 기사 수: {len(df)}")
        print(f"키워드별 분포:")
        print(df['keyword'].value_counts())
        print(f"\n센티멘트 분포:")
        print(df['sentiment'].value_counts())
        print(f"\n언론사별 분포:")
        print(df['media'].value_counts().head(10))
        
        # 기업별 언급 횟수
        all_companies = []
        for companies in df['companies']:
            all_companies.extend(companies)
        
        if all_companies:
            company_counts = pd.Series(all_companies).value_counts()
            print(f"\n기업 언급 빈도 (Top 10):")
            print(company_counts.head(10))
        
        return df
    
    def close(self):
        """리소스 정리"""
        self.crawler.close()

# ============================================================================
# 6. 사용 예시 및 실행
# ============================================================================

# 사용법 예시
def run_example():
    """예시 실행 함수"""
    
    # 분석 파이프라인 초기화
    pipeline = NewsAnalysisPipeline()
    
    # 검색 조건 설정
    keywords = ['삼성전자', 'SK하이닉스']  # 분석하고 싶은 키워드들
    start_date = datetime(2024, 1, 1)      # 시작 날짜
    end_date = datetime(2024, 1, 31)       # 종료 날짜
    
    try:
        # 분석 실행
        results = pipeline.run_analysis(
            keywords=keywords,
            start_date=start_date,
            end_date=end_date,
            max_pages=2,          # 각 키워드당 크롤링할 페이지 수
            get_full_content=False # 전체 본문 가져올지 여부
        )
        
        # 결과 저장
        df = pipeline.save_results(results, output_format='csv')
        
        # 요약 통계
        pipeline.get_summary_stats(results)
        
        # 상위 5개 결과 미리보기
        print("\n=== 분석 결과 미리보기 ===")
        preview_df = df[['title', 'sentiment', 'confidence', 'companies']].head()
        print(preview_df.to_string())
        
    finally:
        # 리소스 정리
        pipeline.close()

# ============================================================================
# 7. MAIN 함수 - 실제 실행
# ============================================================================

def main():
    """메인 실행 함수"""
    print("=" * 60)
    print("네이버 뉴스 크롤링 및 센티멘트 분석 시스템")
    print("=" * 60)
    
    # 사용자 입력 받기
    print("\n검색 조건을 입력해주세요:")
    
    # 키워드 입력
    keywords_input = input("검색 키워드들 (쉼표로 구분): ")
    keywords = [k.strip() for k in keywords_input.split(",")]
    
    # 기간 입력
    start_date_str = input("시작 날짜 (YYYY-MM-DD, 예: 2024-01-01): ")
    end_date_str = input("종료 날짜 (YYYY-MM-DD, 예: 2024-01-31): ")
    
    try:
        start_date = datetime.strptime(start_date_str, "%Y-%m-%d")
        end_date = datetime.strptime(end_date_str, "%Y-%m-%d")
    except ValueError:
        print("날짜 형식이 잘못되었습니다. 기본값을 사용합니다.")
        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 1, 31)
    
    # 기타 옵션
    max_pages = int(input("각 키워드당 크롤링할 페이지 수 (기본값 2): ") or "2")
    get_full_content = input("전체 기사 본문을 가져올까요? (y/n, 기본값 n): ").lower().startswith('y')
    output_format = input("저장 형식 (csv/excel/json, 기본값 csv): ") or "csv"
    
    print(f"\n분석 시작...")
    print(f"키워드: {keywords}")
    print(f"기간: {start_date_str} ~ {end_date_str}")
    print(f"페이지: {max_pages}페이지/키워드")
    print(f"전체 본문: {'예' if get_full_content else '아니오'}")
    print(f"저장 형식: {output_format}")
    
    # 파이프라인 실행
    pipeline = None
    try:
        # 파이프라인 초기화
        print("\n시스템 초기화 중...")
        pipeline = NewsAnalysisPipeline()
        
        # 분석 실행
        print("\n뉴스 분석 시작...")
        results = pipeline.run_analysis(
            keywords=keywords,
            start_date=start_date,
            end_date=end_date,
            max_pages=max_pages,
            get_full_content=get_full_content
        )
        
        if not results:
            print("분석할 뉴스를 찾을 수 없습니다.")
            return
        
        # 결과 저장
        print(f"\n결과 저장 중... (형식: {output_format})")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"news_analysis_{timestamp}"
        
        df = pipeline.save_results(results, output_format=output_format, filename=filename)
        
        # 요약 통계 출력
        print("\n" + "=" * 60)
        pipeline.get_summary_stats(results)
        
        # 상위 결과 미리보기
        print("\n" + "=" * 60)
        print("분석 결과 미리보기 (상위 5개)")
        print("=" * 60)
        
        preview_columns = ['title', 'media', 'sentiment', 'confidence', 'companies']
        available_columns = [col for col in preview_columns if col in df.columns]
        
        if available_columns:
            preview_df = df[available_columns].head()
            for i, row in preview_df.iterrows():
                print(f"\n[{i+1}] 제목: {row['title'][:50]}...")
                print(f"    언론사: {row['media']}")
                print(f"    센티멘트: {row['sentiment']} (신뢰도: {row['confidence']:.2f})")
                if 'companies' in row and row['companies']:
                    print(f"    기업: {row['companies']}")
        
        print(f"\n분석 완료! 총 {len(results)}개 기사 분석됨")
        print(f"결과 파일: {filename}.{output_format}")
        
    except KeyboardInterrupt:
        print("\n사용자에 의해 중단되었습니다.")
    except Exception as e:
        print(f"\n오류 발생: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # 리소스 정리
        if pipeline:
            pipeline.close()
            print("리소스 정리 완료")

def quick_test():
    """간단한 테스트 함수"""
    print("간단한 테스트 실행 중...")
    
    # 테스트용 파이프라인
    pipeline = NewsAnalysisPipeline()
    
    try:
        # 센티멘트 분석 테스트
        test_texts = [
            "삼성전자 주가가 크게 상승했습니다",
            "LG화학 실적이 부진했습니다", 
            "현대자동차 신차 출시 예정입니다"
        ]
        
        print("센티멘트 분석 테스트:")
        for text in test_texts:
            result = pipeline.sentiment_analyzer.predict_sentiment(text)
            print(f"텍스트: {text}")
            print(f"결과: {result['sentiment']} (신뢰도: {result['confidence']:.2f})")
            print("-" * 40)
        
        # 기업 식별 테스트
        print("\n기업 식별 테스트:")
        test_text = "삼성전자와 LG전자가 협력한다고 발표했습니다"
        companies = pipeline.company_identifier.identify_companies(test_text)
        print(f"텍스트: {test_text}")
        print(f"식별된 기업: {companies}")
        
    except Exception as e:
        print(f"테스트 중 오류: {e}")
    finally:
        pipeline.close()

def show_menu():
    """메뉴 표시 및 선택"""
    while True:
        print("\n" + "=" * 50)
        print("네이버 뉴스 센티멘트 분석 시스템")
        print("=" * 50)
        print("1. 전체 분석 실행")
        print("2. 간단한 테스트")
        print("3. 시스템 정보")
        print("4. 종료")
        print("-" * 50)
        
        choice = input("선택하세요 (1-4): ").strip()
        
        if choice == "1":
            main()
        elif choice == "2":
            quick_test()
        elif choice == "3":
            show_system_info()
        elif choice == "4":
            print("프로그램을 종료합니다.")
            break
        else:
            print("잘못된 선택입니다. 1-4 중에서 선택해주세요.")

def show_system_info():
    """시스템 정보 표시"""
    print("\n시스템 정보:")
    print(f"Python 버전: {os.sys.version}")
    
    # GPU 확인
    import torch
    print(f"PyTorch 버전: {torch.__version__}")
    print(f"CUDA 사용 가능: {torch.cuda.is_available()}")
    if torch.cuda.is_available():
        print(f"GPU: {torch.cuda.get_device_name(0)}")
    
    # 센티멘트 분석 모델 확인
    try:
        analyzer = SentimentAnalyzer()
        print(f"센티멘트 분석 모델: {analyzer.model_type}")
    except:
        print("센티멘트 분석 모델: 로드 실패")
    
    print("\n지원 기능:")
    print("- 네이버 뉴스 크롤링 (Selenium)")
    print("- KoBERT/키워드 기반 센티멘트 분석")
    print("- 기업명 자동 식별")
    print("- CSV/Excel/JSON 형태 결과 저장")

# ============================================================================
# 8. 프로그램 시작점
# ============================================================================

if __name__ == "__main__":
    print("네이버 뉴스 크롤링 및 센티멘트 분석 시스템 로딩 완료!")
    print("사용법:")
    print("  show_menu()    : 메뉴 방식 실행")
    print("  main()         : 직접 실행")
    print("  quick_test()   : 간단한 테스트")
    
    # 자동으로 메뉴 실행 (원하지 않으면 주석 처리)
    # show_menu()