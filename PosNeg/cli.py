"""
cli.py
CLI 명령어 인터페이스
"""

import click
import time
import logging
from tqdm import tqdm
from config.settings import Config
from models.loader import ModelLoader
from metrics.implementations import MetricFactory
from analyzers.analyzer import WordSimilarityAnalyzer
from utils.exporter import ResultExporter

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('analysis.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


@click.group()
def cli():
    """Word2Vec 단어 유사도 분석 시스템"""
    pass


# =============================================================================
# 1. search - 단어 유사도 검색
# =============================================================================

@cli.command()
@click.option('--model', '-m', default='multilingual',
              type=click.Choice(list(Config.MODELS.keys())))
@click.option('--metric', default='cosine',
              type=click.Choice(Config.METRICS))
@click.option('--query', '-q', multiple=True, help='검색 단어')
@click.option('--input', '-i', default=None, help='엑셀/CSV 파일')
@click.option('--column', default=None, help='읽을 컬럼명')
@click.option('--top-k', '-k', default=10, help='결과 개수')
@click.option('--export', '-e', default=None, help='출력 파일')
@click.option('--format', '-f', type=click.Choice(['xlsx', 'csv']), default='xlsx')
def search(model, metric, query, input, column, top_k, export, format):
    """단어 유사도 검색"""
    
    start_time = time.time()
    logger.info(f"검색 시작 - 모델: {model}, 지표: {metric}")
    
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
    for q in tqdm(queries, desc="검색 중", unit="단어"):
        try:
            result = analyzer.search(q, metric_obj, top_k)
            result.display()
            results.append(result)
        except KeyError as e:
            logger.error(f"{q}: {e}")
            print(f"\n[오류] {q}: {e}")
    
    # 엑셀/CSV 출력
    if export and results:
        exporter = ResultExporter()
        if format == 'xlsx':
            exporter.export_to_excel(results, export)
        else:
            exporter.export_to_csv(results, export)
    
    elapsed = time.time() - start_time
    logger.info(f"검색 완료 - 소요시간: {elapsed:.2f}초")
    print(f"\n✓ 처리 완료! 소요 시간: {elapsed:.2f}초\n")


# =============================================================================
# 2. compare-sentences - 단어와 문장 비교
# =============================================================================

@cli.command()
@click.option('--model', '-m', default='multilingual',
              type=click.Choice(list(Config.MODELS.keys())))
@click.option('--metric', default='cosine',
              type=click.Choice(Config.METRICS))
@click.option('--query', '-q', required=True, help='기준 단어')
@click.option('--input', '-i', required=True, help='문장 엑셀 파일')
@click.option('--column', default=None, help='문장 컬럼명')
@click.option('--export', '-e', default=None, help='출력 파일')
def compare_sentences(model, metric, query, input, column, export):
    """단어와 문장들 비교"""
    
    from utils.importer import WordImporter
    
    start_time = time.time()
    logger.info(f"문장 비교 시작 - 쿼리: {query}, 모델: {model}")
    
    print(f"\n{'='*60}")
    print(f"단어-문장 유사도 분석")
    print(f"{'='*60}")
    
    # 모델 로드
    config = Config()
    loader = ModelLoader(config)
    loader.load(model)
    
    # 문장 로드
    sentences = WordImporter.load_sentences_from_excel(input, column)
    logger.info(f"{len(sentences)}개 문장 로드 완료")
    
    print(f"\n기준 단어: '{query}'")
    print(f"비교 문장 수: {len(sentences)}")
    print(f"{'='*60}\n")
    
    # Sentence Transformer 사용
    if hasattr(loader, 'is_sentence_model') and loader.is_sentence_model:
        print("벡터 변환 중...")
        query_vec = loader.encode_text(query)
        
        sentence_vecs = []
        for sent in tqdm(sentences, desc="문장 처리", unit="문장"):
            sentence_vecs.append(loader.encode_text(sent))
        
        from sklearn.metrics.pairwise import cosine_similarity
        
        results = []
        print("\n유사도 계산 중...")
        for idx, (sent, sent_vec) in enumerate(tqdm(
            zip(sentences, sentence_vecs),
            total=len(sentences),
            desc="유사도 계산",
            unit="문장"
        ), 1):
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
            logger.error(f"오류 발생: {e}")
            print(f"\n❌ 오류: {e}")
            return
    
    # 콘솔 출력
    print(f"\n{'='*70}")
    print(f"결과: '{query}'와 문장 유사도")
    print(f"{'='*70}")
    
    for rank, (idx, sentence, score, words) in enumerate(results[:10], 1):
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
    
    elapsed = time.time() - start_time
    logger.info(f"문장 비교 완료 - 소요시간: {elapsed:.2f}초")
    print(f"\n{'='*70}")
    print(f"✓ 처리 완료! 소요 시간: {elapsed:.2f}초")
    print(f"{'='*70}\n")


# =============================================================================
# 3. analogy - 단어 유추
# =============================================================================

@cli.command()
@click.option('--model', '-m', default='multilingual',
              type=click.Choice(list(Config.MODELS.keys())))
@click.option('--metric', default='cosine',
              type=click.Choice(Config.METRICS))
@click.option('--a', required=True)
@click.option('--b', required=True)
@click.option('--c', required=True)
@click.option('--top-k', '-k', default=5)
@click.option('--export', '-e', default=None)
def analogy(model, metric, a, b, c, top_k, export):
    """단어 유추: A - B + C = ?"""
    
    logger.info(f"단어 유추: {a} - {b} + {c}")
    
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
# 4. list-models
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
# 5. list-metrics
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
    
    logger.info(f"엑셀 저장: {filepath}")
    print(f"\n✓ 엑셀 파일 저장: {filepath}")

import os
import re
import pandas as pd
from pandas import ExcelWriter

def _sanitize_sheet_name(name: str) -> str:
    # Excel sheet name: max 31 chars, no []:*?/\
    name = re.sub(r'[\[\]\:\*\?\/\\]', '_', str(name))
    return name[:31] if len(name) > 31 else name

def _unique_sheet_name(writer: ExcelWriter, base: str) -> str:
    base = _sanitize_sheet_name(base) or "Sheet"
    existing = set(writer.book.sheetnames) if hasattr(writer, "book") else set()
    if base not in existing:
        return base
    i = 2
    while True:
        candidate = _sanitize_sheet_name(f"{base}_{i}")[:31]
        if candidate not in existing:
            return candidate
        i += 1

def _export_sentence_results(query: str, model: str, metric: str, results, export: str):
    """
    results: iterable of dict-like rows, e.g. [{'rank':1,'text':'...', 'score':0.71}, ...]
    export : path to excel file (one file, many sheets)
    """
    df = pd.DataFrame(results)
    df.index += 1  # 보기 좋게 1-base
    df.insert(0, "query", query)
    df.insert(1, "model", model)
    df.insert(2, "metric", metric)

    # 파일 유무에 따라 모드/옵션 분기
    file_exists = os.path.exists(export)
    mode = "a" if file_exists else "w"

    # openpyxl 엔진 강제 (xlsx)
    writer_kwargs = dict(engine="openpyxl", mode=mode)

    # append 모드에서만 사용할 수 있는 옵션
    if file_exists:
        writer_kwargs["if_sheet_exists"] = "replace"

    # 시트명은 쿼리로, 길고 특수문자 많으면 정리
    base_sheet = _sanitize_sheet_name(query) or "result"
    try:
        with pd.ExcelWriter(export, **writer_kwargs) as writer:
            # append 모드에서는 기존 시트 목록을 보고 고유 시트명 보장
            sheet_name = (
                _unique_sheet_name(writer, base_sheet)
                if file_exists else base_sheet
            )
            df.to_excel(writer, sheet_name=sheet_name, index=False)
    except PermissionError:
        # 엑셀이 열려 있는 경우 흔한 이슈
        raise SystemExit(
            f"엑셀 파일이 열려 있습니다: {export}\n파일을 닫고 다시 실행하세요."
        )




if __name__ == '__main__':
    cli()