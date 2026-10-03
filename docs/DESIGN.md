# Desktop workspace design

The 0.7 refresh keeps the native C++/Qt application. It uses Product Design's
screen-audit guidance and Qt's UI Compiler (`uic`) to turn the Qt Designer
`apps/desktop/preview_layout.ui` form into the main workspace. The form can be
opened in Qt Designer or Qt Creator for future visual editing. Designer itself
was not installed or driven during this change. No Figma document or generated
web mockup is substituted for the working desktop application.

## Observed flow and changes

1. **Open media / inspect detections.** A fresh offscreen capture of the old
   1080×720 window showed three wide control rows above a short video viewport.
   The new 1280×820 workspace puts analysis settings in a scrollable right-hand
   inspector; the video becomes the primary surface. Open media is the single
   accented header action.
2. **Configure tracking / draw a line.** Controls are grouped by analysis,
   tracking and session counts, with visible labels and a short line-edit hint.
   Existing timestamp-preserving interactions remain covered by desktop tests.
3. **Live camera entry.** The window describes exactly what Start does, shows
   camera state, and separates source/settings from the preview and Start/Stop.
   Merely opening the window enumerates devices without starting capture.
4. **Saved review.** The shared theme keeps typography, buttons, selected events
   and focus states consistent with the player; saved-run behaviour is retained.

## Visual system and verification

`theme.hpp` centralizes slate surfaces, mint primary actions, readable muted text,
6px controls, larger panel corners and visible keyboard focus borders. Segoe UI
uses the installed Windows font; no font files are redistributed. Labels and
accessible names identify key inputs. The inspector scrolls at smaller supported
sizes instead of hiding controls beyond the window.

Qt integration tests capture the actual widgets with generated/sample media and
exercise playback and reconfiguration. Screenshots support layout inspection;
they do not establish screen-reader, high-contrast or full accessibility compliance.
Those, native dialog behaviour and additional DPI settings still require testing.

## Video analysis refresh (0.9)

The recorded workflow now starts with **Choose video** or a local file drop. A single **Analyse video** action uses the existing native pipeline. It does not ask for a counting line or output filename. Model and confidence sit behind **Analysis settings**. The source label shows the basename, with its path in a tooltip.

The empty state gives the video area the full width. During processing, a narrow progress bar and occasional analysed frames provide feedback. After completion, a compact appearance list sits beside the large review viewport; entries show labels and first/last times. Counts occupy one status line; IDs, observation count and peak confidence are in tooltips. Save/CSV and playback controls appear only with results, while paging appears only for larger lists. The old technical configuration paragraph, timeline row and crossing setup are absent from new analyses.

This is implemented in native Qt Widgets in `saved_run_window.cpp`, using the shared theme. Actual-widget captures cover empty, completed and 920 × 620 layouts. Automated Qt drag/drop events cover local Unicode paths, unsupported drops and active-job rejection. Tests exercise unsaved prompts, partial cancellation/close, review, saving/export and reopening. Native File Explorer dragging, system dialogs, screen readers, high contrast and additional DPI settings remain manual checks. No new design-tool service or frontend framework was added.

## Small player polish in 0.10

The player/live settings gain one Processing device selector. The existing frame-detail line reports the actual CPU/GPU path; runtime/device/fallback detail stays in a tooltip. A muted blue accent on main-player details and a 160 ms source-label fade provide subtle colour/motion without animating video or blocking analysis. CPU-specific checkbox/timing wording is neutral when either backend is available.

The saved-analysis layout, theme, intake and review controls remain as shipped in 0.9. It inherits the player preference when opened. Real Qt captures and an opt-in GPU desktop test check switching without a timestamp/resolution reset and saved-analysis save/export on the same flow. Camera testing remains file/synthetic or idle enumeration; no capture was started.
