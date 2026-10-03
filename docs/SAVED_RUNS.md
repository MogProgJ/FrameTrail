# Video analysis and saved results (0.9)

Video analysis works directly from a recording. It no longer needs a counting line, enabled player tracking, or a destination filename before processing. The native CPU pipeline records **object appearances** with timestamps, then lets you review and save the result.

## Use the window

1. Open **Video analysis…** from the player. You can do this without opening media first.
2. **Choose video…**, or drag one video from File Explorer into the window. A video already open in the player is offered as the initial selection. Dropping a file selects it; processing starts when you click Analyse.
3. Optionally open **Analysis settings** to choose YOLOX-Nano or YOLOX-S and adjust confidence. All 80 model categories are considered. The player's selected model/confidence supply the initial settings, but player detection, tracking and counting-line switches are not prerequisites.
4. Click **Analyse video**. The window shows source-time progress and occasional analysed frames. Every decoded frame is processed in source order; the preview can skip frames independently. Long recordings can take substantial CPU time.
5. Review the appearance list. Each row shows an object label, first-seen time, last-seen time, and a thumbnail. Click it to open its first frame, paused. **Play** continues the original recording without inference; **Back to appearance** returns to that frame. IDs, observations and confidence are in the row tooltip.
6. Choose **Save analysis…** for a `.frametrail` file, or **Export CSV…** for a spreadsheet-readable report. Saving is optional and happens after processing. **Open analysis…** reopens a saved result, even without an installed model.

Analysis first writes to a unique temporary workspace. There is no pre-analysis filename collision. Before replacing or closing unsaved results, the window offers Save, Discard, or Cancel. Closing an active analysis requests cancellation, then offers the same choice for any partial result. Unsaved results are not a recovery mechanism after a crash; save results you want to keep.

The list loads at most 100 entries at once. Previous/Next appear only when needed. Playback controls, result actions and the results panel appear when a result is available. Model/confidence controls remain behind Analysis settings.

## What an appearance means

An appearance is the detections associated with one native tracker ID: first observation, last observation, observed-frame count, peak confidence, and a thumbnail of the first frame. Repeated observations update that row instead of generating a new row for each frame. Each run considers all model categories independently of the player's people/vehicle filter.

**These are predictions, not verified identities or a count of unique real objects.** Brief, single-frame predictions are retained. A wrong label can become an entry. Tracking can split one object into several appearances or merge nearby objects; cuts, camera movement, occlusion and crowded scenes are difficult. The first/last span may include short gaps with no detection, so it is not a continuous-presence or dwell-time measurement. The current model recognizes 80 categories and will miss objects outside them. See [model evaluation](MODEL_EVALUATION.md) and [tracking](TRACKING.md).

Times come from decoded source presentation timestamps, including variable frame rate. Original frame sequences are zero-based. Missing timestamps remain blank in CSV rather than being guessed. The displayed review frame has the saved first-observation box; subsequent playback does not invent new boxes or rerun inference.

The reader accepts video formats supported by the bundled FFmpeg build, including common MP4/MKV recordings. Not every codec/container has been verified. Missing, damaged and audio-only inputs report errors; still images are rejected by this video workflow. A valid recording with no predictions is a completed empty result. The main player still supports image detection.

## Saving and exporting

A `.frametrail` file is a SQLite database using application ID `FTRL` and schema **3**. It contains:

- Source/model paths and file stamps, selected Nano/S profile and frozen detector/tracker settings.
- A persistent random run identity, creation time, codec/dimensions/duration, committed progress, status and error.
- Appearance IDs, classes, first/last frame sequences and optional timestamps, observation counts, first/peak confidence, first box and embedded thumbnails.
- Crossing events for runs created through the existing CLI counting workflow.

Thumbnails are aspect-preserving RGB PPM images capped at 160 × 90, about 43 KB of pixel data at most per appearance. Full frames, continuous box histories and the video itself are not embedded. **Keep the source video separately** for playback. Long recordings with many fragmented tracks can produce large databases even though processing memory stays bounded.

CSV has one header and one row per appearance, with these columns:

