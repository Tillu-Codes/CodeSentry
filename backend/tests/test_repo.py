import io
import zipfile

import pytest

from repo.github_loader import (
    GitHubURLError,
    GithubRepo,
    build_raw_url,
    parse_github_url,
)
from repo.scanner import JOBS, run_scan_job, scan_files
from repo.zip_loader import extract_zip_python_files


def test_parse_github_url_simple():
    assert parse_github_url("https://github.com/octocat/Hello-World") == (
        "octocat",
        "Hello-World",
        None,
    )


def test_parse_github_url_with_branch():
    assert parse_github_url("https://github.com/octocat/Hello-World/tree/main") == (
        "octocat",
        "Hello-World",
        "main",
    )


def test_parse_github_url_git_ssh_and_git_suffix():
    assert parse_github_url("git@github.com:octocat/Hello-World.git") == (
        "octocat",
        "Hello-World",
        None,
    )


def test_parse_github_url_https_git_suffix_and_trailing_slash():
    assert parse_github_url("https://github.com/octocat/Hello-World.git") == (
        "octocat",
        "Hello-World",
        None,
    )
    assert parse_github_url("https://github.com/octocat/Hello-World/") == (
        "octocat",
        "Hello-World",
        None,
    )


def test_parse_github_url_branch_with_git_suffix_and_slash():
    assert parse_github_url("https://github.com/octocat/Hello-World.git/tree/develop/") == (
        "octocat",
        "Hello-World",
        "develop",
    )


def test_parse_github_url_naked_owner_repo():
    assert parse_github_url("github.com/octocat/Hello-World") == (
        "octocat",
        "Hello-World",
        None,
    )


def test_parse_github_url_www_and_http():
    assert parse_github_url("http://www.github.com/octocat/Hello-World") == (
        "octocat",
        "Hello-World",
        None,
    )


def test_parse_github_url_invalid():
    with pytest.raises(GitHubURLError):
        parse_github_url("not-a-url")
    with pytest.raises(GitHubURLError):
        parse_github_url("")


def test_build_raw_url():
    gh = GithubRepo(owner="octocat", repo="Hello", branch="main", paths=[])
    assert (
        build_raw_url(gh, "pkg/util.py")
        == "https://raw.githubusercontent.com/octocat/Hello/main/pkg/util.py"
    )


def test_extract_zip_python_files():
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("app/main.py", "cur.execute(f'SELECT * FROM t WHERE id = {x}')")
        zf.writestr("app/README.md", "not python")
        zf.writestr("__MACOSX/app/._main.py", "junk")
    files = extract_zip_python_files(buf.getvalue())
    assert list(files) == ["app/main.py"]


def test_extract_zip_python_files_bad_zip():
    assert extract_zip_python_files(b"not a zip") == {}


def test_scan_files_aggregates():
    files = {
        "a.py": 'import sqlite3\ncur = sqlite3.connect("d.db").cursor()\nuid = input("id: ")\ncur.execute(f"SELECT * FROM u WHERE id = {uid}")\n',
        "b.py": "def f(x):\n    return x + 1\n",
    }
    findings, per_file = scan_files(files, enrich=False, llm_missed_issues=False)
    assert {p.file for p in per_file} == {"a.py", "b.py"}
    assert per_file[0].total_issues >= 1
    assert any(f.type == "SQL Injection" for f in findings)
    assert findings[0].file == "a.py"


def test_run_scan_job_lifecycle():
    scan_id = "test-job-1"
    from models import ScanJob

    JOBS[scan_id] = ScanJob(scan_id=scan_id, status="queued", total_files=1)
    run_scan_job(scan_id, {"x.py": "x = 1\n"}, enrich=False, llm_missed_issues=False)
    job = JOBS[scan_id]
    assert job.status == "done"
    assert job.scanned_files == 1
    assert job.total_issues == job.risk_score == 0
    JOBS.pop(scan_id, None)