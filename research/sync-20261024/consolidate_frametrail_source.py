from pathlib import Path
import hashlib,json,shutil,subprocess

APP=Path(r'C:\Users\nazee\Documents\All Modules\FrameTrail')
CONT=Path(r'C:\Users\nazee\Documents\Codex\2026-10-18\frametrail-continuation')
SNAP=CONT/'outputs/native-lean-guide-20261019-v1/source'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(rel,text):
 p=APP/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(text,encoding='utf-8')
prior=subprocess.check_output(['git','rev-parse','HEAD'],cwd=APP,text=True).strip()
changes=[]; verified=0
for p in sorted(SNAP.rglob('*')):
 if not p.is_file() or '.deps' in p.relative_to(SNAP).parts:continue
 rel=p.relative_to(SNAP);dest=APP/rel
 if not dest.exists() or dest.read_bytes()!=p.read_bytes():
  changes.append({'path':rel.as_posix(),'previous_sha256':sha(dest) if dest.exists() else None,'snapshot_sha256':sha(p)})
  dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,dest)
 assert sha(dest)==sha(p);verified+=1
write('docs/SOURCE_CONSOLIDATION_20261024.json',json.dumps({'schema':1,'date':'2026-10-24','preserved_checkout_commit':prior,'source':'research/continuation-20261018/outputs/native-lean-guide-20261019-v1/source','reason':'Bring the latest previously verified desktop continuation source into the main build tree. Preserve earlier checkout revision and every versioned research source snapshot.','copied_source_files_verified':verified,'changed_files':changes,'models_or_scientific_results_changed':False},indent=2)+'\n')
shutil.copyfile(CONT/'AGENTS.md',APP/'AGENTS.md')
shutil.copyfile(CONT/'CURRENT_HANDOFF.md',APP/'CURRENT_HANDOFF.md')
old=(APP/'HANDOFF.md').read_text(encoding='utf-8')
write('HANDOFF.md','# Latest handoff — 24 October 2026\n\nRead [PROJECT_PROGRESS.md](PROJECT_PROGRESS.md) and [CURRENT_HANDOFF.md](CURRENT_HANDOFF.md) first. The code in the main tree now includes the latest single-window desktop and Quick Guide continuation. Full findings and original versioned handoffs are archived under [research/](research/README.md). The sections below are preserved historical context and do not supersede the latest handoff.\n\n---\n\n'+old)
readme=(APP/'README.md').read_text(encoding='utf-8')
start=readme.index('**Status:');end=readme.index('\n\n',start)
readme=readme[:start]+'**Status, 24 October 2026:** the desktop now has one workspace for Preview, Analysis, Smooth Playback, Camera and a searchable Quick Guide. YOLOX-S remains the default; RF-DETR remains an explicit experimental preview with an ONNX hold. The four-trial billboard experiment and three TRAIN-only studies are complete, with no qualifying model. The accepted broader billboard definition is undergoing data qualification. Read [current project progress](PROJECT_PROGRESS.md), [latest handoff](CURRENT_HANDOFF.md) and the [research archive](research/README.md).'+readme[end:]
write('README.md',readme)
for rel in ['docs/STATUS.md','docs/ROADMAP.md']:
 text=(APP/rel).read_text(encoding='utf-8')
 first=text.index('\n')+1
 text=text[:first]+'\n> Current update (24 October 2026): see [project progress](../PROJECT_PROGRESS.md) and [latest handoff](../CURRENT_HANDOFF.md). Older dated sections below preserve the development history.\n'+text[first:]
 write(rel,text)
