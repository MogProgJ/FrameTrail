"""Build/seal once after tests. No network, inference, training or scheduler calls."""
import json,hashlib,shutil,tarfile,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;OUT=HERE.parent;sys.path.insert(0,str(HERE/'tools'))
from batch_guard import *
T=OUT/'selector-batch-proposal-7809335-20261018-v1/rf-selector-a77d9663-v1'
C=OUT/'fresh-paired-controls-20261021-v1';D=OUT/'data-review-7840599-20261021-v1'
def textfile(p,text):p.write_text(text,encoding='utf-8',newline='\n')
def copy(src,dst):dst.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(src,dst)
def build():
    base=HERE/'rf-fresh-selector-v1';base.mkdir(exist_ok=False);(base/'receipts').mkdir()
    for p in (HERE/'tools').iterdir():
        if p.is_file() and p.suffix in ('.py','.sh','.sbatch'):copy(p,base/p.name)
    for name in ('scoped_engine.py','scoped_rf.py','scoped_metrics.py','selection_policy.py','selector_mechanics.py','determinism_policy.py','release_guard.py','rf-mapping.json'):
        copy(T/name,base/name)
    receipt_sources={
      'CPU_PLAN.json':C/'PLAN.json','CPU_INPUTS.json':C/'INPUTS.json','EXECUTION_ORDER_NOTE.json':C/'EXECUTION_ORDER_NOTE.json',
      'LOSS_PREFLIGHT.json':C/'PREFLIGHT_REPORT.json','CPU_CONTROL_REPORT.json':C/'PAIRED_CONTROL_REPORT.json',
      'CPU_AUDIT.json':C/'INDEPENDENT_AUDIT.json','CPU_STEP_ZERO.json':C/'STEP_ZERO_REPRODUCTION.json',
      'TRAIN_GEOMETRY_DIAGNOSIS.json':C/'TRAIN_GEOMETRY_DIAGNOSIS.json','FRESH_BASELINE.json':OUT/'fresh-data-baseline-20261021-v1/BASELINE_REPORT.json',
      'READINESS_REPORT.json':D/'READINESS_REPORT.json','SCENE_AND_ANNOTATION_REVIEW.json':D/'FINAL_SCENE_AND_ANNOTATION_REVIEW.json',
      'EXPERIMENT_DESIGN.json':OUT/'training-strategy-20261019-v1/EXPERIMENT_DESIGN.json',
      'fresh-full-manifest.json':D/'reviewed-release-v1/scoped-fresh-additions-v1.json',
      'validation-original.json':T/'inputs/validation-original.json','validation-current.json':T/'inputs/validation-resume.json'}
    for name,path in receipt_sources.items():copy(path,base/'receipts'/name)
    for seed in (17,29):copy(C/f'schedule-{seed}.json',base/f'schedule-{seed}.json')
    full=read(receipt_sources['fresh-full-manifest.json']);subset=dict(full);subset['images']=[r for r in full['images'] if r['split'] in ('train','val')]
    fresh=base/'fresh';fresh.mkdir();write(fresh/'scoped-fresh-additions-v1.json',subset)
    original_root=receipt_sources['fresh-full-manifest.json'].parent
    for r in subset['images']:
        for name in (r['source_path'],r['rights_receipt_path'],f"source-pages/{r['image_id']}.html.gz",f"source-evidence/{r['image_id']}.json",f"reviews/{r['image_id']}.json"):
            copy(contained(original_root,name),contained(fresh,name))
    frozen_inputs=read(C/'INPUTS.json');records=[]
    for r in frozen_inputs['records']:
        records.append(dict(image_id=r['image_id'],pool=r['pool'],row=r['row'],source='fresh' if r['source']=='fresh-reviewed-release' else 'old'))
    write(base/'INPUTS.json',dict(records=records,parent_sha256=sha(C/'INPUTS.json')))
    scope=dict(schema=1,date='2026-10-22',method='M1-main-and-encoder-row133',seeds=[17,29],max_updates=1500,main_lr=.0001,encoder_lr=.00003,
      dense_encoder_weight=1,weight_decay=0,clip=.1,AMP=False,active_seconds=1800,active_budget_includes_deferred_cpu_validation=True,finalization_seconds=480,
      array='0-1%2',cpus=2,memory_gib=8,wall_minutes=45,max_allocated_gpu_hours=1.5,validation_steps=list(STEPS),starting_checkpoint_sha256=CHECKPOINT,
      retries=0,requeues=0,replacement_jobs=0,test_photos_used_on_cluster=0,scoring_device='local-pinned-Torch-2.8.0+cpu',production_adoption=False,
      schedule_sha256={str(seed):sha(C/f'schedule-{seed}.json') for seed in (17,29)},old_release_sha256=OLD_RELEASE,
      full_fresh_release_sha256=sha(receipt_sources['fresh-full-manifest.json']),cpu_plan_sha256=sha(C/'PLAN.json'),
      selection=dict(min_extra_hits=3,max_extra_fp=0,original_unknown_cap=530,both_baselines=True,both_seeds=True,test_reselection=False),
      fresh_test_veto='One locked winner vs pinned current baseline on the same 32 untouched TEST photos; require >=3 additional billboard hits and 0 extra billboard FP. Freeze before TEST inference. Veto only, no runner-up.',
      deferred_validation='All six fixed patch states saved, no adaptive training/selection on GPU. Common pinned CPU scorer after one retrieval; combined GPU-active + per-seed local validation must remain <1800 seconds or seed is incomplete. This changes execution placement, not states/objective/thresholds/gates.',
      execution_order_deviation='Exact schedules sealed after baseline but before fits. 19Oct TRAIN pools/seeds/four-slot rule fixed earlier; sampler did not consume validation metrics. See unchanged receipt; do not claim full preregistration.',
      authorization='Standing human continuous-work clarification18Oct in CONT/AGENTS.md and supplied project instructions: bounded cluster continuation without routine approval; direct KIT authentication still required.',
      scope_rationale='Remaining two prespecified trials only. M0 controls already completed/failed quality gates. No extra learning-rate sweeps, backbone/box unfreezing, retries, or data/threshold changes. Two tasks maximize useful evidence without repeating failed controls.')
    validate_scope(scope);validate_inputs(records,[read(base/f'schedule-{seed}.json') for seed in (17,29)]);write(base/'SCOPE.json',scope)
    write(base/'AUTHORIZATION.json',dict(scope_sha256=sha(base/'SCOPE.json'),source=str(HERE.parent.parent/'AGENTS.md'),basis=scope['authorization'],new_scope_recorded_before_submission=True,submitted=False))
    local_refs=set(receipt_sources.values())|{C/'schedule-17.json',C/'schedule-29.json',C/'INPUTS.json',T/'inputs/selected-7805570.pt',T/'rf-mapping.json',HERE/'local_followup.py'}
    for seed in (17,29):local_refs.update((C/f'seed-{seed}/REPORT.json',C/f'seed-{seed}/validation-0000.json',C/f'seed-{seed}/validation-1500.json'))
    for p in (T/'known-regression').rglob('*'):
        if p.is_file():local_refs.add(p)
    write(HERE/'LOCAL_INPUTS.json',dict(refs=[dict(path=str(p),sha256=sha(p)) for p in sorted(local_refs)]))
    seal={p.relative_to(base).as_posix():sha(p) for p in sorted(base.rglob('*')) if p.is_file()}
    write(base/'package-files.json',seal)
    archive=HERE/'frametrail-rf-fresh-selector-v1.tar.gz'
    with tarfile.open(archive,'x:gz') as tf:
        for p in sorted(base.rglob('*')):
            if p.is_file():tf.add(p,arcname=base.name+'/'+p.relative_to(base).as_posix(),recursive=False)
    start=HERE/'START_FRESH_SELECTOR_ON_CLUSTER.sh'
    textfile(start,'''#!/bin/bash
set -euo pipefail
task_project="$(ws_find frametrail)/FrameTrail"
task_archive="$task_project/output/frametrail-rf-fresh-selector-v1.tar.gz"
task_actual=$(sha256sum "$task_archive" | awk '{print $1}')
[[ "$task_actual" == "ARCHIVE_SHA" ]] || { echo 'Archive checksum differs; stop.'; exit 1; }
task_tools="$task_project/output/training-general-v1/rf-fresh-selector-v1"
if [[ -e "$task_tools" ]]; then
  [[ -d "$task_tools" && ! -L "$task_tools" && -f "$task_tools/package-files.json" ]] || exit 1
else
  mkdir "$task_tools"
  tar --extract --gzip --file="$task_archive" --strip-components=1 --no-same-owner --directory="$task_tools"
fi
task_seal=$(sha256sum "$task_tools/package-files.json" | awk '{print $1}')
[[ "$task_seal" == "SEAL_SHA" ]] || { echo 'Package seal differs; stop.'; exit 1; }
bash "$task_tools/submit.sh"
'''.replace('ARCHIVE_SHA',sha(archive)).replace('SEAL_SHA',sha(base/'package-files.json')))
    write(HERE/'archive-receipt.json',dict(archive=archive.name,archive_sha256=sha(archive),bytes=archive.stat().st_size,cluster_start_script=start.name,
      cluster_start_script_sha256=sha(start),package_seal_sha256=sha(base/'package-files.json'),scope_sha256=sha(base/'SCOPE.json'),files=len(seal),fresh_upload_photos=92,test_pixels_uploaded=0,
      cluster_submitted=False,production_adoption=False))
    print(json.dumps(read(HERE/'archive-receipt.json'),indent=2))
if __name__=='__main__':build()
