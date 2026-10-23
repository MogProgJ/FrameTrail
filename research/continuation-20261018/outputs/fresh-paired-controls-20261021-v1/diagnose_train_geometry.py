"""TRAIN-only geometry diagnosis from pinned initial full-layout caches; no fitting/heldout probing."""
import json,sys,hashlib
from pathlib import Path
C=Path(__file__).resolve().parent;OUT=C.parent
T=OUT/'selector-batch-proposal-7809335-20261018-v1/rf-selector-a77d9663-v1'
WHEEL=Path(r'C:\Users\nazee\.codex\visualizations\2026\10\11\01a12a01-d564-7de0-91f4-a16484eea2cb\rf-comparison-package-20261013-v1\local-assignment-wheel\torch_hungarian-0.1.0rc0-py3-none-any.whl')
sys.path[:0]=[str(T),str(OUT/'frozen-head-cpu-7809335-20261018-v1'),str(WHEEL)]
import torch
from scipy.optimize import linear_sum_assignment
from scoped_rf import target_from_row,ScopedRFCriterion
from cache_engine import replay
from rfdetr.utilities import box_ops
def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def sha(p):
 with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def main():
 torch.set_num_threads(2);torch.use_deterministic_algorithms(True)
 plan=read(C/'PLAN.json');inputs=read(plan['input_ref']['path'])
 head=torch.load(inputs['initial_head_ref']['path'],map_location='cpu',weights_only=True)
 matcher=ScopedRFCriterion(615).matcher;rows=[]
 with torch.no_grad():
  for r in inputs['records']:
   if r['pool'] not in ('fresh_positive','old_positive'):continue
   assert r['row']['split']=='train'
   p=r['cache_ref'];assert sha(p['path'])==p['sha256']
   value=torch.load(p['path'],map_location='cpu',weights_only=True);cache=value.get('cache',value)
   out=replay(cache,head['weight'],head['bias']);target=target_from_row(r['row'],615)
   wanted=target['boxes'][target['labels']==133]
   overlaps=box_ops.box_iou(box_ops.box_cxcywh_to_xyxy(out['pred_boxes'][0]),box_ops.box_cxcywh_to_xyxy(wanted))[0]
   q,t=linear_sum_assignment(-(overlaps.numpy()>=.5).astype(float)-overlaps.numpy()*1e-5)
   mq,mt=matcher(out,[target])[0];keep=target['labels'][mt]==133;mq=mq[keep];mt=mt[keep]
   matched=box_ops.elementwise_box_iou(box_ops.box_cxcywh_to_xyxy(out['pred_boxes'][0,mq]),box_ops.box_cxcywh_to_xyxy(target['boxes'][mt]))[0]
   rows.append(dict(image_id=r['image_id'],pool=r['pool'],targets=len(wanted),
    one_to_one_geometry_covered=int((overlaps[q,t]>=.5).sum()),actual_loss_matches_IoU_at_least_0_5=int((matched>=.5).sum()),
    baseline_max_billboard_score=float(out['pred_logits'][0,:,133].sigmoid().max())))
 totals={}
 for pool in ('fresh_positive','old_positive'):
  part=[r for r in rows if r['pool']==pool]
  totals[pool]=dict(photos=len(part),**{k:sum(r[k] for r in part) for k in ('targets','one_to_one_geometry_covered','actual_loss_matches_IoU_at_least_0_5')})
 report=dict(status='TRAIN-only-initial-geometry-audited',plan_sha256=sha(C/'PLAN.json'),totals=totals,records=rows,test_photos_used=0,validation_photos_probed=0,optimizer_updates=0)
 with (C/'TRAIN_GEOMETRY_DIAGNOSIS.json').open('x',encoding='utf-8') as f:f.write(json.dumps(report,indent=2)+'\n')
 print(json.dumps(totals))
if __name__=='__main__':main()

