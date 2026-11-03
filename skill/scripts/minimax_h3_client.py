#!/usr/bin/env python3
"""Minimal MiniMax H3 text-to-video client.

Official docs:
- https://platform.minimax.io/docs/guides/video-generation.md
- https://platform.minimax.io/docs/guides/models-intro.md

The API key is read from MINIMAX_API_KEY and is never printed.
"""

from __future__ import annotations

import argparse
import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

DEFAULT_BASE_URL = "https://api.minimax.io"
DEFAULT_MODEL = "MiniMax-H3"
DEFAULT_DURATION = 4
DEFAULT_RESOLUTION = "768P"
DEFAULT_RATIO = "9:16"


class MiniMaxError(RuntimeError):
    pass


def request_json(
    url: str,
    *,
    api_key: str,
    method: str = "GET",
    payload: dict[str, Any] | None = None,
    timeout: int = 60,
) -> dict[str, Any]:
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Accept": "application/json",
        "User-Agent": "short-drama-production-agent/1.3",
    }
    data = None
    if payload is not None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json; charset=utf-8"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            body = response.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", "replace")
        raise MiniMaxError(f"HTTP {exc.code}: {body[:1000]}") from exc
    except urllib.error.URLError as exc:
        raise MiniMaxError(f"Network error: {exc}") from exc
    try:
        parsed = json.loads(body)
    except json.JSONDecodeError as exc:
        raise MiniMaxError(f"Invalid JSON response: {body[:1000]}") from exc
    if not isinstance(parsed, dict):
        raise MiniMaxError(f"Unexpected response: {parsed!r}")
    base = parsed.get("base_resp") or {}
    code = base.get("status_code")
    if code not in (None, 0):
        raise MiniMaxError(f"MiniMax error {code}: {base.get('status_msg') or parsed}")
    return parsed


def build_text_to_video_payload(
    prompt: str,
    *,
    duration: int = DEFAULT_DURATION,
    resolution: str = DEFAULT_RESOLUTION,
    ratio: str = DEFAULT_RATIO,
    model: str = DEFAULT_MODEL,
) -> dict[str, Any]:
    prompt = prompt.strip()
    if not prompt:
        raise ValueError("prompt is empty")
    if len(prompt) > 7000:
        raise ValueError("prompt exceeds 7000 characters")
    if not isinstance(duration, int) or not 4 <= duration <= 15:
        raise ValueError("duration must be an integer from 4 to 15 seconds")
    if resolution not in {"768P", "2K"}:
        raise ValueError("resolution must be 768P or 2K")
    if ratio not in {"9:16", "16:9", "1:1", "4:3", "3:4", "adaptive"}:
        raise ValueError("unsupported ratio")
    return {
        "model": model,
        "content": [{"type": "text", "text": prompt}],
        "duration": duration,
        "resolution": resolution,
        "ratio": ratio,
    }


class MiniMaxH3Client:
    def __init__(
        self,
        api_key: str | None = None,
        base_url: str = DEFAULT_BASE_URL,
        model: str = DEFAULT_MODEL,
    ) -> None:
        self.api_key = api_key or os.environ.get("MINIMAX_API_KEY", "")
        self.base_url = base_url.rstrip("/")
        self.model = model
        if not self.api_key:
            raise MiniMaxError("MINIMAX_API_KEY is not configured")

    def create_text_to_video(
        self,
        prompt: str,
        *,
        duration: int = DEFAULT_DURATION,
        resolution: str = DEFAULT_RESOLUTION,
        ratio: str = DEFAULT_RATIO,
    ) -> dict[str, Any]:
        payload = build_text_to_video_payload(
            prompt,
            duration=duration,
            resolution=resolution,
            ratio=ratio,
            model=self.model,
        )
        response = request_json(
            f"{self.base_url}/v2/video_generation",
            api_key=self.api_key,
            method="POST",
            payload=payload,
        )
        task_id = response.get("task_id") or response.get("task", {}).get("id")
        if not task_id:
            raise MiniMaxError(f"No task_id in response: {response}")
        return {"task_id": str(task_id), "request": payload, "response": response}

    def query_task(self, task_id: str) -> dict[str, Any]:
        return request_json(
            f"{self.base_url}/v2/query/video_generation/{task_id}",
            api_key=self.api_key,
        )

    def wait_for_task(
        self,
        task_id: str,
        *,
        timeout_seconds: int = 900,
        poll_seconds: int = 5,
    ) -> dict[str, Any]:
        deadline = time.time() + timeout_seconds
        while time.time() < deadline:
            data = self.query_task(task_id)
            task = data.get("task") or data
            status = str(task.get("status") or "").lower()
            if status == "succeeded":
                return data
            if status in {"failed", "fail", "cancelled", "canceled"}:
                raise MiniMaxError(f"H3 task {task_id} ended with status={status}: {task.get('error') or task}")
            time.sleep(max(1, poll_seconds))
        raise MiniMaxError(f"Timed out waiting for task {task_id}")

    def download_video(self, download_url: str, output_path: Path) -> Path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        req = urllib.request.Request(download_url, headers={"User-Agent": "short-drama-production-agent/1.3"})
        try:
            with urllib.request.urlopen(req, timeout=180) as response:
                output_path.write_bytes(response.read())
        except (urllib.error.URLError, urllib.error.HTTPError) as exc:
            raise MiniMaxError(f"Video download failed: {exc}") from exc
        return output_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Submit a MiniMax H3 text-to-video task")
    parser.add_argument("--prompt-file", type=Path, required=True)
    parser.add_argument("--shot-id", default="S01-01")
    parser.add_argument("--duration", type=int, default=DEFAULT_DURATION)
    parser.add_argument("--resolution", default=DEFAULT_RESOLUTION, choices=["768P", "2K"])
    parser.add_argument("--ratio", default=DEFAULT_RATIO)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--base-url", default=os.environ.get("MINIMAX_BASE_URL", DEFAULT_BASE_URL))
    parser.add_argument("--out", type=Path, default=None)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--no-download", action="store_true")
    args = parser.parse_args()

    prompt = args.prompt_file.read_text(encoding="utf-8").strip()
    payload = build_text_to_video_payload(
        prompt,
        duration=args.duration,
        resolution=args.resolution,
        ratio=args.ratio,
        model=args.model,
    )
    if args.dry_run:
        print(json.dumps({"dry_run": True, "shot_id": args.shot_id, "payload": payload}, ensure_ascii=False, indent=2))
        return

    client = MiniMaxH3Client(base_url=args.base_url, model=args.model)
    created = client.create_text_to_video(
        prompt,
        duration=args.duration,
        resolution=args.resolution,
        ratio=args.ratio,
    )
    task_id = created["task_id"]
    print(json.dumps({"task_id": task_id, "shot_id": args.shot_id}, ensure_ascii=False, indent=2))
    result = client.wait_for_task(task_id)
    task = result.get("task") or result
    content = task.get("content") or {}
    download_url = content.get("url")
    if not download_url:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        raise MiniMaxError("Task succeeded but no content.url was returned")
    print(json.dumps({"status": "succeeded", "download_url": download_url}, ensure_ascii=False, indent=2))
    if not args.no_download:
        out = args.out or Path("outputs/generated-h3-videos") / f"{args.shot_id}-{task_id}.mp4"
        client.download_video(download_url, out)
        print(f"saved: {out}")


if __name__ == "__main__":
    main()
