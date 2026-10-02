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
