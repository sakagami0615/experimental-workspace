import numpy as np
import pandas as pd
import pytest

from database_masking.config import ColumnPolicy, MaskingConfig
from database_masking.detectors.analyzer import build_analyzer
from database_masking.masking.anonymizer import apply_column_policy
from database_masking.masking.pseudonymizer import pseudonymize

SALT = b"test-salt-0123456789"


def test_drop_removes_column():
    df = pd.DataFrame({"email": ["a@example.com"], "age": ["30"]})
    config = MaskingConfig(columns={
        "email": ColumnPolicy(action="drop"),
        "age": ColumnPolicy(action="keep"),
    })

    result = apply_column_policy(df, config, analyzer=None, salt=SALT)

    assert "email" not in result.columns
    assert result["age"].tolist() == ["30"]


def test_pseudonymize_replaces_value_deterministically():
    df = pd.DataFrame({"name": ["山田太郎", "山田太郎"]})
    config = MaskingConfig(columns={
        "name": ColumnPolicy(action="pseudonymize", entity_type="PERSON"),
    })

    result = apply_column_policy(df, config, analyzer=None, salt=SALT)

    expected = pseudonymize("山田太郎", "PERSON", SALT)
    assert result["name"].tolist() == [expected, expected]


def test_keep_leaves_value_unchanged():
    df = pd.DataFrame({"product": ["商品A"]})
    config = MaskingConfig(columns={"product": ColumnPolicy(action="keep")})

    result = apply_column_policy(df, config, analyzer=None, salt=SALT)

    assert result["product"].tolist() == ["商品A"]


def test_pseudonymize_empty_value_stays_empty():
    df = pd.DataFrame({"name": [""]})
    config = MaskingConfig(columns={
        "name": ColumnPolicy(action="pseudonymize", entity_type="PERSON"),
    })

    result = apply_column_policy(df, config, analyzer=None, salt=SALT)

    assert result["name"].tolist() == [""]


def test_pseudonymize_skips_nan_value():
    df = pd.DataFrame({"name": ["山田太郎", np.nan]})
    config = MaskingConfig(columns={
        "name": ColumnPolicy(action="pseudonymize", entity_type="PERSON"),
    })

    result = apply_column_policy(df, config, analyzer=None, salt=SALT)

    assert result["name"].iloc[0] == pseudonymize("山田太郎", "PERSON", SALT)
    assert pd.isna(result["name"].iloc[1])


@pytest.fixture(scope="module")
def analyzer():
    config = MaskingConfig(columns={}, spacy_model="ja_core_news_sm")
    return build_analyzer(config)


def test_freetext_masks_phone_number(analyzer):
    df = pd.DataFrame({"inquiry": ["090-1234-5678へ折り返し希望"]})
    config = MaskingConfig(columns={"inquiry": ColumnPolicy(action="freetext")})

    result = apply_column_policy(df, config, analyzer=analyzer, salt=SALT)

    masked = result["inquiry"].iloc[0]
    assert "090-1234-5678" not in masked
    assert "PHONE_NUMBER_" in masked
    # PHONE_NUMBER(score 0.7)とJP_POSTAL_CODE(score 0.6)が同じ範囲で重複検出されるため、
    # 重複解消ロジックにより低スコアのJP_POSTAL_CODEトークンは出力に含まれないはず
    assert "JP_POSTAL_CODE_" not in masked


def test_freetext_masks_hyphenless_phone_number_without_corruption(analyzer):
    # この環境のspaCyモデルではこの入力に対して重複検出は誘発されないが、
    # ハイフンなし電話番号のマスキングとテキスト破損がないことの確認として維持する。
    df = pd.DataFrame({"inquiry": ["09012345678へご連絡ください"]})
    config = MaskingConfig(columns={"inquiry": ColumnPolicy(action="freetext")})

    result = apply_column_policy(df, config, analyzer=analyzer, salt=SALT)

    masked = result["inquiry"].iloc[0]
    assert "09012345678" not in masked
    assert masked.endswith("へご連絡ください")
