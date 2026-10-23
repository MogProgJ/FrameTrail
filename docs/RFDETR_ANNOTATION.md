# RF-DETR-assisted annotation review

Prepared 7 October 2026. This is an offline annotation tool, **not** integration
into the native FrameTrail app, a training run, or evidence of improved accuracy.

## Latest update — 8 October 2026

Open **editor-rfdetr-v4.html** in the same RF workspace. It already contains the
user's latest supplied JSON plus the explicitly authorized save=confirm repair;
do not import the older 17:30 JSON over this resumed state. Earlier files/pages
and the original Downloads JSON are preserved. If you made additional edits in
v3 page after that upload, download its latest JSON before switching, then use
**Import JSON** in v4 to resume those edits. Keep both backups. Do not assume a
different file URL can recover all newer browser-session edits automatically.

The recording-driven layout fix keeps the photograph fitted to a bounded desktop
frame, removes the sticky sidebar/fixed status overlay, and separates **Saved boxes**
and **RF suggestions** into tabs. The selected box editor and the selected list
have independent bounded scrolling when needed; they are not nested sticky lists.
Narrow windows use an ordinary stacked page layout. **Image notes / review** and
**Help** open explicit closable dialogs; uncommon coordinates/source controls
remain under Advanced.

To remove a saved box or RF suggestion, select it, type into **Reason for removing
this box** directly above **Remove this box**, then click Remove. The input is
always visible in the box editor, not hidden in another accordion. A blank reason
focuses that field without changing annotations. Removal retains the original
record and logs the reason. Save or discard unrelated unsaved class/geometry
changes first. A typed removal reason also blocks navigation/confirmation until
you remove the box or clear/discard the reason.

- **Save & confirm changes/new box/observation** confirms that individual record.
- **Use RF box to update this saved box** now updates AND confirms the target.
- RF rows show **applied to saved box · confirmed/pending** and select that target,
  not the rejected duplicate. Removing the actual saved target is shown distinctly.
- Explicit `proposal-link` events preserve immutable `linked_to` target IDs;
  linked duplicate records must remain rejected and cannot be reactivated.
- **Mark pending**, restoring seed geometry and dragging a saved boundary remain
  deliberate recheck paths. Press Save & confirm after a boundary adjustment.
- **Download JSON backup** downloads a backup only. It does not confirm untouched
  drafts, unselected RF proposals, whole-image coverage, rights or training.

The new snapshot is **annotations-user-confirmed-v3.json**, with an adjacent
`.repair.json` receipt. It preserves all 318 input events and appends 78 transparent
repair events: five explicit links and 73 user-authorized confirmations (42 supported
boxes and 31 observations). Two reopened duplicate records are rejected again;
the five linked targets, including all three publisher apple boxes, are confirmed.
Untouched pending drafts stay pending. Geometry, class names/IDs, source provenance,
whole-image review/rights fields and training approval were not altered.

Result: 74 confirmed / 473 pending / 27 rejected supported records; 31 confirmed
observations, still excluded from training targets. All 60 images retain review
holds and no whole-image passes. A new versioned autosave key prevents an older
session overwriting the resumed state. Older seed-compatible JSON remains structurally
valid, but import refuses a snapshot with reactivated legacy links rather than
silently loading duplicate active targets. Old editors do not understand new link
events; use v4 going forward. V4 preserves the v3-compatible autosave key and does
not migrate or modify annotation state. The recording shows newer browser edits;
these have not been received as a JSON file. The embedded snapshot remains the
last supplied/repaired state, not a capture of those newer edits.

```powershell
$taskRfWorkspace = 'C:\Users\nazee\Documents\All Modules\FrameTrail\output\kit-results\7450934\photo-pilot-7449188-first60\annotation-workspace-rfdetr-v1'
Start-Process -FilePath "$taskRfWorkspace\editor-rfdetr-v4.html"
```

