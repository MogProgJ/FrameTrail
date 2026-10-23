# FrameTrail — continuation snapshot, 11 October 2026

This is the authoritative recent-work continuation supplement to the project's older HANDOFF.md (8 October). It preserves material decisions, evidence, provenance and next actions, not a verbatim transcript of every message. Original documents, JSON histories, scripts, receipts, photographs and user logs preserve the detailed evidence. Inspect those before changing their state. Newer human messages and actual results take precedence.

## 1. Read order and boundaries

Project: `C:\Users\nazee\Documents\All Modules\FrameTrail`.

Read HANDOFF.md first, followed by docs/KIT_CLUSTER_QUICKSTART.md, docs/TRAINING.md, docs/ROADMAP.md, then this supplement. HANDOFF's latest annotation checkpoint is old; the 11 October v3 JSON below supersedes it. Consult docs/ANNOTATION_REVIEW.md, docs/RFDETR_ANNOTATION.md and docs/ANNOTATION_UI_FIX.md for relevant tooling.

The previous chat's shell was rooted in unrelated `C:\Users\nazee\Documents\All Modules\MiniERP\MiniERP-Springboot`. Do not modify MiniERP or work on its nested auxiliary FrameTrail checkout. Use explicit workdir/path for the normal FrameTrail project. Preserve existing edits, untracked `gemini_generated_video_07b260f6-analysis.csv`, footage, saved .frametrail analyses, all previous JSONs, source files and local analysis artifacts. No destructive reset, sync, clean, overwrite or model replacement.

Conversation artifact root (TASK_ROOT below):
`C:\Users\nazee\.codex\visualizations\2026\10\04\01a10654-052b-7933-b51b-b32609e31e2e`

FrameTrail may be read-only under the new chat's sandbox. Obtain scoped permission for writes; never use MiniERP as a write workaround. Git status attempts had environment/worktree permission failures; no reliable clean-tree claim was made. No commit, PR, automation or new chat has been created for this handoff.

The native approved choose/drop video → analyse → appearances/timestamps → optional save/CSV interface must remain intact. Do not alter it to accommodate annotation/training work.

## 2. User intent and product direction

The project started as C/C++ learning and now aims for a useful broad everyday-object detector. Dog/fox, low light, small objects, blur and occlusion are difficult slices, not the entire scope. No detector promises every possible object. Wider labels are not proof of reliable recognition.

Native C++/Qt/FFmpeg app remains version 0.12; 0.13 denotes offline Python dataset/training tooling. ONNX Runtime CPU/DirectML detection, tracking, appearance review and CSV are already implemented. YOLOX-S remains default when installed. Open Images broad and YOLO World profiles are experimental; none of the new fine-tuned weights has been adopted. Existing pretrained and tiny mechanical-training checkpoints already exist.

Python is already used offline; Python need not be introduced into the shipped C++ application merely to train. RF-DETR requires its own explicit preprocessing/output/vocabulary adapter if eventually integrated. Consider a Python inference worker only if a useful model cannot fit the native adapter and measured benefits justify it.

Fine-tuning is training from pretrained weights, not a separate non-training activity. Correcting JSON does not train a model. Checkpoints are the result of training but need evaluation and compatible export before adoption. No guaranteed improvement from these 60 photographs.

The user liked RF-DETR predictions and chose to use it first as an offline annotation assistant, not automatically replace the app model. It is not established as universally the best 2026 detector. The future camera/Jetson/Raspberry Pi inference → reviewed data → retraining loop is a conditional direction, not an activated camera, hardware choice/purchase or automatic self-training system. It would require permission, privacy, hardware/resource and held-out accuracy evaluation.

The user wants a finite, assistant-led workflow rather than endless manual re-review. Use automation for prelabels/checks and bounded human decisions, not blanket approval. The first 60 prose audits were accepted (roughly first 15 human, remainder assistant), followed by user corrections of all 60 in the box editor. Accepted prose is not complete ground truth, a release pass or rights clearance.

## 3. Completed KIT infrastructure and mechanical training

