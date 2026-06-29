from app.auth import generate_password, hash_password, verify_password


def test_hash_password_verifies_original_password():
    password_hash = hash_password("correct horse battery staple")

    assert verify_password("correct horse battery staple", password_hash)


def test_hash_password_rejects_wrong_password():
    password_hash = hash_password("correct horse battery staple")

    assert not verify_password("wrong password", password_hash)


def test_hash_password_uses_unique_salts():
    first_hash = hash_password("same-password")
    second_hash = hash_password("same-password")

    assert first_hash != second_hash


def test_generate_password_returns_random_visible_secret():
    first_password = generate_password()
    second_password = generate_password()

    assert len(first_password) >= 12
    assert first_password != second_password

