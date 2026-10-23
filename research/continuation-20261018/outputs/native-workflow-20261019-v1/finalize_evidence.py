from pathlib import Path
import hashlib
import json
import statistics

root = Path(__file__).resolve().parent
def read(relative):
    return json.loads((root / relative).read_text(encoding='utf-8-sig'))
def sha(path):
    return hashlib.file_digest(path.open('rb'), 'sha256').hexdigest()

before = read('evidence/baseline/balanced-readable/result.json')
after = read('evidence/updated/balanced/result.json')
standard = read('evidence/updated/standard/result.json')
cache = read('evidence/full-cache-balanced/result.json')
smokes = read('PACKAGED_SMOKE.json')
models = read('MODEL_INTEGRITY.json')
assert all(r['status'] == 'passed' for r in [before, after, standard, cache])
assert all(r['exit_code'] == 0 for r in smokes)
assert all(m['unchanged'] for m in models) and len(models) == 7
assert '100% tests passed, 0 tests failed out of 13' in (root/'regression-console.txt').read_text(encoding='utf-8-sig')
prior = root.parent / 'native-balanced-7805570-20261018-v1'
assert all(sha(prior/'source'/name) == value for name, value in read('baseline-source-sha256.json').items())

receipt = {
    'status': 'local-workflow-fixes-packaged-and-verified', 'date': '2026-10-19',
    'application_sha256': sha(root/'app/frametrail-desktop.exe'),
    'default_model': 'YOLOX-S', 'models_unchanged': 7, 'model_integrity': 'MODEL_INTEGRITY.json',
    'source_changes': 'source-changes.json', 'prior_source_preserved': True,
    'regression_checks_passed': 13, 'workflow_diagnostics': {'balanced': after, 'standard': standard},
    'full_cached_playback': cache, 'packaged_smoke': smokes,
    'fixes': ['Cancellation feedback remains stopping until completion',
              'Preparation preview is bounded to one worker frame, refreshed at most twice per second',
              'Elapsed time, measured processing FPS and approximate remaining time',
              'ETA accounts for timestamp origin; missing/stalled/early timestamps do not produce an estimate',
              'Detection boxes have no fill; label brush no longer obscures later objects',
              'Requested cancellation keeps raw diagnostics in saved data/tooltip, with clear partial-result wording',
              'Missing-model and cancelled-before-preview states replace the misleading preparation placeholder'],
    'performance_scope': 'Five detector samples per run, repeated sample video, CPU only. Not an accuracy or controlled speedup study.',
    'ui_heartbeat_scope': 'Includes screenshot capture, initial layout, save and reopen. Not a rendering SLA or screen-reader check.',
    'visible_app_launched': False, 'capture_tool': 'Qt offscreen QWidget.grab, current run, explicitly loaded system font',
    'new_cluster_jobs': 0, 'SSH_attempts': 0, 'cluster_state': 'user-reported outage; latest data-job status unconfirmed',
    'training_updates': 0, 'strict_numerical_export_gate_passed': False, 'production_adoption': False,
    'selected_checkpoint': 'job 7805570 step 100',
    'selected_checkpoint_sha256': 'c1e7b571476a9bdc02533359dfe3f599afab98822aa90df265e9068f43f46bd3',
}
(root/'FINAL_RECEIPT.json').write_text(json.dumps(receipt, indent=2)+'\n', encoding='utf-8')

base = root/'evidence/baseline/balanced-readable'
current = root/'evidence/updated/balanced'
def picture(path, alt):
    return f'![{alt}]({path.as_posix()})'
