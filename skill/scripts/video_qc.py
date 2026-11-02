#!/usr/bin/env python3
"""Prepare a generated-video QC package: metadata, frames, contact sheet, technical checks.

This script does not judge semantic quality. It creates evidence for an Agent or human
to inspect. Semantic review must use the video/frames and the original shot specification.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any


def run(cmd: list[str], *, timeout: int = 300) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=timeout,
        check=False,
    )


def die(message: str, code: int = 2) -> None:
    print(f"error: {message}", file=sys.stderr)
    raise SystemExit(code)


def parse_fraction(value: str | None) -> float | None:
    if not value or value in {"0/0", "N/A"}:
        return None
    if "/" in value:
        numerator, denominator = value.split("/", 1)
        try:
            den = float(denominator)
            return float(numerator) / den if den else None
        except ValueError:
            return None
    try:
        return float(value)
    except ValueError:
        return None


def parse_ratio(value: str) -> float:
    match = re.fullmatch(r"\s*(\d+(?:\.\d+)?)\s*[:/]\s*(\d+(?:\.\d+)?)\s*", value)
    if not match:
        raise argparse.ArgumentTypeError("ratio must look like 9:16 or 2.39:1")
    left, right = map(float, match.groups())
    if left <= 0 or right <= 0:
        raise argparse.ArgumentTypeError("ratio values must be positive")
    return left / right


def probe_with_ffmpeg(ffmpeg: str, video: Path) -> dict[str, Any]:
    """Build minimal media metadata from ffmpeg's input summary when ffprobe is absent."""
    result = run([ffmpeg, "-hide_banner", "-i", str(video)], timeout=60)
    text = result.stderr
    duration_match = re.search(r"Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)", text)
    duration = None
    if duration_match:
        hours, minutes, seconds = duration_match.groups()
        duration = int(hours) * 3600 + int(minutes) * 60 + float(seconds)
    video_line = next(
        (line for line in text.splitlines() if re.search(r"Stream .*Video:", line)),
        None,
    )
    if not video_line:
        die("ffmpeg reported no video stream")
    size_match = re.search(r"(?<!\d)(\d{2,6})x(\d{2,6})(?!\d)", video_line)
    width = int(size_match.group(1)) if size_match else None
    height = int(size_match.group(2)) if size_match else None
    fps_match = re.search(r"([0-9.]+)\s+fps", video_line)
    fps = float(fps_match.group(1)) if fps_match else None
    audio_count = sum(1 for line in text.splitlines() if re.search(r"Stream .*Audio:", line))
    format_match = re.search(r"Input #0,\s*([^,]+)", text)
    input_format = format_match.group(1).strip() if format_match else video.suffix.lstrip(".")
    bitrate_match = re.search(r"bitrate:\s*(\d+)\s*kb/s", text)
    bitrate = str(int(bitrate_match.group(1)) * 1000) if bitrate_match else None
    streams: list[dict[str, Any]] = [
        {
            "codec_type": "video",
            "width": width,
            "height": height,
            "avg_frame_rate": f"{fps}/1" if fps is not None else None,
            "r_frame_rate": f"{fps}/1" if fps is not None else None,
            "duration": duration,
        }
    ]
    for _ in range(audio_count):
        streams.append({"codec_type": "audio"})
    return {
        "format": {
            "duration": duration,
            "size": str(video.stat().st_size),
            "bit_rate": bitrate,
            "format_name": input_format,
        },
        "streams": streams,
        "probe_backend": "ffmpeg-input-summary",
    }


def probe_video(ffprobe: str, video: Path) -> dict[str, Any]:
    cmd = [
        ffprobe,
        "-v",
        "error",
        "-show_entries",
        "format=duration,size,bit_rate,format_name:stream=index,codec_type,codec_name,width,height,avg_frame_rate,r_frame_rate,duration,sample_rate,channels",
        "-of",
        "json",
        str(video),
    ]
    result = run(cmd, timeout=60)
    if result.returncode != 0:
        die(f"ffprobe failed: {result.stderr.strip()}")
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        die(f"could not parse ffprobe JSON: {exc}")


