import json

import pandas as pd
import pytest

from database_masking.config import MaskingConfig
from database_masking.detectors.analyzer import build_analyzer
from database_masking.verify.report import write_report
from database_masking.verify.scanner import ResidualCandidate, scan_dataframe


@pytest.fixture(scope="module")
def analyzer():
    config = MaskingConfig(columns={}, spacy_model="ja_core_news_sm")
    return build_analyzer(config)


def test_scan_dataframe_flags_residual_phone_number(analyzer):
    df = pd.DataFrame({"inquiry": ["090-1234-5678へ折り返し希望"]})

    candidates = scan_dataframe(df, analyzer)

    entity_types = {c.entity_type for c in candidates}
    assert "PHONE_NUMBER" in entity_types
    assert candidates[0].row_index == 0
    assert candidates[0].column == "inquiry"


def test_scan_dataframe_no_candidates_on_clean_text(analyzer):
    df = pd.DataFrame({"product": ["商品Aを購入"]})

    candidates = scan_dataframe(df, analyzer)

    assert candidates == []


def test_scan_dataframe_skips_empty_values(analyzer):
    df = pd.DataFrame({"note": [""]})

    candidates = scan_dataframe(df, analyzer)

    assert candidates == []


def test_scan_dataframe_ignores_pseudonym_token_self_detection(analyzer):
    df = pd.DataFrame({"customer_id": ["CUSTOMER_ID_03df7aa8"]})

    candidates = scan_dataframe(df, analyzer)

    assert candidates == []


def test_scan_dataframe_still_detects_leak_adjacent_to_pseudonym_token(analyzer):
    df = pd.DataFrame({
        "inquiry": ["商品Bについて田中健一様からPERSON_70bc1374への電話がありました"],
    })

    candidates = scan_dataframe(df, analyzer)

    detected_texts = {c.detected_text for c in candidates}
    assert any("健一" in text for text in detected_texts)


def test_pseudonym_token_pattern_derived_from_entity_type_pattern():
    from database_masking.config import ENTITY_TYPE_NAME_PATTERN
    from database_masking.verify.scanner import PSEUDONYM_TOKEN_PATTERN

    assert PSEUDONYM_TOKEN_PATTERN.search("CUSTOMER_ID_03df7aa8") is not None
    assert PSEUDONYM_TOKEN_PATTERN.search("customer_id_03df7aa8") is None
    assert ENTITY_TYPE_NAME_PATTERN.match("CUSTOMER_ID") is not None


def test_write_report_json(tmp_path):
    candidates = [
        ResidualCandidate(
            row_index=0, column="inquiry", entity_type="PERSON",
            detected_text="田中様", score=0.85,
        )
    ]
    output_path = tmp_path / "report.json"

    write_report(candidates, str(output_path))

    data = json.loads(output_path.read_text(encoding="utf-8"))
    assert data == [{
        "row_index": 0,
        "column": "inquiry",
        "entity_type": "PERSON",
        "detected_text": "田中様",
        "score": 0.85,
    }]


def test_write_report_csv(tmp_path):
    candidates = [
        ResidualCandidate(
            row_index=0, column="inquiry", entity_type="PERSON",
            detected_text="田中様", score=0.85,
        )
    ]
    output_path = tmp_path / "report.csv"

    write_report(candidates, str(output_path))

    content = output_path.read_text(encoding="utf-8")
    assert "田中様" in content
    assert "PERSON" in content


def test_write_report_rejects_unsupported_extension(tmp_path):
    output_path = tmp_path / "report.txt"

    with pytest.raises(ValueError):
        write_report([], str(output_path))