The user manually runs SSH/SCP with password and OTP. Host `uc3.scc.kit.edu`, user `ka_udxvl`. Never request/store credentials. Clearly distinguish Windows PowerShell commands from Linux cluster commands. The assistant has not logged in/submitted remote jobs.

Resolve cluster project dynamically: `$(ws_find frametrail)/FrameTrail`. Historical resolved path: `/pfs/work9/workspace/scratch/ka_udxvl-frametrail/FrameTrail`.

Historical workspace report on 4 October: expiry 3 November 2026, three available extensions. Verify current lifetime before long work; scratch is not backed up. Historical quota: 8.569 GiB used, soft 40 TiB/hard 44 TiB; .venv 7.3 GiB. Shared filesystem free space is not personal quota. Do not treat old queue availability as current.

- 7441565: successful GPU diagnostic, NVIDIA A100 80 GB, driver 595.71.05, reported driver CUDA support 13.2.
- 7442046: old failed training attempt after interrupted environment setup; torch missing. It is not the latest run.
- Installation subsequently completed: `No broken requirements found`. Working module `devel/miniforge/25.3.1-python-3.12`, Python 3.12.11, PyTorch 2.8.0+cu128, Ultralytics 8.3.228.
- 7446193: replacement smoke completed Slurm exit 0, actual A100 CUDA tensor/training, experiment status completed, both checkpoints present and locally hash-verified. One epoch, 320 pixels, batch 2, 70 train/11 validation; 15 locked test images untouched. Training wrapper 106.91 sec, complete job 3m44s. No adoption or accuracy improvement claim.

Local smoke evidence:
`FrameTrail\output\kit-results\7446193\cluster-smoke-7446193` plus adjacent Slurm log.

SHA256:
- best.pt: `77723b84f509ed4dba7d78bac60fb4de00250f3b2bd0d5e6e158bc34c68ac37b`
- last.pt: `f7f80e66e6bb143bc882baae1c2ff5c6348281151163e6016693a2f417a007e6`
- smoke dataset lock: `9c71e1b1d749f1d2c97604fc37aa363c51831e3838e5c7254bd26ba1016cb0b2`

Original sample: 96 images/447 boxes, split 70/11/15; incomplete publisher-validation annotations, mechanical only, not approved for substantial accuracy training. Local CPU one-epoch training, full-vocabulary ONNX export and native CPU/DirectML numeric/vocabulary checks also succeeded. These are integration mechanics, not independent product accuracy.

Do not repeat completed uploads, setup, model downloads, smoke submission or retrieval without new evidence. Success of future training requires the actual new job ID, Slurm state/exit, log, real CUDA operation, experiment.json and checkpoint verification; disappearing from squeue is insufficient.

## 4. Open Images acquisition: metadata is not millions of photos

- Metadata job 7447265 completed exit 0 in 5m18s: 1,743,042 publisher-train image records, 14,610,229 boxes, 601 raw/597 canonical categories; 599 raw labels have boxes. Metadata catalogue SHA256 `bd42dbb1129406c16cda37401670ecba04d6d956cde0071ab79de6190162e78d`.
- Human image-level labels were downloaded but NOT indexed/used in loss; publisher inside flags were not indexed. Do not assume absent labels are verified negatives or missing-label-aware training is implemented.
- Selection 7448416 was historical v1, 600 IDs but missed two anchors through budget allocation.
- Balanced v2 selection 7449188 completed exit 0 in 45sec: 600 unique IDs across six domains and all 52 acquisition anchors, no overlap with old 96. Selection SHA256 `69d67561b87f4efad265f4713a415ff985e7bc551fa01b931c574c1e16d68ef5`. 28 anchors get 12 IDs, 24 get 11; lantern/balloon each 11, eligible pools 462/1344.
- Photo job 7450934 acquired only first 60 clean JPEGs, verified locally. Remaining 540 selected photos have NOT been acquired. Neither 1.9 million photos nor an approved larger dataset has been downloaded.

Intake root:
`C:\Users\nazee\Documents\All Modules\FrameTrail\output\kit-results\7450934\photo-pilot-7449188-first60`

