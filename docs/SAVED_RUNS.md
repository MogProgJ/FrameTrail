# Saved analysis and event review

The player is useful for checking a model and drawing a line. Its counters describe the current preview segment and reset when settings change. A **saved run** instead analyses the entire recording from the beginning with one frozen configuration. Seeking, playback, and later player edits cannot change that run's counts.

## Try the workflow

1. Open a recording in the player. Enable **Detect objects (CPU)** and **Track & count**, select classes/confidence/direction, and draw the counting line.
2. Click **Saved analysis…**. The player pauses. This window captures the current source and settings; close it and reopen from the player if you want a different configuration.
3. Click **Analyse entire recording…** and choose a **new** `.frametrail` filename. Analysis runs on the CPU independently of playback speed. The window reports processed frames, source time, and events. CPU analysis of a long movie may take substantial time; no speed guarantee is implied.
4. On completion, browse the crossing events. Each row includes a thumbnail, timestamp, class, track ID, event ID, direction, and original zero-based frame sequence. Zero events is a valid result, especially with unsuitable footage or a line that nothing crosses.
5. Click a row or its timeline marker. The original event frame opens, paused. **Play from event** plays the subsequent source footage without inference. **Back to selected event** returns to that frame. There are no regenerated boxes/trails in review; the saved counting line remains visible.
6. Use **Export events CSV…** with a new filename. Later, choose **Open saved run…** from the same window, even without a current media file or installed model.

The list holds at most 100 events. Previous/Next buttons navigate pages; timeline markers belong to the displayed page. Unknown-time events appear in the list without a timeline marker. A single-frame image cannot produce a crossing event.

## What is saved

Each `.frametrail` file is one SQLite database, using schema version 1 and application ID `FTRL`. It contains:

- Absolute source/model paths, file sizes and modification times, creation time, and the adapter/runtime/tracker version contract.
- Detector confidence/NMS thresholds, tracked COCO classes, normalized line endpoints, direction, deadband, and re-arm distance.
- Initial media dimensions/codec/duration, committed frame progress, last source timestamp, and analysis status/error.
- Event IDs, source sequences, optional presentation timestamps in microseconds, track IDs, classes, crossing direction/position, and thumbnails.

Thumbnails are aspect-preserving RGB PPM blobs capped at 160×90. The format avoids a separate image-codec dependency and thumbnail sidecar files. At most roughly 43 KB of pixel data is stored per event; large event collections still consume disk space. Full frames, continuous box histories, and the video itself are not copied into the database. Keep the source recording separately.

Each run has a persistent random 128-bit identity, included in CSV. Event/track IDs are scoped to that run; combine run ID and event ID when merging exports. Copying or renaming the saved file preserves its run identity. Settings are fixed for the run. A rerun uses a new file/identity and does not overwrite previous evidence.

## Reliability and partial results

`AnalysisJob` owns one ordered decode → detect → track → write worker. `RunStore` owns SQLite through a C++ RAII wrapper around its C API. Each frame's events and progress are committed in one transaction. Repeating an identical event ID does not insert another event; a conflicting ID fails and rolls back the transaction. Storage errors fail the analysis rather than silently dropping events. Counts are derived from committed event rows.

**Cancel analysis** and closing the window request cancellation and retain committed results with `cancelled` status. Errors after database creation produce `failed` partial results. An interrupted process may leave `running`, which the UI labels **Interrupted / unfinished**; it is not a completed analysis. An abrupt interruption during a SQLite transaction can also require journal recovery before read-only review succeeds. Preserve the database and any adjacent journal if recovery is needed. No resume-analysis command is implemented; run the source again into a new file.

Review opens SQLite read-only. Missing models do not prevent browsing/export. Missing or changed sources leave thumbnails and CSV available but disable source playback. Restoring the original recording to its original path restores review. File size/modification-time checks detect ordinary changes; they are not a cryptographic content identity, and automatic relinking is not implemented.

Native seeking goes backward to a keyframe, flushes decoder state, and decodes forward to the saved timestamp. If seeking is unsupported or the recording has unknown/repeated/non-increasing timestamps, review decodes from the beginning to the saved frame sequence. This preserves identity but may take time for late events. After a fast seek, decoder sequences are local decode ordinals, so review shows source timestamps rather than presenting them as original frame numbers. The event list retains the original analysis sequence.

Version 0.6 improves review playback timing: a precise 5 ms timer replaces the previous 20 ms polling ceiling, and a delayed UI tick selects the newest due frame instead of slowly presenting every overdue frame. The selected event still opens on its exact frame. Only presentation frames may be skipped; stored analysis stays unchanged. A 60 FPS regression test covers clock progress, catching up after a blocked UI tick, and pause continuity. Large-video decoding/rendering limits can still cause uneven playback.

Exports preserve unknown timestamps as empty fields, quote text fields, and preserve UTF-8 paths. Existing output files are refused. Failed writes remove the new partial CSV when possible and report the failure. The saved run is unchanged by export.

## CLI equivalent

```powershell
New-Item -ItemType Directory -Path output -Force
.\build\windows-msvc\Release\frametrail.exe inspect "C:\Videos\entrance.mp4" --detect models\yolox_nano.onnx --track --line 0.1,0.5,0.9,0.5 --save-run output\entrance.frametrail
.\build\windows-msvc\Release\frametrail.exe run output\entrance.frametrail
.\build\windows-msvc\Release\frametrail.exe run output\entrance.frametrail --export output\entrance-events.csv
```

`--save-run` requires detection/tracking and rejects `--max-frames` so a limited sample cannot be reported as a complete recording. Source/model files are required only for analysis and source playback. Saved-run inspection/export does not run inference. The CLI relies on OS process interruption; use desktop cancellation for a graceful partial result.

## Dependency and checks

SQLite 3.53.4 is compiled from its official amalgamation as C, linked statically into the C++ core, and pinned in `dependencies/sqlite.json`. The downloaded archive's SHA3-256 was checked against the [publisher's download page](https://sqlite.org/download.html); the acquisition script verifies the committed SHA-256. Run `scripts/fetch-storage.ps1`, or the normal dependency script, before building. No database server or system-wide installation is required. SQLite source is [public domain](https://sqlite.org/copyright.html).

Automated checks cover transaction rollback, idempotency, bounded pagination, settings round trips, UTF-8/comma-containing paths, CSV failures/overwrite refusal, partial states, missing/changed sources, VFR and delayed-frame seeking, sequence fallback, inference isolation, and cancellation. A controlled translated reference photo produces one saved event at source frame 4 / 400,000 µs through the real model and native tracker. Desktop checks exercise analysis, thumbnail selection, seeking, playback, reopening without a model, and byte-for-byte database immutability. This is integration evidence, not accuracy evidence on real people/vehicle footage. Representative footage and sustained memory/disk/throughput measurements remain open.
