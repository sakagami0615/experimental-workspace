import pytest

from document_masking.__main__ import build_parser, main


def test_cli_mask_and_verify(tmp_path):
    input_path = tmp_path / "memo.txt"
    masked_path = tmp_path / "memo_masked.txt"
    report_path = tmp_path / "report.json"
    salt_path = tmp_path / "salt.key"

    input_path.write_text("山田太郎様から090-1234-5678に連絡希望。", encoding="utf-8")

    exit_code = main([
        "mask", "--input", str(input_path), "--output", str(masked_path),
        "--salt-file", str(salt_path),
    ])
    assert exit_code == 0
    assert "山田太郎" not in masked_path.read_text(encoding="utf-8")

    exit_code = main([
        "verify", "--input", str(masked_path), "--output", str(report_path),
    ])
    assert exit_code in (0, 1)
    assert report_path.exists()


def test_cli_requires_command():
    try:
        main([])
        assert False, "SystemExitが発生するはず"
    except SystemExit as exc:
        assert exc.code != 0


def test_cli_rejects_dictionary_file_option():
    parser = build_parser()

    with pytest.raises(SystemExit):
        parser.parse_args([
            "mask",
            "--input",
            "input.txt",
            "--output",
            "masked.txt",
            "--dictionary-file",
            "dictionary.csv",
        ])
