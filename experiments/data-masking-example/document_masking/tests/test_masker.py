import pytest

from document_masking.detectors.analyzer import build_analyzer
from document_masking.masking.masker import mask_text, mask_file

SALT = b"test-salt-0123456789"


@pytest.fixture(scope="module")
def analyzer():
    return build_analyzer(spacy_model="ja_core_news_sm")


def test_mask_text_replaces_phone_number(analyzer):
    masked = mask_text("090-1234-5678へ折り返し希望", analyzer, SALT)
    assert "090-1234-5678" not in masked
    assert "PHONE_NUMBER_" in masked


def test_mask_text_empty_string_returns_empty(analyzer):
    assert mask_text("", analyzer, SALT) == ""


def test_mask_text_handles_overlapping_detections_without_corruption(analyzer):
    masked = mask_text("電話番号は09012345678です", analyzer, SALT)
    assert "09012345678" not in masked
    assert masked.endswith("です")


def test_mask_file_reads_and_writes_text(tmp_path, analyzer):
    input_path = tmp_path / "memo.txt"
    output_path = tmp_path / "memo_masked.txt"
    input_path.write_text("山田太郎様から090-1234-5678に連絡希望。", encoding="utf-8")

    mask_file(input_path, output_path, analyzer, SALT)

    result = output_path.read_text(encoding="utf-8")
    assert "山田太郎" not in result
    assert "090-1234-5678" not in result
    assert "PERSON_" in result
    assert "PHONE_NUMBER_" in result
