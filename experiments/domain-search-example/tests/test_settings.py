import pytest

from settings import AppSettings


def test_rejects_empty_allowed_domains():
    with pytest.raises(ValueError, match="ALLOWED_DOMAINS"):
        AppSettings(allowed_domains="")


def test_parses_allowed_domains_from_comma_separated_value():
    settings = AppSettings(
        allowed_domains="learn.microsoft.com, docs.aws.amazon.com ",
        ollama_base_url="http://ollama.example:11434",
    )

    assert settings.allowed_domain_list == (
        "learn.microsoft.com",
        "docs.aws.amazon.com",
    )
