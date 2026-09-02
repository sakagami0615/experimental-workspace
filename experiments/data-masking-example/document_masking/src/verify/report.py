"""残存PII候補をCSV/JSONレポートとして出力するモジュール。"""

import csv
import json
from pathlib import Path

from document_masking.verify.scanner import ResidualCandidate

FIELDNAMES = ["entity_type", "detected_text", "score"]


def write_report(candidates: list[ResidualCandidate], output_path: str) -> None:
    """残存PII候補のリストをCSVまたはJSONファイルへ書き出す。

    Args:
        candidates: 書き出す残存PII候補のリスト。
        output_path: 出力先パス。拡張子`.csv`/`.json`で形式を判定する。

    Raises:
        ValueError: サポート対象外の拡張子が指定された場合。
    """
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    suffix = path.suffix.lower()

    if suffix == ".json":
        path.write_text(
            json.dumps([c.to_dict() for c in candidates], ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    elif suffix == ".csv":
        with path.open("w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
            writer.writeheader()
            for c in candidates:
                writer.writerow(c.to_dict())
    else:
        raise ValueError(f"サポートされていないレポート形式です: {suffix}")
