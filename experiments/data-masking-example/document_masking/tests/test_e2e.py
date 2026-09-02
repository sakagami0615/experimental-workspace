import json

from document_masking.__main__ import main
from sample_data.generate_sample import generate_memo_text


def test_end_to_end_mask_and_verify(tmp_path):
    input_path = tmp_path / "memo.txt"
    input_path.write_text(generate_memo_text(), encoding="utf-8")

    masked_path = tmp_path / "masked.txt"
    report_path = tmp_path / "verify_report.json"
    salt_path = tmp_path / "salt.key"

    exit_code = main([
        "mask", "--input", str(input_path), "--output", str(masked_path),
        "--salt-file", str(salt_path),
    ])
    assert exit_code == 0

    masked_content = masked_path.read_text(encoding="utf-8")
    assert "田中太郎" not in masked_content
    assert "090-1234-5678" not in masked_content

    exit_code = main([
        "verify", "--input", str(masked_path), "--output", str(report_path),
    ])
    assert exit_code in (0, 1)
    data = json.loads(report_path.read_text(encoding="utf-8"))
    assert isinstance(data, list)
