import pandas as pd
import pytest

from database_masking.config import ColumnPolicy, MaskingConfig
from database_masking.masking.pipeline import (
    ColumnCoverageError,
    run_mask,
    validate_columns_covered,
)


def test_validate_columns_covered_raises_on_undefined_column():
    df = pd.DataFrame({"name": ["x"], "email": ["y"]})
    config = MaskingConfig(columns={"name": ColumnPolicy(action="keep")})

    with pytest.raises(ColumnCoverageError):
        validate_columns_covered(df, config)


def test_validate_columns_covered_passes_when_all_defined():
    df = pd.DataFrame({"name": ["x"]})
    config = MaskingConfig(columns={"name": ColumnPolicy(action="keep")})

    validate_columns_covered(df, config)  # 例外が発生しないこと


def test_run_mask_end_to_end_without_freetext(tmp_path):
    input_path = tmp_path / "input.csv"
    policy_path = tmp_path / "policy.yaml"
    output_path = tmp_path / "output.csv"
    salt_path = tmp_path / "salt.key"

    pd.DataFrame({
        "customer_id": ["CUST-000001"],
        "email": ["taro@example.com"],
        "age": ["30"],
    }).to_csv(input_path, index=False)

    policy_path.write_text(
        "columns:\n"
        "  customer_id: {action: pseudonymize, entity_type: CUSTOMER_ID}\n"
        "  email: {action: drop}\n"
        "  age: {action: keep}\n",
        encoding="utf-8",
    )

    run_mask(str(input_path), str(policy_path), str(output_path), salt_path=salt_path)

    result = pd.read_csv(output_path, dtype=str)
    assert "email" not in result.columns
    assert result["age"].tolist() == ["30"]
    assert result["customer_id"].iloc[0].startswith("CUSTOMER_ID_")
    assert salt_path.exists()


def test_run_mask_raises_on_undefined_column(tmp_path):
    input_path = tmp_path / "input.csv"
    policy_path = tmp_path / "policy.yaml"
    output_path = tmp_path / "output.csv"
    salt_path = tmp_path / "salt.key"

    pd.DataFrame({"age": ["30"], "email": ["a@example.com"]}).to_csv(input_path, index=False)
    policy_path.write_text("columns:\n  age: {action: keep}\n", encoding="utf-8")

    with pytest.raises(ColumnCoverageError):
        run_mask(str(input_path), str(policy_path), str(output_path), salt_path=salt_path)


import sqlite3


def test_run_mask_from_sqlite_to_csv(tmp_path):
    db_path = tmp_path / "input.db"
    policy_path = tmp_path / "policy.yaml"
    output_path = tmp_path / "output.csv"
    salt_path = tmp_path / "salt.key"

    conn = sqlite3.connect(db_path)
    conn.execute("CREATE TABLE customers (customer_id TEXT, age TEXT)")
    conn.execute("INSERT INTO customers VALUES ('CUST-000001', '30')")
    conn.commit()
    conn.close()

    policy_path.write_text(
        "columns:\n"
        "  customer_id: {action: pseudonymize, entity_type: CUSTOMER_ID}\n"
        "  age: {action: keep}\n",
        encoding="utf-8",
    )

    run_mask(
        str(db_path), str(policy_path), str(output_path),
        salt_path=salt_path, input_table="customers",
    )

    result = pd.read_csv(output_path, dtype=str)
    assert result["age"].tolist() == ["30"]
    assert result["customer_id"].iloc[0].startswith("CUSTOMER_ID_")
