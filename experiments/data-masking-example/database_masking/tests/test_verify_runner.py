import json

import pandas as pd

from database_masking.verify.runner import run_verify


def test_run_verify_detects_residual_and_returns_nonzero(tmp_path):
    input_path = tmp_path / "masked.csv"
    policy_path = tmp_path / "policy.yaml"
    output_path = tmp_path / "report.json"

    pd.DataFrame({"inquiry": ["090-1234-5678へ折り返し希望"]}).to_csv(input_path, index=False)
    policy_path.write_text("columns:\n  inquiry: {action: freetext}\n", encoding="utf-8")

    exit_code = run_verify(str(input_path), str(policy_path), str(output_path))

    assert exit_code == 1
    data = json.loads(output_path.read_text(encoding="utf-8"))
    assert any(c["entity_type"] == "PHONE_NUMBER" for c in data)


def test_run_verify_clean_data_returns_zero(tmp_path):
    input_path = tmp_path / "masked.csv"
    policy_path = tmp_path / "policy.yaml"
    output_path = tmp_path / "report.json"

    pd.DataFrame({"product": ["商品A"]}).to_csv(input_path, index=False)
    policy_path.write_text("columns:\n  product: {action: keep}\n", encoding="utf-8")

    exit_code = run_verify(str(input_path), str(policy_path), str(output_path))

    assert exit_code == 0
    data = json.loads(output_path.read_text(encoding="utf-8"))
    assert data == []


import sqlite3


def test_run_verify_from_sqlite_table(tmp_path):
    db_path = tmp_path / "masked.db"
    policy_path = tmp_path / "policy.yaml"
    output_path = tmp_path / "report.json"

    conn = sqlite3.connect(db_path)
    conn.execute("CREATE TABLE customers (inquiry TEXT)")
    conn.execute("INSERT INTO customers VALUES ('090-1234-5678へ折り返し希望')")
    conn.commit()
    conn.close()

    policy_path.write_text("columns:\n  inquiry: {action: freetext}\n", encoding="utf-8")

    exit_code = run_verify(str(db_path), str(policy_path), str(output_path), input_table="customers")

    assert exit_code == 1
