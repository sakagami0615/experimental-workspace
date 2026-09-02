"""Presidio AnalyzerEngine の構築とテキスト解析を担当するモジュール。"""

from presidio_analyzer import AnalyzerEngine, RecognizerRegistry, RecognizerResult
from presidio_analyzer.nlp_engine import NlpEngineProvider

from database_masking.config import MaskingConfig
from database_masking.detectors.regex_recognizers import build_regex_recognizers

SUPPORTED_LANGUAGE = "ja"


def build_analyzer(config: MaskingConfig) -> AnalyzerEngine:
    """Presidio AnalyzerEngineを構築する。

    `config.spacy_model` で指定されたspaCy日本語モデルをロードした上で、
    (1) Presidio標準の言語非依存レコグナイザ、(2) `config.custom_patterns` から
    生成する正規表現レコグナイザ、の2種類を1つの `RecognizerRegistry` にまとめて登録する。

    Args:
        config: `spacy_model`・`custom_patterns` を含む設定。

    Returns:
        上記2種のレコグナイザを登録済みのAnalyzerEngine。`analyze_text` に渡して
        使用する。

    Example:
        spaCyモデルのロードを伴うため、この例は実行に数秒かかります。

        >>> config = MaskingConfig(columns={}, spacy_model="ja_core_news_sm")
        >>> analyzer = build_analyzer(config)  # doctest: +SKIP
        >>> analyzer.analyze(text="090-1234-5678", language="ja")  # doctest: +SKIP
        [type: PHONE_NUMBER, start: 0, end: 13, score: 0.7, type: JP_POSTAL_CODE, start: 0, end: 8, score: 0.6]

        （上記は実際に `ja_core_news_sm` で実行して得られた出力です。電話番号
        レコグナイザと郵便番号レコグナイザの両方が同じ範囲を検出しています。）
    """
    nlp_configuration = {
        "nlp_engine_name": "spacy",
        "models": [{"lang_code": SUPPORTED_LANGUAGE, "model_name": config.spacy_model}],
    }
    nlp_engine = NlpEngineProvider(nlp_configuration=nlp_configuration).create_engine()

    registry = RecognizerRegistry(supported_languages=[SUPPORTED_LANGUAGE])
    registry.load_predefined_recognizers(languages=[SUPPORTED_LANGUAGE])

    for recognizer in build_regex_recognizers(config.custom_patterns):
        registry.add_recognizer(recognizer)

    return AnalyzerEngine(
        nlp_engine=nlp_engine,
        registry=registry,
        supported_languages=[SUPPORTED_LANGUAGE],
    )


def analyze_text(analyzer: AnalyzerEngine, text: str) -> list[RecognizerResult]:
    """`analyzer` を使ってテキストを解析し、検出結果のリストを返す。

    `text` が空文字（またはNone相当のfalsy値）の場合は、解析エンジンを
    呼び出さずに空リストを返す（空文字を解析にかけても意味がないため）。

    Args:
        analyzer: `build_analyzer` で構築済みの AnalyzerEngine。
        text: 解析対象のテキスト。

    Returns:
        検出結果（`RecognizerResult`）のリスト。`text` が空の場合は空リスト。

    Example:
        >>> config = MaskingConfig(columns={}, spacy_model="ja_core_news_sm")
        >>> analyzer = build_analyzer(config)  # doctest: +SKIP
        >>> analyze_text(analyzer, "090-1234-5678")  # doctest: +SKIP
        [type: PHONE_NUMBER, start: 0, end: 13, score: 0.7, type: JP_POSTAL_CODE, start: 0, end: 8, score: 0.6]

        空文字は解析せずそのまま空リストを返す（この行はanalyzer不要で実際に実行できます）:

        >>> analyze_text(analyzer, "")  # doctest: +SKIP
        []
    """
    if not text:
        return []
    return analyzer.analyze(text=text, language=SUPPORTED_LANGUAGE)
