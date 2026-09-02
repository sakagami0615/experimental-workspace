"""Presidio AnalyzerEngine の構築とテキスト解析を担当するモジュール。"""

from presidio_analyzer import AnalyzerEngine, RecognizerRegistry, RecognizerResult
from presidio_analyzer.nlp_engine import NlpEngineProvider

from document_masking.detectors.regex_recognizers import CustomPattern, build_regex_recognizers

SUPPORTED_LANGUAGE = "ja"


def build_analyzer(
    spacy_model: str = "ja_core_news_sm",
    custom_patterns: list[CustomPattern] = (),
) -> AnalyzerEngine:
    """Presidio AnalyzerEngineを構築する。

    Args:
        spacy_model: 使用するspaCy日本語モデル名。
        custom_patterns: 顧客固有の正規表現検出パターン。

    Returns:
        Regex・Presidio標準の各レコグナイザを登録済みのAnalyzerEngine。
    """
    nlp_configuration = {
        "nlp_engine_name": "spacy",
        "models": [{"lang_code": SUPPORTED_LANGUAGE, "model_name": spacy_model}],
    }
    nlp_engine = NlpEngineProvider(nlp_configuration=nlp_configuration).create_engine()

    registry = RecognizerRegistry(supported_languages=[SUPPORTED_LANGUAGE])
    registry.load_predefined_recognizers(languages=[SUPPORTED_LANGUAGE])

    for recognizer in build_regex_recognizers(list(custom_patterns)):
        registry.add_recognizer(recognizer)

    return AnalyzerEngine(nlp_engine=nlp_engine, registry=registry, supported_languages=[SUPPORTED_LANGUAGE])


def analyze_text(analyzer: AnalyzerEngine, text: str) -> list[RecognizerResult]:
    """`analyzer` を使ってテキストを解析し、検出結果のリストを返す。"""
    if not text:
        return []
    return analyzer.analyze(text=text, language=SUPPORTED_LANGUAGE)
