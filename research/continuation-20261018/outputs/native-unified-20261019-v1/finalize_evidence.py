from pathlib import Path
import hashlib
import json

root = Path(__file__).resolve().parent
continuation = root.parent.parent
def read(name):
    return json.loads((root/name).read_text(encoding='utf-8-sig'))
def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()

normal = read('evidence/unified-final/result.json')
scaled = read('evidence/unified-scale125/result.json')
cache = read('evidence/full-cache-balanced/result.json')
smokes = read('PACKAGED_SMOKE.json')
models = read('MODEL_INTEGRITY.json')
changes = read('source-changes.json')
assert all(item['status'] == 'passed' for item in (normal, scaled, cache))
assert all(item['exit_code'] == 0 for item in smokes)
assert len(models) == 7 and all(item['unchanged'] for item in models)
assert all(not item['file'].startswith(('src\\', 'include\\')) for item in changes)
assert '100% tests passed, 0 tests failed out of 13' in (root/'regression-console.txt').read_text(encoding='utf-8-sig')
assert sha(root/'app/frametrail-desktop.exe') == sha(root/'build/Release/frametrail-desktop.exe')

for name in ('Run-FrameTrail.cmd', 'Run-Balanced-Preview.cmd'):
    launcher = continuation/name
    if launcher.exists() and not (root/('PREVIOUS-'+name)).exists():
        (root/('PREVIOUS-'+name)).write_bytes(launcher.read_bytes())
    launcher.write_bytes(f'@echo off\r\ncall "%~dp0outputs\\{root.name}\\{name}" %*\r\n'.encode('utf-8'))

receipt = {
    'status': 'single-window-workspace-packaged-and-verified', 'date': '2026-10-19',
    'package': str(root), 'canonical_launcher': str(continuation/'Run-FrameTrail.cmd'),
    'application_sha256': sha(root/'app/frametrail-desktop.exe'),
    'sections': ['Preview', 'Analysis', 'Playback', 'Camera'],
    'single_visible_main_window_asserted': True,
    'navigation': 'Persistent checked sidebar, shared breadcrumb, Ctrl+1–4, per-section state',
    'background_policy': 'Analysis and preparation continue with activity badge; preview/review/cached playback pauses when hidden; camera stop is requested on leaving',
    'quit_policy': 'Await active analysis, preserve partial output, honor Save/Discard/Cancel, then stop all remaining workers before closing',
    'normal_integration': normal, 'Qt_scale125_integration': scaled,
    'existing_regression_checks_passed': 13, 'RF_full_cache': cache,
    'packaged_smoke': smokes, 'models_unchanged': 7,
    'inference_and_core_sources_unchanged_from_workflow_package': True,
    'default_model': 'YOLOX-S', 'production_adoption': False,
    'strict_numerical_export_gate_passed': False,
    'selected_RF_checkpoint': 'job 7805570 step 100',
    'selected_checkpoint_sha256': 'c1e7b571476a9bdc02533359dfe3f599afab98822aa90df265e9068f43f46bd3',
    'new_cluster_jobs': 0, 'SSH_attempts': 0,
    'cluster': 'User-reported outage; latest data task remains unconfirmed, no replacement or retry',
    'verification_limits': ['Current-run Qt offscreen captures, including simulated 125% scaling',
                            'No live-camera acquisition or physical monitor/screen-reader certification',
                            'No inference speedup or new accuracy claim',
                            'Legacy explicit RF smooth-launch flag routes to the shared window; that GPU preference was not exercised in this CPU pass'],
}
(root/'FINAL_RECEIPT.json').write_text(json.dumps(receipt, indent=2)+'\n', encoding='utf-8')

captured = root/'evidence/unified-final'
def picture(name, alt):
    return f'![{alt}]({(captured/name).as_posix()})'
