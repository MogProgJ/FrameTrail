# First-60 annotation correction module

Updated 4 October 2026. This is local developer tooling, separate from the approved
FrameTrail saved-analysis interface. No cluster command is needed for this step.

Latest, 7 October: [RF-DETR-assisted review](RFDETR_ANNOTATION.md) adds 318 separate
unreviewed suggestions for these same 60 photos. Open the new sibling workspace's
editor-rfdetr-v4.html resumes the last uploaded/repaired state with the
8 October save=confirm and layout/removal fixes. Download any newer v3 browser
edits and import that JSON into v4 before continuing; follow that guide. The original
workspace and all prior annotations are preserved. The historical steps below
remain useful for the base editor, but RF-decision JSON must be validated against
the RF workspace/catalogue described in the new guide.

## What is available now

The user accepted the visual audits of all 60 photographs. The new correction
workspace is `output/kit-results/7450934/photo-pilot-7449188-first60/annotation-workspace-v1/`.
Open **editor-simple-v3.html**; earlier editor/snapshot versions are preserved.
Before switching, click **Save annotations JSON** in your old page, keep the
downloaded file, and import it into the new page. Browser autosave may be tied to
the old file URL; the new page cannot promise to find it. The new editor starts
from the same prepared v2 annotations, not a copy of unseen browser-session edits.

The first draft contains 322 original publisher records, 84 extra local-model
proposals and 137 assistant-drawn proposals. After 209 recorded correction events,
there are **35 individually confirmed boxes, 489 pending boxes and 19 rejected
records**. The active annotation draft therefore contains 524 boxes across 60
images. These are draft counts, not a quality score or accuracy measurement.

The assistant inspected all 60 initial and corrected contact-sheet panels,
checked selected original images more closely, corrected obvious false species
predictions/conflicting labels, proposed missing targets and adjusted selected
boundaries. The 137 manually drawn rectangles are estimated geometry, not a
completed pixel-precise annotation pass. Individual confirmations were made by
the assistant; they are not human box acceptance or whole-image approval.

**No image has a completed whole-image geometry/coverage pass or rights approval.**
The accepted prose audits were not replaced, and source manifest flags remain
false/unassigned. The remaining 540 pilot candidates have not been downloaded.

## Start here — Windows PowerShell

```powershell
$taskLocalRoot = 'C:\Users\nazee\Documents\All Modules\FrameTrail'
$taskAnnotationRoot = "$taskLocalRoot\output\kit-results\7450934\photo-pilot-7449188-first60\annotation-workspace-v1"
Start-Process -FilePath "$taskAnnotationRoot\editor-simple-v3.html"
```

This opens the offline page in your normal browser. It uses clean local JPEGs,
contains no external scripts and makes no image uploads. Keep the editor in its
workspace: it references `../images/`. Existing `review.html` remains an
inspection-only page; it is not the new editor.

1. Enter your editor name. Choose a photograph with Previous/Next or the selector.
2. Select a pending box in **Boxes in this photo**. Check both its label and edges.
   Blue is publisher; amber is a proposed addition. Green means one box has been
   confirmed, not that the whole photograph is finished.
3. To adjust: drag a selected corner. Numeric coordinates and source details are
   under **Advanced: coordinates and source**. To relabel: use **Find a label**
   to narrow the real **Object label** dropdown, then select an entry. Click
   **Save changes**, or **Confirm this box** when the class and edges are correct.
   Confirm saves the current fields as well; resizing returns a box to pending.
4. To add: click **Add a box**, drag around the visible object, then choose its
   label and click **Save new box** or **Confirm this box**. New rectangles start
   with no label or note: they do not inherit the previous box's Clothing label.
   To remove a wrong target, expand the note section and enter why it is wrong,
   then use **Remove this box**. The record/history stays intact. Escape or the
   cancel button discards unsaved fields/rectangles, not previously saved boxes.
5. Inspect the entire photograph against the accepted audit. Resolve missing
   targets, duplicates and classification uncertainty. Keep unresolved issues in
   Holds; do not guess, clear holds in bulk or treat unboxed targets as negatives.
