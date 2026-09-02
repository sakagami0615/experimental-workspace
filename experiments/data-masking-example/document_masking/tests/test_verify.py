import json

import pytest

from document_masking.detectors.analyzer import build_analyzer
from document_masking.verify.report import write_report
from document_masking.verify.scanner import ResidualCandidate, scan_text


@pytest.fixture(scope="module")
def analyzer():
    return build_analyzer(spacy_model="ja_core_news_sm")


def test_scan_text_flags_residual_phone_number(analyzer):
    candidates = scan_text("090-1234-5678へ折り返し希望", analyzer)
    entity_types = {c.entity_type for c in candidates}
    assert "PHONE_NUMBER" in entity_types


def test_scan_text_no_candidates_on_clean_text(analyzer):
    assert scan_text("商品Aを購入", analyzer) == []


def test_scan_text_ignores_pseudonym_token_self_detection(analyzer):
    candidates = scan_text("CUSTOMER_ID_03df7aa8", analyzer)
    assert candidates == []


def test_write_report_json(tmp_path):
    candidates = [ResidualCandidate(entity_type="PERSON", detected_text="田中様", score=0.85)]
    output_path = tmp_path / "report.json"

    write_report(candidates, str(output_path))

    data = json.loads(output_path.read_text(encoding="utf-8"))
    assert data == [{"entity_type": "PERSON", "detected_text": "田中様", "score": 0.85}]


def test_write_report_csv(tmp_path):
    candidates = [ResidualCandidate(entity_type="PERSON", detected_text="田中様", score=0.85)]
    output_path = tmp_path / "report.csv"

    write_report(candidates, str(output_path))

    content = output_path.read_text(encoding="utf-8")
    assert "田中様" in content


def test_write_report_rejects_unsupported_extension(tmp_path):
    with pytest.raises(ValueError):
        write_report([], str(tmp_path / "report.txt"))
