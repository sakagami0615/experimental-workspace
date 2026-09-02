"""日本の電話番号・郵便番号およびユーザー定義パターン向けの正規表現レコグナイザを構築するモジュール。"""

from dataclasses import dataclass

from presidio_analyzer import Pattern, PatternRecognizer

JP_PHONE_REGEX = r"0\d{1,4}-\d{1,4}-\d{3,4}"
JP_POSTAL_CODE_REGEX = r"\d{3}-\d{4}"


@dataclass(frozen=True)
class CustomPattern:
    """document_masking用の顧客固有正規表現パターン。

    Attributes:
        entity_type: この正規表現が検出するエンティティのラベル（例: "CUSTOMER_CODE"）。
        regex: 検出対象にマッチさせる正規表現文字列。
    """

    entity_type: str
    regex: str


def build_jp_phone_recognizer() -> PatternRecognizer:
    """日本の電話番号を検出する PatternRecognizer（PHONE_NUMBER）を生成する。"""
    pattern = Pattern(name="jp_phone", regex=JP_PHONE_REGEX, score=0.7)
    return PatternRecognizer(supported_entity="PHONE_NUMBER", patterns=[pattern], supported_language="ja")


def build_jp_postal_code_recognizer() -> PatternRecognizer:
    """日本の郵便番号を検出する PatternRecognizer（JP_POSTAL_CODE）を生成する。"""
    # 郵便番号(\d{3}-\d{4})は電話番号の一部と桁数が重なるケースがあるが、
    # 検出漏れを避ける多層防御の観点から意図的に許容している。
    pattern = Pattern(name="jp_postal_code", regex=JP_POSTAL_CODE_REGEX, score=0.6)
    return PatternRecognizer(supported_entity="JP_POSTAL_CODE", patterns=[pattern], supported_language="ja")


def build_custom_recognizers(custom_patterns: list[CustomPattern]) -> list[PatternRecognizer]:
    """CustomPattern のリストから PatternRecognizer のリストを生成する。"""
    recognizers = []
    for cp in custom_patterns:
        pattern = Pattern(name=f"custom_{cp.entity_type}", regex=cp.regex, score=0.8)
        recognizers.append(
            PatternRecognizer(supported_entity=cp.entity_type, patterns=[pattern], supported_language="ja")
        )
    return recognizers


def build_regex_recognizers(custom_patterns: list[CustomPattern] = ()) -> list[PatternRecognizer]:
    """電話番号・郵便番号・カスタムパターンの正規表現レコグナイザを全てまとめて生成する。"""
    return [
        build_jp_phone_recognizer(),
        build_jp_postal_code_recognizer(),
        *build_custom_recognizers(list(custom_patterns)),
    ]
