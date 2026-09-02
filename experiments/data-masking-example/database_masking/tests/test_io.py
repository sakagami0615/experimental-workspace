import sqlite3

import pandas as pd
import pytest

from database_masking.io.readers import build_data_source
from database_masking.io.writers import build_data_sink


def test_csv_round_trip(tmp_path):
    path = tmp_path / "data.csv"
    df = pd.DataFrame({"name": ["山田太郎"], "age": ["30"]})

    build_data_sink(path).write(df)
    result = build_data_source(path).read()

    assert result.to_dict(orient="records") == df.to_dict(orient="records")


def test_excel_round_trip(tmp_path):
    path = tmp_path / "data.xlsx"
    df = pd.DataFrame({"name": ["山田太郎"], "age": ["30"]})

    build_data_sink(path).write(df)
    result = build_data_source(path).read()

    assert result.to_dict(orient="records") == df.to_dict(orient="records")


def test_build_data_source_rejects_unsupported_extension(tmp_path):
    path = tmp_path / "data.txt"
    path.write_text("dummy", encoding="utf-8")

    with pytest.raises(ValueError):
        build_data_source(path)


def test_build_data_sink_rejects_unsupported_extension(tmp_path):
    path = tmp_path / "data.txt"

    with pytest.raises(ValueError):
        build_data_sink(path)


def test_csv_source_creates_output_directory(tmp_path):
    path = tmp_path / "nested" / "dir" / "data.csv"
    df = pd.DataFrame({"age": ["30"]})

    build_data_sink(path).write(df)

    assert path.exists()


def test_excel_preserves_literal_na_string(tmp_path):
    xlsx_path = tmp_path / "data.xlsx"
    df = pd.DataFrame({"code": ["NA", "NULL", "normal"]})

    build_data_sink(xlsx_path).write(df)
    result = build_data_source(xlsx_path).read()

    assert result["code"].tolist() == ["NA", "NULL", "normal"]


def test_sqlite_round_trip(tmp_path):
    db_path = tmp_path / "data.db"
    df = pd.DataFrame({"name": ["山田太郎"], "age": ["30"]})

    build_data_sink(db_path, table_name="customers").write(df)
    result = build_data_source(db_path, table_name="customers").read()

    assert result.to_dict(orient="records") == df.to_dict(orient="records")


def test_build_data_source_sqlite_requires_table(tmp_path):
    db_path = tmp_path / "data.db"
    conn = sqlite3.connect(db_path)
    conn.execute("CREATE TABLE customers (name TEXT)")
    conn.commit()
    conn.close()

    with pytest.raises(ValueError):
        build_data_source(db_path)


def test_build_data_source_sqlite_rejects_invalid_table_name(tmp_path):
    db_path = tmp_path / "data.db"

    with pytest.raises(ValueError):
        build_data_source(db_path, table_name="bad; DROP TABLE customers;")


def test_build_data_sink_sqlite_requires_table(tmp_path):
    db_path = tmp_path / "data.db"

    with pytest.raises(ValueError):
        build_data_sink(db_path)


def test_sqlite_source_reads_existing_table_created_outside_tool(tmp_path):
    db_path = tmp_path / "data.db"
    conn = sqlite3.connect(db_path)
    conn.execute("CREATE TABLE customers (name TEXT, age TEXT)")
    conn.execute("INSERT INTO customers VALUES ('佐藤花子', '25')")
    conn.commit()
    conn.close()

    result = build_data_source(db_path, table_name="customers").read()

    assert result.to_dict(orient="records") == [{"name": "佐藤花子", "age": "25"}]


def test_sqlite_source_converts_null_to_empty_string_not_literal_none(tmp_path):
    db_path = tmp_path / "data.db"
    conn = sqlite3.connect(db_path)
    conn.execute("CREATE TABLE customers (name TEXT, note TEXT)")
    conn.execute("INSERT INTO customers VALUES ('田中太郎', NULL)")
    conn.execute("INSERT INTO customers VALUES ('鈴木一郎', 'None')")
    conn.commit()
    conn.close()

    result = build_data_source(db_path, table_name="customers").read()

    notes = result["note"].tolist()
    assert notes[0] == ""
    assert notes[1] == "None"
