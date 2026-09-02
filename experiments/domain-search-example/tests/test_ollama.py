from ollama import Source, build_answer_prompt


def test_build_answer_prompt_contains_sources_and_safety_rule():
    prompt = build_answer_prompt(
        "What is hybrid search?",
        [
            Source(
                url="https://learn.microsoft.com/a",
                title="Doc",
                text="Hybrid search combines methods.",
            )
        ],
    )

    assert "提供されたSourcesだけを根拠として回答してください" in prompt
    assert "https://learn.microsoft.com/a" in prompt
    assert "Hybrid search combines methods." in prompt
