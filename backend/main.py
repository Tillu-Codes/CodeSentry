import asyncio
import json
import os
import queue
from uuid import uuid4

from dotenv import load_dotenv
from fastapi import BackgroundTasks, Depends, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

load_dotenv()

from auth import is_auth_enabled, optional_user, require_user
from models import (
    Finding,
    RepoScanRequest,
    ScanJob,
    ScanListResponse,
    ScanRequest,
    ScanResponse,
)
from pipeline import analyze_code, compute_risk_score
from repo.github_loader import GitHubURLError, load_github_repo
from repo.scanner import (
    JOBS,
    SCAN_EVENTS,
    run_github_job,
    run_scan_job,
    subscribe,
    unsubscribe,
)
from repo.zip_loader import extract_zip_python_files
from storage.base import ScanRecord
from storage.factory import get_store, storage_name

app = FastAPI(
    title="CodeSentry",
    description="Python bug & security scanner: deterministic rules + pluggable LLM enrichment, "
    "for snippets, GitHub repos and zip archives.",
    version="0.7.0",
)


def _cors_origins() -> list[str]:
    raw = os.getenv("CORS_ORIGINS", "").strip()
    if not raw:
        return ["*"]
    return [o.strip() for o in raw.split(",") if o.strip()]


_cors_allow_credentials = _cors_origins() != ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins(),
    allow_credentials=_cors_allow_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    return {"app": "CodeSentry", "phase": 3, "docs": "/docs"}


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/scan", response_model=ScanJob)
def scan(
    req: ScanRequest,
    background_tasks: BackgroundTasks,
    user_id: str | None = Depends(optional_user),
):
    scan_id = uuid4().hex
    job = ScanJob(
        scan_id=scan_id,
        status="queued",
        total_files=1,
        user_id=user_id,
        label=req.filename,
        source_type="snippet",
    )
    JOBS[scan_id] = job
    background_tasks.add_task(
        run_scan_job,
        scan_id,
        {req.filename: req.code},
        req.enrich,
        req.llm_missed_issues,
        user_id,
        req.filename,
        "snippet",
    )
    return job


@app.post("/scan/repo", response_model=ScanJob)
def scan_repo(
    req: RepoScanRequest,
    background_tasks: BackgroundTasks,
    user_id: str | None = Depends(optional_user),
):
    if not req.github_url:
        raise HTTPException(400, "github_url is required")
    try:
        gh = load_github_repo(req.github_url, req.branch)
    except GitHubURLError as exc:
        raise HTTPException(422, str(exc))
    except Exception as exc:
        raise HTTPException(422, f"Could not read GitHub repository: {exc}")
    if not gh.paths:
        raise HTTPException(422, "No .py files found in this repository")
    scan_id = uuid4().hex
    job = ScanJob(
        scan_id=scan_id,
        status="queued",
        total_files=len(gh.paths),
        user_id=user_id,
        label=req.github_url,
        source_type="repo",
    )
    JOBS[scan_id] = job
    background_tasks.add_task(
        run_github_job, scan_id, gh, req.enrich, req.llm_missed_issues, user_id, req.github_url
    )
    return job


@app.post("/scan/repo/zip", response_model=ScanJob)
async def scan_repo_zip(
    file: UploadFile = File(...),
    enrich: bool = Form(True),
    llm_missed_issues: bool = Form(True),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    user_id: str | None = Depends(optional_user),
):
    content = await file.read()
    files = extract_zip_python_files(content)
    if not files:
        raise HTTPException(422, "No .py files found in the uploaded archive")
    scan_id = uuid4().hex
    job = ScanJob(
        scan_id=scan_id,
        status="queued",
        total_files=len(files),
        user_id=user_id,
        label=file.filename or "archive.zip",
        source_type="zip",
    )
    JOBS[scan_id] = job
    background_tasks.add_task(
        run_scan_job,
        scan_id,
        files,
        enrich,
        llm_missed_issues,
        user_id,
        file.filename or "archive.zip",
        "zip",
    )
    return job


@app.get("/scan/{scan_id}", response_model=ScanJob)
def get_scan(scan_id: str):
    job = JOBS.get(scan_id)
    if not job:
        raise HTTPException(404, "Unknown scan id")
    return job


def _sse(event: dict) -> str:
    return f"data: {json.dumps(event)}\n\n"


@app.get("/scan/{scan_id}/events")
def scan_events(scan_id: str):
    """Server-Sent Events stream: replays current state, then pushes live progress
    and findings as files are scanned. Closes after a done/failed event."""
    job = JOBS.get(scan_id)
    if not job:
        raise HTTPException(404, "Unknown scan id")

    async def event_stream():
        if job.status == "done":
            yield _sse(
                {
                    "type": "done",
                    "status": "done",
                    "scan_id": scan_id,
                    "filename": job.label,
                    "total_files": job.total_files,
                    "total_issues": job.total_issues,
                    "risk_score": job.risk_score,
                    "findings": [f.model_dump() for f in job.findings],
                }
            )
            return
        if job.status == "failed":
            yield _sse({"type": "failed", "status": "failed", "error": job.error})
            return

        yield _sse(
            {
                "type": "snapshot",
                "status": job.status,
                "findings": [f.model_dump() for f in job.findings],
                "scanned": job.scanned_files,
                "total": job.total_files,
            }
        )
        q = subscribe(scan_id)
        try:
            if job.status == "done":
                yield _sse(
                    {
                        "type": "done",
                        "status": "done",
                        "scan_id": scan_id,
                        "filename": job.label,
                        "total_files": job.total_files,
                        "total_issues": job.total_issues,
                        "risk_score": job.risk_score,
                        "findings": [f.model_dump() for f in job.findings],
                    }
                )
                return
            if job.status == "failed":
                yield _sse({"type": "failed", "status": "failed", "error": job.error})
                return
            while True:
                try:
                    evt = q.get_nowait()
                except queue.Empty:
                    await asyncio.sleep(0.15)
                    continue
                yield _sse(evt)
                if evt.get("type") in ("done", "failed"):
                    break
        finally:
            unsubscribe(scan_id)

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.get("/me")
def me(user_id: str = Depends(require_user)):
    return {"user_id": user_id, "storage": storage_name(), "history_size": len(get_store().list_scans(user_id))}


def _scan_summary(record: ScanRecord) -> dict:
    return {
        "scan_id": record.scan_id,
        "filename": record.filename,
        "source_type": record.source_type,
        "total_issues": record.total_issues,
        "risk_score": record.risk_score,
        "created_at": record.created_at,
    }


@app.get("/scans", response_model=ScanListResponse)
def list_scans(user_id: str = Depends(require_user)):
    store = get_store()
    return ScanListResponse(
        scans=[_scan_summary(r) for r in store.list_scans(user_id)],
        storage=storage_name(),
    )


@app.get("/scans/{scan_id}", response_model=ScanRecord)
def get_history_scan(scan_id: str, user_id: str = Depends(require_user)):
    record = get_store().get_scan(user_id, scan_id)
    if not record:
        raise HTTPException(404, "Scan not found")
    return record


@app.delete("/scans/{scan_id}")
def delete_history_scan(scan_id: str, user_id: str = Depends(require_user)):
    if not get_store().delete_scan(user_id, scan_id):
        raise HTTPException(404, "Scan not found")
    return {"deleted": True}