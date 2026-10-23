"""Pinned CPU validation, global lock, then known/fresh TEST veto once. Never select on TEST."""
import os,sys,time,argparse,importlib.metadata
from pathlib import Path
HERE=Path(__file__).resolve().parent;OUT=HERE.parent
T=OUT/'selector-batch-proposal-7809335-20261018-v1/rf-selector-a77d9663-v1'
C=OUT/'fresh-paired-controls-20261021-v1';D=OUT/'data-review-7840599-20261021-v1'
WHEEL=Path(r'C:\Users\nazee\.codex\visualizations\2026\10\11\01a12a01-d564-7de0-91f4-a16484eea2cb\rf-comparison-package-20261013-v1\local-assignment-wheel\torch_hungarian-0.1.0rc0-py3-none-any.whl')
sys.path[:0]=[str(HERE/'rf-fresh-selector-v1'),str(T),str(WHEEL)]
os.environ.update(HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',HF_HUB_DISABLE_TELEMETRY='1',DO_NOT_TRACK='1')
import torch
from batch_guard import *
from verify_results import verify_result
from scoped_engine import build_model,load_sample,validate_release
from scoped_metrics import decode,score
from selection_policy import evaluate
from determinism_policy import math_attention
from regression_stage import gate
from score_video_reference import score as score_reference

def score_role(rows,preds,role):
    # The unchanged primitive insists on 'val'. Explicit temporary scoring adapter;
    # preserve original immutable role in report and never modify release rows.
    import copy
    if any(r['split']!=role for r in rows):raise ValueError('Role mismatch')
    adapted=copy.deepcopy(rows)
    for r in adapted:r['split']='val'
    return score(adapted,preds)

@math_attention()
def run(downloads,job):
    base=HERE/'rf-fresh-selector-v1';verify_files(base);s=validate_scope(read(base/'SCOPE.json'));scope_sha=sha(base/'SCOPE.json');valid_job(job)
    for ref in read(HERE/'LOCAL_INPUTS.json')['refs']:
        if sha(ref['path'])!=ref['sha256']:raise ValueError('Local receipt/input differs: '+ref['path'])
    for i in (0,1):
        result=verify_result(downloads/f'verified-{job}_{i}',base,job,i)
        if not result['complete']:
            write(downloads/'NO_SELECTION_FAILED_TASK.json',dict(status='incomplete-batch-no-selection-no-retry',production_adoption=False));return
    if str(torch.__version__)!='2.8.0+cpu' or importlib.metadata.version('rfdetr')!='1.11.2':raise ValueError('Pinned CPU reference runtime required')
    out=downloads/'local-evaluation';out.mkdir(exist_ok=False)
    torch.set_num_threads(2);torch.manual_seed(17);torch.use_deterministic_algorithms(True)
    full_path=D/'reviewed-release-v1/scoped-fresh-additions-v1.json';full=validate_release(full_path)
    records=read(C/'INPUTS.json')['records'];old_val=[r['row'] for r in records if r['pool']=='old_validation'];fresh_val=[r['row'] for r in records if r['pool']=='fresh_validation']
    original=read(T/'inputs/validation-original.json');current=read(T/'inputs/validation-resume.json');baseline=read(OUT/'fresh-data-baseline-20261021-v1/BASELINE_REPORT.json')['metrics']
    cpu_report=read(C/'PAIRED_CONTROL_REPORT.json');conditions=[]
    for i,r in enumerate(cpu_report['conditions']):
        conditions.append(dict(method='M0',seed=r['seed'],index=i,complete=r['status']=='complete',best=None))
    if any(c['new_candidate_selected'] for c in cpu_report['conditions']):raise ValueError('Expected audited failed CPU controls; never ignore changed controls')
    weights=Path(r'C:\Users\nazee\Documents\All Modules\FrameTrail\.deps\rfdetr-probe-assets\rf-detr-small.pth')
    checkpoint=T/'inputs/selected-7805570.pt'
    if sha(checkpoint)!=CHECKPOINT:raise ValueError('Starting weights')
    model=build_model(weights,base/'rf-mapping.json').cpu().eval();ck=torch.load(checkpoint,map_location='cpu',weights_only=True);model.load_state_dict(ck['model_state_dict'],strict=True);del ck
    for p in model.parameters():p.requires_grad_(False)
    fingerprint=frozen_digest(model.state_dict());initial_rows={k:model.state_dict()[k][133].clone() for k in KEYS}
    def predict(root,rows):
        predictions={}
        with torch.inference_mode():
            for row in rows:
                image,_=load_sample(root,row,'cpu');predictions[row['image_id']]=decode(model(image),row['width'],row['height'])
        return predictions
    for index,seed in enumerate((17,29)):
        folder=downloads/f'verified-{job}_{index}';report=read(folder/'REPORT.json');selection_start=time.monotonic();best=None
        patch0=torch.load(folder/'patch-0000.pt',map_location='cpu',weights_only=True)
        if report['frozen_digest']!=fingerprint or any(tensor_digest(patch0['rows'][k])!=tensor_digest(initial_rows[k]) for k in KEYS):raise ValueError('Step-zero state identity differs')
        # Reuse exact already-scored step0 only after full checkpoint/row/data/hash identity checks.
        write(out/f'M1-{seed}-validation-0000.json',dict(step=0,seed=seed,old=current,fresh=baseline,**qualification(current,baseline,original,current,baseline),step_zero_identity_verified=True))
        complete=True
        for step in STEPS[1:]:
            if report['elapsed_active_seconds']+time.monotonic()-selection_start>=1800:complete=False;break
            patch=torch.load(folder/f'patch-{step:04}.pt',map_location='cpu',weights_only=True);check_patch(patch,scope_sha,seed,step,f'{job}_{index}');apply_patch_rows(model,patch)
            if frozen_digest(model.state_dict())!=fingerprint:raise ValueError('Patch changed inactive/frozen state')
            old=evaluate(old_val,predict(T/'release',old_val));fresh=score(fresh_val,predict(full_path.parent,fresh_val));decision=qualification(old,fresh,original,current,baseline)
            item=dict(method='M1',index=index+2,seed=seed,step=step,old=old,fresh=fresh,**decision,patch_path=str(folder/f'patch-{step:04}.pt'),patch_sha256=sha(folder/f'patch-{step:04}.pt'))
            write(out/f'M1-{seed}-validation-{step:04}.json',item)
            if decision['qualifies'] and (best is None or rank(item)>rank(best)):best=item
            print(json.dumps(dict(seed=seed,step=step,tp=fresh['complete_tp'],fp=fresh['complete_fp'],qualifies=decision['qualifies'])),flush=True)
            if report['elapsed_active_seconds']+time.monotonic()-selection_start>=1800:complete=False;break
        conditions.append(dict(method='M1',seed=seed,index=index+2,complete=complete,best=best,
          combined_training_validation_seconds=report['elapsed_active_seconds']+time.monotonic()-selection_start))
    winner=choose(conditions);write(out/'GLOBAL_SELECTION.json',dict(conditions=conditions,winner=winner,selection='validation-only; paired methods require both seeds',production_adoption=False))
    if winner is None:
        write(out/'FINAL_REPORT.json',dict(status='no-qualifying-method-keep-starting-model',test_photos_used=0,production_adoption=False));return
    # Lock exists BEFORE any known-regression/freshTEST inference; exclusive directory prevents repeated consumption.
    write(out/'WINNER_LOCK.json',dict(winner=winner,scope_sha256=scope_sha,fresh_test_uses='one locked winner once; veto only; no runner-up',production_adoption=False))
    locked_patch=torch.load(winner['patch_path'],map_location='cpu',weights_only=True)
    if sha(winner['patch_path'])!=winner['patch_sha256']:raise ValueError('Locked patch changed')
    apply_patch_rows(model,locked_patch)
    from PIL import Image
    from torchvision.transforms import functional as TF
    predictions={}
    with torch.inference_mode():
        for h,row in read(T/'known-regression/images.json').items():
            path=contained(T,row['path'])
            if sha(path)!=h:raise ValueError('Known regression image changed')
            with Image.open(path) as im:x=TF.normalize(TF.resize(TF.to_tensor(im.convert('RGB')),[512,512],antialias=False),[.485,.456,.406],[.229,.224,.225]).unsqueeze(0)
            predictions[h]=decode(model(x),row['width'],row['height'])
    checks={}
    for path in sorted((T/'known-regression/references').glob('*.json')):
        ref=read(path);payload=dict(reference_sha256=ref['source_sha256'],class_namespace='native-canonical',vocabulary_sha256=ref['vocabulary_sha256'],confidence_threshold=.35,frames=[dict(frame_id=f['id'],detections=predictions[f['sha256']]) for f in ref['frames']])
        scored=score_reference(ref,payload,ref['source_sha256']);write(out/f'known-{path.stem}.json',scored)
        checks[path.stem]={b:gate(read(T/'known-regression'/f'{b}-{path.stem}.json'),scored) for b in ('original','current')}
    write(out/'KNOWN_REGRESSION.json',checks)
    if not all(c['passed'] for group in checks.values() for c in group.values()):
        write(out/'FINAL_REPORT.json',dict(status='locked-winner-vetoed-by-known-regression-no-reselection',test_photos_used=0,production_adoption=False));return
    test=[r for r in full['images'] if r['split']=='test'];assert len(test)==32
    write(out/'FRESH_TEST_CONSUMPTION_LOCK.json',dict(locked_patch_sha256=winner['patch_sha256'],scope_sha256=scope_sha,photos=32,baseline='pinned current starting model',veto=s['fresh_test_veto'],no_runner_up=True))
    candidate_preds=predict(full_path.parent,test);candidate=score_role(test,candidate_preds,'test')
    apply_patch_rows(model,dict(rows=initial_rows));start_preds=predict(full_path.parent,test);start=score_role(test,start_preds,'test')
    passed=candidate['complete_tp']>=start['complete_tp']+3 and candidate['complete_fp']<=start['complete_fp']
    write(out/'FRESH_TEST.json',dict(original_role='test',scorer_adapter='temporary deep copy role val for unchanged score primitive; release untouched',candidate=candidate,baseline=start,candidate_predictions=candidate_preds,baseline_predictions=start_preds,veto_passed=passed,selection_allowed=False))
    if frozen_digest(model.state_dict())!=fingerprint or sha(checkpoint)!=CHECKPOINT:raise ValueError('Frozen inference state changed')
    write(out/'FINAL_REPORT.json',dict(status='locked-winner-passed-evidence-gates-awaiting-separate-ONNX-cost-app-qualification' if passed else 'locked-winner-vetoed-by-fresh-test-no-reselection',winner=winner,test_photos_used=32,production_adoption=False))
if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--downloads',type=Path,required=True);ap.add_argument('--job',required=True);a=ap.parse_args();run(a.downloads,a.job)
