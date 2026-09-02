from sample_data.generate_sample import NAMES, PHONES, generate_rows


def test_generate_rows_returns_expected_columns():
    rows = generate_rows(n=3)

    assert len(rows) == 3
    assert set(rows[0].keys()) == {
        "customer_id", "name", "email", "phone", "address",
        "age", "product", "category", "inquiry", "purchase_date",
    }


def test_generate_rows_customer_id_is_unique_and_sequential():
    rows = generate_rows(n=5)

    ids = [r["customer_id"] for r in rows]
    assert ids == [f"CUST-{i:06d}" for i in range(1, 6)]


def test_generate_rows_inquiry_references_name_or_known_employee():
    rows = generate_rows(n=len(NAMES))

    for row in rows:
        assert row["name"] in row["inquiry"] or "鈴木一郎" in row["inquiry"]


def test_generate_rows_phone_values_come_from_fixed_list():
    rows = generate_rows(n=3)

    for row in rows:
        assert row["phone"] in PHONES


def test_main_also_writes_sqlite_database(tmp_path, monkeypatch):
    import sqlite3

    from sample_data import generate_sample

    csv_path = tmp_path / "customer_raw_sample.csv"
    db_path = tmp_path / "customer_raw_sample.db"
    monkeypatch.setattr(generate_sample, "OUTPUT_PATH", csv_path)
    monkeypatch.setattr(generate_sample, "DB_PATH", db_path)

    generate_sample.main()

    assert db_path.exists()
    conn = sqlite3.connect(db_path)
    try:
        cursor = conn.execute(
            "SELECT " + ", ".join(generate_sample.FIELDNAMES) + " FROM customers ORDER BY customer_id"
        )
        rows_in_db = cursor.fetchall()
    finally:
        conn.close()

    expected_rows = [
        tuple(row[name] for name in generate_sample.FIELDNAMES)
        for row in sorted(generate_sample.generate_rows(), key=lambda r: r["customer_id"])
    ]
    assert rows_in_db == expected_rows
