class Config:
    """전역 설정"""
    
    # 지원 모델
    MODELS = {
        'fasttext-multilingual': 'fasttext-wiki-news-subwords-300',
        'multilingual': 'multilingual' # Sentence Transformer
    }

    # 한국어 모델
    KOREAN_MODELS = {}


    # 지원 유사도 지표
    METRICS = ['cosine', 'euclidean', 'manhattan', 'dot', 'correlation']
    
    # 기본값
    DEFAULT_MODEL = 'multilingual'
    DEFAULT_METRIC = 'cosine'
    DEFAULT_TOP_K = 10
    
    # 출력 설정
    EXPORT_DIR = './results/'
    OUTPUT_DIR = './results/'  # ← 이것도 추가 (ResultExporter가 사용)
    DEFAULT_EXPORT_FORMAT = 'xlsx'
