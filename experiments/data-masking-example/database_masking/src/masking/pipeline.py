"""マスキング処理全体（設定読み込み〜検出〜適用〜出力）を束ねるパイプラインモジュール。"""

from pathlib import Path

import pandas as pd

from database_masking.config import MaskingConfig, load_policy
from database_masking.detectors.analyzer import build_analyzer
from database_masking.io.readers import build_data_source
from database_masking.io.writers import build_data_sink
from database_masking.masking.anonymizer import apply_column_policy
from database_masking.masking.pseudonymizer import DEFAULT_SALT_FILE, load_or_create_salt


class ColumnCoverageError(ValueError):
    """DataFrameにpolicy.yaml未定義のカラムが存在する場合に送出"""


def validate_columns_covered(df: pd.DataFrame, config: MaskingConfig) -> None:
    """DataFrameの全カラムがpolicy.yamlで定義済みであることを検証する。

    未定義のカラムがあると意図せずマスキング対象から漏れる恐れがあるため、
    未定義カラムが1つでもあれば`ColumnCoverageError`を送出する。

    Args:
        df: 検証対象のDataFrame。
        config: `columns`にカラムごとのポリシーを持つ設定。

    Raises:
        ColumnCoverageError: `df`のカラムのうち、`config.columns`に
            定義されていないものが1つでもある場合。

    Example:
        >>> import pandas as pd
        >>> from database_masking.config import MaskingConfig, ColumnPolicy
        >>> df = pd.DataFrame({"age": ["30"]})
        >>> config = MaskingConfig(columns={"age": ColumnPolicy(action="keep")})
        >>> validate_columns_covered(df, config)  # 例外が発生しなければOK

        >>> df2 = pd.DataFrame({"age": ["30"], "name": ["taro"]})
        >>> validate_columns_covered(df2, config)
        Traceback (most recent call last):
            ...
        database_masking.masking.pipeline.ColumnCoverageError: policy.yaml に定義されていないカラムがあります: ['name']
    """
    undefined = [c for c in df.columns if c not in config.columns]
    if undefined:
        raise ColumnCoverageError(
            f"policy.yaml に定義されていないカラムがあります: {undefined}"
        )


def run_mask(
    input_path: str,
    policy_path: str,
    output_path: str,
    salt_path: str | Path = DEFAULT_SALT_FILE,
    input_table: str | None = None,
    output_table: str | None = None,
) -> None:
    """入力データを読み込み、policyに基づきマスキングして出力先へ書き込む一連の処理を実行する。

    freetextアクションを含むポリシーの場合のみPII検出アナライザを構築する
    （不要な初期化コストを避けるため）。

    Args:
        input_path: マスキング対象のCSV/Excel/SQLiteファイルへのパス。
        policy_path: policy.yamlファイルへのパス。
        output_path: マスキング済みデータの出力先パス。
        salt_path: 仮名化に使うソルトファイルのパス。存在しない場合は新規生成される。
        input_table: `input_path`がSQLite（`.db`/`.sqlite`）の場合に読み込むテーブル名。
        output_table: `output_path`がSQLite（`.db`/`.sqlite`）の場合に書き込むテーブル名。

    Raises:
        ColumnCoverageError: 入力データにpolicy.yaml未定義のカラムがある場合。
        PolicyError: policy.yamlの内容が不正な場合。

    Example:
        >>> run_mask(
        ...     "sample_data/customer_raw_sample.csv",
        ...     "config/policy.example.yaml",
        ...     "output/masked.csv",
        ... )  # doctest: +SKIP
    """
    config = load_policy(policy_path)
    df = build_data_source(input_path, input_table).read()
    validate_columns_covered(df, config)

    needs_analyzer = any(p.action == "freetext" for p in config.columns.values())
    analyzer = build_analyzer(config) if needs_analyzer else None

    salt = load_or_create_salt(salt_path)
    masked_df = apply_column_policy(df, config, analyzer, salt)

    build_data_sink(output_path, output_table).write(masked_df)
