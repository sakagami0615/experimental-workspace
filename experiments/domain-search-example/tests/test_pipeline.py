from pipeline import (
    NO_SOURCES_MESSAGE,
    build_engines_blocked_message,
    build_follow_up_questions,
)


def test_build_follow_up_questions_returns_three_domain_search_prompts():
    follow_ups = build_follow_up_questions("Azure AI Search の料金を教えて")

    assert follow_ups == [
        "この内容の前提条件を詳しく確認してください",
        "根拠URLごとの差分を比較してください",
        "関連する制限事項や注意点を確認してください",
    ]


def test_no_sources_message_is_user_facing():
    assert NO_SOURCES_MESSAGE == "指定されたWebサイトからは確認できません。"


def test_build_engines_blocked_message_lists_engine_and_reason():
    message = build_engines_blocked_message(
        [("brave", "too many requests"), ("duckduckgo", "CAPTCHA")]
    )

    assert "brave: too many requests" in message
    assert "duckduckgo: CAPTCHA" in message
    assert "しばらく時間をおいてから再度お試しください。" in message