6. Save image review notes. Whole-image checkboxes require all individual pending
   boxes to be resolved; they still cannot approve rights or training.
7. Click **Save annotations JSON** regularly and keep the downloaded file. Save
   or confirm a new/edited box first; navigation and JSON download cannot silently
   discard those unsaved fields. Filtering the box list keeps typed fields.
   Label search clears the unsaved dropdown selection, requiring an explicit new
   choice; it cannot accidentally confirm the old Clothing label after you type
   bracelet. Coordinates and notes are kept. Review notes are retained on
   navigation and JSON save. Browser autosave
   is best-effort, not a durable backup. Resume with **Import saved JSON**; imports
   replay/validate every recorded edit, including the earlier editor's JSON files.

### Your bracelet box — no need to redraw it

After importing your old JSON, select the box you drew over the bracelet (it may
still say Clothing). In **Object label**, choose **Other object — outside model
label list**, type `bracelet` in **Your object name**, then click **Confirm
observation**. The wrong supported-class record is marked rejected and a boxed
observation is created in one validated transaction. The rectangle is reused;
the original record and previous note are kept in history. An unrelated inherited
note is not copied into the new observation. Save annotations JSON afterwards.

For another bracelet: Add a box → drag → Other object → bracelet → Save observation
or Confirm observation. Observation confirmation means you checked that one
observation; it is not a new detector class, rights clearance or training approval.
If you change an observation into a supported label later, the same safe
conversion preserves its old record rather than rewriting source provenance.

This is a precision/correction pass, not a demand to rewrite the accepted audits.
It is valid to keep a difficult photograph on hold or exclude it from a later
release. Automatic proposals can miss objects, merge instances or invent classes.

## Label contract and remaining policy decisions

The draft policy is `training/annotation-policy-v1.json`. It keeps the frozen
601 raw labels / 597 canonical categories, not merely the 52 sampling anchors.
New person boxes use generic Person rather than inferred age/gender. Unknown
objects, unsupported categories, text, individual keyboard keys and shadows must
not be forced into a plausible-sounding class. For example this vocabulary has
no dedicated generic drinking-glass or bracelet class. **Other object** records a
named rectangle separately in `images[].observations`, with no raw training ID.
It remains in the saved annotations JSON and correction history. New draft exports
also have `unsupported-observations.json`; these rectangles are excluded from
COCO categories/targets, YOLO labels and the draft manifest's training objects.
They are observations, not ignore masks or partial-label-aware supervision.
Training on the draft remains prohibited. Adding actual new recognition classes
requires a separate vocabulary/model/adapter and evaluation decision.
Generic Tableware proposals
are explicitly pending taxonomy review, not silently called eyewear.

Use a tight rectangle around identifiable visible extent, clipped to the image.
Some publisher boxes imply hidden/amodal extent; reconcile that difference
before a training release. Most-specific labels, parent/child co-labels, person
alias deduplication, body-part/garment coverage, group-of, depictions, reflections
and unresolvable tiny targets need a consistent release policy. Inside flags and
human image-level labels are still not indexed here. No partial-label-aware or
ignore-aware loss has been implemented. Keeping a 601-output head does not solve
incomplete supervision or prove retention of all categories.

Rights evidence is a separate field for evidence/links, not a clearance switch.
Publisher attribution/licence metadata is preserved but intended-use rights
review is outstanding. Partitioning, stronger duplicates/leakage checks and an
independent real-footage evaluation set are separate future release gates.

## Saved artifacts and validation — Windows PowerShell

`seed.json` is immutable source/proposal provenance; `annotations-corrected-v2.json`
is the latest prepared draft with append-only before/after correction history.
`assistant-corrections-v1.json` and `assistant-corrections-v2.json` reproduce the
changes. Initial and v1 proofs/snapshots remain available for comparison.
`draft-export-v2/` contains 60 YOLO text files, draft-coco.json, draft-manifest.json,
the annotation state and validation-summary.json. Original photos are referenced,
not altered/copied. **Pending targets are included: do not train from this export.**
There is deliberately no data.yaml or training dataset lock. The ordinary
training exporter/preflight still rejects the draft.

