import os
import stat

from database_masking.masking.pseudonymizer import (
    load_or_create_salt,
    normalize,
    pseudonymize,
)

SALT_A = b"salt-a-0123456789"
SALT_B = b"salt-b-9876543210"


def test_pseudonymize_is_deterministic():
    first = pseudonymize("山田太郎", "PERSON", SALT_A)
    second = pseudonymize("山田太郎", "PERSON", SALT_A)
    assert first == second


def test_pseudonymize_different_values_differ():
    a = pseudonymize("山田太郎", "PERSON", SALT_A)
    b = pseudonymize("田中花子", "PERSON", SALT_A)
    assert a != b


def test_pseudonymize_different_salt_differs():
    a = pseudonymize("山田太郎", "PERSON", SALT_A)
    b = pseudonymize("山田太郎", "PERSON", SALT_B)
    assert a != b


def test_pseudonymize_output_format():
    result = pseudonymize("山田太郎", "PERSON", SALT_A)
    assert result.startswith("PERSON_")
    assert len(result) == len("PERSON_") + 8


def test_normalize_full_width_digits_match_half_width():
    assert normalize("０９０-１２３４-５６７８") == normalize("090-1234-5678")


def test_pseudonymize_full_width_and_half_width_produce_same_token():
    a = pseudonymize("０９０-１２３４-５６７８", "PHONE_NUMBER", SALT_A)
    b = pseudonymize("090-1234-5678", "PHONE_NUMBER", SALT_A)
    assert a == b


def test_load_or_create_salt_creates_file(tmp_path):
    salt_path = tmp_path / ".secrets" / "salt.key"
    assert not salt_path.exists()

    salt = load_or_create_salt(salt_path)

    assert salt_path.exists()
    assert len(salt) == 32


def test_load_or_create_salt_is_persistent(tmp_path):
    salt_path = tmp_path / ".secrets" / "salt.key"

    first = load_or_create_salt(salt_path)
    second = load_or_create_salt(salt_path)

    assert first == second


def test_pseudonymize_output_does_not_contain_original_value():
    result = pseudonymize("山田太郎", "PERSON", SALT_A)
    assert "山田太郎" not in result


def test_load_or_create_salt_file_is_owner_only(tmp_path):
    salt_path = tmp_path / ".secrets" / "salt.key"

    load_or_create_salt(salt_path)

    mode = stat.S_IMODE(os.stat(salt_path).st_mode)
    assert mode == 0o600