Verification: all **117 Python tests** and pure JS/payload/form/link checks pass.
The original upload hash is unchanged; all 60 original photos were rechecked;
no exact active same-category duplicate rectangles remain. Actual browser
interaction/rendering remains unverified: try one save and JSON backup first.
The historical instructions below describe the earlier v2 behavior, not the new
save=confirm semantics.

## Start here

RF-DETR processed all 60 existing photographs using the previously verified
Small ONNX export, CPU, confidence threshold 0.35. It produced **318 unreviewed
suggestions**. Of these, 277 have an exact mapping to the frozen training vocabulary;
41 are observation-only because their COCO category has no exact mapped target.
Two photos received no suggestions: this does not mean they contain no objects.

New workspace:
`output/kit-results/7450934/photo-pilot-7449188-first60/annotation-workspace-rfdetr-v1/`.
Latest page: **editor-rfdetr-v2.html**. The initial editor-rfdetr.html is preserved.
Earlier photographs, source metadata, notes, annotation workspace/pages and model
files were not replaced. The new seed and initial annotation state are copies of
the same seed and prepared v2 history; no suggestion was silently accepted.

Open the latest page in your normal browser — Windows PowerShell:

```powershell
$taskRfWorkspace = 'C:\Users\nazee\Documents\All Modules\FrameTrail\output\kit-results\7450934\photo-pilot-7449188-first60\annotation-workspace-rfdetr-v1'
Start-Process -FilePath "$taskRfWorkspace\editor-rfdetr-v2.html"
```

If you have already made edits in the earlier editor, click **Save annotations
JSON** there first, keep the downloaded file, then **Import saved JSON** here.
The assistant has not received unseen browser-session edits. The identical seed
supports those older files. Import replaces the current session only after a
warning if it has unsaved decisions; it does not overwrite the original file.
RF browser autosave uses a separate key and does not read/write the older key.

## What you do, in simple terms

1. Enter your editor name. Begin with one photograph to check the controls.
2. Look at the **teal dashed boxes**. These are RF-DETR guesses. Click a box or
   its entry under **RF-DETR suggestions**. Its suggested name is already selected.
3. Check the object name and box edges. Drag a pink corner to resize; use the
   dropdown to change the name. **Confirm** saves your reviewed decision, or
   **Save** keeps it pending. Ordinary **Add a box** still handles missed objects.
4. If a suggestion overlaps an existing saved box, check whether it is the same
   object. Choose the matching saved box and click **Use RF box to update this
   saved box**. This updates it without adding another active target, preserves
   its history, and marks it pending for your final confirmation. If RF is wrong
   or you prefer the existing box, write a reason in **Reason for removing this box** and **Remove** the
   RF suggestion. If the overlapping box really is a *different* object, tick
   **This is a different object, not a duplicate** before adding it.
5. Check the *whole photograph*, not only RF boxes. It can miss objects entirely.
   Blue/amber/green saved boxes and accepted audit notes remain available. In
   Display options, **Show boxes** controls saved annotation overlays;
   **Show RF-DETR suggestions** controls the separate proposal overlay.
6. Download JSON backup regularly, especially before closing. Test re-importing
   your first backup, then continue. Send the final saved JSON back for validation.

An RF suggestion is not a saved annotation until you Save/Confirm/Remove it.
These decisions record the original model prediction first, then your edits or
rejection. The immutable prediction catalogue remains separate. The suggestion
list shows saved decisions; rejected suggestions are retained in history. Using
an RF box to update an existing box preserves a rejected duplicate-proposal record
linked to that existing target; it does not mean the existing object was removed.

Removing a saved box or RF suggestion requires a reason. A percentage is a model
score, not an accuracy guarantee. Overlap warnings are conservative heuristics,
not proof that two rectangles describe the same object. Directly adding a pending
proposal cannot pass whole-image review; when applying a new RF decision to an
already passed image, its image geometry/coverage checks are reset for rechecking.
Unprocessed suggestions do not become automatic training labels or negatives.

