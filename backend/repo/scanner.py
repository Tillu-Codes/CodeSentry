import queue
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

from models import FileResult, Finding, ScanJob
from pipeline import (
    SEVERITY_RANK,
    analyze_code,
    compute_risk_score,
    dedupe,
    drop_ai_duplicates,
)
from repo.github_loader import GithubRepo, fetch_raw_github_file
from storage.factory import get_store

JOBS: dict[str, ScanJob] = {}
SCAN_EVENTS: dict[str, queue.Queue] = {}
_LOCK = threading.Lock()
_SCAN_WORKERS = 6
_FETCH_WORKERS = 8


def subscribe(scan_id: str) -> queue.Queue:
    q: queue.Queue = queue.Queue()
    with _LOCK:
        SCAN_EVENTS[scan_id] = q
    return q


def unsubscribe(scan_id: str) -> None:
    with _LOCK:
        SCAN_EVENTS.pop(scan_id, None)


def emit(scan_id: str, event: dict) -> None:
    """Push an event to the scan's SSE subscribers (no-op if nobody is listening)."""
    q = SCAN_EVENTS.get(scan_id)
    if q is not None:
        q.put(event)


def _sort_findings(findings: list[Finding]) -> list[Finding]:
    findings = drop_ai_duplicates(dedupe(findings))
    findings.sort(key=lambda f: (SEVERITY_RANK[f.severity], f.line))
    return findings


def scan_files(
    files: dict[str, str],
    enrich: bool = True,
    llm_missed_issues: bool = True,
    on_progress=None,
    on_file_done=None,
) -> tuple[list[Finding], list[FileResult]]:
    """Run the full pipeline over every file, in parallel, aggregating results."""
    findings_by_file: dict[str, list[Finding]] = {}
    per_file: list[FileResult] = []
    done = 0
    total = len(files)
    with ThreadPoolExecutor(max_workers=_SCAN_WORKERS) as pool:
        future_map = {
            pool.submit(analyze_code, code, path, enrich, llm_missed_issues): path
            for path, code in files.items()
        }
        for future in as_completed(future_map):
            path = future_map[future]
            try:
                file_findings = future.result()
            except Exception:
                file_findings = []
            findings_by_file[path] = file_findings
            per_file.append(FileResult(file=path, total_issues=len(file_findings)))
            done += 1
            if on_progress:
                on_progress(done)
            if on_file_done:
                on_file_done(path, file_findings, done, total)
    per_file.sort(key=lambda p: p.file)
    findings = [f for path in sorted(files) for f in findings_by_file.get(path, [])]
    return _sort_findings(findings), per_file


def _fetch_github_files(gh: GithubRepo, on_progress=None) -> dict[str, str]:
    files: dict[str, str] = {}
    with ThreadPoolExecutor(max_workers=_FETCH_WORKERS) as pool:
        for i, (path, code) in enumerate(
            pool.map(lambda p: (p, fetch_raw_github_file(gh, p)), gh.paths),
            start=1,
        ):
            if code:
                files[path] = code
            if on_progress:
                on_progress(i)
    return files


def run_scan_job(
    scan_id: str,
    files: dict[str, str],
    enrich: bool,
    llm_missed_issues: bool,
    user_id: str | None = None,
    label: str = "",
    source_type: str = "snippet",
) -> None:
    job = JOBS.get(scan_id)
    if not job:
        return
    job.status = "running"
    emit(scan_id, {"type": "status", "status": "running", "total": len(files)})
    _by_file: dict[str, list[Finding]] = {}

    def on_file_done(path: str, file_findings: list[Finding], done: int, total: int) -> None:
        _by_file[path] = file_findings
        agg = _sort_findings([f for lst in _by_file.values() for f in lst])
        with _LOCK:
            job.findings = agg
            job.scanned_files = done
            job.total_issues = len(agg)
            job.risk_score = compute_risk_score(agg)
        emit(scan_id, {"type": "progress", "scanned": done, "total": total})
        emit(
            scan_id,
            {
                "type": "file",
                "file": path,
                "findings": [f.model_dump() for f in file_findings],
            },
        )

    try:
        findings, per_file = scan_files(
            files,
            enrich,
            llm_missed_issues,
            on_progress=lambda n: _set(job, scanned_files=n),
            on_file_done=on_file_done,
        )
        with _LOCK:
            job.findings = findings
            job.per_file = per_file
            job.total_issues = len(findings)
            job.risk_score = compute_risk_score(findings)
            job.scanned_files = len(per_file)
            job.status = "done"
        if user_id:
            get_store().save_scan(
                user_id=user_id,
                scan_id=scan_id,
                filename=label,
                source_type=source_type,
                findings=findings,
                risk_score=job.risk_score,
            )
        emit(
            scan_id,
            {
                "type": "done",
                "status": "done",
                "scan_id": scan_id,
                "filename": label,
                "total_files": len(files),
                "total_issues": len(findings),
                "risk_score": job.risk_score,
                "findings": [f.model_dump() for f in findings],
            },
        )
    except Exception as exc:
        with _LOCK:
            job.status = "failed"
            job.error = str(exc)
        emit(scan_id, {"type": "failed", "status": "failed", "error": str(exc)})


def run_github_job(
    scan_id: str,
    gh: GithubRepo,
    enrich: bool,
    llm_missed_issues: bool,
    user_id: str | None = None,
    label: str = "",
) -> None:
    job = JOBS.get(scan_id)
    if not job:
        return
    job.status = "running"
    emit(scan_id, {"type": "status", "status": "running"})
    try:
        files = _fetch_github_files(gh, on_progress=lambda n: _set(job, scanned_files=n))
        run_scan_job(
            scan_id, files, enrich, llm_missed_issues, user_id=user_id, label=label, source_type="repo"
        )
    except Exception as exc:
        with _LOCK:
            job.status = "failed"
            job.error = str(exc)
        emit(scan_id, {"type": "failed", "status": "failed", "error": str(exc)})


def _set(job: ScanJob, **kwargs) -> None:
    with _LOCK:
        for key, value in kwargs.items():
            setattr(job, key, value)