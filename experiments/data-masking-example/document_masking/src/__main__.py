"""document_maskingのCLIエントリポイント。`mask`/`verify`サブコマンドを提供する。"""

import argparse
import sys
from pathlib import Path

from document_masking.detectors.analyzer import build_analyzer
from document_masking.masking.masker import mask_file
from document_masking.masking.pseudonymizer import load_or_create_salt
from document_masking.verify.report import write_report
from document_masking.verify.scanner import scan_text


def build_parser() -> argparse.ArgumentParser:
    """`mask`/`verify`の2サブコマンドを持つCLI引数パーサーを構築する。"""
    parser = argparse.ArgumentParser(prog="document_masking")
    subparsers = parser.add_subparsers(dest="command", required=True)

    mask_parser = subparsers.add_parser("mask", help="ファイル全体をマスキングする")
    mask_parser.add_argument("--input", required=True, help="対象の.txt/.mdファイル")
    mask_parser.add_argument("--output", required=True)
    mask_parser.add_argument("--salt-file", default=".secrets/salt.key")
    mask_parser.add_argument("--spacy-model", default="ja_core_news_sm")

    verify_parser = subparsers.add_parser("verify", help="残存PIIを検査する")
    verify_parser.add_argument("--input", required=True, help="mask済みの.txt/.mdファイル")
    verify_parser.add_argument("--output", required=True)
    verify_parser.add_argument("--spacy-model", default="ja_core_news_sm")

    return parser


def main(argv: list[str] | None = None) -> int:
    """CLI引数を解析し、対応するサブコマンド処理を実行して終了コードを返す。

    Returns:
        終了コード。`mask`成功時は0、`verify`は残存PII候補の有無に応じて0または1。
    """
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "mask":
        analyzer = build_analyzer(spacy_model=args.spacy_model)
        salt = load_or_create_salt(args.salt_file)
        mask_file(args.input, args.output, analyzer, salt)
        return 0

    if args.command == "verify":
        analyzer = build_analyzer(spacy_model=args.spacy_model)
        text = Path(args.input).read_text(encoding="utf-8")
        candidates = scan_text(text, analyzer)
        write_report(candidates, args.output)
        return 1 if candidates else 0

    parser.error(f"未知のコマンドです: {args.command}")
    return 2


if __name__ == "__main__":
    sys.exit(main())
