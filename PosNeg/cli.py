"""
cli.py
CLI 명령어 인터페이스
"""

import click
from config.settings import Config
from models.loader import ModelLoader
from metrics.implementations import MetricFactory
from analyzers.analyzer import WordSimilarityAnalyzer
from utils.exporter import ResultExporter


@click.group()
def cli():
    """Word2Vec 단어 유사도 분석 시스템"""
    pass


# =============================================================================
# 1. search - 단어 유사도 검색
# =============================================================================

@cli.command()
@click.option('--model', '-m', default='multilingual',
              type=click.Choice(list(Config.MODELS.keys())),
              help='모델 선택')
@click.option('--metric', default='cosine',
              type=click.Choice(Config.METRICS),
              help='유사도 지표')
@click.option('--query', '-q', multiple=True, help='검색 단어')
@click.option('--input', '-i', default=None, help='엑셀/CSV 파일')
@click.option('--column', default=None, help='읽을 컬럼명')
@click.option('--top-k', '-k', default=10, help='결과 개수')
@click.option('--export', '-e', default=None, help='출력 파일')
@click.option('--format', '-f', type=click.Choice(['xlsx', 'csv']), default='xlsx')
def search(model, metric, query, input, column, top_k, export, format):
    """단어 유사도 검색"""
    
    # 입력 방식 결정
    if input:
        from utils.importer import WordImporter
        if input.endswith('.xlsx') or input.endswith('.xls'):
            queries = WordImporter.load_from_excel(input, column)
        elif input.endswith('.csv'):
            queries = WordImporter.load_from_csv(input, column)
        else:
            print("❌ .xlsx 또는 .csv 파일만 가능합니다")
            return
    elif query:
        queries = list(query)
    else:
        print("❌ -q 또는 --input 중 하나는 필수입니다")
        return
    
    # 모델 로드
    config = Config()
    loader = ModelLoader(config)
    loader.load(model)
    
    embeddings, token2id, id2token = loader.get_data()
    analyzer = WordSimilarityAnalyzer(
        embeddings, token2id, id2token, model,
        model_loader=loader
    )
    metric_obj = MetricFactory.create(metric, embeddings)
    
    # Sentence Transformer 경고
    if hasattr(loader, 'is_sentence_model') and loader.is_sentence_model:
        print("\n⚠️  Sentence Transformer 모델입니다.")
        print("   'compare-sentences' 명령어를 사용하세요.\n")
    
    # 검색 실행
    results = []
    for q in queries:
        try:
            result = analyzer.search(q, metric_obj, top_k)
            result.display()
            results.append(result)
        except KeyError as e:
            print(f"\n[오류] {q}: {e}")
    
    # 엑셀/CSV 출력
    if export and results:
        exporter = ResultExporter()
        if format == 'xlsx':
            exporter.export_to_excel(results, export)
        else:
            exporter.export_to_csv(results, export)


# =============================================================================
# 2. compare-sentences - 단어와 문장 비교
# =============================================================================

@cli.command()
@click.option('--model', '-m', default='multilingual',
              type=click.Choice(list(Config.MODELS.keys())),
              help='모델 선택')
@click.option('--metric', default='cosine',
              type=click.Choice(Config.METRICS),
              help='유사도 지표')
