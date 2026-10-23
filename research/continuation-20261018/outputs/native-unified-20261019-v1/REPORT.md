# FrameTrail — one workspace, four sections

Preview, Analysis, Smooth Playback and Camera now share one main window. Sidebar navigation keeps the selected section visible and retains each section's settings, results and prepared playback. Repeated navigation reuses existing sections. File pickers and save/discard prompts remain normal dialogs.

Launch the current build:

```powershell
& "C:\Users\nazee\Documents\Codex\2026-10-18\frametrail-continuation\Run-FrameTrail.cmd"
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

![Analysis section with persistent navigation](C:/Users/nazee/Documents/Codex/2026-10-18/frametrail-continuation/outputs/native-unified-20261019-v1/evidence/unified-final/02-analysis-empty.png)

Playback preparation entry:

![Playback section with a consistent empty canvas](C:/Users/nazee/Documents/Codex/2026-10-18/frametrail-continuation/outputs/native-unified-20261019-v1/evidence/unified-final/03-playback-empty.png)

Camera section, with capture off:

![Embedded camera controls with camera off](C:/Users/nazee/Documents/Codex/2026-10-18/frametrail-continuation/outputs/native-unified-20261019-v1/evidence/unified-final/04-camera-idle.png)

Retained analysis results:

![Analysis results and appearances in the shared window](C:/Users/nazee/Documents/Codex/2026-10-18/frametrail-continuation/outputs/native-unified-20261019-v1/evidence/unified-final/06-analysis-results.png)

Prepared playback:

![Prepared playback and shared navigation](C:/Users/nazee/Documents/Codex/2026-10-18/frametrail-continuation/outputs/native-unified-20261019-v1/evidence/unified-final/07-playback-ready.png)

Compact layout:

![Compact shared playback workspace](C:/Users/nazee/Documents/Codex/2026-10-18/frametrail-continuation/outputs/native-unified-20261019-v1/evidence/unified-final/08-compact-playback.png)

Visible background preparation:

![Preview section with visible playback preparation badge](C:/Users/nazee/Documents/Codex/2026-10-18/frametrail-continuation/outputs/native-unified-20261019-v1/evidence/unified-final/10-background-preparation.png)

Simulated 125% scaling:

![125% Qt scaling](C:/Users/nazee/Documents/Codex/2026-10-18/frametrail-continuation/outputs/native-unified-20261019-v1/evidence/unified-scale125/08-compact-playback.png)

## Validation and limits

All **13 selected existing native regression checks passed**. The extended single-window suite passed at both 100% and 125% Qt scale, checking one visible QMainWindow, keyboard navigation, repeated switching, hidden-work indicators, retained results/cache, source replacement, save/CSV/reopen, camera-off entry and both quit decisions. The screenshots were saved and inspected. Functional captures deliberately use YOLOX-Nano for fast, bounded test work; the packaged default remains YOLOX-S.

The RF full-cache check also passed exact first-frame overlay parity, complete playback, pause, replay after making the test model unavailable, and closing. Both packaged standard and balanced smoke launches returned 0. Seven model hashes match the preceding workflow package. The detector, core and inference sources were not changed in this update. No new speed or accuracy claim is made, and the strict RF ONNX numerical gate remains held.

The camera-enumeration console reports no available devices in this environment; the app displayed Camera off and disabled Start. No camera frames were captured. Offscreen and simulated scale checks do not certify a physical monitor, screen reader or driver. The legacy explicit RF smooth-launch flag was routed through the shared window, but its automatic GPU preference was not exercised here. No KIT access, retrieval, submission, retry or replacement job occurred; the user's reported outage is still the latest state.

Evidence: FINAL_RECEIPT.json, MODEL_INTEGRITY.json, source-changes.json, regression-console.txt, PACKAGED_SMOKE.json and the per-run evidence folders.

Next step: try Preview → Analysis → Playback with a representative video on the actual display, because the unified flow is verified locally and that reveals remaining personal workflow friction.
