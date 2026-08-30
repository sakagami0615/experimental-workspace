from search import build_site_query, parse_search_results, parse_unresponsive_engines


def test_build_site_query_adds_each_allowed_domain():
    query = build_site_query(
        "hybrid search",
        ["learn.microsoft.com", "docs.aws.amazon.com"],
    )

    assert query == "hybrid search (site:learn.microsoft.com OR site:docs.aws.amazon.com)"


def test_parse_search_results_keeps_title_url_and_content():
    payload = {
        "results": [
            {
                "title": "Azure AI Search",
                "url": "https://learn.microsoft.com/a",
                "content": "summary",
            },
            {"title": "Missing URL", "content": "skip"},
        ]
    }

    results = parse_search_results(payload)

    assert len(results) == 1
    assert results[0].title == "Azure AI Search"
    assert results[0].url == "https://learn.microsoft.com/a"
    assert results[0].content == "summary"


def test_parse_unresponsive_engines_returns_engine_and_reason_pairs():
    payload = {
        "unresponsive_engines": [
            ["brave", "too many requests"],
            ["duckduckgo", "CAPTCHA"],
        ]
    }

    unresponsive = parse_unresponsive_engines(payload)

    assert unresponsive == (("brave", "too many requests"), ("duckduckgo", "CAPTCHA"))


def test_parse_unresponsive_engines_defaults_to_empty_tuple():
    assert parse_unresponsive_engines({}) == ()
