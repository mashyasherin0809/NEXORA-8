"""
Flask Web Server and REST / SSE API for NEXORA-8 Agent.
Serves the Agent Monitoring Dashboard and manages background execution.
"""

from collections import deque
import json
import os
import queue
import threading
import time
from typing import Dict, Optional

from flask import Flask, Response, jsonify, render_template, request, send_from_directory

from nexora.config import Config
from nexora.agents.base import AgentEvent
from nexora.agents.orchestrator import OrchestratorAgent, RepairSession
from nexora.analyzer.repo_indexer import CodebaseIndexer
from nexora.guard.hallucination_guard import HallucinationGuard


# In-memory session store & event broadcaster
SESSIONS: Dict[str, RepairSession] = {}
SESSION_EVENT_QUEUES: Dict[str, list[queue.Queue]] = {}
GLOBAL_EVENT_HISTORY = deque(maxlen=200)


def create_app(config: Optional[Config] = None) -> Flask:
    cfg = config or Config()
    
    # Root directory for static dashboard files
    static_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

    app = Flask(
        __name__,
        static_folder=static_root,
        static_url_path="",
    )
    app.config["NEXORA_CONFIG"] = cfg

    @app.after_request
    def add_cors_headers(response):
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type,Authorization"
        response.headers["Access-Control-Allow-Methods"] = "GET,POST,OPTIONS"
        return response

    # --- Static Dashboard Routes ---
    @app.route("/")
    def index():
        return send_from_directory(static_root, "index.html")

    @app.route("/<path:path>")
    def static_files(path):
        full_path = os.path.join(static_root, path)
        if os.path.exists(full_path):
            return send_from_directory(static_root, path)
        return send_from_directory(static_root, "index.html")

    # --- API Endpoints ---
    @app.route("/api/health", methods=["GET"])
    def api_health():
        return jsonify({
            "status": "healthy",
            "agent": "NEXORA-8",
            "version": "1.0.0",
            "model_provider": cfg.model_provider,
            "model_name": cfg.model_name,
            "max_attempts": cfg.max_repair_attempts,
            "sandbox_online": True,
        })

    @app.route("/api/analyze-repo", methods=["POST"])
    def api_analyze_repo():
        data = request.get_json(silent=True) or {}
        repo_path = data.get("repo_path", "")
        if not repo_path or not os.path.isdir(repo_path):
            return jsonify({"error": f"Invalid or non-existent repository path: {repo_path}"}), 400

        indexer = CodebaseIndexer(repo_path)
        index = indexer.index()
        return jsonify(index.to_dict())

    @app.route("/api/run-task", methods=["POST"])
    def api_run_task():
        data = request.get_json(silent=True) or {}
        repo_path = data.get("repo_path", "").strip()
        task = data.get("task", "").strip()
        apply_changes = bool(data.get("apply_changes", False))

        if not task:
            return jsonify({"error": "Task description is required."}), 400

        # If repo_path is not specified or invalid, default to the current repo directory
        if not repo_path or not os.path.isdir(repo_path):
            repo_path = os.path.abspath(os.path.join(static_root, "..", ".."))

        orchestrator = OrchestratorAgent(cfg)

        def event_broadcaster(event: AgentEvent):
            GLOBAL_EVENT_HISTORY.append(event)
            # Push to session queues
            if orchestrator.current_session:
                sid = orchestrator.current_session.session_id
                if sid in SESSION_EVENT_QUEUES:
                    for q in SESSION_EVENT_QUEUES[sid]:
                        q.put(event)

        orchestrator.add_event_listener(event_broadcaster)

        # Run synchronously or in thread based on query param 'async'
        is_async = request.args.get("async", "false").lower() == "true"

        if is_async:
            session_id = f"ses_{int(time.time())}"
            SESSION_EVENT_QUEUES[session_id] = []

            def worker():
                session = orchestrator.execute_task(repo_path, task, apply_to_original=apply_changes)
                SESSIONS[session.session_id] = session

            threading.Thread(target=worker, daemon=True).start()
            return jsonify({
                "session_id": session_id,
                "status": "started",
                "message": "Task launched asynchronously.",
                "stream_url": f"/api/sessions/{session_id}/stream",
            })
        else:
            session = orchestrator.execute_task(repo_path, task, apply_to_original=apply_changes)
            SESSIONS[session.session_id] = session
            return jsonify(session.to_dict())

    @app.route("/api/sessions", methods=["GET"])
    def api_get_sessions():
        result = []
        for s in reversed(list(SESSIONS.values())):
            result.append({
                "id": s.session_id,
                "title": s.task_description,
                "repo": s.repo_path,
                "status": s.status,
                "attempts": s.attempts,
                "cost_usd": s.cost_usd,
                "timestamp": s.start_time,
                "modified_files": [p.file_path for p in s.patches if p.success],
            })
        return jsonify(result)

    @app.route("/api/sessions/<session_id>", methods=["GET"])
    def api_get_session_detail(session_id):
        if session_id not in SESSIONS:
            return jsonify({"error": f"Session '{session_id}' not found."}), 404
        return jsonify(SESSIONS[session_id].to_dict())

    @app.route("/api/sessions/<session_id>/stream", methods=["GET"])
    def api_session_stream(session_id):
        """Server-Sent Events stream for live agent monitor telemetry."""
        q = queue.Queue()
        SESSION_EVENT_QUEUES.setdefault(session_id, []).append(q)

        def event_generator():
            try:
                # First yield existing session state if any
                if session_id in SESSIONS:
                    init_data = json.dumps(SESSIONS[session_id].to_dict())
                    yield f"event: session_state\ndata: {init_data}\n\n"

                while True:
                    try:
                        event: AgentEvent = q.get(timeout=25.0)
                        data = json.dumps(event.to_dict())
                        yield f"event: agent_event\ndata: {data}\n\n"
                    except queue.Empty:
                        # Heartbeat ping to keep SSE connection alive
                        yield ": ping\n\n"
            finally:
                if session_id in SESSION_EVENT_QUEUES and q in SESSION_EVENT_QUEUES[session_id]:
                    SESSION_EVENT_QUEUES[session_id].remove(q)

        return Response(event_generator(), mimetype="text/event-stream")

    @app.route("/api/analyze-diff", methods=["POST"])
    def api_analyze_diff():
        data = request.get_json(silent=True) or {}
        before_code = data.get("before", "")
        after_code = data.get("after", "")
        known_modules_str = data.get("modules", "")
        known_modules = set(known_modules_str.split(",")) if known_modules_str else set()

        guard = HallucinationGuard(known_repo_modules=known_modules, max_diff_lines=cfg.max_diff_lines)
        report = guard.validate_patch(before_code, after_code)
        return jsonify(report.to_dict())

    @app.route("/api/stats", methods=["GET"])
    def api_stats():
        total_sessions = len(SESSIONS)
        success_count = sum(1 for s in SESSIONS.values() if s.status == "success")
        total_regressions_prevented = sum(
            len(s.verification_verdict.regressions) for s in SESSIONS.values() if s.verification_verdict
        )
        return jsonify({
            "total_sessions": total_sessions,
            "success_rate": round(success_count / total_sessions * 100, 1) if total_sessions > 0 else 100.0,
            "regressions_prevented": total_regressions_prevented,
            "active_agents": ["Locator", "Planner", "Patcher", "Guard", "Verifier", "TestGenerator"],
        })

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(host="0.0.0.0", port=5000, debug=True)