| Column | Meaning |
| --- | --- |
| Object / Appearance ID | Predicted class and tracker ID scoped to this run |
| First seen / Last seen | Readable `HH:MM:SS.mmm` source timestamps |
| Span seconds | First-to-last span, three decimal places; may include detection gaps |
| Observations | Number of associated decoded frames |
| Peak confidence percent | Highest prediction confidence, two decimal places |
| First frame / Last frame | Original zero-based source sequences |
| First timestamp us / Last timestamp us | Exact stored microsecond timestamps, blank when unavailable |
| Video / Analysis status / Model / Run ID | Source filename, completion state, model profile and persistent run identity |

Exports use UTF-8 with a byte-order mark, CRLF row endings, quoted text and consistent numeric formatting. This preserves Unicode and comma-containing filenames in spreadsheet apps. CSV stores structured fields; column widths and fonts are controlled by the spreadsheet app, rather than simulated with padding spaces.

The desktop's native save dialog confirms replacement of existing destinations. Saving/exporting stages the file and commits through `QSaveFile`, so a failed operation preserves the existing destination. The source video, model and working database are protected from accidental replacement. The CLI refuses existing CSV destinations. Copying a saved file preserves its run identity; use Run ID plus Appearance ID when merging reports.

## Partial results and review

Cancel retains committed progress with `cancelled` status. An error after database creation retains a `failed` partial result. Both can be reviewed and saved/exported. Errors before database creation leave no fake completed result and allow another selection. An interrupted process can leave `running`, which is shown as incomplete. SQLite journal recovery may be required after an abrupt interruption; retain any adjacent journal. There is no resume-analysis command: reanalyse the source as a new run.

Review opens the database read-only and does not modify evidence. Missing models do not prevent browsing or export. Missing/changed source video leaves thumbnails and exports available but disables source playback. Restoring the original source to its original path restores review. File stamps use size/modification time, not a cryptographic content identity; automatic relinking is not implemented.

Native review seeks backward to a keyframe and decodes forward to the saved timestamp. Unsupported seeking or unsuitable timestamps use original sequence fallback, which can take time for late entries. Review uses a precise 5 ms timer and skips overdue presentation frames after a delayed UI tick. The selected first frame remains exact. Large-video decode/render costs can still cause uneven playback. Closing releases the review source handle.

Schema-1 and schema-2 files remain readable without migration. They display their original **line crossings**, not newly reconstructed object appearances. Older app versions cannot read schema 3. The CLI's `inspect --save-run` counting workflow remains available; `run --export` selects the CSV appropriate to the stored run type:

```powershell
.\build\windows-msvc\Release\frametrail.exe run output\recording.frametrail
.\build\windows-msvc\Release\frametrail.exe run output\recording.frametrail --export output\recording.csv
```

## Pipeline and validation

`AnalysisJob` owns one ordered decode → detect → track → write worker. `RunStore` wraps SQLite's native C API with C++ RAII. A frame's appearance updates, crossing events and progress commit together. Repeating an identical appearance observation does not inflate its count; conflicting IDs or reversed progress fail and roll back. Final counts come from committed rows.

One replaceable analysed-preview slot is published at most every 200 ms. Preview frames and detections share an owned snapshot; the worker never accesses Qt widgets. The UI holds a bounded page of results. A thumbnail is generated only when an appearance/event starts, not on every update. The whole video and result log do not accumulate in RAM. Decoder/model buffers, active tracks, resolution and database size still affect resource use; sustained measurements remain open.

SQLite 3.53.4's pinned C amalgamation is compiled into the core; no database server, Python service or cloud account is required. Dependencies remain acquired explicitly with `scripts/fetch-dependencies.ps1`.

The 0.9 native/desktop suite has 26 checks. Coverage includes real-model ordered appearances, transaction rollback/idempotency, readable CSV/run identities, unknown timestamps, Unicode paths, empty detections, invalid/audio/still input, drag/drop rejection/acceptance, cancellation and close-time partial retention, protected destinations, saving/reopening, missing sources, legacy schemas, exact seeking, database immutability and 60 FPS review timing. The intake flow also completed on the user's supplied local 10-second clip. This validates the workflow, not detector accuracy. Native File Explorer interaction, file dialogs, additional DPI settings and sustained long-recording resource use still need manual validation.
