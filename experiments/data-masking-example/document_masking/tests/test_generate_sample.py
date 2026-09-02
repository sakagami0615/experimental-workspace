from sample_data.generate_sample import generate_memo_text


def test_generate_memo_text_contains_name_and_phone():
    text = generate_memo_text()
    assert "田中太郎" in text or "090-1234-5678" in text
    assert len(text) > 0
