import pandas as pd

from database_masking.__main__ import main


def test_cli_mask_and_verify(tmp_path):
    input_path = tmp_path / "input.csv"
    policy_path = tmp_path / "policy.yaml"
    masked_path = tmp_path / "masked.csv"
    report_path = tmp_path / "report.json"
    salt_path = tmp_path / "salt.key"

    pd.DataFrame({"age": ["30"]}).to_csv(input_path, index=False)
    policy_path.write_text("columns:\n  age: {action: keep}\n", encoding="utf-8")

    exit_code = main([
        "mask", "--input", str(input_path), "--policy", str(policy_path),
        "--output", str(masked_path), "--salt-file", str(salt_path),
    ])
    assert exit_code == 0
    assert masked_path.exists()

    exit_code = main([
        "verify", "--input", str(masked_path), "--policy", str(policy_path),
        "--output", str(report_path),
    ])
    assert exit_code == 0
    assert report_path.exists()


def test_cli_requires_command():
    try:
        main([])
        assert False, "SystemExitが発生するはず"
    except SystemExit as exc:
        assert exc.code != 0


def test_cli_mask_from_sqlite_with_table_options(tmp_path):
    import sqlite3

    db_path = tmp_path / "input.db"
    policy_path = tmp_path / "policy.yaml"
    output_path = tmp_path / "output.csv"
    salt_path = tmp_path / "salt.key"

    conn = sqlite3.connect(db_path)
    conn.execute("CREATE TABLE customers (age TEXT)")
    conn.execute("INSERT INTO customers VALUES ('30')")
    conn.commit()
    conn.close()

    policy_path.write_text("columns:\n  age: {action: keep}\n", encoding="utf-8")

    exit_code = main([
        "mask", "--input", str(db_path), "--policy", str(policy_path),
        "--output", str(output_path), "--salt-file", str(salt_path),
        "--input-table", "customers",
    ])
    assert exit_code == 0
    assert output_path.exists()
