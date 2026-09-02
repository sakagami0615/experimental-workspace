"""入出力データソース／シンクの抽象基底クラスを定義するモジュール。"""

from abc import ABC, abstractmethod

import pandas as pd


class DataSource(ABC):
    """入力データソースの抽象インターフェース。

    将来DB接続（SQLAlchemy等）を実装する場合は、このインターフェースに従う。
    """

    @abstractmethod
    def read(self) -> pd.DataFrame:
        """データを読み込み、DataFrameとして返す。

        Returns:
            読み込んだデータを保持する DataFrame。
        """
        raise NotImplementedError


class DataSink(ABC):
    """出力データシンクの抽象インターフェース。

    将来DB書き込みを実装する場合は、このインターフェースに従う。
    """

    @abstractmethod
    def write(self, df: pd.DataFrame) -> None:
        """DataFrameの内容を出力先に書き込む。

        Args:
            df: 書き込み対象のデータを保持する DataFrame。
        """
        raise NotImplementedError
