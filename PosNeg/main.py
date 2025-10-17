"""
메인 실행 파일

사용 예시:
# CLI
python main.py search -q "king" -m glove-100 --metric cosine -k 10 -e result.xlsx

# 함수
from main import analyze
result = analyze("king", model="glove-100", metric="cosine", top_k=10, export="result.xlsx")
"""

from config.settings import Config
from models.loader import ModelLoader
from metrics.implementations import MetricFactory
from analyzers.analyzer import WordSimilarityAnalyzer
from utils.exporter import ResultExporter


class WordSimilaritySystem:
    """통합 시스템"""
    
    def __init__(self):
        self.config = Config()
        self.loader = None
        self.analyzer = None
        self.current_model = None
        self.exporter = ResultExporter()
    
    def setup(self, model: str = None):
        """초기화"""
        model = model or self.config.DEFAULT_MODEL
        
        self.loader = ModelLoader(self.config)
        self.loader.load(model)
        
        embeddings, token2id, id2token = self.loader.get_data()
        self.analyzer = WordSimilarityAnalyzer(embeddings, token2id, id2token, model)
        self.current_model = model
    
    def search(
        self,
        query: str,
        metric: str = None,
        top_k: int = None,
        display: bool = True,
        export: str = None
    ):
        """검색"""
        metric = metric or self.config.DEFAULT_METRIC
        top_k = top_k or self.config.DEFAULT_TOP_K
        
        metric_obj = MetricFactory.create(metric, self.analyzer.embeddings)
        result = self.analyzer.search(query, metric_obj, top_k)
        
        if display:
            result.display()
        
        if export:
            self.exporter.export_to_excel(result, export)
        
        return result


# 한 줄 실행 함수
_system = None

def analyze(
    query: str,
    model: str = 'fasttext-multilingual',
    metric: str = 'cosine',
    top_k: int = 10,
    export: str = None
):
    """
    한 줄로 실행
    
    예:
        result = analyze("king", model="glove-100", metric="cosine", 
                        top_k=10, export="result.xlsx")
    """
    global _system
    
    if _system is None or _system.current_model != model:
        _system = WordSimilaritySystem()
        _system.setup(model)
    
    return _system.search(query, metric, top_k, display=True, export=export)


# main.py 맨 아래에 추가

def analyze_from_file(
    input_file: str,
    model: str = 'fasttext-multilingual',
    metric: str = 'cosine',
    top_k: int = 10,
    export: str = None,
    column: str = None
):
    """
    엑셀/CSV 파일에서 단어를 읽어서 분석
    
    예시:
        analyze_from_file("words.xlsx", export="result.xlsx")
        analyze_from_file("words.csv", column="단어", export="result.xlsx")
    """
    from utils.importer import WordImporter
    
    # 파일에서 단어 로드
    if input_file.endswith('.xlsx') or input_file.endswith('.xls'):
        queries = WordImporter.load_from_excel(input_file, column)
    elif input_file.endswith('.csv'):
        queries = WordImporter.load_from_csv(input_file, column)
    else:
        raise ValueError("지원하지 않는 파일 형식")
    
    # 시스템 초기화
    global _system
    if _system is None or _system.current_model != model:
        _system = WordSimilaritySystem()
        _system.setup(model)
    
    # 검색 실행
    metric_obj = MetricFactory.create(metric, _system.analyzer.embeddings)
    results = []
    
    for query in queries:
        try:
            result = _system.analyzer.search(query, metric_obj, top_k)
            result.display()
            results.append(result)
        except KeyError as e:
            print(f"\n[오류] {query}: {e}")
    
    # 엑셀 출력
    if export and results:
        _system.exporter.export_to_excel(results, export)
    
    return results




# main.py 맨 아래에 추가

def compare_with_sentences(
    query_word: str,
    input_file: str,
    model: str = 'fasttext-multilingual',
    metric: str = 'cosine',
    export: str = None,
    column: str = None
):
    """
    Python 함수로 단어-문장 비교
    
    예시:
        results = compare_with_sentences(
            query_word="negative",
            input_file="sentences.xlsx",
            export="result.xlsx"
        )
    """
    from utils.importer import WordImporter
    from utils.document_processor import DocumentProcessor
    
    # 시스템 초기화
    global _system
    if _system is None or _system.current_model != model:
        _system = WordSimilaritySystem()
        _system.setup(model)
    
    # 문장 로드
    sentences = WordImporter.load_sentences_from_excel(input_file, column)
    
    # 문서 처리기
    doc_processor = DocumentProcessor(
        _system.analyzer.embeddings,
        _system.analyzer.token2id
    )
    
    metric_obj = MetricFactory.create(metric, _system.analyzer.embeddings)
    
    # 비교 실행
    results = doc_processor.compare_word_with_sentences(
        query_word, sentences, metric_obj
    )
    
    # 결과 출력
    print(f"\n{'='*60}")
    print(f"'{query_word}'와 문장 유사도 분석")
    print(f"{'='*60}\n")
    
    for rank, (idx, sentence, score, words) in enumerate(results[:10], 1):
        preview = sentence[:60] + "..." if len(sentence) > 60 else sentence
        print(f"{rank:2d}. [{idx}] {score:.4f} - {preview}")
    
    # 엑셀 출력
    if export:
        from cli import _export_sentence_results
        _export_sentence_results(query_word, model, metric, results, export)
    
    return results



if __name__ == '__main__':
    from cli import cli
    cli()