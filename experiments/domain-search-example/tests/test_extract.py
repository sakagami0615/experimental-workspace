from extract import extract_text


def test_extract_text_returns_limited_main_text():
    html = "<html><body><main><h1>Title</h1><p>Body text for extraction.</p></main></body></html>"

    text = extract_text(html, max_chars=12)

    assert text == "Title\nBody t"