Photos: `images\IMAGEID.jpg`. Intake manifest SHA256 `a7f1cd4e65482eeae54b691dc24f8d18f6b52cb06e3ca5045ed0801aee0aeea0`. Clean photographs, manifest, receipts, audits and publisher boxes are unchanged. Overlays are separate data, not edits to photos.

The frozen training/application contract is 601 raw labels mapped to 597 canonical categories, not the 52 acquisition anchors. Freeze/reconcile target policy: classes in scope, ancestor/leaf/parts, duplicates, visible extent, tiny/occluded targets and depiction. Do not label every imaginable component, infer sensitive demographics or silently invent new trained classes.

## 5. RF-DETR and annotation tooling

RF-DETR Small pretrained isolated CPU/export probe succeeded, not fine-tuning/native integration/DirectML/accuracy adoption.

Environment `.deps/rfdetr-probe-cpu`: Python 3.12.14, torch 2.8.0+cpu, torchvision 0.23.0+cpu, rfdetr 1.11.2, onnx 1.19.1, onnxruntime 1.30.0, numpy 2.2.6, Pillow 12.3.0.

Probe evidence: `FrameTrail\output\rfdetr-probe\cpu-v3\experiment.json` and comparison.html. Checkpoint 386,045,550 bytes, publisher MD5 matched; SHA256 `d81979a9213a2109345158ce9232668df4c1ae52e9b8db3f2ec0a8cbad959b33`. Official source commit `7433d5919d0f7e72cc6cb78663e0a731afd499e0`; wheel SHA256 `2f23589567123b59302f1cfa9d14d23630f9f583ee6f3468c5891e33fb103b2a`.

ONNX 114,434,018 bytes, SHA256 `a7d8e54b0e8aebc67c0de798f0e8951f9566d82e0ffa0a9cd4b4a22a3138d46d`. RGB [1,3,512,512], ImageNet normalization, direct bilinear resize/antialias False; named outputs dets [1,300,4], labels [1,300,91]. Sparse COCO slots map 80 categories; slot 90 is toothbrush, not background. Six-photo SDK/ONNX decoded matches: 42 above .35,24 above .55. Raw query arrays are not positionwise equivalent; mechanics only. This head is not the 597-class Open Images head.

RF ran once over all 60, yielding 318 proposals: 277 exact frozen-vocabulary mappings,41 observations. Twelve COCO categories lacked exact mapping: cow, frisbee, skis, sports ball, cup, donut, potted plant, dining table, remote, keyboard, microwave, hair drier. Do not silently map cup to Coffee cup or guess numeric class IDs.

Editor workspace: `<intake root>\annotation-workspace-rfdetr-v1`.
- Current editor `editor-rfdetr-v4.html`.
- Immutable seed.json SHA256 `3d7e201aadb6dec01fc90264b0cb3ac2f56bc09e0e5d84e202ba4650261d8b26`.
- Immutable rf-proposals.json SHA256 `84fd28d3c33d85d6af19d487416048c944b37a8d8410ad9ab564326b887c7281`.

Save changes now confirms the individual box; RF update of an existing duplicate confirms the existing target and records the RF item as immutable rejected linked duplicate. Rejected records persist with reasons/history. Linked duplicates cannot be reactivated. Unsupported custom labels are observations kept in JSON, excluded from training; neither new classes nor ignore masks. All untouched RF suggestions and pending records were explicitly rejected at the user's request.

v4 layout: visible removal reason, viewport-fitted image, bounded sidebar/tab queues. Earlier real dropdown/save/duplicate-state/removal/scroll problems were addressed; no live browser interaction verification claimed. Static/pure-JS and replay tests passed. Historical tooling suite 120 Python tests passed at v4 stage; do not claim all rerun after latest QA.

Download JSON is durable backup, not rights/whole-image/training approval. Import latest v3 into editor v4 to continue, first preserve any newer unseen browser edits in their own backup. Existing open tabs/embedded old JSON do not update automatically. The old read-only guide at TASK_ROOT\flagged-cases-212459\review.html shows earlier data, not current v3.

Local-file browser automation was denied by policy. Do not bypass with localhost, Playwright, CDP or alternate browser. open_in_codex attempts returned queued, not proven displayed. Native computer APIs are disabled. Use direct files, validated scripts and user screenshots where appropriate.

