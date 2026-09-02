"""CSV/Excel/SQLiteファイルへデータを書き出す DataSink 実装。"""

import sqlite3
from pathlib import Path

import pandas as pd

from database_masking.io.base import DataSink
from database_masking.io.readers import TABLE_NAME_PATTERN


class CsvDataSink(DataSink):
    """CSVファイルへ書き出す DataSink。"""

    def __init__(self, path: str | Path) -> None:
        """CsvDataSinkを初期化する。

        Args:
            path: 書き出し先のCSVファイルへのパス。
        """
        self.path = Path(path)

    def write(self, df: pd.DataFrame) -> None:
        """出力先ディレクトリを作成した上でDataFrameをCSVとして書き出す。

        Args:
            df: 書き込み対象のデータを保持する DataFrame。

        Example:
            >>> import pandas as pd
            >>> sink = CsvDataSink("/tmp/example_out.csv")
            >>> sink.write(pd.DataFrame({"a": ["1", "2"]}))
            >>> print(Path("/tmp/example_out.csv").read_text(encoding="utf-8"))
            a
            1
            2
            <BLANKLINE>
        """
        self.path.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(self.path, index=False)


class ExcelDataSink(DataSink):
    """Excelファイルへ書き出す DataSink。"""

    def __init__(self, path: str | Path, sheet_name: str = "Sheet1") -> None:
        """ExcelDataSinkを初期化する。

        Args:
            path: 書き出し先のExcelファイルへのパス。
            sheet_name: 書き出し先のシート名。
        """
        self.path = Path(path)
        self.sheet_name = sheet_name

    def write(self, df: pd.DataFrame) -> None:
        """出力先ディレクトリを作成した上でDataFrameをExcelとして書き出す。

        Args:
            df: 書き込み対象のデータを保持する DataFrame。
        """
        self.path.parent.mkdir(parents=True, exist_ok=True)
        df.to_excel(self.path, sheet_name=self.sheet_name, index=False)


class SqliteDataSink(DataSink):
    """SQLiteデータベースの1テーブルへ書き出す DataSink。

    Attributes:
        db_path: SQLiteデータベースファイルへのパス（存在しなければ新規作成）。
        table_name: 書き込み先のテーブル名（英数字とアンダースコアのみ）。
    """

    def __init__(self, db_path: str | Path, table_name: str) -> None:
        """SqliteDataSinkを初期化する。

        Args:
            db_path: 書き出し先のSQLiteデータベースファイルへのパス。
            table_name: 書き込み先のテーブル名。
        """
        self.db_path = Path(db_path)
        self.table_name = table_name

    def write(self, df: pd.DataFrame) -> None:
        """テーブルが既に存在する場合は置き換えて書き込む。

        Args:
            df: 書き込み対象のデータを保持する DataFrame。
        """
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        try:
            df.to_sql(self.table_name, conn, if_exists="replace", index=False)
        finally:
            conn.close()


def build_data_sink(path: str | Path, table_name: str | None = None) -> DataSink:
    """拡張子に応じてCSV/Excel/SQLite用の DataSink を生成する。

    Args:
        path: 書き出し先ファイルへのパス。拡張子から種別を判定する。
        table_name: SQLite（`.db`/`.sqlite`）の場合に書き込むテーブル名。
            それ以外の拡張子では無視される。

    Returns:
        拡張子に応じた DataSink（CsvDataSink / ExcelDataSink / SqliteDataSink）。

    Raises:
        ValueError: サポート対象外の拡張子、SQLiteで`table_name`未指定、
            または`table_name`が不正な識別子の場合。

    Example:
        >>> build_data_sink("out.csv")
        <database_masking.io.writers.CsvDataSink object at 0x...>
        >>> build_data_sink("out.txt")
        Traceback (most recent call last):
            ...
        ValueError: サポートされていない拡張子です: .txt
    """
    suffix = Path(path).suffix.lower()
    if suffix == ".csv":
        return CsvDataSink(path)
    if suffix in (".xlsx", ".xls"):
        return ExcelDataSink(path)
    if suffix in (".db", ".sqlite"):
        if not table_name:
            raise ValueError("SQLiteファイルへ書き込むには table_name（CLIでは--output-table）の指定が必要です")
        if not TABLE_NAME_PATTERN.match(table_name):
            raise ValueError(f"テーブル名 '{table_name}' が不正です（英数字とアンダースコアのみ使用可能）")
        return SqliteDataSink(path, table_name)
    raise ValueError(f"サポートされていない拡張子です: {suffix}")