Validate a browser-saved JSON file, then export into a NEW directory:

```powershell
$taskPython = 'C:\Users\nazee\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
$taskEditedFile = Read-Host 'Full path to your saved annotations JSON'
& $taskPython "$taskLocalRoot\scripts\annotate-pilot.py" validate --workspace "$taskAnnotationRoot" --annotations "$taskEditedFile"
if ($LASTEXITCODE -ne 0) { throw 'Validation failed; preserve the file and investigate.' }
& $taskPython "$taskLocalRoot\scripts\annotate-pilot.py" export-draft --workspace "$taskAnnotationRoot" --annotations "$taskEditedFile" --output "$taskAnnotationRoot\draft-export-my-review-01"
```

Choose a new output suffix for every export. Do not overwrite annotations,
publisher manifests, notes, receipts or original images. The tool refuses existing
outputs, altered source hashes, changed geometry/vocabulary, invalid coordinates,
unlogged edits, provenance changes and checklist passes with pending objects.

Verification includes all **81 Python tooling tests**, full-editor JavaScript
syntax, actual generated-page payload/script identity, pure replay/import and
isolated form-state tests. Tests cover empty new-box labels/notes, real-select
markup, no-result label search, supported↔observation conversions, conversion
atomicity, old saved JSON imports, reordered JSON keys, JS/Python interoperability
and observation export separation. These are code/data tests, not browser tests.
Automated visual/browser interaction was
**not** verified: the built-in browser blocks file URLs. No localhost/CDP or other
workaround was used. Your screenshot proves drawing a rectangle in the previous
editor worked, but it inherited Clothing and a clothing correction note. The new
page's dropdown, click-through, corner resizing and JSON download/resume still
need your normal-browser check before extended annotation sessions.

`draft-export-v2/verification.json` records the successful check of all 60 original
photo references, all 60 YOLO files and all 524 active COCO/YOLO targets against
the correction history. The actual training validator rejected the draft's
unassigned partitions. The verification does not assert visual completeness.

## Where we stand and what lies ahead

| Stage | Evidence / current position | Remaining difficulty |
| --- | --- | --- |
| Native app and saved analysis | Working existing broad recognition and saved appearances/CSV; unchanged here | Representative accuracy, tracking and resources still need evaluation |
| KIT GPU mechanics | A100 diagnostic 7441565 and real CUDA smoke 7446193 completed; checkpoints checked | Mechanically proven, not an accuracy improvement |
| Source catalogue | Metadata job 7447265 indexed 1,743,042 source-train images / 14,610,229 boxes | A catalogue is not downloaded photographs or complete labels |
| Balanced selection | 7449188 selected 600 IDs, six domains, 52 anchors | 540 remain unacquired; scale only after label workflow works |
| First photographs / audits | 7450934 acquired 60; bytes/receipts verified; visual audits accepted | Done for intake/audit, not training clearance |
| Correction module | Editable draft, missing-target proposals, recorded fixes, COCO/YOLO draft formats | Pending box precision, whole-image coverage and release policy: labour-intensive |
| Reviewed training data | No approved larger bundle yet | Rights, group splits and leakage checks; hardest ongoing data work |
| Independent evaluation | Broad real-footage locked evaluation not prepared | New camera/site/session examples, full labels and per-domain regression checks |
| Substantial training | Not started; RF-DETR Small remains shortlisted only | Controlled experiment after data/evaluation gates; native compatibility and measured benefit before adoption |

The next useful milestone is a small, defensible reviewed release from these
same photographs, plus measured correction effort. Then choose the next bounded
acquisition batch. Scaling may need better pre-labeling, selective acquisition,
additional review capacity or an explicitly tested partial-label training path.
Thousands of photographs do not become fully reviewed just because a detector
draws rectangles. Training execution is now a known path; proving useful,
reliable improvement across everyday objects is the substantial work ahead.
