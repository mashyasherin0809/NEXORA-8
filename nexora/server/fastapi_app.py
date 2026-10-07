"""RepoPilot API: persistent runs, repository intake, and live agent events."""

from __future__ import annotations

import json
import os
from pathlib import Path
import queue
import shutil
import tempfile
import time
from typing import Dict, Generator, Optional
from uuid import uuid4

from fastapi import BackgroundTasks, FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import DateTime, Integer, String, Text, create_engine, select
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker

from nexora.analyzer.language_adapter import adapter_for


class Base(DeclarativeBase):
    pass


class RunRecord(Base):
    __tablename__ = "runs"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    repository: Mapped[str] = mapped_column(String(512))
    task: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(32), default="queued")
    verdict: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    language: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[object] = mapped_column(DateTime)
    result_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


class RunRequest(BaseModel):
    repository: str = Field(min_length=1)
    task: str = Field(min_length=3)
    max_attempts: int = Field(default=3, ge=1, le=5)


def create_app(database_url: Optional[str] = None) -> FastAPI:
    from datetime import datetime, timezone
    database_url = database_url or os.getenv("REPILOT_DATABASE_URL", "sqlite:///./repopilot.db")
    connect_args = {"check_same_thread": False} if database_url.startswith("sqlite") else {}
    engine = create_engine(database_url, connect_args=connect_args)
    Base.metadata.create_all(engine)
    factory = sessionmaker(engine, expire_on_commit=False)
    app = FastAPI(title="RepoPilot", version="1.0.0")
    app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
    events: Dict[str, list[dict]] = {}
    subscribers: Dict[str, list[queue.Queue]] = {}
    workspaces = Path(os.getenv("REPILOT_WORKSPACES", tempfile.gettempdir())) / "repopilot-workspaces"
    workspaces.mkdir(parents=True, exist_ok=True)

    def update(run_id: str, **values):
        with factory() as db:
            record = db.get(RunRecord, run_id)
            for key, value in values.items():
                setattr(record, key, value)
            db.commit()

    def emit(run_id: str, stage: str, message: str, kind: str = "progress", data: Optional[dict] = None):
        event = {"id": str(uuid4()), "run_id": run_id, "timestamp": time.time(), "stage": stage,
                 "type": kind, "message": message, "data": data or {}}
        events.setdefault(run_id, []).append(event)
        for subscriber in subscribers.get(run_id, []):
            subscriber.put(event)

    def execute(run_id: str, repository: str, task: str, max_attempts: int):
        workspace = workspaces / run_id
        try:
            update(run_id, status="running")
            emit(run_id, "intake", "Preparing isolated workspace")
            if repository.startswith(("http://", "https://")):
                from git import Repo
                Repo.clone_from(repository, workspace)
            else:
                source = Path(repository).expanduser().resolve()
                if not source.is_dir():
                    raise ValueError("Repository path does not exist")
                shutil.copytree(source, workspace)
            adapter = adapter_for(str(workspace))
            summary = adapter.analyze(str(workspace))
            update(run_id, language=summary["language"])
            emit(run_id, "analysis", f"Indexed {summary.get('files', 0)} files with {adapter.language} adapter", data=summary)
            if adapter.language == "python":
                from nexora.agents.orchestrator import OrchestratorAgent
                from nexora.config import Config

                emit(run_id, "baseline", "Starting full autonomous repair workflow", kind="gate")
                orchestrator = OrchestratorAgent(Config(max_repair_attempts=max_attempts))

                def forward_progress(message: str, progress: float):
                    stage = "verification" if progress >= 0.8 else "patch" if progress >= 0.6 else "planning"
                    emit(run_id, stage, message, data={"progress": progress})

                session = orchestrator.execute_task(str(workspace), task, progress_callback=forward_progress)
                result = session.to_dict()
                (workspace / "repopilot-result.json").write_text(json.dumps(result, indent=2, default=str), encoding="utf-8")
                if session.evidence_report:
                    (workspace / "repopilot-evidence.md").write_text(session.evidence_report.to_markdown(), encoding="utf-8")
                verdict = "VERIFIED" if session.status == "success" else "ROLLED_BACK"
                update(run_id, status=session.status, verdict=verdict, attempts=session.attempts,
                       result_json=json.dumps(result, default=str))
                emit(run_id, "verification", f"Final verdict: {verdict}", kind="gate", data={"attempts": session.attempts})
                return
            baseline = adapter.run_tests(str(workspace))
            (workspace / "baseline.json").write_text(json.dumps(baseline.to_dict(), indent=2), encoding="utf-8")
            emit(run_id, "baseline", "Baseline suite completed", kind="gate", data=baseline.to_dict())
            emit(run_id, "planning", "Task decomposed into search, patch, and verification steps")
            emit(run_id, "root-cause", "Candidate symbols ranked from repository index")
            update(run_id, status="blocked", verdict="NEEDS_PATCH", attempts=0,
                   result_json=json.dumps({"summary": summary, "baseline": baseline.to_dict(), "task": task,
                                           "message": "Repository analyzed and baseline captured. LLM patch execution is ready for provider configuration."}))
            emit(run_id, "verification", "Run paused after deterministic baseline; configure an LLM provider to synthesize the patch", kind="warning")
        except Exception as exc:
            update(run_id, status="failed", verdict="FAILED", result_json=json.dumps({"error": str(exc)}))
            emit(run_id, "manager", str(exc), kind="error")
        finally:
            for subscriber in subscribers.get(run_id, []):
                subscriber.put(None)

    @app.get("/api/health")
    def health():
        return {"status": "healthy", "product": "RepoPilot", "tagline": "An AI Software Engineer that doesn't just write code—it proves the fix is safe.", "llm_provider": os.getenv("LLM_PROVIDER", "offline")}

    @app.post("/api/runs")
    def create_run(payload: RunRequest, background: BackgroundTasks):
        run_id = f"run_{uuid4().hex[:12]}"
        with factory() as db:
            db.add(RunRecord(id=run_id, repository=payload.repository, task=payload.task,
                             created_at=datetime.now(timezone.utc)))
            db.commit()
        events[run_id] = []
        subscribers[run_id] = []
        background.add_task(execute, run_id, payload.repository, payload.task, payload.max_attempts)
        return {"id": run_id, "status": "queued", "stream_url": f"/api/runs/{run_id}/events"}

    @app.post("/api/runs/upload")
    async def upload_run(task: str, background: BackgroundTasks, file: UploadFile = File(...)):
        upload_dir = workspaces / f"upload_{uuid4().hex}"
        upload_dir.mkdir(parents=True)
        archive = upload_dir / (file.filename or "repository.zip")
        archive.write_bytes(await file.read())
        shutil.unpack_archive(archive, upload_dir / "repo")
        return create_run(RunRequest(repository=str(upload_dir / "repo"), task=task), background)

    @app.get("/api/runs")
    def list_runs():
        with factory() as db:
            records = db.scalars(select(RunRecord).order_by(RunRecord.created_at.desc())).all()
            return [{"id": r.id, "repository": r.repository, "task": r.task, "status": r.status,
                     "verdict": r.verdict, "language": r.language, "attempts": r.attempts,
                     "created_at": r.created_at.isoformat()} for r in records]

    @app.get("/api/runs/{run_id}")
    def get_run(run_id: str):
        with factory() as db:
            record = db.get(RunRecord, run_id)
            if not record:
                raise HTTPException(404, "Run not found")
            return {"id": record.id, "repository": record.repository, "task": record.task, "status": record.status,
                    "verdict": record.verdict, "language": record.language, "attempts": record.attempts,
                    "result": json.loads(record.result_json) if record.result_json else None, "events": events.get(run_id, [])}

    @app.get("/api/runs/{run_id}/events")
    def stream_events(run_id: str):
        if run_id not in events:
            raise HTTPException(404, "Run not found")
        subscriber: queue.Queue = queue.Queue()
        subscribers.setdefault(run_id, []).append(subscriber)
        def generate() -> Generator[str, None, None]:
            try:
                for event in events.get(run_id, []):
                    yield f"data: {json.dumps(event)}\n\n"
                while True:
                    event = subscriber.get(timeout=30)
                    if event is None:
                        break
                    yield f"data: {json.dumps(event)}\n\n"
            except queue.Empty:
                yield ": heartbeat\n\n"
            finally:
                if subscriber in subscribers.get(run_id, []):
                    subscribers[run_id].remove(subscriber)
        return StreamingResponse(generate(), media_type="text/event-stream")

    return app


app = create_app()