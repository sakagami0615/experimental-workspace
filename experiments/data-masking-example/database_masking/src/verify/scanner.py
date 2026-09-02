"""マスキング済みDataFrameを再スキャンし、検出漏れした残存PII候補を洗い出すモジュール。"""

import re
from dataclasses import dataclass

import pandas as pd
from presidio_analyzer import AnalyzerEngine

from database_masking.config import ENTITY_TYPE_NAME_FRAGMENT
from database_masking.detectors.analyzer import analyze_text

# entity_type部分の命名規約は database_masking.config.ENTITY_TYPE_NAME_FRAGMENT を
# 単一の情報源として共有し、トークン全体（entity_type + "_" + 8桁16進数）にマッチする
# 形に組み立てる。
PSEUDONYM_TOKEN_PATTERN = re.compile(rf"{ENTITY_TYPE_NAME_FRAGMENT}_[0-9a-f]{{8}}")


@dataclass
class ResidualCandidate:
    """スキャンで検出された、マスキング漏れの可能性があるPII候補1件を表す。

    Attributes:
        row_index: 検出元の行インデックス（0始まり）。
        column: 検出元のカラム名。
        entity_type: 検出されたエンティティ種別（例: `"PERSON"`）。
        detected_text: 検出された文字列そのもの。
        score: 検出スコア（0.0〜1.0、高いほど確信度が高い）。
    """

    row_index: int
    column: str
    entity_type: str
    detected_text: str
    score: float

    def to_dict(self) -> dict[str, str | int | float]:
        """レポート出力（JSON/CSV）用にフィールドをdictへ変換する。

        Returns:
            `row_index`/`column`/`entity_type`/`detected_text`/`score`の
            各フィールドを持つdict。

        Example:
            >>> c = ResidualCandidate(
            ...     row_index=0, column="memo", entity_type="PERSON",
            ...     detected_text="山田太郎", score=0.85,
            ... )
            >>> c.to_dict()
            {'row_index': 0, 'column': 'memo', 'entity_type': 'PERSON', 'detected_text': '山田太郎', 'score': 0.85}
        """
        return {
            "row_index": self.row_index,
            "column": self.column,
            "entity_type": self.entity_type,
            "detected_text": self.detected_text,
            "score": self.score,
        }


def scan_dataframe(df: pd.DataFrame, analyzer: AnalyzerEngine) -> list[ResidualCandidate]:
    """DataFrame全セルをPII検出にかけ、既に仮名化済みのトークン部分を除外した残存候補を返す。

    検出結果が仮名トークン（`PSEUDONYM_TOKEN_PATTERN`）と範囲が重なる場合は
    誤検出とみなしスキップする。

    Args:
        df: スキャン対象のDataFrame（マスキング済みデータを想定）。
        analyzer: PII検出に使うPresidio AnalyzerEngine。

    Returns:
        検出された残存PII候補のリスト（仮名トークンと重なるものは除外済み）。

    Example:
        >>> import pandas as pd
        >>> from database_masking.detectors.analyzer import build_analyzer
        >>> from database_masking.config import load_policy
        >>> config = load_policy("config/policy.example.yaml")  # doctest: +SKIP
        >>> analyzer = build_analyzer(config)  # doctest: +SKIP
        >>> df = pd.DataFrame({"memo": ["連絡先は山田太郎です"]})  # doctest: +SKIP
        >>> scan_dataframe(df, analyzer)  # doctest: +SKIP
        [ResidualCandidate(row_index=0, column='memo', entity_type='PERSON', detected_text='山田太郎', score=0.85)]
    """
    candidates: list[ResidualCandidate] = []
    for column in df.columns:
        for row_index, value in df[column].items():
            if not value:
                continue
            text = str(value)
            token_spans = [
                (m.start(), m.end())
                for m in PSEUDONYM_TOKEN_PATTERN.finditer(text)
            ]
            for result in analyze_text(analyzer, text):
                if any(
                    result.start < token_end and token_start < result.end
                    for token_start, token_end in token_spans
                ):
                    continue
                candidates.append(
                    ResidualCandidate(
                        row_index=int(row_index),
                        column=column,
                        entity_type=result.entity_type,
                        detected_text=text[result.start:result.end],
                        score=result.score,
                    )
                )
    return candidates
