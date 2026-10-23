"""Eight fixed training photos, two checkpoints, no optimizer or updates."""
import os,sys,json,hashlib,random,time
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parent
TOOLS=Path(r'C:\Users\nazee\.codex\visualizations\2026\10\17\01a14c2d-b771-7a40-ba9b-e8277e4905a1\work\rf-balanced-continuation-20261018-v1\rf-balanced-ddbb57c6-v1')
WHEEL=Path(r'C:\Users\nazee\.codex\visualizations\2026\10\11\01a12a01-d564-7de0-91f4-a16484eea2cb\rf-comparison-package-20261013-v1\local-assignment-wheel\torch_hungarian-0.1.0rc0-py3-none-any.whl')
sys.dont_write_bytecode=True;sys.path[:0]=[str(TOOLS),str(WHEEL)]
os.environ.update(HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',HF_HUB_DISABLE_TELEMETRY='1',MPLCONFIGDIR=str(HERE/'runtime-cache'))
import torch
from scoped_engine import build_model,load_sample
from scoped_rf import ScopedRFCriterion,weighted_loss
from determinism_policy import math_attention
from rfdetr.utilities import box_ops
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):
 with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def save(name,d):
 with (HERE/name).open('x',encoding='utf-8') as f:json.dump(d,f,indent=2,allow_nan=False)
def fingerprint(model):
 d=hashlib.sha256()
 for k,v in model.state_dict().items():d.update(k.encode());d.update(v.detach().cpu().contiguous().numpy().tobytes())
 return d.hexdigest()
@math_attention()
def main():
 torch.set_num_threads(2);torch.manual_seed(17);torch.use_deterministic_algorithms(True)
 manifest=TOOLS/'release/candidate-manifest-v2.json';assert sha(manifest)=='e43a2c7a415c4f82209a1fc2471d8677503f51315e71f422ec0d6665eac377b9'
 train=[r for r in read(manifest)['images'] if r['split']=='train']
 positives=sorted([r for r in train if any(t['canonical_id']==133 for t in r['targets'])],key=lambda r:r['image_id'])
 negatives=sorted([r for r in train if r['scope'].get('133')=='absent'],key=lambda r:r['image_id'])
 rng=random.Random(171022);selected=[('positive',r) for r in rng.sample(positives,4)]+[('explicit-negative',r) for r in rng.sample(negatives,4)]
 save('SELECTION.json',dict(seed=171022,positive_pool=len(positives),negative_pool=len(negatives),selected=[dict(role=role,image_id=r['image_id'],image_sha256=r['image_sha256']) for role,r in selected],selection_uses_training_only=True))
 run=ROOT/'rf-balanced-verification-repair-7805570-20261018-v1/verified-7805570/output/rf-balanced-7805570'
 paths={'selected-100':run/'best.pt','rejected-last-2000':run/'last.pt'}
 hashes={str(p):sha(p) for p in [manifest,*paths.values(),*[TOOLS/'release'/r['source_path'] for _,r in selected]]}
 save('INPUT_HASHES.json',hashes)
 net=build_model(Path(r'C:\Users\nazee\Documents\All Modules\FrameTrail\.deps\rfdetr-probe-assets\rf-detr-small.pth'),TOOLS/'rf-mapping.json').cpu().eval();net.requires_grad_(False);head=net.class_embed;head.requires_grad_(True)
 mask=torch.zeros(616);mask[133]=1;head.weight.register_hook(lambda g:g*mask[:,None]);head.bias.register_hook(lambda g:g*mask)
 criterion=ScopedRFCriterion(615);records=[];states=[]
 for label,path in paths.items():
  ck=torch.load(path,map_location='cpu',weights_only=True);net.load_state_dict(ck['model_state_dict'],strict=True);del ck
  before=fingerprint(net)
  for role,row in selected:
   assert row['split']=='train';net.zero_grad(set_to_none=True);image,target=load_sample(TOOLS/'release',row);out=net(image);out['pred_logits'].retain_grad()
   losses=criterion(out,[target]);total=weighted_loss(losses);assert torch.isfinite(total);total.backward()
   inactive=[i for i in range(616) if i!=133]
   assert not head.weight.grad[inactive].any() and not head.bias.grad[inactive].any()
   assert all(p.grad is None for name,p in net.named_parameters() if name not in ['class_embed.weight','class_embed.bias'])
   main=out['pred_logits'].detach().sigmoid()[0,:,133];grad=out['pred_logits'].grad[0,:,133];match=[]
   for t in row['targets']:
    if t['canonical_id']!=133:continue
    box=torch.tensor(t['normalized_cxcywh']).unsqueeze(0)
    overlaps=box_ops.box_iou(box_ops.box_cxcywh_to_xyxy(out['pred_boxes'][0].detach()),box_ops.box_cxcywh_to_xyxy(box))[0][:,0]
    valid=overlaps>=.5
    match.append(dict(covering_queries=int(valid.sum()),max_probability_on_covering_queries=float(main[valid].max()) if valid.any() else None))
   if role=='explicit-negative':assert bool((grad>=-1e-8).all())
   record=dict(checkpoint=label,role=role,image_id=row['image_id'],max_billboard_probability=float(main.max()),targets=match,head_weight_gradient_l2=float(head.weight.grad[133].norm()),head_bias_gradient=float(head.bias.grad[133]),main_positive_gradient_sum=float(grad[grad>0].sum()),main_negative_gradient_sum=float(grad[grad<0].sum()))
   records.append(record);print(label,role,row['image_id'],flush=True)
  after=fingerprint(net);assert before==after;states.append(dict(checkpoint=label,before=before,after=after,unchanged=True))
 assert all(sha(Path(p))==h for p,h in hashes.items())
 save('REVIEW.json',dict(status='training-only-gradient-review-complete',records=records,state_checks=states,training_photos=8,forward_backward_checks=16,active_gradient_row=133,optimizer_created=False,optimizer_updates=0,all_weights_unchanged=True,all_inputs_unchanged=True,heldout_or_validation_used=False,limits='Small fixed training-only diagnostic, not performance measurement or proof that another trial will work. The step-2000 state is rejected diagnostic evidence, never a reselected candidate.'))
if __name__=='__main__':main()
