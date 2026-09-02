"""ダミー顧客データを生成するスクリプト。

外部通信・外部ライブラリ（Faker等）には依存せず、固定リストの組み合わせのみで
合成データを生成する。生成されるデータに実在の個人情報は含まれない。
"""

import csv
import sqlite3
from pathlib import Path

NAMES = ["山田太郎", "佐藤花子", "鈴木次郎", "田中美咲", "高橋健一"]
ADDRESSES = ["東京都渋谷区1-2-3", "大阪府大阪市北区4-5-6", "愛知県名古屋市中区7-8-9"]
PRODUCTS = ["商品A", "商品B", "商品C"]
CATEGORIES = ["家電", "衣料", "食品"]
PHONES = ["090-1234-5678", "080-2345-6789", "070-3456-7890"]
INQUIRY_TEMPLATES = [
    "{name}様から{product}について問い合わせがありました。{phone}へ折り返し希望とのことです。",
    "{name}様が{product}を購入されました。特記事項なし。",
    "担当の鈴木一郎が{name}様に{product}をご案内しました。",
]

OUTPUT_PATH = Path(__file__).parent / "customer_raw_sample.csv"
DB_PATH = Path(__file__).parent / "customer_raw_sample.db"
FIELDNAMES = [
    "customer_id", "name", "email", "phone", "address",
    "age", "product", "category", "inquiry", "purchase_date",
]


def generate_rows(n: int = 15) -> list[dict[str, str]]:
    """固定リストの組み合わせからn件分のダミー顧客レコードを生成する。

    Args:
        n: 生成するレコード件数。

    Returns:
        FIELDNAMESの各キーを持つレコード（辞書）のリスト。

    Example:
        >>> generate_rows(1)
        [{'customer_id': 'CUST-000001', 'name': '山田太郎', 'email': 'user1@example.com', 'phone': '090-1234-5678', 'address': '東京都渋谷区1-2-3', 'age': '20', 'product': '商品A', 'category': '家電', 'inquiry': '山田太郎様から商品Aについて問い合わせがありました。090-1234-5678へ折り返し希望とのことです。', 'purchase_date': '2026-01-01'}]
    """
    rows = []
    for i in range(n):
        name = NAMES[i % len(NAMES)]
        product = PRODUCTS[i % len(PRODUCTS)]
        phone = PHONES[i % len(PHONES)]
        template = INQUIRY_TEMPLATES[i % len(INQUIRY_TEMPLATES)]
        rows.append({
            "customer_id": f"CUST-{i + 1:06d}",
            "name": name,
            "email": f"user{i + 1}@example.com",
            "phone": phone,
            "address": ADDRESSES[i % len(ADDRESSES)],
            "age": str(20 + i % 40),
            "product": product,
            "category": CATEGORIES[i % len(CATEGORIES)],
            "inquiry": template.format(name=name, product=product, phone=phone),
            "purchase_date": f"2026-{(i % 12) + 1:02d}-{(i % 28) + 1:02d}",
        })
    return rows


def main() -> None:
    """サンプルデータを生成し、CSVとSQLiteデータベースの両方に書き出す。"""
    rows = generate_rows()
    with OUTPUT_PATH.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)
    print(f"生成しました: {OUTPUT_PATH} ({len(rows)}件)")

    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute("DROP TABLE IF EXISTS customers")
        columns_sql = ", ".join(f"{name} TEXT" for name in FIELDNAMES)
        conn.execute(f"CREATE TABLE customers ({columns_sql})")
        placeholders = ", ".join("?" for _ in FIELDNAMES)
        conn.executemany(
            f"INSERT INTO customers VALUES ({placeholders})",
            [tuple(row[name] for name in FIELDNAMES) for row in rows],
        )
        conn.commit()
    finally:
        conn.close()
    print(f"生成しました: {DB_PATH} (customersテーブル, {len(rows)}件)")


if __name__ == "__main__":
    main()
