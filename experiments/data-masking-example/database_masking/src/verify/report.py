"""残存PII候補一覧をJSON/CSV形式のレポートファイルへ書き出すモジュール。"""

import csv
import json
from pathlib import Path

from database_masking.verify.scanner import ResidualCandidate

FIELDNAMES = ["row_index", "column", "entity_type", "detected_text", "score"]


def write_report(candidates: list[ResidualCandidate], output_path: str) -> None:
    """候補一覧を出力先パスの拡張子（.json/.csv）に応じた形式で書き出す。

    出力先ディレクトリが存在しない場合は自動作成する。

    Args:
        candidates: 書き出す残存PII候補のリスト。
        output_path: 出力先パス。拡張子が`.json`ならJSON、`.csv`ならCSV形式
            で書き出す。

    Raises:
        ValueError: `output_path`の拡張子が`.json`/`.csv`のいずれでもない場合。

    Example:
        >>> import tempfile, os
        >>> from database_masking.verify.scanner import ResidualCandidate
        >>> c = ResidualCandidate(
        ...     row_index=0, column="memo", entity_type="PERSON",
        ...     detected_text="山田太郎", score=0.85,
        ... )
        >>> with tempfile.TemporaryDirectory() as d:
        ...     p = os.path.join(d, "report.json")
        ...     write_report([c], p)
        ...     print(open(p, encoding="utf-8").read())
        [
          {
            "row_index": 0,
            "column": "memo",
            "entity_type": "PERSON",
            "detected_text": "山田太郎",
            "score": 0.85
          }
        ]
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