## Names and vocabulary

The existing 601-raw/597-canonical annotation vocabulary is unchanged. RF-DETR
Small has 80 COCO categories. Mapping uses exact canonical IDs only, preferring
generic Person over age/gender aliases. It does not invent a label mapping.

Twelve COCO categories have no exact mapped Open Images target in our registry:
cow, frisbee, skis, sports ball, cup, donut, potted plant, dining table, remote,
keyboard, microwave and hair drier. A similar-sounding label is not assumed
equivalent. These suggestions start as **Other object** observations; you can
explicitly choose a defensible supported label during review. Observation-only
boxes retain RF provenance and are excluded from COCO/YOLO training targets.

You can still name/draw bracelet or other outside-vocabulary objects. This saves
observations, not a new trained recognition class. New-class training, taxonomy,
native adapters and evaluation require a later explicit scope decision.

## Developer reproduction and validation

No new upload, environment installation, model download, cluster job or camera
activation was needed. The inference input/preprocessing/output contract remains
the verified [RF-DETR CPU probe](RFDETR_PROBE.md). The runner is bounded to 60
existing photos and a NEW sibling workspace under FrameTrail output, preserving
relative photograph links. Incomplete/changed catalogues, model identities,
source hashes or class mappings fail closed. Partial outputs remain diagnostic
and cannot load as a completed proposal catalogue.

Intentional reproduction only — Windows PowerShell, a NEW output name:

```powershell
Set-Location 'C:\Users\nazee\Documents\All Modules\FrameTrail'
$taskIntake = 'output\kit-results\7450934\photo-pilot-7449188-first60'
& '.\.deps\rfdetr-probe-cpu\Scripts\python.exe' -B scripts\annotate-rfdetr.py `
  --workspace "$taskIntake\annotation-workspace-v1" `
  --annotations "$taskIntake\annotation-workspace-v1\annotations-corrected-v2.json" `
  --experiment output\rfdetr-probe\cpu-v3\experiment.json `
  --output "$taskIntake\annotation-workspace-rfdetr-v2"
```

Use the RF workspace, not the old workspace, when validating a saved JSON that
contains RF decisions. Keep the catalogue and workspace receipt with it:

```powershell
$taskPython = 'C:\Users\nazee\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
$taskEditedFile = Read-Host 'Full path of your saved annotations JSON'
& $taskPython -B scripts\annotate-pilot.py validate `
  --workspace $taskRfWorkspace --annotations $taskEditedFile
```

`preparation.json` records successful inference and the preserved base-state hash.
`rf-proposals.json` SHA256 is
`84fd28d3c33d85d6af19d487416048c944b37a8d8410ad9ab564326b887c7281`;
the latest editor SHA256 is
`282e7f3c18dca377951ccf6396d20e16db87926fc6c998884a722c76da199c74`.
Preparation source snapshots and both editor versions are kept. RF decision
events require exact original catalogue membership/provenance before ordinary
logged corrections; observations cannot impersonate manual or publisher targets.

All **111 Python tests** passed, including 11 new catalogue/history/export and
JS→Python review-interoperability tests. Pure JS tests checked actual 60-image
payload/script identity, duplicate resolution, preselected labels and earlier
state compatibility. All 318 predictions have valid supported-box/observation
representations. All 60 original photographs, the base state/seed, note files
and RF model identity were rechecked. No browser rendering, real dragging or
native dropdown behavior is claimed verified; try one photo and save/re-import
in your own browser before a long review session. No browser-policy workaround
was used.

## What completion will mean

Reviewing suggestions finishes neither rights clearance nor a training release.
After your JSON comes back, check geometry, whole-image coverage, unresolved
holds and taxonomy policy, then rights/splits/leakage and independent evaluation.
Only a reviewed release can feed substantial KIT fine-tuning. No trained weights,
accuracy improvement or automatic acceptance policy is claimed by this module.