report = f'''# FrameTrail — one workspace, four sections

Preview, Analysis, Smooth Playback and Camera now share one main window. Sidebar navigation keeps the selected section visible and retains each section's settings, results and prepared playback. Repeated navigation reuses existing sections. File pickers and save/discard prompts remain normal dialogs.

Launch the current build:

```powershell
& "{continuation / 'Run-FrameTrail.cmd'}"
```

The package also contains Run-FrameTrail.cmd and Run-Balanced-Preview.cmd. YOLOX-S remains the normal default; the balanced RF model remains an explicit experimental preview. The previous source, executables and sealed package receipts are preserved. Only the new continuation-level launchers point to this package.

## Flow and visual review

1. **Preview — healthy.** The shared sidebar, current-section breadcrumb and inspector keep the existing graphite/lavender design. Preview pauses when leaving. Existing inspector and tracking controls retain their identities and shortcuts. Ctrl+I applies only in Preview; its Space shortcut does not intercept controls in other sections.
2. **Analysis — healthy.** Analysis opens inside the content area. It can run while the user visits another section, with a persistent activity badge. Results, thumbnails and settings survive navigation. Save, CSV export and reopening passed; closing while active waits for partial results and still honors the unsaved-result choice.
3. **Playback — healthy.** A dedicated in-window preparation screen offers Choose video and Use preview video. The latter also copies Preview's model, threshold and device. Opening the section does not start work by itself. Prepared overlays persist when switching sections; playback pauses while hidden. Changing the selected source first releases the old cache and prevents stale overlays from being presented as the new video.
4. **Camera — idle navigation healthy.** The camera controls are embedded and retain settings. Opening the section does not acquire a camera. Leaving requests capture to stop. No actual camera was acquired in this check; live capture/driver shutdown still needs hardware verification.
5. **Background work — healthy.** The shared badge distinguishes Analysis running, Playback preparing and camera activity. Hidden preparation continues; closing during it stops workers and never promotes the incomplete cache.
6. **Compact and scaled layout — healthy within inspected captures.** The 1100×720 logical layout and simulated 125% Qt scaling preserve the navigation, video area and transport controls. Duplicate section branding was removed; empty Playback uses the same framed canvas and text hierarchy as the other sections.
7. **Quit — healthy.** Cancel in the quit prompt keeps the app and partial analysis available. Discard permits coordinated shutdown. Tested both active analysis and active preparation, including different lazy section-creation orders. Normal navigation causes no discard prompt and creates no second main window.

## Current-run screenshots

Analysis, inside the shared workspace:

{picture('02-analysis-empty.png', 'Analysis section with persistent navigation')}

Playback preparation entry:

{picture('03-playback-empty.png', 'Playback section with a consistent empty canvas')}

Camera section, with capture off:

{picture('04-camera-idle.png', 'Embedded camera controls with camera off')}

Retained analysis results:

{picture('06-analysis-results.png', 'Analysis results and appearances in the shared window')}

Prepared playback:

{picture('07-playback-ready.png', 'Prepared playback and shared navigation')}

Compact layout:

{picture('08-compact-playback.png', 'Compact shared playback workspace')}

Visible background preparation:

{picture('10-background-preparation.png', 'Preview section with visible playback preparation badge')}

Simulated 125% scaling:

![125% Qt scaling]({(root/'evidence/unified-scale125/08-compact-playback.png').as_posix()})

## Validation and limits

All **13 selected existing native regression checks passed**. The extended single-window suite passed at both 100% and 125% Qt scale, checking one visible QMainWindow, keyboard navigation, repeated switching, hidden-work indicators, retained results/cache, source replacement, save/CSV/reopen, camera-off entry and both quit decisions. The screenshots were saved and inspected. Functional captures deliberately use YOLOX-Nano for fast, bounded test work; the packaged default remains YOLOX-S.

The RF full-cache check also passed exact first-frame overlay parity, complete playback, pause, replay after making the test model unavailable, and closing. Both packaged standard and balanced smoke launches returned 0. Seven model hashes match the preceding workflow package. The detector, core and inference sources were not changed in this update. No new speed or accuracy claim is made, and the strict RF ONNX numerical gate remains held.

The camera-enumeration console reports no available devices in this environment; the app displayed Camera off and disabled Start. No camera frames were captured. Offscreen and simulated scale checks do not certify a physical monitor, screen reader or driver. The legacy explicit RF smooth-launch flag was routed through the shared window, but its automatic GPU preference was not exercised here. No KIT access, retrieval, submission, retry or replacement job occurred; the user's reported outage is still the latest state.

Evidence: FINAL_RECEIPT.json, MODEL_INTEGRITY.json, source-changes.json, regression-console.txt, PACKAGED_SMOKE.json and the per-run evidence folders.

Next step: try Preview → Analysis → Playback with a representative video on the actual display, because the unified flow is verified locally and that reveals remaining personal workflow friction.
'''
(root/'REPORT.md').write_text(report, encoding='utf-8')
(root/'USE.txt').write_text('FrameTrail: one window, four sections\n\nPreview / Analysis / Playback / Camera remain in the shared sidebar.\nCtrl+1, Ctrl+2, Ctrl+3, Ctrl+4 switch sections.\nAnalysis and preparation can continue in the background; the top badge shows activity.\nPlayback pauses while hidden. Leaving Camera requests capture to stop.\n\nPlayback: choose a video or copy the Preview video/settings, then Prepare playback.\nQuitting preserves the Save/Discard/Cancel choice for unsaved analyses.\n\nRun-FrameTrail.cmd uses the unchanged YOLOX-S default.\nRun-Balanced-Preview.cmd selects the unchanged held RF preview.\nSee REPORT.md for verification scope and screenshots.\n', encoding='utf-8')

