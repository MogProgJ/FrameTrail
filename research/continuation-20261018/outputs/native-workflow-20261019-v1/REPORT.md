# FrameTrail local video workflow pass — 19 October 2026

The updated native app is packaged beside this report. Open `Run-FrameTrail.cmd` for the existing YOLOX-S default, or `Run-Balanced-Preview.cmd` for the explicit experimental RF preview. Both use the unchanged model bytes. The previous package and original project source are preserved.

## Findings and repairs

1. **Preparation: improved.** Previously a blank canvas remained throughout preparation. The current run now shows the latest processed frame and detections while preparation continues. One preview is retained in the worker, refreshed at most twice per second. Elapsed wall time, processing FPS and an approximate time-left estimate make CPU cost visible. Initial/model-opening and insufficient/unknown timestamp states avoid premature estimates.
2. **Compact layout: checked.** The 800×560 capture keeps progress, preview and cancellation controls visible, with the existing design and readable text.
3. **Cancel preparation: fixed.** Before the change, clicking Cancel showed “Stopping preparation…” and then reverted to “Preparing … cancel anytime” while stopping. The new stopping state persists. An interrupted cache remains unusable; it is never promoted to a completed cache.
4. **Analysis: improved.** Running analysis shows progress and a preview. Later detection boxes were being painted with the previous label's dark brush, obscuring the video. Each box now explicitly uses no fill. A pixel-level regression checks that a second box leaves its interior unchanged.
5. **Cancel/save/export: checked.** Requested cancellation retains partial frames and appearances. Saving and CSV export succeed. Raw runtime termination diagnostics stay in the saved data and tooltip; the main status presents cancellation and partial results clearly.
6. **Reopen: checked.** Reopening preserves cancelled status, frame count and stored appearances. The existing regression suite also checks missing-source thumbnails, unsaved-result prompts, close while active, source/model protection and save/export behaviour.
7. **Failure: improved.** A missing model produces a clear failure state and recovery instruction, rather than leaving the centre saying it is still preparing.

## Measurement and checks

RF baseline median detector time: **606.8 ms/frame**. Inference accounts for **98.1%** of those samples. This confirms that changing GUI paint or progress text alone cannot remove most RF CPU cost. No inference-speed improvement is claimed: the five-frame samples are short, repeated-image workloads and system load varies.

Updated RF cancellation observed by the test UI: cache **76.8 ms**, analysis **85.8 ms**. Standard model: cache **38.6 ms**, analysis **52.8 ms**. These include an intentional 30 ms observation wait and polling; they are not a cross-machine latency guarantee. The RF cache cancellation probe stops after ten prepared frames; the saved-analysis probe stops after the first preview.

All **13 selected existing regression checks passed**. Both new standard/RF diagnostics passed, including bounded preview, stable cancellation text, saved partial status, reopen and missing-model handling. Feedback contracts cover unknown duration, timestamp offset, initial samples and stalled timestamps. Full 16-frame RF cache preparation completed in **9.18 seconds**; exact first-frame overlay parity, complete playback, pause, replay without a model and closing passed. This short fixture does not establish general real-time throughput. Packaged standard and balanced smoke launches both returned 0, offscreen.

The RF diagnostic's UI heartbeat p95 was 32.5 ms and maximum 225.5 ms. Those observations include screenshot capture, layout, save and reopen; they do not isolate steady-state rendering or prove a responsiveness improvement.

## Captured evidence

Current-run Qt offscreen captures were saved and inspected. The first diagnostic's fontless captures were rejected for visual review; the diagnostic was repaired to load the installed system font. The `05-analysis-partial.png` capture was also excluded from this visual report because it caught the thumbnail-to-decoder transition. Save/export success is checked from persisted data and the regression results instead.

Before: preparation canvas remained blank.

![Before: preparation without a video preview](C:/Users/nazee/Documents/Codex/2026-10-18/frametrail-continuation/outputs/native-workflow-20261019-v1/evidence/baseline/balanced-readable/01-cache-preparing.png)

After, step 1: preview and progress during preparation.

![Step 1: preparation with bounded preview and time estimate](C:/Users/nazee/Documents/Codex/2026-10-18/frametrail-continuation/outputs/native-workflow-20261019-v1/evidence/updated/balanced/01-cache-preparing.png)

Step 2: compact window.

![Step 2: compact preparation layout](C:/Users/nazee/Documents/Codex/2026-10-18/frametrail-continuation/outputs/native-workflow-20261019-v1/evidence/updated/balanced/02-cache-compact.png)

Step 3: cancelled preparation cannot play an incomplete cache.

![Step 3: cancelled preparation](C:/Users/nazee/Documents/Codex/2026-10-18/frametrail-continuation/outputs/native-workflow-20261019-v1/evidence/updated/balanced/03-cache-cancelled.png)

Before: later boxes inherited a dark fill from label painting.

![Before: filled detection boxes obscured the video](C:/Users/nazee/Documents/Codex/2026-10-18/frametrail-continuation/outputs/native-workflow-20261019-v1/evidence/baseline/balanced-readable/04-analysis-running.png)

After, step 4: clean unfilled detection boxes while analysing.

![Step 4: analysis with unfilled detection boxes](C:/Users/nazee/Documents/Codex/2026-10-18/frametrail-continuation/outputs/native-workflow-20261019-v1/evidence/updated/balanced/04-analysis-running.png)

Steps 5–6: saved partial analysis reopened with appearances and clear status.

![Steps 5 and 6: reopened partial analysis](C:/Users/nazee/Documents/Codex/2026-10-18/frametrail-continuation/outputs/native-workflow-20261019-v1/evidence/updated/balanced/06-analysis-reopened.png)

Step 7: missing-model failure.

![Step 7: missing-model recovery message](C:/Users/nazee/Documents/Codex/2026-10-18/frametrail-continuation/outputs/native-workflow-20261019-v1/evidence/updated/balanced/07-cache-failed.png)

## Limits and current project state

This was an offscreen native workflow check, not a screen-reader audit, a physical display/high-DPI review or a full accessibility certification. Screenshots support visible hierarchy, text and 800×560 layout findings; Windows keyboard/assistive-technology behaviour still needs a dedicated check. Repeated sample frames test application behaviour, not new model accuracy. No detection thresholds, model weights, source release, adoption gates or existing qualification results were changed. The strict ONNX numerical gate remains held; the RF build is still an explicit preview and production adoption remains false.

KIT is unavailable according to the user. No SSH, retrieval or new submission was attempted. Completion of the newest data collection is unconfirmed. Previously retrieved/audited arrays 7809335 and 7818553 remain local and complete; the outage does not undo those results. Do not retry or replace a potentially existing cluster task.

Detailed receipts: `FINAL_RECEIPT.json`, `MODEL_INTEGRITY.json`, `source-changes.json`, `regression-console.txt`, diagnostic result files and `PACKAGED_SMOKE.json`. The initial diagnostic build/fixture mistakes are preserved in their console files and were corrected before accepted runs.

Next step: exercise the updated app with a representative project video, because the automated fixture verifies behaviour but cannot establish how the user's normal clips feel.
