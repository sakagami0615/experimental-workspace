import trafilatura


def extract_text(html: str, max_chars: int) -> str | None:
    """Extract readable text from HTML and limit its size."""
    text = trafilatura.extract(html, include_comments=False, include_tables=False)
    if not text:
        return None
    return text[:max_chars]
