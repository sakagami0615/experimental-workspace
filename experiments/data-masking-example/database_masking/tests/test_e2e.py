import csv
import json

from database_masking.__main__ import main
from sample_data.generate_sample import FIELDNAMES, NAMES, PHONES, generate_rows


def test_end_to_end_mask_and_verify(tmp_path):
    input_path = tmp_path / "customer_raw_sample.csv"
    rows = generate_rows(n=10)
    with input_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)

    policy_path = "config/policy.example.yaml"
    masked_path = tmp_path / "masked.csv"
    report_path = tmp_path / "verify_report.json"
    salt_path = tmp_path / "salt.key"

    exit_code = main([
        "mask", "--input", str(input_path), "--policy", policy_path,
        "--output", str(masked_path), "--salt-file", str(salt_path),
    ])
    assert exit_code == 0

    masked_content = masked_path.read_text(encoding="utf-8")
    header = masked_content.split("\n", 1)[0]
    assert "email" not in header
    assert "phone" not in header
    for name in NAMES:
        assert name not in masked_content
    for phone in PHONES:
        assert phone not in masked_content

    exit_code = main([
        "verify", "--input", str(masked_path), "--policy", policy_path,
        "--output", str(report_path),
    ])
    assert exit_code in (0, 1)
    data = json.loads(report_path.read_text(encoding="utf-8"))
    assert isinstance(data, list)
