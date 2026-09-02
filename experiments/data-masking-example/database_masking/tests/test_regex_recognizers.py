from database_masking.config import CustomPattern
from database_masking.detectors.regex_recognizers import (
    build_custom_recognizers,
    build_jp_phone_recognizer,
    build_jp_postal_code_recognizer,
    build_regex_recognizers,
)


def test_jp_phone_recognizer_matches_mobile_format():
    recognizer = build_jp_phone_recognizer()
    results = recognizer.analyze("連絡先は090-1234-5678です", entities=["PHONE_NUMBER"])
    assert len(results) == 1
    assert results[0].entity_type == "PHONE_NUMBER"


def test_jp_phone_recognizer_matches_landline_format():
    recognizer = build_jp_phone_recognizer()
    results = recognizer.analyze("03-1234-5678へ電話", entities=["PHONE_NUMBER"])
    assert len(results) == 1


def test_jp_phone_recognizer_no_match_on_plain_text():
    recognizer = build_jp_phone_recognizer()
    results = recognizer.analyze("これは電話番号を含みません", entities=["PHONE_NUMBER"])
    assert len(results) == 0


def test_jp_postal_code_recognizer_matches():
    recognizer = build_jp_postal_code_recognizer()
    results = recognizer.analyze("〒150-0001に送付", entities=["JP_POSTAL_CODE"])
    assert len(results) == 1


def test_custom_recognizer_matches_customer_code():
    cp = CustomPattern(entity_type="CUSTOMER_CODE", regex=r"CUST-\d{6}")
    recognizers = build_custom_recognizers([cp])

    results = recognizers[0].analyze("顧客番号CUST-928172です", entities=["CUSTOMER_CODE"])

    assert len(results) == 1
    assert results[0].entity_type == "CUSTOMER_CODE"


def test_build_regex_recognizers_includes_custom_patterns():
    cp = CustomPattern(entity_type="EMPLOYEE_CODE", regex=r"EMP-\d{4}")

    recognizers = build_regex_recognizers([cp])

    entity_types = {r.supported_entities[0] for r in recognizers}
    assert {"PHONE_NUMBER", "JP_POSTAL_CODE", "EMPLOYEE_CODE"} <= entity_types
