import pytest
from app.auth import get_password_hash, verify_password, create_access_token, decode_access_token

def test_hash_and_verify():
    pw = "s3cret"
    hashed = get_password_hash(pw)
    assert verify_password(pw, hashed)
    assert not verify_password("wrong", hashed)

def test_jwt_token():
    token = create_access_token({"sub": "testuser"})
    payload = decode_access_token(token)
    assert payload["sub"] == "testuser"