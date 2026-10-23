"""Score frozen selected state against KNOWN references; never reselect/train."""
import argparse,json,os,time
from pathlib import Path
import torch
from PIL import Image
from torchvision.transforms import functional as TF
from continuation_guard import read,sha,variant
from scoped_engine import build_model
from scoped_metrics import decode
from determinism_policy import math_attention
from head_policy import fingerprint_frozen
from score_video_reference import score
T=Path(__file__).resolve().parent
def save(p,v):
    with p.open('x',encoding='utf-8') as f:json.dump(v,f,indent=2,allow_nan=False)
def gate(b,c):
    zero=dict(complete_tp=0,complete_fp=0,partial_positive_hits=0);failures=[]
    for name in sorted(set(b['by_class'])|set(c['by_class'])):
        before=b['by_class'].get(name,zero);after=c['by_class'].get(name,zero)
        for k in zero:
            good=after[k]<=before[k] if k=='complete_fp' else after[k]>=before[k]
            if not good:failures.append(dict(category=name,metric=k,before=before[k],after=after[k]))
    return dict(passed=not failures,failures=failures)
@math_attention()
def run(project):
    v=variant(T);run_id=os.environ['SLURM_ARRAY_JOB_ID']+'_'+str(v['index'])
    out=project/'output'/('rf-selector-'+run_id);report=read(out/'experiment-report.json')
    best=out/'best.pt';pinned=sha(best)
    if pinned!=report['best_checkpoint_sha256']:raise ValueError('Selected checkpoint differs')
    save(out/'regression-lock.json',dict(best_checkpoint_sha256=pinned,best_step=report['best_step'],selection='already frozen by validation alone',references='known, consumed; not fresh heldout',production_adoption=False))
    if not report['new_candidate_selected']:
        save(out/'known-regression.json',dict(status='step-zero-unchanged-reuse-pinned-current-scores',best_checkpoint_sha256=pinned,scored_new_images=0,retention_passed=True,reference_sets=6,production_adoption=False));return
    torch.set_num_threads(2);torch.manual_seed(17);torch.cuda.manual_seed_all(17);torch.use_deterministic_algorithms(True)
    torch.backends.cuda.matmul.allow_tf32=False;torch.backends.cudnn.allow_tf32=False;torch.backends.cudnn.benchmark=False
    model=build_model(project/'output/rf-comparison-v1/assets/rf-detr-small.pth',T/'rf-mapping.json')
    ck=torch.load(best,map_location='cpu',weights_only=True);model.load_state_dict(ck['model_state_dict'],strict=True);del ck
    model=model.to('cuda:0').eval();frozen=fingerprint_frozen(model);predictions={};started=time.monotonic()
    with torch.inference_mode():
        for h,row in read(T/'known-regression/images.json').items():
            if time.monotonic()-started>420:raise ValueError('Regression time cap; preserve partial output')
            path=T/row['path']
            if sha(path)!=h:raise ValueError('Known image changed')
            with Image.open(path) as im:x=TF.normalize(TF.resize(TF.to_tensor(im.convert('RGB')),[512,512],antialias=False),[.485,.456,.406],[.229,.224,.225]).unsqueeze(0).to('cuda:0')
            predictions[h]=decode(model(x),row['width'],row['height'])
    save(out/'known-regression-predictions.json',predictions);checks={}
    for path in sorted((T/'known-regression/references').glob('*.json')):
        ref=read(path);payload=dict(reference_sha256=ref['source_sha256'],class_namespace='native-canonical',vocabulary_sha256=ref['vocabulary_sha256'],confidence_threshold=.35,frames=[dict(frame_id=f['id'],detections=predictions[f['sha256']]) for f in ref['frames']])
        result=score(ref,payload,ref['source_sha256']);save(out/('known-scored-'+path.stem+'.json'),result)
        checks[path.stem]={b:gate(read(T/'known-regression'/f'{b}-{path.stem}.json'),result) for b in ('original','current')}
    if fingerprint_frozen(model)!=frozen or sha(best)!=pinned:raise ValueError('Frozen inference state/checkpoint changed')
    save(out/'known-regression.json',dict(status='known-regression-scored-no-reselection',best_checkpoint_sha256=pinned,scored_new_images=len(predictions),reference_sets=6,retention_passed=all(c['passed'] for group in checks.values() for c in group.values()),checks=checks,references_consumed=True,optimizer_updates=0,production_adoption=False,elapsed_seconds=time.monotonic()-started))
if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--project',type=Path,required=True);run(ap.parse_args().project)
