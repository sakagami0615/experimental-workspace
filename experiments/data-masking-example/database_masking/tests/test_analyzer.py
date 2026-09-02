import pytest

from database_masking.config import CustomPattern, MaskingConfig
from database_masking.detectors.analyzer import analyze_text, build_analyzer


@pytest.fixture(scope="module")
def analyzer():
    config = MaskingConfig(columns={}, spacy_model="ja_core_news_sm")
    return build_analyzer(config)


def test_analyzer_detects_person_name(analyzer):
    results = analyze_text(analyzer, "田中太郎様から問い合わせがありました")
    entity_types = {r.entity_type for r in results}
    assert "PERSON" in entity_types


def test_analyzer_detects_custom_phone_pattern(analyzer):
    results = analyze_text(analyzer, "090-1234-5678へご連絡ください")
    entity_types = {r.entity_type for r in results}
    assert "PHONE_NUMBER" in entity_types


def test_analyze_text_returns_empty_list_for_empty_string(analyzer):
    assert analyze_text(analyzer, "") == []


def test_analyzer_detects_configured_custom_pattern():
    config = MaskingConfig(
        columns={},
        custom_patterns=[CustomPattern(entity_type="CUSTOMER_CODE", regex=r"CUST-\d{6}")],
        spacy_model="ja_core_news_sm",
    )
    analyzer = build_analyzer(config)

    results = analyze_text(analyzer, "顧客番号CUST-928172です")

    entity_types = {r.entity_type for r in results}
    assert "CUSTOMER_CODE" in entity_types

