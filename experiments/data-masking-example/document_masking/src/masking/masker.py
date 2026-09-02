"""ファイル全体をテキストとして読み込み、PIIエンティティを検出して仮名化するモジュール。"""

from pathlib import Path

from presidio_analyzer import AnalyzerEngine, RecognizerResult

from document_masking.detectors.analyzer import analyze_text
from document_masking.masking.pseudonymizer import pseudonymize


def _select_non_overlapping(results: list[RecognizerResult]) -> list[RecognizerResult]:
    """検出結果同士の重複を解消し、置換に使う範囲だけを選び出す。

    複数レイヤー（Regex/NER）が同じ文字範囲を重複検出しうるため、
    スコア降順（同点ならスパン長の降順）で貪欲に選び、既に選ばれた範囲と
    重なる検出結果は除外する。文字列置換はオフセットに基づくため、重複を
    放置すると2回目以降の置換が既に置換済みの文字列を誤って切り出してしまう。

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


def mask_text(text: str, analyzer: AnalyzerEngine, salt: bytes) -> str:
    """テキスト全体をPIIエンティティ検出し、重複しない検出結果を後方から順に仮名で置換する。

    末尾側から置換することで、前方の未処理範囲のオフセットが後続の置換によって
    ずれるのを防ぐ。

    Args:
        text: マスキング対象のテキスト（ファイル全体の内容を想定）。
        analyzer: PII検出に使うPresidio AnalyzerEngine。
        salt: 仮名化に使うソルト値。

    Returns:
        検出されたPIIエンティティを仮名トークンに置換したテキスト。
        `text`が空の場合はそのまま返す。

    Example:
        議事録やメモなど、ファイル全体を自由記述テキストとして扱う想定の例です。
        氏名と電話番号の両方が検出され、それぞれ仮名トークンに置換されます
        （`build_analyzer` で構築した実際の AnalyzerEngine で実行して得た
        本物の出力です）。

        >>> text = "山田太郎様から商品Aについて問い合わせがありました。090-1234-5678へ折り返し希望とのことです。"
        >>> mask_text(text, analyzer, b"example-salt-for-docstring")  # doctest: +SKIP
        'PERSON_c742a05e様から商品Aについて問い合わせがありました。PHONE_NUMBER_23dcd604へ折り返し希望とのことです。'

        `text` が空文字の場合はanalyzerを呼び出さずそのまま返します
        （この行はanalyzer不要で実際に実行できます）:

        >>> mask_text("", None, b"salt")
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


def mask_file(input_path: str | Path, output_path: str | Path, analyzer: AnalyzerEngine, salt: bytes) -> None:
    """テキストファイルを読み込み、マスキングした結果を別ファイルへ書き出す。

    出力先の親ディレクトリが存在しない場合は自動的に作成する。

    Args:
        input_path: マスキング対象の.txt/.mdファイルへのパス。
        output_path: マスキング済みテキストの出力先パス。
        analyzer: PII検出に使うPresidio AnalyzerEngine。
        salt: 仮名化に使うソルト値。
    """
    text = Path(input_path).read_text(encoding="utf-8")
    masked = mask_text(text, analyzer, salt)
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(masked, encoding="utf-8")
