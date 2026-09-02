"""マスキングポリシー（policy.yaml）の読み込みと検証を担当するモジュール。"""

import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml

VALID_ACTIONS = {"drop", "pseudonymize", "keep", "freetext"}
DEFAULT_SPACY_MODEL = "ja_core_news_sm"

# entity_type の命名規約（大文字・数字・アンダースコアのみ）を定義する共有フラグメント。
# database_masking.verify.scanner の PSEUDONYM_TOKEN_PATTERN もこのフラグメントから
# 組み立てるため、単一の情報源として維持する（ENTITY_TYPE_NAME_PATTERN 単体を編集しても
# こちらを直接編集しない限りズレない）。
ENTITY_TYPE_NAME_FRAGMENT = r"[A-Z][A-Z0-9]*(?:_[A-Z0-9]+)*"
ENTITY_TYPE_NAME_PATTERN = re.compile(rf"^{ENTITY_TYPE_NAME_FRAGMENT}$")


class PolicyError(ValueError):
    """policy.yaml の内容が不正な場合に送出される例外。"""


@dataclass(frozen=True)
class ColumnPolicy:
    """1カラムに対するマスキング方針。

    Attributes:
        action: `"drop"` / `"pseudonymize"` / `"keep"` / `"freetext"` のいずれか。
        entity_type: `action="pseudonymize"` の場合に使う仮名化ラベル
            （例: `"PERSON"`）。それ以外のactionではNone。
    """

    action: str
    entity_type: str | None = None


@dataclass(frozen=True)
class CustomPattern:
    """policy.yaml の `custom_patterns` セクションで定義される、ユーザー独自の正規表現検出パターン。

    Attributes:
        entity_type: この正規表現が検出するエンティティのラベル
            （例: `"CUSTOMER_CODE"`）。命名規約は大文字・数字・アンダースコアのみ。
        regex: 検出対象にマッチさせる正規表現文字列。
    """

    entity_type: str
    regex: str


@dataclass(frozen=True)
class MaskingConfig:
    """policy.yaml をパースして得られる、マスキング処理全体の設定。

    Attributes:
        columns: カラム名をキーとした ColumnPolicy の辞書。
        custom_patterns: policy.yaml の `custom_patterns` セクションから
            構築された CustomPattern のリスト。
        spacy_model: 解析に使用するspaCyの日本語モデル名。
    """

    columns: dict[str, ColumnPolicy]
    custom_patterns: list[CustomPattern] = field(default_factory=list)
    spacy_model: str = DEFAULT_SPACY_MODEL


def load_policy(policy_path: str | Path) -> MaskingConfig:
    """policy.yaml を読み込み、内容を検証した上で MaskingConfig を構築する。

    Args:
        policy_path: policy.yaml ファイルへのパス。

    Returns:
        バリデーション済みの設定を保持する MaskingConfig。

    Raises:
        PolicyError: `columns` セクションの欠落、`action` の不正値、
            `entity_type` の命名規約違反、`custom_patterns` の不正な正規表現
            など、policy.yaml の内容が不正な場合。

    Example:
        >>> config = load_policy("config/policy.example.yaml")
        >>> config.columns["name"].action
        'pseudonymize'
    """
    raw = yaml.safe_load(Path(policy_path).read_text(encoding="utf-8"))
    if not raw or not raw.get("columns"):
        raise PolicyError(f"{policy_path}: 'columns' セクションが見つかりません")
    unknown_keys = set(raw) - {"columns", "custom_patterns", "spacy_model"}
    if unknown_keys:
        raise PolicyError(f"{policy_path}: 未対応の設定項目です: {sorted(unknown_keys)}")

    columns: dict[str, ColumnPolicy] = {}
    for name, spec in raw["columns"].items():
        spec = spec or {}
        if "action" not in spec:
            raise PolicyError(f"カラム '{name}': 'action' が指定されていません")
        action = spec["action"]
        if action not in VALID_ACTIONS:
            raise PolicyError(
                f"カラム '{name}': action '{action}' は不正です "
                f"(有効な値: {sorted(VALID_ACTIONS)})"
            )
        entity_type = spec.get("entity_type")
        if action == "pseudonymize" and not entity_type:
            raise PolicyError(
                f"カラム '{name}': action=pseudonymize には entity_type が必須です"
            )
        if entity_type and (
            not isinstance(entity_type, str) or not ENTITY_TYPE_NAME_PATTERN.match(entity_type)
        ):
            raise PolicyError(
                f"カラム '{name}': entity_type '{entity_type}' は不正です "
                f"(大文字・数字・アンダースコアのみ使用可能、例: CUSTOMER_ID)"
            )
        columns[name] = ColumnPolicy(action=action, entity_type=entity_type)

    custom_patterns: list[CustomPattern] = []
    for entry in raw.get("custom_patterns") or []:
        if not isinstance(entry, dict):
            raise PolicyError(f"custom_patterns の要素はマッピングである必要があります: {entry}")
        entity_type = entry.get("entity_type")
        regex = entry.get("regex")
        if not entity_type or not regex:
            raise PolicyError(
                f"custom_patterns の各要素には entity_type と regex が必須です: {entry}"
            )
        if not isinstance(entity_type, str) or not ENTITY_TYPE_NAME_PATTERN.match(entity_type):
            raise PolicyError(
                f"custom_patterns の entity_type '{entity_type}' は不正です "
                f"(大文字・数字・アンダースコアのみ使用可能、例: CUSTOMER_CODE)"
            )
        try:
            re.compile(regex)
        except re.error as exc:
            raise PolicyError(f"custom_patterns の regex が不正です '{regex}': {exc}") from exc
        custom_patterns.append(CustomPattern(entity_type=entity_type, regex=regex))

    return MaskingConfig(
        columns=columns,
        custom_patterns=custom_patterns,
        spacy_model=raw.get("spacy_model", DEFAULT_SPACY_MODEL),
    )