report = f'''# FrameTrail local video workflow pass — 19 October 2026

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

RF baseline median detector time: **{statistics.median(s['total_ms'] for s in before['frame_samples']):.1f} ms/frame**. Inference accounts for **{100*sum(s['inference_ms'] for s in before['frame_samples'])/sum(s['total_ms'] for s in before['frame_samples']):.1f}%** of those samples. This confirms that changing GUI paint or progress text alone cannot remove most RF CPU cost. No inference-speed improvement is claimed: the five-frame samples are short, repeated-image workloads and system load varies.

Updated RF cancellation observed by the test UI: cache **{after['cache_cancel_ms']:.1f} ms**, analysis **{after['analysis_cancel_ms']:.1f} ms**. Standard model: cache **{standard['cache_cancel_ms']:.1f} ms**, analysis **{standard['analysis_cancel_ms']:.1f} ms**. These include an intentional 30 ms observation wait and polling; they are not a cross-machine latency guarantee. The RF cache cancellation probe stops after ten prepared frames; the saved-analysis probe stops after the first preview.

All **13 selected existing regression checks passed**. Both new standard/RF diagnostics passed, including bounded preview, stable cancellation text, saved partial status, reopen and missing-model handling. Feedback contracts cover unknown duration, timestamp offset, initial samples and stalled timestamps. Full 16-frame RF cache preparation completed in **{cache['preparation_seconds']:.2f} seconds**; exact first-frame overlay parity, complete playback, pause, replay without a model and closing passed. This short fixture does not establish general real-time throughput. Packaged standard and balanced smoke launches both returned 0, offscreen.

The RF diagnostic's UI heartbeat p95 was {after['ui_heartbeat_p95_gap_ms']:.1f} ms and maximum {after['ui_heartbeat_max_gap_ms']:.1f} ms. Those observations include screenshot capture, layout, save and reopen; they do not isolate steady-state rendering or prove a responsiveness improvement.

## Captured evidence

Current-run Qt offscreen captures were saved and inspected. The first diagnostic's fontless captures were rejected for visual review; the diagnostic was repaired to load the installed system font. The `05-analysis-partial.png` capture was also excluded from this visual report because it caught the thumbnail-to-decoder transition. Save/export success is checked from persisted data and the regression results instead.

Before: preparation canvas remained blank.

{picture(base/'01-cache-preparing.png', 'Before: preparation without a video preview')}

After, step 1: preview and progress during preparation.

{picture(current/'01-cache-preparing.png', 'Step 1: preparation with bounded preview and time estimate')}

Step 2: compact window.

{picture(current/'02-cache-compact.png', 'Step 2: compact preparation layout')}

Step 3: cancelled preparation cannot play an incomplete cache.

{picture(current/'03-cache-cancelled.png', 'Step 3: cancelled preparation')}

Before: later boxes inherited a dark fill from label painting.

{picture(base/'04-analysis-running.png', 'Before: filled detection boxes obscured the video')}

After, step 4: clean unfilled detection boxes while analysing.

{picture(current/'04-analysis-running.png', 'Step 4: analysis with unfilled detection boxes')}

Steps 5–6: saved partial analysis reopened with appearances and clear status.

{picture(current/'06-analysis-reopened.png', 'Steps 5 and 6: reopened partial analysis')}

Step 7: missing-model failure.

{picture(current/'07-cache-failed.png', 'Step 7: missing-model recovery message')}

## Limits and current project state

This was an offscreen native workflow check, not a screen-reader audit, a physical display/high-DPI review or a full accessibility certification. Screenshots support visible hierarchy, text and 800×560 layout findings; Windows keyboard/assistive-technology behaviour still needs a dedicated check. Repeated sample frames test application behaviour, not new model accuracy. No detection thresholds, model weights, source release, adoption gates or existing qualification results were changed. The strict ONNX numerical gate remains held; the RF build is still an explicit preview and production adoption remains false.

KIT is unavailable according to the user. No SSH, retrieval or new submission was attempted. Completion of the newest data collection is unconfirmed. Previously retrieved/audited arrays 7809335 and 7818553 remain local and complete; the outage does not undo those results. Do not retry or replace a potentially existing cluster task.

Detailed receipts: `FINAL_RECEIPT.json`, `MODEL_INTEGRITY.json`, `source-changes.json`, `regression-console.txt`, diagnostic result files and `PACKAGED_SMOKE.json`. The initial diagnostic build/fixture mistakes are preserved in their console files and were corrected before accepted runs.

Next step: exercise the updated app with a representative project video, because the automated fixture verifies behaviour but cannot establish how the user's normal clips feel.
'''
(root/'REPORT.md').write_text(report, encoding='utf-8')
(root/'USE.txt').write_text('FrameTrail — local workflow update, 19 October 2026\n\nRun-FrameTrail.cmd: normal YOLOX-S default.\nRun-Balanced-Preview.cmd: unchanged explicit experimental RF preview.\n\nNew: preparation preview, elapsed time/rate/approximate time left, stable Cancel feedback, clear partial-result wording, unfilled detection boxes.\n\nNo cluster access is needed. The selected RF model remains a preview; strict export qualification is still held.\nSee REPORT.md and FINAL_RECEIPT.json for measured scope and checks.\n', encoding='utf-8')