## 6. Annotation provenance, user decisions and workbook

All versions preserved; never overwrite original uploads.

Older user export `Downloads\frametrail-annotations-2026-10-08T17-30-05.755Z.json` SHA256 `24076c82ba6dfa4b611d108ce8326e907fc2b4a2ef10ca8b6549baadc8067b7c`. Its repaired/embedded editor state is now stale.

User exports 10 October:
- `Downloads\frametrail-annotations-2026-10-10T15-22-01.739Z.json` (earlier, preserved).
- `Downloads\frametrail-annotations-2026-10-10T21-24-59.533Z.json`, SHA256 `22e5333b2c620168a4669ab0ed7c0bf03475bf8006bddd58da09133d77736be0`. 1,548 events; supported 600 confirmed/18 pending/173 rejected; observations70 confirmed/5 rejected.

User instructed: reject all pending; reject untouched RF; check duplicates; flag ambiguous cases for user choice; assistant take over remaining QA where possible.

Bulk closeout `Downloads\frametrail-annotations-20261010-rejections-v1.json`, SHA256 `3b33664129b06d1c3a8328f937eb418fdb2229dd513e7af16e3292104747b74c`: 1,760 events (+212); supported600 confirmed/0 pending/273 rejected; observations70 confirmed/0 pending/20 rejected. The 318 RF items all have saved decisions:115 linked,98 standalone confirmed,105 ordinary rejected,0 untouched. Confirmed geometry unchanged.

User workbook `Downloads\Book1.xlsx`,9,902 bytes,SHA256 `8423f13b2c3b1e0395e409cfc285405f9dc5e70f84f29dd561b750d00aab8683`, Sheet1 A1:B23. Its Photo 1–22 mean GUIDE CASE NUMBERS, not photo numbers. Choices: 1B,2both,3B,4B,5B,6B,7A,8A,9A,10B,11A,12A,13A,14B,15neither,16A,17B,18A,19both,20A,21B,22B. Workbook remains unchanged.

Applied20 non-conflicting cases in `Downloads\frametrail-annotations-20261011-case-decisions-v1.json`, SHA256 `de1625f101a8be751e17c73a1c6038ce8fde9dd661a4e12c85f541438dba1f7a`:1,778 events,supported583 confirmed/290 rejected,observations69 confirmed/21 rejected. Cases15/16 shared conflicting A; C1 not specified in workbook.

Explicit human clarification: keep two smaller pizza B boxes; reject shared large A. Leave C1/photo24 central rider's Helmet rejected and withhold photo from training.

Applied in `Downloads\frametrail-annotations-20261011-case-decisions-v2.json`, SHA256 `0f4384803b880848a0a7a2a5b99a5f501c088a975c2adb7e51423bc6d093acc0`:1,780 events,supported582 confirmed/291 rejected,observations69 confirmed/21 rejected.

Pizza large `rf-d5a8a64686d5b51d-3abd5ac8ddc726d7-7` rejected; smaller `...-6` and `...-4` confirmed. Photo24 Helmet `manual-24-115` remains rejected, coordinates[403.456,37.248,465.92,101.656]; training hold recorded. Never restore this against the human decision.

## 7. Final QA and latest authorised v3 fixes

The final QA screened supported-overlay contact sheets for all60, with targeted original-resolution checks of photos5,8,14,21,28,29,31,54,56 (27 also inspected). This is not an exhaustive pixel-perfect 601-class ground-truth check. QA report has eight findings in seven photos.

Pre-fix profile:115 raw/114 canonical represented;486 raw/483 canonical absent;65 represented raw classes have at most2 boxes. All60 publisher split train; dataset split unassigned. 59 source-author groups,60 unique image IDs,zero duplicate SHA or dHash<=3 candidates (not proof against crops/session leakage).

A source-group preview excluding only24 yielded39/13/7; PREVIEW ONLY, not assigned and predates latest five exclusions. Training manifest validator rejected unassigned splits (`Invalid split or duplicate image ID`), not evidence of duplicate IDs.

