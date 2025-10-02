import numpy as np
import gensim.downloader as api
import requests
import gzip
from pathlib import Path
from typing import Tuple, Dict

try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False


class ModelLoader:
    def __init__(self, config):
        self.config = config
        self.model = None
        self.embeddings = None
        self.token2id = None
        self.id2token = None
        self.is_sentence_model = False  # ← 추가
    
    def load(self, model_name: str):
        """모델 로드 - 타입 자동 감지"""
        
        # ⭐ Sentence Transformer 먼저 체크! (순서 중요)
        if model_name == 'multilingual' or model_name.startswith('paraphrase'):
            if not SENTENCE_TRANSFORMERS_AVAILABLE:
                raise ImportError(
                    "sentence-transformers가 설치되지 않았습니다.\n"
                    "설치: pip install sentence-transformers"
                )
            self._load_sentence_transformer(model_name)
            self.is_sentence_model = True
            
        # 한국어 FastText
        elif model_name in self.config.KOREAN_MODELS:
            self._load_korean_model(model_name)
            
        # 영어 Gensim 모델
        elif model_name in self.config.MODELS:
            self._load_english_model(model_name)
            
        else:
            raise ValueError(f"지원하지 않는 모델: {model_name}")


    def _load_sentence_transformer(self, model_name: str):
        """Sentence Transformer 로드 (한국어 지원!)"""
        
        # 모델 이름 매핑
        model_map = {
            'multilingual': 'paraphrase-multilingual-MiniLM-L12-v2',
            'korean-sbert': 'jhgan/ko-sroberta-multitask',
        }
        
        actual_model = model_map.get(model_name, model_name)
        
        print(f"\n{'='*60}")
        print(f"다국어 모델 로드: {actual_model}")
        print(f"{'='*60}")
        print("※ 한국어, 영어 등 50+ 언어 지원")
        
        self.model = SentenceTransformer(actual_model)
        ###### CPU 강제
        self.model = SentenceTransformer(actual_model, device='cpu')
        
        # 더미 어휘 생성 (문장 모델은 어휘 개념이 없음)
        self.token2id = {}
        self.id2token = {}
        
        print(f"✓ 로드 완료!\n")


    def _load_english_model(self, model_name: str):
        """기존 영어 모델 로드"""
        gensim_model = self.config.MODELS[model_name]
        
        print(f"\n{'='*60}")
        print(f"영어 모델 로드: {model_name}")
        print(f"{'='*60}")
        
        self.model = api.load(gensim_model)
        self._extract_embeddings()
        
        print(f"✓ 로드 완료!\n")
    
    def _load_korean_model(self, model_name: str):
        """한국어 모델 로드 (FastText)"""
        model_info = self.config.KOREAN_MODELS[model_name]
        
        print(f"\n{'='*60}")
        print(f"한국어 모델 로드: {model_name}")
        print(f"{'='*60}")
        
        # 캐시 디렉토리
        cache_dir = Path('./models/korean/')
        cache_dir.mkdir(exist_ok=True, parents=True)
        
        cache_file = cache_dir / 'korean_fasttext.vec'
        
        # 파일이 없으면 다운로드
        if not cache_file.exists():
            print("※ 최초 실행 시 다운로드 (약 5GB, 시간 소요)")
            self._download_korean_model(model_info['url'], cache_file)
        
        # 파일에서 로드
        print("모델 파일 읽는 중...")
        self._load_from_vec_file(cache_file)
        
        print(f"✓ 한국어 모델 로드 완료!\n")
    
    def _download_korean_model(self, url: str, save_path: Path):
        """한국어 모델 다운로드"""
        print(f"다운로드 중: {url}")
        
        response = requests.get(url, stream=True)
        total_size = int(response.headers.get('content-length', 0))
        
        # .gz 파일 다운로드 및 압축 해제
        with gzip.open(response.raw, 'rb') as f_in:
            with open(save_path, 'wb') as f_out:
                f_out.write(f_in.read())
        
        print(f"✓ 다운로드 완료: {save_path}")
    
    def _load_from_vec_file(self, filepath: Path, max_words: int = 100000):
        """
        .vec 파일에서 임베딩 로드
        
        형식:
        첫 줄: vocab_size embed_dim
        이후: word val1 val2 val3 ...
        
        max_words: 메모리 절약을 위해 상위 N개만 로드
        """
        embeddings_list = []
        words = []
        
        with open(filepath, 'r', encoding='utf-8') as f:
            # 첫 줄 읽기 (vocab_size, dim)
            first_line = f.readline().strip().split()
            vocab_size = int(first_line[0])
            embed_dim = int(first_line[1])
            
            print(f"  전체 어휘: {vocab_size:,} (상위 {max_words:,}개 로드)")
            print(f"  임베딩 차원: {embed_dim}")
            
            # 단어 읽기
            for i, line in enumerate(f):
                if i >= max_words:
                    break
                
                parts = line.strip().split()
                word = parts[0]
                vector = [float(x) for x in parts[1:]]
                
                words.append(word)
                embeddings_list.append(vector)
                
                if (i + 1) % 10000 == 0:
                    print(f"  진행: {i+1:,} / {max_words:,}")
        
        # numpy 배열로 변환
        self.embeddings = np.array(embeddings_list)
        self.token2id = {word: i for i, word in enumerate(words)}
        self.id2token = {i: word for i, word in enumerate(words)}
        
        print(f"  ✓ {len(words):,}개 단어 로드 완료")


    def encode_text(self, text: str) -> np.ndarray:
        """텍스트를 벡터로 변환 (단어 or 문장)"""
        if self.is_sentence_model:
            return self.model.encode(text, convert_to_numpy=True)
        else:
            # 기존 단어 기반 모델
            if text in self.token2id:
                return self.embeddings[self.token2id[text]]
            else:
                raise KeyError(f"'{text}'는 사전에 없습니다")
            

    def _extract_embeddings(self):
        """기존 코드 (영어 모델용)"""
        vocab = list(self.model.key_to_index.keys())
        vocab_size = len(vocab)
        embed_dim = self.model.vector_size
        
        print(f"  어휘 크기: {vocab_size:,}")
        print(f"  임베딩 차원: {embed_dim}")
        
        self.embeddings = np.zeros((vocab_size, embed_dim))
        self.token2id = {}
        self.id2token = {}
        
        for idx, word in enumerate(vocab):
            self.embeddings[idx] = self.model[word]
            self.token2id[word] = idx
            self.id2token[idx] = word
    
    def get_data(self) -> Tuple[np.ndarray, Dict, Dict]:
        return self.embeddings, self.token2id, self.id2token