continuation = root.parent.parent
handoff = continuation/'CURRENT_HANDOFF.md'
archive = root/'HANDOFF_BEFORE_WORKFLOW.md'
if not archive.exists():
    archive.write_bytes(handoff.read_bytes())
note = f'''# Current FrameTrail state — 19 October 2026

The user reports KIT is down indefinitely. No SSH, status, retrieval or submission was attempted during this app-side pass. The newest data collection's submission/completion is unconfirmed; do not assume it finished or create a replacement. Arrays 7809335 and 7818553 were previously retrieved and independently audited locally. Preserve all existing cluster evidence and no-retry policy.

Authorized local video usability/performance work is complete and packaged:
{root}

Use Run-FrameTrail.cmd in that folder for the existing YOLOX-S default; Run-Balanced-Preview.cmd is the unchanged explicit RF preview. Fixes: persistent stopping feedback, bounded preparation preview, elapsed/FPS/approximate remaining time, no label-brush fill leaking into detection boxes, clear cancelled partial-result wording, corrected preparation failure state. All 13 selected existing native checks passed; both workflow diagnostics, exact full-cache overlay/pause/model-free replay checks, and both packaged smoke launches passed. Seven packaged model hashes are unchanged; original source and older package are preserved.

RF CPU inference remains the main measured cost (~98% of sampled detector processing). No inference speedup or new model accuracy is claimed. The user can use the app while KIT is unavailable. Strict ONNX numerical qualification remains held, production_adoption=false, current RF checkpoint remains job 7805570 step 100 (c1e7b571476a9bdc02533359dfe3f599afab98822aa90df265e9068f43f46bd3).

Evidence and scope: REPORT.md, FINAL_RECEIPT.json, MODEL_INTEGRITY.json and SCOPE.json in the new folder. Offscreen captures were inspected; physical display/high-DPI/assistive-technology checks remain unverified. Do not repeat the completed model trials or numerical export alternatives without reviewing the detailed earlier evidence below.

Carry all standing communication/autonomy/batching instructions into continuations. End responses with one concrete project next step and why. Continue useful local work without routine approval prompts; do not contact KIT while the outage remains the latest known condition.

Next step: exercise the updated package with a representative project video, because synthetic workflow checks cannot establish real-clip usability. When KIT access returns, check/retrieve the existing data task once using the prepared tools, with no replacement submission.

---

## Preserved earlier model/data handoff

'''
handoff.write_text(note+archive.read_text(encoding='utf-8-sig'), encoding='utf-8')
latest = {'status': receipt['status'], 'package': str(root), 'cluster': receipt['cluster_state'], 'production_adoption': False,
          'next_step': 'Use a representative project video to assess the verified local workflow; retain existing cluster tasks during outage.'}
(root.parent/'LATEST_FRAMETRAIL_STATE_WORKFLOW_READY.json').write_text(json.dumps(latest,indent=2)+'\n', encoding='utf-8')
print(json.dumps({'status':receipt['status'],'checks':13,'models_unchanged':7,'report':str(root/'REPORT.md')}))
