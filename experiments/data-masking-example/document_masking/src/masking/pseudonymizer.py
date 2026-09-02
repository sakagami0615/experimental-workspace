"""値をHMACベースの仮名（トークン）に変換する仮名化処理を提供するモジュール。"""

import hashlib
import hmac
import secrets
import unicodedata
from pathlib import Path

DEFAULT_SALT_FILE = Path(".secrets/salt.key")


def load_or_create_salt(salt_path: str | Path = DEFAULT_SALT_FILE) -> bytes:
    """ソルトファイルが存在すればその内容を読み込み、なければ新規生成して保存する。

    生成したソルトファイルはパーミッション0o600で保存される。同じソルトを
    使い続けることで同一の値は常に同じ仮名に変換される（再現性の確保）。

    Args:
        salt_path: ソルトファイルへのパス。指定しない場合は`DEFAULT_SALT_FILE`
            （`.secrets/salt.key`）が使われる。

    Returns:
        ソルトとして使う32バイトのランダムなバイト列。

    Example:
        >>> import tempfile, os
        >>> with tempfile.TemporaryDirectory() as d:
        ...     p = os.path.join(d, "salt.key")
        ...     salt1 = load_or_create_salt(p)
        ...     salt2 = load_or_create_salt(p)
        ...     len(salt1), salt1 == salt2
        (32, True)
    """
    path = Path(salt_path)
    if path.exists():
        return path.read_bytes()
    path.parent.mkdir(parents=True, exist_ok=True)
    salt = secrets.token_bytes(32)
    path.write_bytes(salt)
    path.chmod(0o600)
    return salt


def normalize(value: str) -> str:
    """Unicode正規化（NFKC）と前後の空白除去を行い、表記ゆれを吸収する。

    Args:
        value: 正規化対象の文字列。

    Returns:
        NFKC正規化し前後の空白を取り除いた文字列。

    Example:
        >>> normalize("　山田　太郎　")
        '山田 太郎'
        >>> normalize("ＡＢＣ123")
        'ABC123'
    """
    return unicodedata.normalize("NFKC", value).strip()


def pseudonymize(value: str, entity_type: str, salt: bytes) -> str:
    """値をソルト付きHMAC-SHA256でハッシュ化し、決定的な仮名トークンを生成する。

    Args:
        value: 仮名化対象の元の値。
        entity_type: 仮名トークンのラベルとして使うエンティティ種別
            （大文字英数字とアンダースコアのみ。例: `"PERSON"`）。
        salt: HMACの鍵として使うランダムなソルト値。

    Returns:
        `{entity_type}_{8桁16進数}` 形式の仮名トークン文字列。

    Example:
        >>> pseudonymize("山田太郎", "PERSON", b"fixed-salt-for-doctest")
        'PERSON_e282d2e2'
    """
    normalized = normalize(value)
    digest = hmac.new(salt, normalized.encode("utf-8"), hashlib.sha256).hexdigest()
    return f"{entity_type}_{digest[:8]}"
