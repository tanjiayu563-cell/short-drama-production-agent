# Changelog

## v1.3.0 — 2026-11-03

### Added

- Selection-level adaptation rules for deciding visual action, dialogue, voice-over, off-screen sound, text inserts, performance, or omission.
- Scene-level relationship mapping with explicit versus inferred relationships, power distance, concealment, and spatial blocking.
- Anti-repetition shot grammar and a selection-to-beat workbench that produces up to six differentiated beats.
- Workbench relationship display, beat cards, apply-to-shot action, and copyable storyboard plan.

### Changed

- The Agent now produces a visual/narration allocation table, relationship map, and shot-variety audit before final prompts.
- The local workbench can distinguish dialogue, internal thought, text clues, sound cues, action, and exposition before generating prompts.

## v1.2.0 — 2026-11-03

### Added

- MiniMax H3 model adapter with official capability notes, multimodal reference roles, 4–15 second constraints, and consistency-card requirements.
- Local single-file novel-to-shot workbench: import `.txt`/`.md`/unencrypted `.epub`, select a passage, match assets, import reference images or descriptions, and generate MiniMax H3 prompts.
- Workbench project export/import, local autosave, prompt character counter, reference-count warnings, history, and Markdown export.
- MiniMax H3 prompt template and end-to-end example.

### Changed

- Asset consistency now tracks character, scene, and prop IDs, aliases, descriptions, locks, image files, and reference order.
- The workbench switches text-only references to T2V and uses reference generation only when image assets are present.
- Prompt drafts expose H3 mode, duration, resolution, aspect ratio, camera command, style lock, sound, continuity, and edit boundaries.

### Clarified

- MiniMax is the brand name; the API model name is `MiniMax-H3`.
- The workbench handles plain text, Markdown, and unencrypted EPUB in-browser; complex `.docx` layout is not parsed directly.

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
