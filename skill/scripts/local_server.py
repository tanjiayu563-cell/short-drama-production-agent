#!/usr/bin/env python3
"""Local-only bridge between the HTML workbench and MiniMax H3.

The browser never receives the API key. Run:

  export MINIMAX_API_KEY="..."
  python3 scripts/local_server.py

Then open http://127.0.0.1:8787/workbench/index.html
"""

from __future__ import annotations

import argparse
import json
import os
import re
import threading
from datetime import datetime, timezone
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from minimax_h3_client import (
    DEFAULT_BASE_URL,
    DEFAULT_DURATION,
    DEFAULT_RATIO,
    DEFAULT_RESOLUTION,
    MiniMaxError,
    MiniMaxH3Client,
    build_text_to_video_payload,
)

ROOT = Path(__file__).resolve().parents[2]
OUTPUT_ROOT = ROOT.parent / "generated-h3-videos"
JOBS: dict[str, dict[str, Any]] = {}
JOBS_LOCK = threading.Lock()


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def task_data(response: dict[str, Any]) -> dict[str, Any]:
    task = response.get("task") or response
    return task if isinstance(task, dict) else {}


class Handler(SimpleHTTPRequestHandler):
    server_version = "ShortDramaH3Bridge/1.3"

    def __init__(self, *args: Any, directory: str | None = None, **kwargs: Any) -> None:
        super().__init__(*args, directory=directory or str(ROOT), **kwargs)

    def log_message(self, fmt: str, *args: Any) -> None:
        # Do not log prompt text. The default logger only receives request line.
        print(f"[{self.log_date_time_string()}] {fmt % args}")

    def send_json(self, status: int, payload: dict[str, Any]) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self) -> None:
        self.send_response(HTTPStatus.NO_CONTENT)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.end_headers()

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path == "/api/health":
            self.send_json(200, {
                "ok": True,
                "configured": bool(os.environ.get("MINIMAX_API_KEY")),
                "model": "MiniMax-H3",
                "base_url": os.environ.get("MINIMAX_BASE_URL", DEFAULT_BASE_URL),
                "defaults": {
                    "duration": DEFAULT_DURATION,
                    "resolution": DEFAULT_RESOLUTION,
                    "ratio": DEFAULT_RATIO,
                },
            })
            return
        if path.startswith("/api/jobs/"):
            task_id = path.rsplit("/", 1)[-1]
            self.query_job(task_id)
            return
        if path.startswith("/generated/"):
            self.serve_generated(path)
            return
        if path == "/":
            self.send_response(HTTPStatus.FOUND)
            self.send_header("Location", "/workbench/index.html")
            self.end_headers()
            return
        super().do_GET()

    def do_POST(self) -> None:
        if urlparse(self.path).path != "/api/generate":
            self.send_json(404, {"error": "Not found"})
            return
        length = int(self.headers.get("Content-Length", "0"))
        if length <= 0 or length > 2_000_000:
            self.send_json(400, {"error": "Invalid request size"})
            return
        try:
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            self.send_json(400, {"error": "Invalid JSON"})
            return
        prompt = str(payload.get("prompt") or "").strip()
        shot_id = str(payload.get("shot_id") or "unnamed-shot")[:100]
        duration = int(payload.get("duration") or DEFAULT_DURATION)
        resolution = str(payload.get("resolution") or DEFAULT_RESOLUTION)
        ratio = str(payload.get("ratio") or DEFAULT_RATIO)
        try:
            request_payload = build_text_to_video_payload(
                prompt,
                duration=duration,
                resolution=resolution,
                ratio=ratio,
            )
            if not os.environ.get("MINIMAX_API_KEY"):
                raise MiniMaxError("MINIMAX_API_KEY is not configured. Start the server with the environment variable set.")
            client = MiniMaxH3Client(base_url=os.environ.get("MINIMAX_BASE_URL", DEFAULT_BASE_URL))
            created = client.create_text_to_video(
                prompt,
                duration=duration,
                resolution=resolution,
                ratio=ratio,
            )
            task_id = created["task_id"]
            with JOBS_LOCK:
                JOBS[task_id] = {
                    "task_id": task_id,
                    "shot_id": shot_id,
                    "model": "MiniMax-H3",
                    "prompt": prompt,
                    "duration": duration,
                    "resolution": resolution,
                    "ratio": ratio,
                    "status": "submitted",
                    "created_at": now_iso(),
                    "request": request_payload,
                }
            self.send_json(200, {"ok": True, "task_id": task_id, "shot_id": shot_id, "status": "submitted"})
        except (ValueError, MiniMaxError) as exc:
            self.send_json(503 if "configured" in str(exc) else 400, {"ok": False, "error": str(exc)})

    def query_job(self, task_id: str) -> None:
        try:
            client = MiniMaxH3Client(base_url=os.environ.get("MINIMAX_BASE_URL", DEFAULT_BASE_URL))
            response = client.query_task(task_id)
            task = task_data(response)
            status = str(task.get("status") or "unknown").lower()
            job = JOBS.get(task_id, {"task_id": task_id, "status": status})
            job["status"] = status
            job["updated_at"] = now_iso()
            if status == "succeeded":
                content = task.get("content") or {}
                download_url = content.get("url")
                if download_url:
                    video_path = OUTPUT_ROOT / f"{job.get('shot_id','shot')}-{task_id}.mp4"
                    client.download_video(download_url, video_path)
                    job["video_path"] = str(video_path)
                    job["video_url"] = f"/generated/{video_path.name}"
                else:
                    job["error"] = "Task succeeded but content.url was absent"
            elif status in {"failed", "fail", "cancelled", "canceled"}:
                job["error"] = task.get("error") or status
            with JOBS_LOCK:
                JOBS[task_id] = job
            self.send_json(200, {"ok": status not in {"failed", "fail", "cancelled", "canceled"}, "task_id": task_id, "job": job, "task": task})
        except (MiniMaxError, ValueError) as exc:
            self.send_json(502, {"ok": False, "task_id": task_id, "error": str(exc)})

    def serve_generated(self, path: str) -> None:
        name = path.rsplit("/", 1)[-1]
        if not re.fullmatch(r"[A-Za-z0-9._-]+\.mp4", name):
            self.send_json(404, {"error": "Not found"})
            return
        file_path = OUTPUT_ROOT / name
        if not file_path.is_file():
            self.send_json(404, {"error": "Video not ready"})
            return
        self.send_response(200)
        self.send_header("Content-Type", "video/mp4")
        self.send_header("Content-Length", str(file_path.stat().st_size))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(file_path.read_bytes())


def main() -> None:
    parser = argparse.ArgumentParser(description="Serve workbench and local MiniMax H3 bridge")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8787)
    args = parser.parse_args()
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    server = ThreadingHTTPServer((args.host, args.port), Handler)
    print(f"Workbench: http://{args.host}:{args.port}/workbench/index.html")
    print(f"API health: http://{args.host}:{args.port}/api/health")
    print("API key configured:", bool(os.environ.get("MINIMAX_API_KEY")))
    server.serve_forever()


if __name__ == "__main__":
    main()
