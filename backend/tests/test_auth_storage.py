import time
import uuid

import jwt
import pytest
from fastapi.testclient import TestClient

import auth
import storage.factory
import storage.memory
from storage.base import ScanRecord

from main import app

BAD_CODE = """import sqlite3
cur = sqlite3.connect("d.db").cursor()
uid = input("id: ")
cur.execute(f"SELECT * FROM users WHERE id = {uid}")
"""


@pytest.fixture(autouse=True)
def _reset_state(monkeypatch):
    monkeypatch.setattr(storage.factory, "_store", None)
    monkeypatch.setenv("SUPABASE_URL", "")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "")
    monkeypatch.setenv("SUPABASE_JWT_SECRET", "test-secret-0123456789abcdef0123456789abcdef")
    yield


def _token(user_id: str = "user-1") -> str:
    return jwt.encode(
        {"sub": user_id, "aud": "authenticated", "exp": int(time.time()) + 3600},
        "test-secret-0123456789abcdef0123456789abcdef",
        algorithm="HS256",
    )


def _client() -> TestClient:
    return TestClient(app)


# --- auth.verify_token ---


def test_verify_token_valid():
    token = _token()
    assert auth.verify_token(token) == "user-1"


def test_verify_token_wrong_secret():
    token = jwt.encode(
        {"sub": "u", "aud": "authenticated"}, "wrong-secret-0123456789abcdefghij", algorithm="HS256"
    )
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc:
        auth.verify_token(token)
    assert exc.value.status_code == 401


def test_verify_token_bad_audience():
    token = jwt.encode(
        {"sub": "u", "aud": "service_role", "exp": int(time.time()) + 3600},
        "test-secret-0123456789abcdef0123456789abcdef",
        algorithm="HS256",
    )
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc:
        auth.verify_token(token)
    assert exc.value.status_code == 401


# --- MemoryStore ---


def test_memory_store_crud():
    store = storage.memory.MemoryStore()
    store.save_scan("u1", "s1", "a.py", "snippet", [], 0)
    scans = store.list_scans("u1")
    assert len(scans) == 1
    assert scans[0].scan_id == "s1"
    assert scans[0].total_issues == 0

    assert store.get_scan("u1", "s1") is not None
    assert store.get_scan("u1", "nope") is None
    assert store.delete_scan("u1", "s1") is True
    assert store.delete_scan("u1", "s1") is False
    assert store.list_scans("u1") == []


def test_memory_store_isolates_users():
    store = storage.memory.MemoryStore()
    store.save_scan("u1", "s1", "a.py", "snippet", [], 0)
    assert store.list_scans("u2") == []
    assert store.get_scan("u2", "s1") is None


# --- authenticated history API ---


def test_me_requires_token():
    resp = _client().get("/me")
    assert resp.status_code == 401


def test_scan_persists_history_for_authenticated_user():
    client = _client()
    resp = client.post(
        "/scan",
        json={"filename": "x.py", "code": BAD_CODE},
        headers={"Authorization": f"Bearer {_token()}"},
    )
    assert resp.status_code == 200
    scan_id = resp.json()["scan_id"]
    assert scan_id

    scans = client.get("/scans", headers={"Authorization": f"Bearer {_token()}"}).json()
    assert scans["storage"] == "memory"
    assert any(s["scan_id"] == scan_id for s in scans["scans"])

    detail = client.get(
        f"/scans/{scan_id}", headers={"Authorization": f"Bearer {_token()}"}
    ).json()
    assert detail["filename"] == "x.py"
    assert len(detail["findings"]) == detail["total_issues"] >= 2

    deleted = client.delete(
        f"/scans/{scan_id}", headers={"Authorization": f"Bearer {_token()}"}
    )
    assert deleted.status_code == 200
    gone = client.get(
        f"/scans/{scan_id}", headers={"Authorization": f"Bearer {_token()}"}
    )
    assert gone.status_code == 404


def test_anonymous_scan_not_persisted():
    client = _client()
    resp = client.post("/scan", json={"filename": "x.py", "code": BAD_CODE})
    scan_id = resp.json()["scan_id"]
    assert scan_id
    resp = client.get("/scans", headers={"Authorization": f"Bearer {_token('anon-check')}"})
    assert resp.status_code == 200
    assert all(s["scan_id"] != scan_id for s in resp.json()["scans"])


def test_users_cannot_read_each_others_history():
    client = _client()
    client.post(
        "/scan",
        json={"filename": "x.py", "code": BAD_CODE},
        headers={"Authorization": f"Bearer {_token('alice')}"},
    )
    resp = client.get(
        "/scans", headers={"Authorization": f"Bearer {_token('bob')}"}
    )
    assert resp.status_code == 200
    assert resp.json()["scans"] == []