handoff = continuation/'CURRENT_HANDOFF.md'
archive = root/'HANDOFF_BEFORE_UNIFIED.md'
if not archive.exists():
    archive.write_bytes(handoff.read_bytes())
note = f'''# Current FrameTrail state — unified app, 19 October 2026

The user's request to keep all app sections in one window is implemented and packaged. Current package:
{root}

Stable normal launcher: {continuation / 'Run-FrameTrail.cmd'}
Stable explicit RF preview launcher: {continuation / 'Run-Balanced-Preview.cmd'}

Preview, Analysis, Playback and Camera share a persistent sidebar and stacked content area. State is retained; Ctrl+1–4 switches sections. Analysis/preparation can continue with a global activity badge; hidden playback pauses; leaving Camera requests stop. Playback has an explicit preparation entry and releases old overlays when its source changes. Shared-window quit honors unsaved partial-analysis Save/Discard/Cancel before stopping all workers. Old source/build packages are preserved.

Verification: 13 selected existing native checks passed, the extended unified-window test passed at normal and simulated 125% Qt scale, full RF cache parity/pause/model-free replay passed, and both packaged smoke launches returned 0. Captures were inspected. Live camera hardware and physical-display/screen-reader behaviour remain unverified. Seven model hashes are unchanged. Core/detector/inference sources are unchanged from the preceding workflow package. Normal default remains YOLOX-S; RF remains the explicit job 7805570 step 100 preview, strict ONNX numerical qualification held, production_adoption=false.

KIT remains down according to the user. Latest data collection submission/completion is unconfirmed. No SSH, retrieval, retry, replacement or submission was attempted. Previously audited arrays 7809335/7818553 remain local and complete. Preserve all qualification, batching and no-retry gates.

Read REPORT.md and FINAL_RECEIPT.json in the current package for evidence. Carry all standing communication/autonomy instructions forward: continue authorized local work without routine permission prompts, and end every response with one concrete project next step and why.

Next step: use the unified Preview → Analysis → Playback flow with a representative project video on the actual display, because local functional and scale checks are complete and real-use feedback can identify the next refinement.

---

## Preserved prior handoff

'''
handoff.write_text(note+archive.read_text(encoding='utf-8-sig'), encoding='utf-8')
(root.parent/'LATEST_FRAMETRAIL_STATE_UNIFIED_READY.json').write_text(json.dumps({'status':receipt['status'],'package':str(root),'launcher':str(continuation/'Run-FrameTrail.cmd'),'cluster':receipt['cluster'],'production_adoption':False},indent=2)+'\n', encoding='utf-8')
print(json.dumps({'status':receipt['status'],'launcher':str(continuation/'Run-FrameTrail.cmd'),'models_unchanged':7,'regression_checks':13}))