def parse_blackdetect(stderr: str) -> list[dict[str, float | None]]:
    events: list[dict[str, float | None]] = []
    pattern = re.compile(
        r"black_start:(?P<start>[0-9.]+)\s+black_end:(?P<end>[0-9.]+)\s+"
        r"black_duration:(?P<duration>[0-9.]+)"
    )
    for match in pattern.finditer(stderr):
        events.append({key: float(value) for key, value in match.groupdict().items()})
    return events


def parse_freezedetect(stderr: str) -> list[dict[str, float | None]]:
    events: list[dict[str, float | None]] = []
    starts = [float(x) for x in re.findall(r"freeze_start:\s*([0-9.]+)", stderr)]
    ends = [float(x) for x in re.findall(r"freeze_end:\s*([0-9.]+)", stderr)]
    durations = [float(x) for x in re.findall(r"freeze_duration:\s*([0-9.]+)", stderr)]
    for index, start in enumerate(starts):
        events.append(
            {
                "start": start,
                "end": ends[index] if index < len(ends) else None,
                "duration": durations[index] if index < len(durations) else None,
            }
        )
    return events


def technical_scan(ffmpeg: str, video: Path) -> dict[str, Any]:
    cmd = [
        ffmpeg,
        "-hide_banner",
        "-nostats",
        "-i",
        str(video),
        "-vf",
        "blackdetect=d=0.20:pix_th=0.10,freezedetect=n=0.003:d=1.0",
        "-an",
        "-f",
        "null",
        "-",
    ]
    result = run(cmd, timeout=300)
    # A null-output scan can return non-zero for unsupported filters. Preserve a warning.
    return {
        "scan_returncode": result.returncode,
        "black_events": parse_blackdetect(result.stderr),
        "freeze_events": parse_freezedetect(result.stderr),
        "scan_warning": None
        if result.returncode == 0
        else result.stderr.strip().splitlines()[-1] if result.stderr.strip() else "scan failed",
    }


def scene_cuts(ffmpeg: str, video: Path, threshold: float) -> list[float]:
    cmd = [
        ffmpeg,
        "-hide_banner",
        "-nostats",
        "-i",
        str(video),
        "-vf",
        f"select='gt(scene,{threshold})',showinfo",
        "-an",
        "-f",
        "null",
        "-",
    ]
    result = run(cmd, timeout=300)
    if result.returncode != 0:
        return []
    values = [float(x) for x in re.findall(r"pts_time:([0-9.]+)", result.stderr)]
    return sorted(set(round(x, 3) for x in values))


def extract_frames(
    ffmpeg: str,
    video: Path,
    frames_dir: Path,
    duration: float | None,
    max_frames: int,
    interval_arg: float | None,
) -> tuple[list[dict[str, Any]], float]:
    frames_dir.mkdir(parents=True, exist_ok=True)
    if interval_arg is not None:
        interval = interval_arg
    elif duration and duration > 0:
        interval = max(0.1, duration / max_frames)
    else:
        interval = 0.5
    cmd = [
        ffmpeg,
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-i",
        str(video),
        "-vf",
        f"fps=1/{interval:.6f}",
        "-frames:v",
        str(max_frames),
        "-q:v",
        "2",
        str(frames_dir / "frame_%03d.jpg"),
    ]
    result = run(cmd, timeout=300)
    if result.returncode != 0:
        die(f"frame extraction failed: {result.stderr.strip()}")

    frames = sorted(frames_dir.glob("frame_*.jpg"))
    manifest: list[dict[str, Any]] = []
    for index, frame in enumerate(frames, start=1):
        timestamp = round((index - 1) * interval, 3)
        manifest.append({"index": index, "timestamp": timestamp, "path": str(frame)})
    return manifest, interval


