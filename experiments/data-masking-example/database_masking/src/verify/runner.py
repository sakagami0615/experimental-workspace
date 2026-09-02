"""verifyコマンドのエントリポイント。データ読み込みからスキャン・レポート出力までを実行する。"""

from database_masking.config import load_policy
from database_masking.detectors.analyzer import build_analyzer
from database_masking.io.readers import build_data_source
from database_masking.verify.report import write_report
from database_masking.verify.scanner import scan_dataframe


def run_verify(
    input_path: str,
    policy_path: str,
    output_path: str,
    input_table: str | None = None,
) -> int:
    """入力データをスキャンして残存PIIレポートを出力し、検出有無を終了コードとして返す。

    戻り値は候補が1件以上あれば1、なければ0（CIでの検知に利用できるよう
    シェルの終了コード相当の値にしている）。

    Args:
        input_path: スキャン対象のCSV/Excel/SQLiteファイルへのパス
            （マスキング済みデータを想定）。
        policy_path: policy.yamlファイルへのパス。
        output_path: 残存PIIレポートの出力先パス（.json/.csv）。
        input_table: `input_path`がSQLite（`.db`/`.sqlite`）の場合に読み込むテーブル名。

    Returns:
        残存PII候補が1件以上あれば1、なければ0。

    Example:
        >>> run_verify(
        ...     "output/masked.csv",
        ...     "config/policy.example.yaml",
        ...     "output/verify_report.json",
        ... )  # doctest: +SKIP
        0
    """
    config = load_policy(policy_path)
    analyzer = build_analyzer(config)
    df = build_data_source(input_path, input_table).read()

    candidates = scan_dataframe(df, analyzer)
    write_report(candidates, output_path)

    return 1 if candidates else 0
