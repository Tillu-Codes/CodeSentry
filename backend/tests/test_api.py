import io
import json
import zipfile

from fastapi.testclient import TestClient

from main import app

client = TestClient(app)

BAD_CODE = '''import sqlite3
cur = sqlite3.connect("d.db").cursor()
uid = input("id: ")
cur.execute(f"SELECT * FROM users WHERE id = {uid}")
'''


def _sse_events(scan_id: str) -> list[dict]:
    events = []
    with client.stream("GET", f"/scan/{scan_id}/events") as resp:
        assert resp.status_code == 200
        for line in resp.iter_lines():
            if line.startswith("data: "):
                events.append(json.loads(line[len("data: ") :]))
    return events


def test_scan_snippet_endpoint():
    resp = client.post("/scan", json={"filename": "x.py", "code": BAD_CODE})
    assert resp.status_code == 200
    job = resp.json()
    assert job["scan_id"]

    events = _sse_events(job["scan_id"])
    done = [e for e in events if e["type"] == "done"]
    assert done, "expected a done event"
    assert done[0]["total_issues"] >= 2
    assert any(f["type"] == "SQL Injection" for f in done[0]["findings"])
    assert all(
        "severity" in f and "file" in f and "line" in f for f in done[0]["findings"]
    )


def test_scan_events_stream_ends_with_done():
    resp = client.post("/scan", json={"filename": "x.py", "code": BAD_CODE})
    events = _sse_events(resp.json()["scan_id"])
    assert events[-1]["type"] == "done"
    assert events[-1]["total_issues"] >= 2


def test_scan_events_unknown_scan_404():
    resp = client.get("/scan/nope/events")
    assert resp.status_code == 404


def test_scan_repo_requires_url():
    resp = client.post("/scan/repo", json={})
    assert resp.status_code == 400
    assert "github_url" in resp.json()["detail"]


def test_scan_repo_zip_flow():
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("pkg/a.py", BAD_CODE)
        zf.writestr("pkg/b.py", "def ok():\n    return 1\n")
    resp = client.post(
        "/scan/repo/zip",
        files={"file": ("repo.zip", buf.getvalue(), "application/zip")},
    )
    assert resp.status_code == 200
    job = resp.json()
    assert job["total_files"] == 2

    resp = client.get(f"/scan/{job['scan_id']}")
    job = resp.json()
    assert job["status"] in ("queued", "running", "done")
    assert job["total_files"] == 2


def test_scan_zip_without_py_files_rejected():
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("README.md", "# nothing here")
    resp = client.post(
        "/scan/repo/zip",
        files={"file": ("repo.zip", buf.getvalue(), "application/zip")},
    )
    assert resp.status_code == 422


def test_get_unknown_scan_404():
    resp = client.get("/scan/nope")
    assert resp.status_code == 404