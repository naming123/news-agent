# config.py
from dataclasses import dataclass
from pathlib import Path
import yaml
import json
from typing import Optional

@dataclass
class CrawlerConfig:
    """크롤러 설정"""
    max_articles: int = 100
    delay_min: float = 1.0
    delay_max: float = 2.0
    source: str = "naver"
    output_dir: str = "outputs"
    
@dataclass
class AppConfig:
    """애플리케이션 전체 설정"""
    crawler: CrawlerConfig
    ui_theme: str = "default"
    debug: bool = False
    
class ConfigManager:
    """설정 관리자"""
    
    def __init__(self, config_path: Optional[str] = None):
        self.config_path = Path(config_path or "config.yaml")
        self.config = self._load_config()
    
    def _load_config(self) -> AppConfig:
        """설정 파일 로드"""
        if self.config_path.exists():
            with open(self.config_path, 'r', encoding='utf-8') as f:
                if self.config_path.suffix == '.yaml':
                    data = yaml.safe_load(f)
                elif self.config_path.suffix == '.json':
                    data = json.load(f)
                else:
                    data = {}
                    
            crawler_config = CrawlerConfig(**data.get('crawler', {}))
            return AppConfig(
                crawler=crawler_config,
                ui_theme=data.get('ui_theme', 'default'),
                debug=data.get('debug', False)
            )
        else:
            # 기본 설정
            return AppConfig(crawler=CrawlerConfig())
    
    def save_config(self):
        """설정 저장"""
        data = {
            'crawler': {
                'max_articles': self.config.crawler.max_articles,
                'delay_min': self.config.crawler.delay_min,
                'delay_max': self.config.crawler.delay_max,
                'source': self.config.crawler.source,
                'output_dir': self.config.crawler.output_dir
            },
            'ui_theme': self.config.ui_theme,
            'debug': self.config.debug
        }
        
        with open(self.config_path, 'w', encoding='utf-8') as f:
            if self.config_path.suffix == '.yaml':
                yaml.dump(data, f, allow_unicode=True)
            else:
                json.dump(data, f, indent=2, ensure_ascii=False)