All publisher attribution fields contain metadata/CC BY2.0 URLs but current rights evidence is blank/unapproved. Official source licensing guidance requires checking individual photos; annotation and image licences differ. Cached Flickr photo1 author/title/licence corroboration was not a fresh live check. Seven targeted Flickr pages unavailable (5,15,21,56,8,39,58), remaining52 not checked; local urllib DNS failed. Unavailable page does not prove rights absent/revoked. No access-control bypass.

Photo45 confirmed Pepper Mill observation must not be blindly restored as Bottle. Initial photo21 Wine glass concern was not retained as a definite class error after original-resolution review: partly occluded, ambiguous.

User explicitly authorised clear QA fixes and ambiguity holds. Latest output:
`C:\Users\nazee\Downloads\frametrail-annotations-20261011-qa-fixed-v3.json`
Identical TASK_ROOT\release-fixes-20261011\frametrail-annotations-20261011-qa-fixed-v3.json.

Size3,448,190 bytes; SHA256 `843c99c48ea70bdf97fe6a0f00087e5a2e5100c455ad09d6e86e8db26f173ca9`.

Four fixes:
1. Photo5 Q1: reject false Couch RF `rf-d5a8a64686d5b51d-276dee336c643993-6`; existing Backpack remains, no extra Backpack.
2. Photo56 Q2: `rf-d5a8a64686d5b51d-6f716b522ec9676c-7`, raw343 Mouse (animal) → raw129 Computer mouse, confirmed, same geometry and immutable RF origin.
3. Photo31 Q3: reject extra front-only Truck `rf-d5a8a64686d5b51d-ca828f832b8ba661-5`; full publisher-6 Truck and distinct left truck remain.
4. Photo31 Q8: confirmed outside-vocabulary License Plate observation `observation-a9e4fcca-c42b-4750-b517-fca47ae65788` converted at SAME reviewed geometry to confirmed supported `manual-qa-20261011-photo31-license-plate`,raw568 Vehicle registration plate. Old observation rejected/preserved with conversion reference; new origin manual. Atomic conversion tested before complete replay.

Nine events appended (four fixes/conversion events + four new image holds); old event prefix, original uploads, all22 A/B outcomes, existing geometry/origins, frozen vocabulary, rights and approval flags unchanged. Full Python source/photo/seed/RF replay and actual editor JS validation passed.

Latest full archive:60 photos; supported581 confirmed/0 pending/293 rejected; observations68 confirmed/0 pending/22 rejected;1,789 events. Geometry passes0,coverage passes0,all60 have holds. `approved_for_training=false`. Individual box confirmations are not a whole-image or rights pass.

Explicit training exclusions (photos retained, not deleted):
- photo8 `74d3e8ed4d6a7463`: case2 keep-both outcome preserved;3 Person boxes for2 people; withheld rather than overriding human choice.
- photo15 `6669c1da381cfac8`: source title acrylic on resin raises depiction/artwork ambiguity; withheld, not definite classification of all pixels as artwork.
- photo24 `d6cbb0a6be0298f7`: user explicitly retained rejected central Helmet and withheld photo.
- photo28 `b2920354898bc0f3`: two Bed boxes/one bed visible-extent ambiguity; withheld, no silent edits.
- photo29 `c1d68295e6a58241`: far-left Tree lacks accepted single-instance box; withheld rather than unreviewed addition/restoration of rejected broad multi-tree box.

Remaining55 screening candidates:523 confirmed supported boxes,111 raw/110 canonical categories. NOT approved; no partitions assigned. Enforce exact IDs from training-exclusions.json in any future release.

## 8. Next move: source-evidence CPU job, not GPU training yet

Chosen next training route after release gates: small, controlled full-vocabulary YOLOv8s Open Images fine-tune, because KIT CUDA/export/native contract is proven. RF-DETR stays offline annotation assistant. No model replacement. Freeze budget/hyperparameters only after approved dataset is known; no run claims broader improvement.

