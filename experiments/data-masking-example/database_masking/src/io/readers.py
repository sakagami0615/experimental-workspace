"""CSV/Excel/SQLiteファイルからデータを読み込む DataSource 実装。"""

import re
import sqlite3
from pathlib import Path

import pandas as pd

from database_masking.io.base import DataSource

TABLE_NAME_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


class CsvDataSource(DataSource):
    """CSVファイルを読み込む DataSource。全列を文字列として扱う。"""

    def __init__(self, path: str | Path) -> None:
        """CsvDataSourceを初期化する。

        Args:
            path: 読み込み対象のCSVファイルへのパス。
        """
        self.path = Path(path)

    def read(self) -> pd.DataFrame:
        """CSVファイルを読み込みDataFrameとして返す（欠損値変換なし・全列str）。

        Returns:
            全列を文字列として読み込んだ DataFrame。

        Example:
            >>> df = CsvDataSource("sample_data/customer_raw_sample.csv").read()
            >>> df.shape
            (15, 10)
            >>> list(df.columns)
            ['customer_id', 'name', 'email', 'phone', 'address', 'age', 'product', 'category', 'inquiry', 'purchase_date']
        """
        return pd.read_csv(self.path, dtype=str, keep_default_na=False)


class ExcelDataSource(DataSource):
    """Excelファイルを読み込む DataSource。全列を文字列として扱う。"""

    def __init__(self, path: str | Path, sheet_name: str | int = 0) -> None:
        """ExcelDataSourceを初期化する。

        Args:
            path: 読み込み対象のExcelファイルへのパス。
            sheet_name: 読み込み対象のシート名またはシートのインデックス。
        """
        self.path = Path(path)
        self.sheet_name = sheet_name

    def read(self) -> pd.DataFrame:
        """指定シートを読み込み、欠損値を空文字に変換したDataFrameを返す。

        Returns:
            全列を文字列として読み込み、欠損値を空文字に変換した DataFrame。
        """
        df = pd.read_excel(self.path, sheet_name=self.sheet_name, dtype=str, keep_default_na=False)
        return df.fillna("")


class SqliteDataSource(DataSource):
    """SQLiteデータベースの1テーブルを読み込む DataSource。全列を文字列として扱う。

    Attributes:
        db_path: SQLiteデータベースファイルへのパス。
        table_name: 読み込み対象のテーブル名（英数字とアンダースコアのみ）。
    """

    def __init__(self, db_path: str | Path, table_name: str) -> None:
        """SqliteDataSourceを初期化する。

        Args:
            db_path: 読み込み対象のSQLiteデータベースファイルへのパス。
            table_name: 読み込み対象のテーブル名。
        """
        self.db_path = Path(db_path)
        self.table_name = table_name

    def read(self) -> pd.DataFrame:
        """テーブルの全行・全列を読み込み、文字列型のDataFrameとして返す。

        Returns:
            全列を文字列として読み込んだ DataFrame（NULLは空文字に変換）。
        """
        conn = sqlite3.connect(self.db_path)
        try:
            df = pd.read_sql_query(f"SELECT * FROM {self.table_name}", conn)
        finally:
            conn.close()
        # SQL NULLはread_sql_query経由でNone/NaNとして返る。先にfillna("")で
        # 欠損値を空文字に変換してからastype(str)する（先にastype(str)すると
        # Noneが文字列"None"になってしまい、セルの実際の値が偶然"None"だった
        # 場合と区別できなくなる。Excel読み込みで同種の問題が過去に見つかった
        # ため、同じ轍を踏まないよう順序に注意している）。
        return df.fillna("").astype(str)


def build_data_source(path: str | Path, table_name: str | None = None) -> DataSource:
    """拡張子に応じてCSV/Excel/SQLite用の DataSource を生成する。

    Args:
        path: 読み込み対象ファイルへのパス。拡張子から種別を判定する。
        table_name: SQLite（`.db`/`.sqlite`）の場合に読み込むテーブル名。
            それ以外の拡張子では無視される。

    Returns:
        拡張子に応じた DataSource（CsvDataSource / ExcelDataSource / SqliteDataSource）。

    Raises:
        ValueError: サポート対象外の拡張子、SQLiteで`table_name`未指定、
            または`table_name`が不正な識別子の場合。

    Example:
        >>> build_data_source("data.csv")
        <database_masking.io.readers.CsvDataSource object at 0x...>
        >>> build_data_source("data.txt")
        Traceback (most recent call last):
            ...
        ValueError: サポートされていない拡張子です: .txt
    """
    suffix = Path(path).suffix.lower()
    if suffix == ".csv":
        return CsvDataSource(path)
    if suffix in (".xlsx", ".xls"):
        return ExcelDataSource(path)
    if suffix in (".db", ".sqlite"):
        if not table_name:
            raise ValueError("SQLiteファイルを読み込むには table_name（CLIでは--input-table）の指定が必要です")
        if not TABLE_NAME_PATTERN.match(table_name):
            raise ValueError(f"テーブル名 '{table_name}' が不正です（英数字とアンダースコアのみ使用可能）")
        return SqliteDataSource(path, table_name)
    raise ValueError(f"サポートされていない拡張子です: {suffix}")
