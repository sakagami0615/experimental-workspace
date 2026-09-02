"""マスキング済みテキストを再スキャンし、検出漏れした残存PII候補を洗い出すモジュール。"""

import re
from dataclasses import dataclass

from presidio_analyzer import AnalyzerEngine

from document_masking.detectors.analyzer import analyze_text

# entity_type は大文字英数字とアンダースコアのみで構成される命名規約に従う
# （document_masking.masking.pseudonymizer が生成する仮名トークンと同じ規約）。
PSEUDONYM_TOKEN_PATTERN = re.compile(r"[A-Z][A-Z0-9]*(?:_[A-Z0-9]+)*_[0-9a-f]{8}")


@dataclass
class ResidualCandidate:
    """スキャンで検出された、マスキング漏れの可能性があるPII候補1件を表す。

    Attributes:
        entity_type: 検出されたエンティティ種別（例: "PERSON"）。
        detected_text: 検出された文字列そのもの。
        score: 検出スコア（0.0〜1.0、高いほど確信度が高い）。
    """

    entity_type: str
    detected_text: str
    score: float

    def to_dict(self) -> dict[str, str | float]:
        """レポート出力（JSON/CSV）用にフィールドをdictへ変換する。"""
        return {
            "entity_type": self.entity_type,
            "detected_text": self.detected_text,
            "score": self.score,
        }


def scan_text(text: str, analyzer: AnalyzerEngine) -> list[ResidualCandidate]:
    """テキスト全体をPII検出にかけ、仮名化トークン自身を除外した残存候補を返す。

    Args:
        text: スキャン対象のテキスト（マスキング済みファイルの内容を想定）。
        analyzer: PII検出に使うPresidio AnalyzerEngine。

    Returns:
        残存PII候補（`ResidualCandidate`）のリスト。
    """
    if not text:
        return []
    token_spans = [(m.start(), m.end()) for m in PSEUDONYM_TOKEN_PATTERN.finditer(text)]
    candidates: list[ResidualCandidate] = []
    for result in analyze_text(analyzer, text):
        if any(result.start < end and start < result.end for start, end in token_spans):
            continue
        candidates.append(
            ResidualCandidate(
                entity_type=result.entity_type,
                detected_text=text[result.start:result.end],
                score=result.score,
            )
        )
    return candidates
