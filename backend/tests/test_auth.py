"""Auth unit tests: hashing and JWT round-trip."""

import uuid

import jwt

from app.auth import ALGORITHM, create_access_token, hash_password, verify_password
from app.config import get_settings
from app.models import User


def test_password_hash_roundtrip():
    h = hash_password("s3cret-pass")
    assert h != "s3cret-pass"
    assert verify_password("s3cret-pass", h)
    assert not verify_password("wrong", h)


def test_jwt_contains_role_and_subject():
    user = User(id=uuid.uuid4(), email="r@x.com", password_hash="h",
                full_name="R", role="recruiter")
    token = create_access_token(user)
    payload = jwt.decode(token, get_settings().secret_key, algorithms=[ALGORITHM])
    assert payload["sub"] == str(user.id)
    assert payload["role"] == "recruiter"
    assert "exp" in payload
