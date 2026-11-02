# Changelog

## v1.1.0 — 2026-11-02

### Added

- Model-aware video prompt pack for T2V, I2V, R2V, V2V, extension, and editing.
- Verified Seedance 2.0/2.5 reference notes with official source links.
- Generated-video QC workflow with technical checks, semantic scoring, P0/P1/P2 issues, root-cause analysis, and versioned refinement.
- `video_qc.py` to extract metadata, sampled frames, a contact sheet, black-frame/freeze events, and scene cuts.
- Video prompt pack, QC report, and iteration log templates.
- End-to-end Seedance prompt example for shot S01-10.

### Changed

- Storyboard shot cards now include generation mode, model/version, references, start/end state, acceptance criteria, failure modes, and fallback.
- Delivery package now requires video prompt documentation and QC/iteration records when video output exists.
- README documents FFmpeg dependency and the distinction between technical checks and semantic review.
- `video_qc.py` works with FFmpeg alone when `ffprobe` is unavailable, and includes a macOS AVFoundation fallback for metadata/frame extraction.

### Clarified

- “Muse” remains ambiguous and unverified as a video-generation model; model-specific syntax is not invented.
- A successful QC script run is not a passing video verdict.
- Each iteration should change one primary variable and retain prior prompts, parameters, and evidence.

## v1.0.0 — 2026-10-27

- Initial release: script diagnosis, visual direction, Style Lock, character/scene consistency, shot list, production handoff, quality gates, and original demo.