ignore=(APP/'.gitignore').read_text(encoding='utf-8')
write('.gitignore',ignore+'\n# User-local demonstration footage and derived analysis; retained locally\n/gemini_generated_video_*.mp4\n/gemini_generated_video_*-analysis.csv\n\n# Keep copied research evidence separate from local runtime artifacts\n/research/**/__pycache__/\n/research/**/.env\n/research/**/.env.*\n')
attrs=(APP/'.gitattributes').read_text(encoding='utf-8')
write('.gitattributes',attrs+'\n# Frozen research evidence must retain its original bytes and hashes.\n/research/** -text\n')
write('PROJECT_PROGRESS.md','''# FrameTrail progress

Updated 24 October 2026. This is the current entry point; dated reports in the research archive are immutable historical evidence.

## Application

The main build tree now contains the latest desktop source from the verified 19 October continuation: one window with Preview, Analysis, Smooth Playback, Camera and Quick Guide. Navigation retains section state; guide search explains category support and can select a model. The latest package reported a 47.21% smaller core distribution by moving optional models alongside it; this is not a total-storage or inference-speed claim. See the [desktop report](research/continuation-20261018/outputs/native-lean-guide-20261019-v1/REPORT.md) and [source consolidation receipt](docs/SOURCE_CONSOLIDATION_20261024.json).

YOLOX-S remains the default. RF job 7805570 step 100 is an explicit experimental preview. The ONNX numerical hold remains open; `production_adoption=false`. No model has been promoted by this sync.

## Training and findings

The exact four-trial selector batch 7870268 finished and was evaluated once. No checkpoint qualified; `winner=null` and TEST predictions remain zero. Under the frozen narrow billboard labels, final M0 seeds 17/29 scored 11 TP / 8 FP and 10 TP / 8 FP; M1 scored 12 TP / 8 FP and 13 TP / 7 FP on 32 fresh validation photos. Both methods exceeded the legacy unknown-query cap of 530; unknown detections are not automatically false positives. See the [postrun report](research/continuation-20261018/outputs/fresh-selector-batch-20261022-v1/POSTRUN_REPORT.md).

Three separately authorized CPU studies completed eight fits each (24 fits, 3,840 diagnostic updates total), using only cached TRAIN features and fixed scene/identity folds. No saved or deployed model resulted. Full-query supervision disproved omitted negative queries as the sole explanation. The photo-maximum loss MLP fit its fitting queries cleanly but still alarmed on 15/77 held-fold absent photos at 0.5, with 48/71 covered positive queries hit. None demonstrated clean support across all folds. These reused TRAIN diagnostics are not independent model qualification. See the [photo-level study](research/continuation-20261018/outputs/train-photo-max-loss-7870268-20261022-v1/STUDY_REPORT.md).

## Accepted task and data revision

The user explicitly confirmed that restaurant/business identity boards and promotional boards both count as billboards. Earlier labels and completed metrics stay frozen. Some earlier negative supervision conflicts with the intended expanded task, so those old results cannot qualify a model under the new definition.

The first original-image review covered 323 photos. The separate draft identifies 20 previously absent photos containing in-scope boards (19 fresh, one old TRAIN). All 119 previously unknown validation photos retain unknown status. The draft is assistant-reviewed, not independent human gold, and is not approved for training. One inherited target around a 7 Av street-name sign is explicitly held and ineligible. See the [revision report](research/continuation-20261018/outputs/broad-billboard-definition-20261022-v1/REVISION_REPORT.md) and [task definition](research/continuation-20261018/outputs/broad-billboard-definition-20261022-v1/TASK_DEFINITION.json).

The corrected fresh draft lacks 11 TRAIN, 6 validation and 4 TEST truly absent photos. TRAIN also needs five genuine shop confusers and one traffic confuser to meet the existing family minima. An inventory enumerates 223 unused local candidates with fixed prospective roles; none is admitted yet. Complete content, annotation, rights, scene, duplicate and legacy-guard checks before any expanded baseline or fit. Do not silently treat business boards as negative or unknown photos as background.

## What GitHub contains

The current application and tooling source, earlier source snapshots, research scripts, experiment plans, authorizations, reports, metrics, annotation drafts, provenance records and handoffs are archived in [research/](research/README.md). The source manifest records original byte hashes. Raw media, model/checkpoint files, SDKs, build products, cached feature tensors and authentication/runtime files remain local; an inventory documents exclusions. This repository is a code and evidence archive, not a full binary backup or a data/model release.

Next step: qualify unused local photos to close the 11/6/4 absent-photo gaps, because the expanded billboard definition needs trustworthy coverage before another training comparison.
''')
write('research/README.md','''# FrameTrail research and evidence archive

Snapshot recorded 24 October 2026. Start with [current project progress](../PROJECT_PROGRESS.md) and the [latest handoff](../CURRENT_HANDOFF.md).

- [Continuation](continuation-20261018/): scripts, plans, authorization receipts, results, audits, versioned source snapshots and handoffs from the canonical continuation workspace. `outputs/` preserves the original names and directory structure.
- [Earlier local output](local-output/): inspectable text records from the application checkout, including earlier evaluations, annotation work and cluster receipts.
- [Source manifest](SOURCE_MANIFEST.json): original SHA-256 and byte count for each archived file. Git attributes disable newline conversion in this archive.
- [Local artifact inventory](LOCAL_ARTIFACT_INVENTORY.json): source path, size and reason for each excluded local file. Existing scientific manifests retain model/image artifact hashes. This inventory is not a backup of excluded contents.

All original reports and receipts remain historical snapshots, including failed attempts and superseded scope decisions. Absolute paths in those records describe the original Windows/cluster environment; a fresh clone will need explicit path configuration. Archived scripts may create exclusive snapshots or submit jobs: reading or publishing them does not authorize rerunning them. The latest task definition and handoff supersede older pending questions without changing old results.

The archive intentionally excludes raw photos/video, screenshots or embedded photo payloads, model weights/checkpoints, feature/cache binaries, generated packages/builds, third-party runtimes and authentication/session artifacts. These stay preserved locally. No dataset, trained-model or production release is claimed. Annotation drafts are assistant-reviewed and have unresolved qualification holds.

Current research entry points:

- [Training strategy](continuation-20261018/outputs/training-strategy-20261019-v1/STRATEGY.md)
- [Four-trial experiment](continuation-20261018/outputs/fresh-selector-batch-20261022-v1/POSTRUN_REPORT.md)
- [64-query discrimination](continuation-20261018/outputs/train-discrimination-7870268-20261022-v1/STUDY_REPORT.md)
- [Full-query control](continuation-20261018/outputs/train-discrimination-full-query-7870268-20261022-v1/CONTROL_REPORT.md)
- [Photo-level loss](continuation-20261018/outputs/train-photo-max-loss-7870268-20261022-v1/STUDY_REPORT.md)
- [Expanded definition and first review](continuation-20261018/outputs/broad-billboard-definition-20261022-v1/REVISION_REPORT.md)
- [Focused next-chat handoff](continuation-20261018/NEXT_CHAT_BROAD_BILLBOARD_20261022.md)

Next step: qualify the unused local candidates against the expanded definition, because the missing truly absent examples block a trustworthy new baseline.
''')
print(json.dumps({'copied_files_verified':verified,'updated_files':len(changes),'prior_commit':prior}))
