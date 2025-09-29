# crawler.py
from typing import List, Dict, Optional
from datetime import datetime
from dataclasses import dataclass
import logging
import time
import random
from abc import ABC, abstractmethod

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.chrome.options import Options
import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

@dataclass
class NewsArticle:
    """뉴스 기사 데이터 모델"""
    title: str
    link: str
    press: str
    date: str
    summary: str
    keyword: str = ""
    company: str = ""
    group: str = ""
    original_link: str = ""
    search_query: str = ""
    crawl_time: str = ""
    date_from: str = ""
    date_to: str = ""
    
    def to_dict(self) -> Dict:
        return self.__dict__

class NewsDataFetcher(ABC):
    """뉴스 데이터 수집 인터페이스"""
    
    @abstractmethod
    def fetch(self, keyword: str, start_date: str, end_date: str) -> List[NewsArticle]:
        pass

class NaverNewsCrawler(NewsDataFetcher):
    """네이버 뉴스 크롤러 - 자연스러운 스크롤"""
    
    def __init__(self):
        self.END_MESSAGE = "뉴스 기사와 댓글로 인한 문제 발생시 24시간 센터로 접수해주세요"
        self.setup_driver()
        
    def setup_driver(self):
        """Chrome 드라이버 설정 - 봇 감지 회피"""
        options = Options()
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        
        # 헤드리스 모드는 사용하지 않음 (봇 감지 회피)
        # options.add_argument('--headless')
        
        self.driver = webdriver.Chrome(options=options)
        self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
    def fetch(
        self, 
        keyword: str, 
        start_date: str, 
        end_date: str
    ) -> List[NewsArticle]:
        """자연스러운 무한 스크롤로 뉴스 수집"""
        articles = []
        seen_links = set()
        
        # URL 구성
        url = f"https://search.naver.com/search.naver?where=news&query={keyword}&sm=tab_opt&sort=0&photo=0&field=0&pd=3&ds={start_date}&de={end_date}"
        
        try:
            self.driver.get(url)
            time.sleep(random.uniform(2, 4))  # 초기 로딩 대기
            
            # 인간같은 초기 행동
            self._human_like_behavior()
            
            last_height = 0
            no_change_count = 0
            scroll_count = 0
            
            while True:
                # 현재 보이는 기사들 수집
                news_items = self.driver.find_elements(By.CSS_SELECTOR, '.news_area')
                
                for item in news_items:
                    try:
                        link_elem = item.find_element(By.CSS_SELECTOR, '.news_tit')
                        link = link_elem.get_attribute('href')
                        
                        if link not in seen_links:
                            seen_links.add(link)
                            article = self._parse_news_item_selenium(item, keyword, start_date, end_date)
                            if article:
                                articles.append(article)
                                logger.info(f"수집: {len(articles)}번째 기사 - {article.title[:30]}...")
                    except:
                        continue
                
                # 끝 메시지 확인
                page_text = self.driver.page_source
                if self.END_MESSAGE in page_text:
                    logger.info("페이지 끝 도달 - 수집 완료")
                    break
                
                # 자연스러운 스크롤
                self._natural_scroll()
                scroll_count += 1
                
                # 가끔 쉬기 (인간처럼)
                if scroll_count % random.randint(5, 8) == 0:
                    logger.info("잠시 휴식...")
                    time.sleep(random.uniform(3, 7))
                    self._random_mouse_movement()
                
                # 높이 변화 체크
                new_height = self.driver.execute_script("return document.body.scrollHeight")
                if new_height == last_height:
                    no_change_count += 1
                    if no_change_count >= 3:
                        # 한번 더 확인
                        time.sleep(2)
                        if self.END_MESSAGE in self.driver.page_source:
                            logger.info("더 이상 기사 없음 - 수집 완료")
                            break
                else:
                    no_change_count = 0
                last_height = new_height
                
                # 너무 오래 걸리면 중단
                if scroll_count > 100:
                    logger.warning("스크롤 횟수 초과 - 수집 중단")
                    break
                    
        except Exception as e:
            logger.error(f"크롤링 오류: {e}")
        finally:
            self.driver.quit()
            
        logger.info(f"총 {len(articles)}개 기사 수집 완료")
        return articles
    
    def _natural_scroll(self):
        """자연스러운 스크롤 패턴"""
        # 랜덤한 스크롤 거리
        scroll_options = [
            lambda: self.driver.execute_script("window.scrollBy(0, window.innerHeight * 0.8)"),
            lambda: self.driver.execute_script("window.scrollBy(0, window.innerHeight * 1.2)"),
            lambda: self.driver.execute_script("window.scrollBy(0, window.innerHeight * 0.6)"),
            lambda: self.driver.execute_script("window.scrollBy(0, Math.floor(Math.random() * 500 + 300))"),
        ]
        
        random.choice(scroll_options)()
        
        # 자연스러운 대기 시간
        time.sleep(random.uniform(1.5, 3.5))
        
        # 가끔 위로 살짝 스크롤 (인간처럼)
        if random.random() < 0.1:
            self.driver.execute_script("window.scrollBy(0, -100)")
            time.sleep(random.uniform(0.5, 1))
            
    def _human_like_behavior(self):
        """초기 인간같은 행동 패턴"""
        # 페이지 살짝 스크롤
        self.driver.execute_script("window.scrollBy(0, 200)")
        time.sleep(random.uniform(0.5, 1))
        
        # 다시 위로
        self.driver.execute_script("window.scrollBy(0, -100)")
        time.sleep(random.uniform(0.5, 1))
        
    def _random_mouse_movement(self):
        """랜덤 마우스 움직임"""
        try:
            actions = ActionChains(self.driver)
            # 랜덤 위치로 마우스 이동
            x = random.randint(100, 500)
            y = random.randint(100, 400)
            actions.move_by_offset(x, y).perform()
            time.sleep(random.uniform(0.1, 0.3))
            actions.move_by_offset(-x//2, -y//2).perform()
        except:
            pass
    
    def _parse_news_item_selenium(self, item, keyword: str, start_date: str, end_date: str) -> Optional[NewsArticle]:
        """Selenium으로 뉴스 아이템 파싱"""
        try:
            # 제목과 링크
            title_elem = item.find_element(By.CSS_SELECTOR, '.news_tit')
            title = title_elem.get_attribute('title')
            link = title_elem.get_attribute('href')
            
            # 언론사
            try:
                press = item.find_element(By.CSS_SELECTOR, '.info_group .press').text
            except:
                press = ''
            
            # 날짜
            try:
                date = item.find_element(By.CSS_SELECTOR, '.info_group span.info').text
            except:
                date = ''
            
            # 요약
            try:
                summary = item.find_element(By.CSS_SELECTOR, '.dsc_txt').text
            except:
                summary = ''
            
            return NewsArticle(
                title=title,
                link=link,
                press=press,
                date=date,
                summary=summary,
                keyword=keyword,
                original_link=link,
                search_query=keyword,
                crawl_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                date_from=start_date,
                date_to=end_date
            )
            
        except Exception as e:
            logger.warning(f"파싱 실패: {e}")
            return None

class NewsCrawlerFactory:
    """크롤러 팩토리"""
    
    @staticmethod
    def create(source: str = "naver") -> NewsDataFetcher:
        crawlers = {
            "naver": NaverNewsCrawler,
        }
        
        crawler_class = crawlers.get(source, NaverNewsCrawler)
        return crawler_class()

# 기존 코드 호환성
class NewsCrawler:
    def __init__(self, source: str = "naver"):
        self.fetcher = NewsCrawlerFactory.create(source)
    
    def fetch_news_data(
        self, 
        keyword: str,
        start_date: str,
        end_date: str,
        max_articles: int = None  # 무시됨
    ) -> List[Dict]:
        """max_articles는 무시하고 끝까지 수집"""
        articles = self.fetcher.fetch(keyword, start_date, end_date)
        return [article.to_dict() for article in articles]