def make_contact_sheet(ffmpeg: str, frames_dir: Path, output: Path) -> bool:
    frames = sorted(frames_dir.glob("frame_*.jpg"))
    if not frames:
        return False
    cmd = [
        ffmpeg,
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-framerate",
        "1",
        "-i",
        str(frames_dir / "frame_%03d.jpg"),
        "-vf",
        "scale=320:568:force_original_aspect_ratio=decrease,"
        "pad=320:568:(ow-iw)/2:(oh-ih)/2:color=0x111111,"
        "tile=4x6:padding=8:margin=8:color=0x111111",
        "-frames:v",
        "1",
        "-q:v",
        "2",
        str(output),
    ]
    result = run(cmd, timeout=120)
    return result.returncode == 0 and output.exists()


def stream_summary(probe: dict[str, Any]) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
    streams = probe.get("streams", [])
    videos = [s for s in streams if s.get("codec_type") == "video"]
    audios = [s for s in streams if s.get("codec_type") == "audio"]
    return (videos[0] if videos else None), audios


def run_macos_backend(
    video: Path,
    out_dir: Path,
    max_frames: int,
    interval: float | None,
) -> dict[str, Any]:
    """Fallback for macOS using an Objective-C AVFoundation helper.

    It provides metadata, sampled frames and a contact sheet. Black/freeze/scene
    detection remains unavailable without FFmpeg.
    """
    if sys.platform != "darwin":
        die("ffmpeg and ffprobe are required on this platform")
    xcrun = shutil.which("xcrun")
    if not xcrun:
        die("ffmpeg/ffprobe not found and Xcode command-line tools are unavailable")
    source = Path(__file__).with_name("video_qc_macos.m")
    if not source.is_file():
        die("ffmpeg/ffprobe not found and the macOS fallback source is missing")
    bin_dir = out_dir / "_bin"
    bin_dir.mkdir(parents=True, exist_ok=True)
    binary = bin_dir / "video_qc_macos"
    compile_cmd = [
        xcrun,
        "clang",
        "-fobjc-arc",
        "-framework",
        "Foundation",
        "-framework",
        "AVFoundation",
        "-framework",
        "CoreMedia",
        "-framework",
        "ImageIO",
        "-framework",
        "CoreGraphics",
        str(source),
        "-o",
        str(binary),
    ]
    compiled = run(compile_cmd, timeout=120)
    if compiled.returncode != 0:
        die(f"macOS video helper compilation failed: {compiled.stderr.strip()}")
    cmd = [
        str(binary),
        "--input",
        str(video),
        "--output-dir",
        str(out_dir),
        "--max-frames",
        str(max_frames),
    ]
    if interval is not None:
        cmd.extend(["--interval", str(interval)])
    result = run(cmd, timeout=300)
    if result.returncode != 0:
        die(f"macOS frame extraction failed: {result.stderr.strip()}")
    meta_path = out_dir / "macos-meta.json"
    if not meta_path.is_file():
        die("macOS fallback did not produce metadata")
    try:
        return json.loads(meta_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        die(f"could not parse macOS metadata: {exc}")


def build_summary(report: dict[str, Any]) -> str:
    media = report["media"]
    tech = report["technical"]
    checks = report["checks"]
    lines = [
        f"# 生成视频技术质检｜{report['shot_id']}",
        "",
        f"- 文件：`{report['source']}`",
        f"- 后端：{report.get('backend') or '[需核实]'}",
        f"- 模型：{report.get('model') or '[需核实]'}",
        f"- 时长：{media.get('duration_seconds')} 秒",
        f"- 画幅：{media.get('width')} × {media.get('height')}",
        f"- 帧率：{media.get('fps')}",
        f"- 音频轨：{'有' if media.get('has_audio') else '无'}",
        f"- 联系表：`{report['artifacts'].get('contact_sheet')}`",
        "",
        "## 基础检查",
        "",
        f"- 画幅匹配：{checks.get('ratio_match')}",
        f"- 时长匹配：{checks.get('duration_match')}",
        f"- 黑帧事件：{len(tech.get('black_events', []))}",
        f"- 冻结事件：{len(tech.get('freeze_events', []))}",
        f"- 检测到场景切点：{len(tech.get('scene_cuts', []))}",
        "",
        "## 语义质检",
        "",
        "需要 Agent 或人工查看视频、联系表和原镜头卡后填写。脚本不判定以下项目：",
        "",
        "- 主体身份与服装一致性；",
        "- 关键动作是否完成；",
        "- 构图、运镜和光影是否遵循提示词；",
        "- 手部、道具、反射、文字和物理是否异常；",
        "- 音频、口型与动作是否同步；",
        "- 是否可接上一镜和下一镜。",
        "",
        "使用 `assets/video-qc-report-template.md` 完成语义评分、问题分级和下一轮修改。",
        "",
    ]
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("video", type=Path, help="generated video file")
    parser.add_argument("--out", type=Path, required=True, help="output directory")
    parser.add_argument("--shot-id", default="unnamed-shot", help="shot identifier")
    parser.add_argument("--model", default="", help="generated model and version")
    parser.add_argument("--target-duration", type=float, help="target duration in seconds")
    parser.add_argument("--target-ratio", type=parse_ratio, help="target ratio, e.g. 9:16")
    parser.add_argument("--target-fps", type=float, help="target frame rate")
    parser.add_argument("--duration-tolerance", type=float, default=0.10, help="relative duration tolerance")
    parser.add_argument("--ratio-tolerance", type=float, default=0.03, help="relative ratio tolerance")
    parser.add_argument("--fps-tolerance", type=float, default=0.5, help="absolute fps tolerance")
    parser.add_argument("--max-frames", type=int, default=24, help="maximum sampled frames")
    parser.add_argument("--interval", type=float, help="fixed sampling interval in seconds")
    parser.add_argument("--scene-threshold", type=float, default=0.35, help="scene cut threshold; 0 disables")
    parser.add_argument("--require-audio", action="store_true", help="mark missing audio as a failed check")
    parser.add_argument("--ffmpeg", help="path to ffmpeg")
    parser.add_argument("--ffprobe", help="path to ffprobe")
    args = parser.parse_args()

    video = args.video.expanduser().resolve()
    if not video.is_file():
        die(f"video not found: {video}")
    if args.max_frames < 1 or args.max_frames > 100:
        die("--max-frames must be between 1 and 100")
    if args.interval is not None and args.interval <= 0:
        die("--interval must be positive")

    out_dir = args.out.expanduser().resolve()
    frames_dir = out_dir / "frames"
    out_dir.mkdir(parents=True, exist_ok=True)

    ffmpeg = args.ffmpeg or shutil.which("ffmpeg")
    ffprobe = args.ffprobe or shutil.which("ffprobe")
    backend = "ffmpeg"
    if ffmpeg:
        probe = probe_video(ffprobe, video) if ffprobe else probe_with_ffmpeg(ffmpeg, video)
        video_stream, audio_streams = stream_summary(probe)
        if not video_stream:
            die("no video stream found")
        duration_value = probe.get("format", {}).get("duration")
        if duration_value is None:
            duration_value = video_stream.get("duration")
        try:
            duration = float(duration_value) if duration_value is not None else None
        except (TypeError, ValueError):
            duration = None
        fps = parse_fraction(video_stream.get("avg_frame_rate")) or parse_fraction(
            video_stream.get("r_frame_rate")
        )
        width = video_stream.get("width")
        height = video_stream.get("height")
        audio_count = len(audio_streams)
        has_audio = bool(audio_streams)
        source_format = probe.get("format", {}).get("format_name")
        source_size = probe.get("format", {}).get("size")
        source_bitrate = probe.get("format", {}).get("bit_rate")

        frames, interval = extract_frames(
            ffmpeg, video, frames_dir, duration, args.max_frames, args.interval
        )
        contact_sheet = out_dir / "contact-sheet.jpg"
        contact_ok = make_contact_sheet(ffmpeg, frames_dir, contact_sheet)
        technical = technical_scan(ffmpeg, video)
        technical["scene_cuts"] = (
            scene_cuts(ffmpeg, video, args.scene_threshold)
            if args.scene_threshold > 0
            else []
        )
    else:
        backend = "macos-avfoundation"
        meta = run_macos_backend(video, out_dir, args.max_frames, args.interval)
        duration = meta.get("duration_seconds")
        width = meta.get("width")
        height = meta.get("height")
        fps = meta.get("fps")
        audio_count = int(meta.get("audio_streams") or 0)
        has_audio = bool(meta.get("has_audio"))
        source_format = meta.get("format_name")
        source_size = meta.get("size_bytes")
        source_bitrate = meta.get("bit_rate")
        interval = meta.get("interval_seconds")
        frames = meta.get("frames") or []
        contact_value = meta.get("contact_sheet")
        contact_sheet = Path(contact_value) if contact_value else out_dir / "contact-sheet.jpg"
        contact_ok = bool(contact_value and Path(contact_value).is_file())
        technical = {
            "backend": backend,
            "scan_returncode": None,
            "black_events": [],
            "freeze_events": [],
            "scene_cuts": [],
            "scan_warning": "macOS fallback provides metadata and frames only; use FFmpeg for black/freeze/scene scans.",
        }
        if not frames:
            print("warning: no frames could be decoded; provide FFmpeg or review the video directly", file=sys.stderr)

    actual_ratio = (float(width) / float(height)) if width and height else None

    ratio_match: bool | None = None
    if args.target_ratio is not None and actual_ratio:
        ratio_match = abs(actual_ratio - args.target_ratio) / args.target_ratio <= args.ratio_tolerance

    duration_match: bool | None = None
    if args.target_duration is not None and duration is not None:
        duration_match = abs(duration - args.target_duration) <= max(
            0.25, args.target_duration * args.duration_tolerance
        )

    fps_match: bool | None = None
    if args.target_fps is not None and fps is not None:
        fps_match = abs(fps - args.target_fps) <= args.fps_tolerance

    audio_match = has_audio if args.require_audio else None

    report: dict[str, Any] = {
        "shot_id": args.shot_id,
        "source": str(video),
        "model": args.model,
        "backend": backend,
        "media": {
            "duration_seconds": duration,
            "width": width,
            "height": height,
            "aspect_ratio": actual_ratio,
            "fps": fps,
            "has_audio": has_audio,
            "audio_streams": audio_count,
            "format_name": source_format,
            "size_bytes": source_size,
            "bit_rate": source_bitrate,
        },
        "checks": {
            "ratio_match": ratio_match,
            "duration_match": duration_match,
            "fps_match": fps_match,
            "audio_match": audio_match,
        },
        "targets": {
            "duration_seconds": args.target_duration,
            "aspect_ratio": args.target_ratio,
            "fps": args.target_fps,
            "require_audio": args.require_audio,
        },
        "technical": technical,
        "sampling": {"interval_seconds": interval, "frame_count": len(frames)},
        "frames": frames,
        "artifacts": {
            "metadata_json": str(out_dir / "qc.json"),
            "summary_markdown": str(out_dir / "qc-summary.md"),
            "contact_sheet": str(contact_sheet) if contact_ok else None,
            "frames_dir": str(frames_dir),
        },
        "review": {
            "semantic_review_complete": False,
            "verdict": None,
            "scores": None,
            "issues": [],
            "next_action": None,
        },
    }

    (out_dir / "qc.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (out_dir / "qc-summary.md").write_text(build_summary(report), encoding="utf-8")

    warning = None
    if not frames:
        warning = "No frames were decoded. Visual QC is incomplete; install FFmpeg or review the video directly."
    print(json.dumps(
        {
            "ok": bool(frames),
            "output_dir": str(out_dir),
            "contact_sheet": str(contact_sheet) if contact_ok else None,
            "frame_count": len(frames),
            "semantic_review_required": True,
            "warning": warning,
        },
        ensure_ascii=False,
        indent=2,
    ))


if __name__ == "__main__":
    main()
