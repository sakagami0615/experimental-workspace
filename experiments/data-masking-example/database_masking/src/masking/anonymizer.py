"""policy.yamlのカラム単位ポリシーに基づき、DataFrameへマスキングを適用するモジュール。"""

import pandas as pd
from presidio_analyzer import AnalyzerEngine, RecognizerResult

from database_masking.config import MaskingConfig
from database_masking.detectors.analyzer import analyze_text
from database_masking.masking.pseudonymizer import pseudonymize


def apply_column_policy(
    df: pd.DataFrame,
    config: MaskingConfig,
    analyzer: AnalyzerEngine | None,
    salt: bytes,
) -> pd.DataFrame:
    """設定されたカラムポリシー（drop/pseudonymize/keep/freetext）をDataFrameの各列に適用する。

    元のDataFrameは変更せずコピーを返す。`config.columns`に定義されていない
    カラムは何もせずそのまま残る（呼び出し側で事前にカバレッジ検証する想定）。

    Args:
        df: マスキング対象のDataFrame。
        config: カラムごとのマスキング方針を持つ設定。
        analyzer: `freetext`アクションのカラムを検出するためのPresidio
            AnalyzerEngine。`freetext`カラムが存在しない場合は`None`でよい。
        salt: 仮名化に使うソルト値。

    Returns:
        カラムポリシーを適用した新しいDataFrame（元のDataFrameは変更しない）。

    Example:
        >>> import pandas as pd
        >>> from database_masking.config import MaskingConfig, ColumnPolicy
        >>> df = pd.DataFrame({"name": ["山田太郎"], "age": ["30"]})
        >>> config = MaskingConfig(columns={
        ...     "name": ColumnPolicy(action="pseudonymize", entity_type="PERSON"),
        ...     "age": ColumnPolicy(action="keep"),
        ... })
        >>> apply_column_policy(df, config, None, b"salt")
                      name age
        0  PERSON_7d88edcb  30
    """
    result = df.copy()

    for column, policy in config.columns.items():
        if column not in result.columns:
            continue

        if policy.action == "drop":
            result = result.drop(columns=[column])
        elif policy.action == "pseudonymize":
            result[column] = result[column].apply(
                lambda value: pseudonymize(value, policy.entity_type, salt)
                if value and not pd.isna(value)
                else value
            )
        elif policy.action == "keep":
            continue
        elif policy.action == "freetext":
            result[column] = result[column].apply(
                lambda value: _mask_freetext(value, analyzer, salt)
            )

    return result


def _select_non_overlapping(results: list[RecognizerResult]) -> list[RecognizerResult]:
    """検出結果同士の重複を解消し、置換に使う範囲だけを選び出す。

    検出結果は複数レイヤー（Regex/NER）が同じ文字範囲を重複検出しうる。
    文字列置換は元テキストのオフセットに基づいて行うため、重複した範囲を
    そのまま処理すると2回目以降の置換が既に置換済みの文字列を誤って
    切り出してしまう。そのためスコア降順（同点ならスパン長の降順）で
    貪欲に選び、既に選ばれた範囲と重なる検出結果は除外する。

    Args:
        results: 重複を含みうる検出結果のリスト。

    Returns:
        互いに重ならない検出結果のリスト（スコア降順の貪欲選択で決定）。

    Example:
        >>> from presidio_analyzer import RecognizerResult
        >>> results = [
        ...     RecognizerResult(entity_type="PERSON", start=0, end=4, score=0.85),
        ...     RecognizerResult(entity_type="LOCATION", start=2, end=6, score=0.6),
        ...     RecognizerResult(entity_type="PHONE_NUMBER", start=10, end=20, score=0.9),
        ... ]
        >>> [(r.entity_type, r.start, r.end) for r in _select_non_overlapping(results)]
        [('PHONE_NUMBER', 10, 20), ('PERSON', 0, 4)]
    """
    selected: list[RecognizerResult] = []
    for r in sorted(results, key=lambda r: (-r.score, -(r.end - r.start))):
        if not any(r.start < s.end and s.start < r.end for s in selected):
            selected.append(r)
    return selected


def _mask_freetext(text: str, analyzer: AnalyzerEngine | None, salt: bytes) -> str:
    """自由記述テキストをPIIエンティティ検出し、重複しない検出結果を後方から順に仮名で置換する。

    末尾側から置換することで、前方の未処理範囲のオフセットが後続の置換によって
    ずれるのを防ぐ。

    Args:
        text: マスキング対象の自由記述テキスト。
        analyzer: PII検出に使うPresidio AnalyzerEngine。
        salt: 仮名化に使うソルト値。

    Returns:
        検出されたPIIエンティティを仮名トークンに置換したテキスト。
        `text`が空の場合はそのまま返す。

    Example:
        顧客からの問い合わせ文（自由記述）を想定した例です。氏名と電話番号の
        両方が検出され、それぞれ仮名トークンに置換されます
        （`build_analyzer` で構築した実際の AnalyzerEngine で実行して得た
        本物の出力です）。

        >>> text = "山田太郎様から商品Aについて問い合わせがありました。090-1234-5678へ折り返し希望とのことです。"
        >>> _mask_freetext(text, analyzer, b"example-salt-for-docstring")  # doctest: +SKIP
        'PERSON_c742a05e様から商品Aについて問い合わせがありました。PHONE_NUMBER_23dcd604へ折り返し希望とのことです。'

        `text` が空文字の場合はanalyzerを呼び出さずそのまま返します
        （この行はanalyzer不要で実際に実行できます）:

        >>> _mask_freetext("", None, b"salt")
        ''
    """
    if not text:
        return text
    results = analyze_text(analyzer, text)
    non_overlapping = _select_non_overlapping(results)
    for r in sorted(non_overlapping, key=lambda r: r.start, reverse=True):
        original = text[r.start:r.end]
        token = pseudonymize(original, r.entity_type, salt)
        text = text[:r.start] + token + text[r.end:]
    return text
