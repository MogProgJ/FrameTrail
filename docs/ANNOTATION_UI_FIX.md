# Annotation UI fix — 8 October 2026

Scope: the user's offline first-60 RF annotation editor, not the native app.
Product Design audit guidance was used to inspect two captured states from the
supplied 8.28-second recording, followed by authorized implementation.

## Recorded evidence and changes

1. Removal reports that a reason is needed in Box note, but the note accordion is
   collapsed elsewhere. Now a dedicated, explicitly labelled reason textarea sits
   immediately above Remove. Blank reasons focus it and show an inline error;
   no annotation is changed. Original notes remain in event history.
2. Scrolling moves the photo offscreen while the sticky selected-box panel remains
   beside empty space and long lists. Now the desktop photo fits its viewport
   frame without cropping. The editor is not sticky, the status is not a fixed
   overlay, and saved/RF lists share a tabbed, independently bounded list area.
   Long lists still scroll; smaller windows use a stacked page. Rare advanced
   controls may require scrolling the editor panel, without displacing the photo.

Captured evidence is in the current task's visualization folder:
`annotation-ui-recording-01.png` and `annotation-ui-recording-02.png`.
The pre-fix flow is obstructive; the implemented change addresses both observed
causes. New rendered usability is not independently verified.

## Resume safely

1. In the current v3 browser page, finish/discard unsaved fields, then download its
   annotations JSON. Keep that file: the recording contains newer decisions than
   the last uploaded snapshot.
2. Open `editor-rfdetr-v4.html` in the same RF workspace and import that new JSON.
   Do not replace it with the older 17:30 upload.
3. Select a wrong box, type a reason directly above Remove and remove it. Check
   that the photo stays visible while switching/scrolling lists. Download another
   backup and test importing it before a long session.

The generated v4 embeds the unchanged repaired v3 snapshot and catalogue; old
pages and JSON are preserved. No model download, cluster job, training or RF
inference was required. Training readiness/rights/completeness remain unapproved.

## Verification and limitation

120 Python regression tests passed. Pure JS/form-stub tests checked the actual
page payload/source identity, rejection history/provenance, missing-reason focus,
unsaved-edit guards, tab state, aspect-ratio sizing and overlay coordinate mapping.
Hashes of v3, the original user JSON, repaired JSON and RF catalogue are unchanged.
Generation rechecked the immutable intake and all 60 source photographs.

Local-file live browser access was blocked by tool policy. No alternative browser,
localhost/CDP workaround or hidden access was used. These checks do not establish
rendered layout, real pointer dragging, dialog interaction or browser downloads.
The short manual check above remains required to confirm those on the user's setup.
