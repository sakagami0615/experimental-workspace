"""日本の電話番号・郵便番号およびユーザー定義パターン向けの正規表現レコグナイザを構築するモジュール。"""

from presidio_analyzer import Pattern, PatternRecognizer

from database_masking.config import CustomPattern

JP_PHONE_REGEX = r"0\d{1,4}-\d{1,4}-\d{3,4}"
JP_POSTAL_CODE_REGEX = r"\d{3}-\d{4}"


def build_jp_phone_recognizer() -> PatternRecognizer:
    """日本の電話番号を検出する PatternRecognizer（PHONE_NUMBER）を生成する。

    Returns:
        `PHONE_NUMBER`エンティティを検出する PatternRecognizer。

    Example:
        >>> recognizer = build_jp_phone_recognizer()
        >>> recognizer.analyze("連絡先は090-1234-5678です", entities=["PHONE_NUMBER"])
        [type: PHONE_NUMBER, start: 4, end: 17, score: 0.7]
    """
    pattern = Pattern(name="jp_phone", regex=JP_PHONE_REGEX, score=0.7)
    return PatternRecognizer(
        supported_entity="PHONE_NUMBER",
        patterns=[pattern],
        supported_language="ja",
    )


def build_jp_postal_code_recognizer() -> PatternRecognizer:
    """日本の郵便番号を検出する PatternRecognizer（JP_POSTAL_CODE）を生成する。

    Returns:
        `JP_POSTAL_CODE`エンティティを検出する PatternRecognizer。

    Example:
        >>> recognizer = build_jp_postal_code_recognizer()
        >>> recognizer.analyze("郵便番号150-0001です", entities=["JP_POSTAL_CODE"])
        [type: JP_POSTAL_CODE, start: 4, end: 12, score: 0.6]
    """
    # 郵便番号(\d{3}-\d{4})は電話番号の一部と桁数が重なるケースがあるが、
    # 検出漏れを避ける多層防御の観点から意図的に許容している。
    pattern = Pattern(name="jp_postal_code", regex=JP_POSTAL_CODE_REGEX, score=0.6)
    return PatternRecognizer(
        supported_entity="JP_POSTAL_CODE",
        patterns=[pattern],
        supported_language="ja",
    )


def build_custom_recognizers(custom_patterns: list[CustomPattern]) -> list[PatternRecognizer]:
    """policy.yaml で定義された CustomPattern 群から PatternRecognizer のリストを生成する。

    Args:
        custom_patterns: policy.yaml の `custom_patterns` セクションから
            構築された CustomPattern のリスト。

    Returns:
        各 CustomPattern に対応する PatternRecognizer のリスト
        （`custom_patterns`が空なら空リスト）。

    Example:
        >>> from database_masking.config import CustomPattern
        >>> patterns = [CustomPattern(entity_type="CUSTOMER_CODE", regex=r"CUST-\\d{6}")]
        >>> recognizers = build_custom_recognizers(patterns)
        >>> recognizers[0].analyze("CUST-000001の顧客", entities=["CUSTOMER_CODE"])
        [type: CUSTOMER_CODE, start: 0, end: 11, score: 0.8]
    """
    recognizers = []
    for cp in custom_patterns:
        pattern = Pattern(name=f"custom_{cp.entity_type}", regex=cp.regex, score=0.8)
        recognizers.append(
            PatternRecognizer(
                supported_entity=cp.entity_type,
                patterns=[pattern],
                supported_language="ja",
            )
        )
    return recognizers


def build_regex_recognizers(
    custom_patterns: list[CustomPattern] = (),
) -> list[PatternRecognizer]:
    """電話番号・郵便番号・カスタムパターンの正規表現レコグナイザを全てまとめて生成する。

    Args:
        custom_patterns: policy.yaml の `custom_patterns` セクションから
            構築された CustomPattern のリスト。省略時は空。

    Returns:
        電話番号用・郵便番号用・カスタムパターン用の PatternRecognizer を
        まとめたリスト（先頭2件が電話番号・郵便番号、以降がカスタムパターン）。

    Example:
        >>> recognizers = build_regex_recognizers()
        >>> [r.supported_entities for r in recognizers]
        [['PHONE_NUMBER'], ['JP_POSTAL_CODE']]
    """
    return [
        build_jp_phone_recognizer(),
        build_jp_postal_code_recognizer(),
        *build_custom_recognizers(list(custom_patterns)),
    ]