Three remaining release gates:
1. Actual whole-image completeness/geometry clearance and coherent target hierarchy/part/depiction rules. No bulk flip of review flags or interpretation of missing labels as verified negatives.
2. Individual source-use/rights evidence and review. Evidence collection is not automatic legal clearance.
3. Source-group partitions, immutable reviewed bundle/lock and independent real-footage evaluation. All60 developed annotations; not an untouched field benchmark. Check broad-model regression, not just present categories.

No corrected-data training data.yaml, training dataset-lock.json or new GPU training job exists. The QA snapshot-lock.json is NOT a training release lock.

Prepared CPU source package (NOT yet uploaded/submitted; no actual new ID):
`TASK_ROOT\release-fixes-20261011\frametrail-source-evidence-tools-v1.tar.gz`
and `.tar.gz.sha256`.8,312 bytes,SHA256 `fb2b64a434e27ef65db11223d77ad84b99bb151cf5d38c987b7e0d7d17c83721`.

Archive source-tools-v1 contains collect-source-evidence.py,run-cluster-source-evidence.sbatch,README.md,source-plan.json only. It requests cpu_il,1CPU,2GB,15min,noGPU; reuses existing Miniforge/project .venv. Collects only public Flickr HTML for exact55 candidates,2MB/page and110MB total raw HTML cap,one request/page,10sec timeout,no retries/fallback endpoints. No credentials/cookies/photos/model/env downloads/training. Exact HTTPS Flickr pages only; rejects login/image/external/token-bearing redirects. Saves compressed HTML, timestamps/hashes/candidate CC links. Generic footer licences may be unrelated; extracted links remain unreviewed.

Exit0 means all HTML attempts retrieved, not rights approval. Exit2 intentionally means some unavailable; report/pages retained. Unavailable sources neither prove absent rights nor authorise bypass. Offline syntax/plan/exclusion/URL/cap/nonHTML/link/archive tests passed, and mocked55-page failure-path exit2 test passed. These fixtures are not real evidence. Remote Bash syntax/reachability remain unverified.

Exact runnable Windows/Linux commands are in TASK_ROOT\release-fixes-20261011\NEXT.md. Windows uploads this new package+checksum. Linux checks SHA, extracts with --keep-old-files, checks bash -n and submits source-tools-v1/run-cluster-source-evidence.sbatch. Do not repeat extraction blindly if already done. Use ACTUAL sbatch number, never a fabricated/stale ID.