@click.option('--query', '-q', required=True, help='기준 단어')
@click.option('--input', '-i', required=True, help='문장 엑셀 파일')
@click.option('--column', default=None, help='문장 컬럼명')
@click.option('--export', '-e', default=None, help='출력 파일')
def compare_sentences(model, metric, query, input, column, export):
    """단어와 문장들 비교"""
    
    from utils.importer import WordImporter
    
    print(f"\n{'='*60}")
    print(f"단어-문장 유사도 분석")
    print(f"{'='*60}")
    
    # 모델 로드
    config = Config()
    loader = ModelLoader(config)
    loader.load(model)
    
    # 문장 로드
    sentences = WordImporter.load_sentences_from_excel(input, column)
    
    print(f"\n기준 단어: '{query}'")
    print(f"비교 문장 수: {len(sentences)}")
    print(f"{'='*60}\n")
    
    # Sentence Transformer 사용
    if hasattr(loader, 'is_sentence_model') and loader.is_sentence_model:
        query_vec = loader.encode_text(query)
        sentence_vecs = [loader.encode_text(sent) for sent in sentences]
        
        from sklearn.metrics.pairwise import cosine_similarity
        
        results = []
        for idx, (sent, sent_vec) in enumerate(zip(sentences, sentence_vecs), 1):
            similarity = cosine_similarity(
                query_vec.reshape(1, -1),
                sent_vec.reshape(1, -1)
            )[0][0]
            results.append((idx, sent, float(similarity), []))
        
        results.sort(key=lambda x: x[2], reverse=True)
        
    else:
        # 기존 단어 기반 방식
        from utils.document_processor import DocumentProcessor
        embeddings, token2id, id2token = loader.get_data()
        
        doc_processor = DocumentProcessor(embeddings, token2id)
        metric_obj = MetricFactory.create(metric, embeddings)
        
        try:
            results = doc_processor.compare_word_with_sentences(
                query, sentences, metric_obj
            )
        except KeyError as e:
            print(f"\n❌ 오류: {e}")
            return
    
    # 콘솔 출력
    print(f"{'='*70}")
    print(f"결과: '{query}'와 문장 유사도")
    print(f"{'='*70}")
    
    for rank, (idx, sentence, score, words) in enumerate(results, 1):
        preview = sentence[:50] + "..." if len(sentence) > 50 else sentence
        bar_len = int(score * 40) if score > 0 else 0
        bar = '█' * bar_len
        
        print(f"\n{rank:2d}. [문장 {idx}] 유사도: {score:.4f} {bar}")
        print(f"    {preview}")
        if words:
            print(f"    인식된 단어: {', '.join(words[:10])}")
    
    # 엑셀 출력
    if export:
        _export_sentence_results(query, model, metric, results, export)


# =============================================================================
# 3. analogy - 단어 유추
# =============================================================================

@cli.command()
@click.option('--model', '-m', default='multilingual',
              type=click.Choice(list(Config.MODELS.keys())))
@click.option('--metric', default='cosine',
              type=click.Choice(Config.METRICS))
@click.option('--a', required=True, help='단어 A')
@click.option('--b', required=True, help='단어 B')
@click.option('--c', required=True, help='단어 C')
@click.option('--top-k', '-k', default=5)
@click.option('--export', '-e', default=None)
def analogy(model, metric, a, b, c, top_k, export):
    """단어 유추: A - B + C = ?"""
    
    config = Config()
    loader = ModelLoader(config)
    loader.load(model)
    
    embeddings, token2id, id2token = loader.get_data()
    analyzer = WordSimilarityAnalyzer(embeddings, token2id, id2token, model)
    metric_obj = MetricFactory.create(metric, embeddings)
    
    result = analyzer.analogy(a, b, c, metric_obj, top_k)
    result.display()
    
    if export:
        exporter = ResultExporter()
        exporter.export_to_excel(result, export)


# =============================================================================
# 4. list-models - 모델 목록
# =============================================================================

@cli.command()
def list_models():
    """사용 가능한 모델 목록"""
    print("\n사용 가능한 모델:")
    print("="*60)
    for key in Config.MODELS.keys():
        print(f"  - {key}")
    print()


# =============================================================================
# 5. list-metrics - 지표 목록
# =============================================================================

@cli.command()
def list_metrics():
    """사용 가능한 유사도 지표"""
    print("\n사용 가능한 유사도 지표:")
    print("="*60)
    for metric in Config.METRICS:
        print(f"  - {metric}")
    print()


# =============================================================================
# 헬퍼 함수
# =============================================================================

def _export_sentence_results(query, model, metric, results, filename):
    """문장 비교 결과를 엑셀로 저장"""
    import pandas as pd
    from pathlib import Path
    
    output_dir = Path(Config.OUTPUT_DIR)
    output_dir.mkdir(exist_ok=True, parents=True)
    filepath = output_dir / filename
    
    data = {
        'Query': [query] * len(results),
        'Model': [model] * len(results),
        'Metric': [metric] * len(results),
        'Rank': list(range(1, len(results) + 1)),
        'Sentence_Index': [idx for idx, _, _, _ in results],
        'Sentence': [sent for _, sent, _, _ in results],
        'Similarity_Score': [score for _, _, score, _ in results],
        'Recognized_Words': [', '.join(words) for _, _, _, words in results]
    }
    
    df = pd.DataFrame(data)
    df.to_excel(filepath, index=False, sheet_name='Results')
    
    print(f"\n✓ 엑셀 파일 저장: {filepath}")


if __name__ == '__main__':
    cli()