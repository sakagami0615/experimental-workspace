"""既知の制限を記録する回帰テスト。

ここに記載するテストは、現時点で解決されていない既知の制限を意図的に失敗させることで
記録するものです。`xfail(strict=True)` を使うため、将来この制限が解消された場合
（例: spaCyモデルを`ja_core_news_lg`に変更した等）、テストが予期せず成功（XPASS）して
CIが失敗するため、修正が見過ごされることを防ぎます。
"""
import csv

import pytest

from database_masking.__main__ import main
from sample_data.generate_sample import FIELDNAMES, generate_rows


@pytest.mark.xfail(
    strict=True,
    reason=(
        "既知のja_core_news_sm検出漏れ: 複数トークンの日本語人名のうち、仮名化トークンに"
        "直接隣接する「名」部分がPERSONとして認識されない。詳細は設計書8.1節を参照。"
        "このテストが予期せず成功した場合（例: ja_core_news_lgへの変更後）、"
        "マーカーを削除し正式なテストとして扱うこと。"
    ),
)
def test_given_name_fragment_does_not_leak_for_multi_token_name(tmp_path):
    input_path = tmp_path / "customer_raw_sample.csv"
    rows = generate_rows(n=10)
    with input_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)

    policy_path = "config/policy.example.yaml"
    masked_path = tmp_path / "masked.csv"
    salt_path = tmp_path / "salt.key"

    exit_code = main([
        "mask", "--input", str(input_path), "--policy", policy_path,
        "--output", str(masked_path), "--salt-file", str(salt_path),
    ])
    assert exit_code == 0

    masked_content = masked_path.read_text(encoding="utf-8")
    assert "健一" not in masked_content
