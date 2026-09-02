from allowlist import is_allowed_url


def test_allows_exact_domain():
    assert is_allowed_url(
        "https://learn.microsoft.com/en-us/azure/search/",
        ["learn.microsoft.com"],
    )


def test_allows_subdomain_of_allowed_domain():
    assert is_allowed_url(
        "https://docs.learn.microsoft.com/path",
        ["learn.microsoft.com"],
    )


def test_rejects_lookalike_domain():
    assert not is_allowed_url(
        "https://learn.microsoft.com.evil.example/path",
        ["learn.microsoft.com"],
    )


def test_rejects_urls_without_http_scheme():
    assert not is_allowed_url(
        "file:///etc/passwd",
        ["learn.microsoft.com"],
    )
