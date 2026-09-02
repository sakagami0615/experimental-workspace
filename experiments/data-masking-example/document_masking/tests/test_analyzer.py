import pytest

from document_masking.detectors.analyzer import analyze_text, build_analyzer


@pytest.fixture(scope="module")
def analyzer():
    return build_analyzer(spacy_model="ja_core_news_sm")


def test_analyzer_detects_person_name(analyzer):
    results = analyze_text(analyzer, "田中太郎様から問い合わせがありました")
    entity_types = {r.entity_type for r in results}
    assert "PERSON" in entity_types


def test_analyzer_detects_phone_number(analyzer):
    results = analyze_text(analyzer, "090-1234-5678へご連絡ください")
    entity_types = {r.entity_type for r in results}
    assert "PHONE_NUMBER" in entity_types


def test_analyze_text_returns_empty_list_for_empty_string(analyzer):
    assert analyze_text(analyzer, "") == []
