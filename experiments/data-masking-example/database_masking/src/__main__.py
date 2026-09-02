"""database_maskingのCLIエントリポイント。`mask`/`verify`サブコマンドを提供する。"""

import argparse
import sys

from database_masking.masking.pipeline import run_mask
from database_masking.verify.runner import run_verify


def build_parser() -> argparse.ArgumentParser:
    """`mask`/`verify`の2サブコマンドを持つCLI引数パーサーを構築する。

    Returns:
        `mask`/`verify`サブコマンドを持つ`ArgumentParser`。

    Example:
        >>> parser = build_parser()
        >>> args = parser.parse_args(
        ...     ["mask", "--input", "in.csv", "--policy", "policy.yaml", "--output", "output/masked.csv"]
        ... )
        >>> args.command, args.input, args.policy, args.output, args.salt_file
        ('mask', 'in.csv', 'policy.yaml', 'output/masked.csv', '.secrets/salt.key')
    """
    parser = argparse.ArgumentParser(prog="database_masking")
    subparsers = parser.add_subparsers(dest="command", required=True)

    mask_parser = subparsers.add_parser("mask", help="データをマスキングする")
    mask_parser.add_argument("--input", required=True)
    mask_parser.add_argument("--policy", required=True)
    mask_parser.add_argument("--output", required=True)
    mask_parser.add_argument("--salt-file", default=".secrets/salt.key")
    mask_parser.add_argument("--input-table", default=None, help="入力がSQLiteの場合のテーブル名")
    mask_parser.add_argument("--output-table", default=None, help="出力がSQLiteの場合のテーブル名")

    verify_parser = subparsers.add_parser("verify", help="残存PIIを検査する")
    verify_parser.add_argument("--input", required=True)
    verify_parser.add_argument("--policy", required=True)
    verify_parser.add_argument("--output", required=True)
    verify_parser.add_argument("--input-table", default=None, help="入力がSQLiteの場合のテーブル名")

    return parser


def main(argv: list[str] | None = None) -> int:
    """CLI引数を解析し、対応するサブコマンド処理を実行して終了コードを返す。

    Args:
        argv: 解析対象のコマンドライン引数リスト。`None`の場合は
            `sys.argv`から取得する（`argparse`のデフォルト挙動）。

    Returns:
        終了コード。`mask`成功時は0、`verify`は残存PII候補の有無に応じて
        0または1を返す。

    Example:
        シェルから実行する場合:

        ```
        $ python -m database_masking mask \\
            --input sample_data/customer_raw_sample.csv \\
            --policy config/policy.example.yaml \\
            --output output/masked.csv
        $ python -m database_masking verify \\
            --input output/masked.csv \\
            --policy config/policy.example.yaml \\
            --output output/verify_report.json
        ```
    """
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "mask":
        run_mask(
            args.input, args.policy, args.output, salt_path=args.salt_file,
            input_table=args.input_table, output_table=args.output_table,
        )
        return 0
    if args.command == "verify":
        return run_verify(args.input, args.policy, args.output, input_table=args.input_table)

    parser.error(f"未知のコマンドです: {args.command}")
    return 2


if __name__ == "__main__":
    sys.exit(main())