Result `output/training-general-v1/source-evidence-JOBID/source-evidence.json` and pages/*.html.gz; log `frametrail-source-evidence-JOBID.log` under cluster project. Inspect with sacct and log/report; retrieve entire result folder plus log through Windows SCP. Standard syntax:

```powershell
# Windows PowerShell: change JOBID only after sbatch prints the actual number.
$taskJob = 'ACTUALJOBID'
$taskLocalRoot = 'C:\Users\nazee\Documents\All Modules\FrameTrail'
$taskClusterUser = 'ka_udxvl'
$taskRemoteRoot = "/pfs/work9/workspace/scratch/${taskClusterUser}-frametrail/FrameTrail"
$taskResults = "$taskLocalRoot\output\kit-results\$taskJob"
New-Item -ItemType Directory -Path $taskResults -Force | Out-Null
scp -r "${taskClusterUser}@uc3.scc.kit.edu:${taskRemoteRoot}/output/training-general-v1/source-evidence-${taskJob}" "$taskResults"
scp "${taskClusterUser}@uc3.scc.kit.edu:${taskRemoteRoot}/frametrail-source-evidence-${taskJob}.log" "$taskResults"
```

Verify actual remote root through ws_find if it changes. scp copies FROM remote-user@host:/remote/path TO local destination; -r is for folders; result-folder/log prefixes vary by job, ID alone is not sufficient. Authentication stays in user's terminal.

Start next chat by reading current artifacts and asking whether this CPU package/job was uploaded/submitted since this snapshot. If no, provide only next bounded commands from NEXT.md. If yes, inspect actual job evidence. Do not submit GPU training just because CPU collection exits0.

## 9. Evidence/artifact index

TASK_ROOT is the absolute conversation artifact root from section1. All originals/versions remain. Read receipts instead of rerunning old builders (some refuse existing outputs; some older analysis scripts as main write old filenames).

Annotation closeout/flagging:
- inspect_annotations_20261010.py (read-only helper when imported; check its main before running)
- closeout_20261010_212459.py;verify_closeout_212459.cjs
- assessment-212459-before.json;assessment-212459-after.json;closeout-212459-receipt.json
- remaining-cases-212459.json/.md;flagged-cases-212459/review.html and22 case crops+C1
- closeout-checks-212459.ipynb

Workbook/case replay:
- apply_case_choices_20261011.py;verify_case_choices_20261011.cjs
- case-decisions-20261011-receipt.json;case-decisions-20261011-assessment.json
- resolve_final_cases_20261011.py;verify_final_cases_20261011.cjs
- case-decisions-20261011-final-receipt.json;case-decisions-20261011-final-assessment.json

Final QA folder release-qa-20261011:
- READINESS.md (illustrated eight findings/seven photos)
- priority-findings.json;readiness-profile.json;attribution-register.json;source-checks.json
- proposed-release-policy.json (proposal, NOT frozen/approved change)
- frozen-draft-reference-v1/annotations.json (byte-identical v2),snapshot-lock.json (unapproved QA snapshot)
- readiness-checks.ipynb;profile_release.py;package_readiness.py
- supported-proof/photos-01-06.jpg through55-60 (10 contact sheets)
- detail-proof/photo-NN-annotated.png and cleanPNG (17 targeted renders, not all claimed inspected)
- sources-final.html

Notebooks were executed as ordinary Python cells/std-library checks; nbformat/nbclient/Jupyter/viewer unavailable. No kernel/presentation verification claimed.

Final fixes/source package folder release-fixes-20261011:
- latest frametrail-annotations-20261011-qa-fixed-v3.json
- fix-receipt.json;post-fix-assessment.json;verify_fixes.cjs
- training-candidate.json;training-exclusions.json;NEXT.md
- source-package-receipt.json;package_source_tools.py;test_source_report.py
- frametrail-source-evidence-tools-v1.tar.gz and checksum
- source-tools-v1/ unpacked source;contract-fixtures/ (synthetic, not fetched evidence)
- root-level apply_release_fixes_20261011.py

Source archive entry hashes:
- collect-source-evidence.py:9344f37613251a071d0d298ddf23f6477381f73ee632820542f2827d23228de4
- run-cluster-source-evidence.sbatch:4a0f3de0654ce3a7f579d4789e10eea5aaf06dfa87ea71ddf48d236974efcb7b
- README.md:16675266f21b27aa274ad57391cbad51b17c555e81ef610885e0c8befe435ec9
- source-plan.json:454acd838917b7a0c940e3ebf02907467b0c65541395d34f1dd61a95d3eebced

Bundled runtime previously available at `C:\Users\nazee\.cache\codex-runtimes\codex-primary-runtime\dependencies`:python/python.exe,node/bin/node.exe,node/node_modules,native/git/cmd/git.exe. Check availability rather than reinstall. Do not infer fresh package state from this record.

## 10. Progress and remaining difficulty

Completed: native app and saved-analysis workflow; offline full-vocabulary tooling; working KIT environment/A100 smoke/checkpoints; publisher-train metadata catalogue; balanced600-ID selection; first60 photos; prose audit; editable box tool; RF prelabels; user's corrections and22-case decisions; deterministic rejection closeout; targetedQA/four fixes/five exact exclusions; prepared source-evidence module.

Current stage: reviewed annotation drafts and55 screened candidates, not approved training release. Infrastructure is no longer the main uncertainty; data completeness, usable source rights, taxonomy policy and honest evaluation are.

Next: collect/review source evidence, assistant-led final label/geometry gate, freeze actual source-group dataset and evaluation plan; then bounded KIT fine-tune, verify artifacts, compare unchanged baselines, export/test candidate, adopt only if measured improvement justifies regressions/resources. Expand remaining540/larger reviewed data modularly after the quality process is proven. A55-photo pilot is useful for workflow, not sufficient for robust597-category accuracy.

No permission to change unrelated project/app interface, purchase hardware, activate cameras, publish datasets, bypass access controls or automatically adopt a model is implied by the training goal.
