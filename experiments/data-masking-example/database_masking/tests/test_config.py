import pytest

from database_masking.config import PolicyError, load_policy


def test_load_policy_valid(tmp_path):
    policy_path = tmp_path / "policy.yaml"
    policy_path.write_text(
        """
columns:
  customer_id: {action: pseudonymize, entity_type: CUSTOMER_ID}
  age: {action: keep}
custom_patterns:
  - entity_type: CUSTOMER_CODE
    regex: 'CUST-\\d{6}'
spacy_model: ja_core_news_sm
""",
        encoding="utf-8",
    )

    config = load_policy(policy_path)

    assert config.columns["customer_id"].action == "pseudonymize"
    assert config.columns["customer_id"].entity_type == "CUSTOMER_ID"
    assert config.columns["age"].action == "keep"
    assert config.custom_patterns[0].entity_type == "CUSTOMER_CODE"
    assert config.custom_patterns[0].regex == "CUST-\\d{6}"
    assert config.spacy_model == "ja_core_news_sm"


def test_load_policy_rejects_dictionary_file(tmp_path):
    policy_path = tmp_path / "policy.yaml"
    policy_path.write_text(
        """
columns:
  age: {action: keep}
dictionary_file: config/custom_dictionary.csv
""",
        encoding="utf-8",
    )

    with pytest.raises(PolicyError):
        load_policy(policy_path)


def test_load_policy_defaults_spacy_model(tmp_path):
    policy_path = tmp_path / "policy.yaml"
    policy_path.write_text("columns:\n  age: {action: keep}\n", encoding="utf-8")

    config = load_policy(policy_path)

    assert config.spacy_model == "ja_core_news_sm"
    assert config.custom_patterns == []


def test_load_policy_missing_action(tmp_path):
    policy_path = tmp_path / "policy.yaml"
    policy_path.write_text("columns:\n  age: {}\n", encoding="utf-8")

    with pytest.raises(PolicyError):
        load_policy(policy_path)


def test_load_policy_invalid_action_value(tmp_path):
    policy_path = tmp_path / "policy.yaml"
    policy_path.write_text("columns:\n  age: {action: delete}\n", encoding="utf-8")

    with pytest.raises(PolicyError):
        load_policy(policy_path)


def test_load_policy_pseudonymize_without_entity_type(tmp_path):
    policy_path = tmp_path / "policy.yaml"
    policy_path.write_text("columns:\n  name: {action: pseudonymize}\n", encoding="utf-8")

    with pytest.raises(PolicyError):
        load_policy(policy_path)


def test_load_policy_invalid_regex(tmp_path):
    policy_path = tmp_path / "policy.yaml"
    policy_path.write_text(
        """
columns:
  age: {action: keep}
custom_patterns:
  - entity_type: BAD
    regex: '[unclosed'
""",
        encoding="utf-8",
    )

    with pytest.raises(PolicyError):
        load_policy(policy_path)


def test_load_policy_missing_columns_section(tmp_path):
    policy_path = tmp_path / "policy.yaml"
    policy_path.write_text("custom_patterns: []\n", encoding="utf-8")

    with pytest.raises(PolicyError):
        load_policy(policy_path)


def test_load_policy_null_columns_section(tmp_path):
    policy_path = tmp_path / "policy.yaml"
    policy_path.write_text("columns:\n", encoding="utf-8")

    with pytest.raises(PolicyError):
        load_policy(policy_path)


def test_load_policy_custom_pattern_not_a_mapping(tmp_path):
    policy_path = tmp_path / "policy.yaml"
    policy_path.write_text(
        """
columns:
  age: {action: keep}
custom_patterns:
  - just_a_string
""",
        encoding="utf-8",
    )

    with pytest.raises(PolicyError):
        load_policy(policy_path)


def test_load_policy_rejects_lowercase_entity_type(tmp_path):
    policy_path = tmp_path / "policy.yaml"
    policy_path.write_text(
        "columns:\n  name: {action: pseudonymize, entity_type: employee_code}\n",
        encoding="utf-8",
    )

    with pytest.raises(PolicyError):
        load_policy(policy_path)


def test_load_policy_rejects_lowercase_custom_pattern_entity_type(tmp_path):
    policy_path = tmp_path / "policy.yaml"
    policy_path.write_text(
        """
columns:
  age: {action: keep}
custom_patterns:
  - entity_type: customer_code
    regex: 'CUST-\\d{6}'
""",
        encoding="utf-8",
    )

    with pytest.raises(PolicyError):
        load_policy(policy_path)


def test_load_policy_rejects_non_string_entity_type(tmp_path):
    policy_path = tmp_path / "policy.yaml"
    policy_path.write_text(
        "columns:\n  name: {action: pseudonymize, entity_type: 123}\n",
        encoding="utf-8",
    )

    with pytest.raises(PolicyError):
        load_policy(policy_path)


def test_load_policy_rejects_non_string_custom_pattern_entity_type(tmp_path):
    policy_path = tmp_path / "policy.yaml"
    policy_path.write_text(
        """
columns:
  age: {action: keep}
custom_patterns:
  - entity_type: 456
    regex: 'CUST-\\d{6}'
""",
        encoding="utf-8",
    )

    with pytest.raises(PolicyError):
        load_policy(policy_path)
