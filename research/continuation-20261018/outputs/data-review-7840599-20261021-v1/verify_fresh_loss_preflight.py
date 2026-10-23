"""Meaningful fresh/old full-forward versus full-layout cached loss/gradient preflight; zero optimizer updates."""
import os,sys,json,time,hashlib,copy
from pathlib import Path
OUT=Path(__file__).resolve().parent.parent
T=OUT/'selector-batch-proposal-7809335-20261018-v1/rf-selector-a77d9663-v1'
F=OUT/'frozen-head-cpu-7809335-20261018-v1'
C=OUT/'fresh-paired-controls-20261021-v1'
WHEEL=Path(r'C:\Users\nazee\.codex\visualizations\2026\10\11\01a12a01-d564-7de0-91f4-a16484eea2cb\rf-comparison-package-20261013-v1\local-assignment-wheel\torch_hungarian-0.1.0rc0-py3-none-any.whl')
sys.path[:0]=[str(T),str(F),str(WHEEL)]
os.environ.update(HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',HF_HUB_DISABLE_TELEMETRY='1',DO_NOT_TRACK='1')
import torch
from scoped_engine import build_model,load_sample
from scoped_rf import ScopedRFCriterion,weighted_loss,target_from_row
from cache_engine import replay,max_output_error
from determinism_policy import math_attention
from selector_mechanics import configure,fingerprint_frozen,capture_dense,dense_billboard_loss
def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def sha(p):
 with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def load(ref):
 assert sha(ref['path'])==ref['sha256']
 value=torch.load(ref['path'],map_location='cpu',weights_only=True)
 return value.get('cache',value)
@math_attention()
def main():
 started=time.monotonic();torch.set_num_threads(2);torch.manual_seed(17);torch.use_deterministic_algorithms(True)
 plan=read(C/'PLAN.json');inputs=read(plan['input_ref']['path']);assert sha(plan['input_ref']['path'])==plan['input_ref']['sha256']
 records={r['image_id']:r for r in inputs['records']}
 first=read(plan['schedule_refs'][0]['path'])[0]
 model=build_model(Path(r'C:\Users\nazee\Documents\All Modules\FrameTrail\.deps\rfdetr-probe-assets\rf-detr-small.pth'),T/'rf-mapping.json').cpu().eval()
 cp=T/'inputs/selected-7805570.pt';assert sha(cp)==plan['starting_checkpoint_sha256']
 state=torch.load(cp,map_location='cpu',weights_only=True);model.load_state_dict(state['model_state_dict'],strict=True);del state
 initial=torch.load(inputs['initial_head_ref']['path'],map_location='cpu',weights_only=True)
 assert torch.equal(initial['weight'],model.class_embed.weight) and torch.equal(initial['bias'],model.class_embed.bias)
 _,check,allowed=configure(model,0,plan['main_lr']);frozen=fingerprint_frozen(model,allowed)
 criterion=ScopedRFCriterion(615);tests=[]
 for iid in first:
  r=records[iid];assert r['row']['split']=='train'
  image,target=load_sample(r['base'],r['row'],'cpu');cache=load(r['cache_ref'])
  model.zero_grad(set_to_none=True);full=model(image)
  value=weighted_loss(criterion(full,[target]));value.backward()
  wg=model.class_embed.weight.grad.detach().clone();bg=model.class_embed.bias.grad.detach().clone()
  w=torch.nn.Parameter(initial['weight'].clone());b=torch.nn.Parameter(initial['bias'].clone())
  mask=torch.zeros(616);mask[133]=1
  w.register_hook(lambda grad:grad*mask[:,None]);b.register_hook(lambda grad:grad*mask)
  cached=replay(cache,w,b);other=weighted_loss(criterion(cached,[target]));other.backward()
  error=max_output_error(full,cached)
  assert error==0 and torch.equal(value.detach(),other.detach()),(iid,error,float(value),float(other))
  assert torch.equal(wg,w.grad) and torch.equal(bg,b.grad),iid
  inactive=[i for i in range(616) if i!=133]
  assert not bool(wg[inactive].any()) and not bool(bg[inactive].any())
  assert all(p.grad is None for name,p in model.named_parameters() if name not in allowed)
  assert bool(wg[133].abs().sum())
  check();assert fingerprint_frozen(model,allowed)==frozen
  if r['source']=='fresh-reviewed-release':
   unknown=copy.deepcopy(cache)
   for layer in [unknown['enc_outputs']]:pass
   # Probe gradients at decoder logits directly: fresh unknown classes/background receive zero loss gradient.
   out=replay(cache,initial['weight'],initial['bias'])
   layers=[out]+out.get('aux_outputs',[])+([out['enc_outputs']] if 'enc_outputs' in out else [])
   for layer in layers:layer['pred_logits']=layer['pred_logits'].detach().clone().requires_grad_()
   v=weighted_loss(criterion(out,[target]));v.backward()
   for layer in layers:
    g=layer['pred_logits'].grad
    assert g is not None and not bool(g[...,inactive].any())
  tests.append(dict(image_id=iid,pool=r['pool'],full_cached_output_error=error,loss=float(value.detach()),loss_equal=True,main_weight_and_bias_gradients_equal=True,inactive_parameter_gradients_zero=True))
  print('Loss/gradient parity '+r['pool']+' '+iid,flush=True)
 # Selector objective: active main+encoder row133 gradients only; no optimizer update.
 model.zero_grad(set_to_none=True);_,check,allowed=configure(model,.00003,.0001);frozen=fingerprint_frozen(model,allowed)
 fresh=records[first[0]];image,target=load_sample(fresh['base'],fresh['row'],'cpu')
 outputs,raw=capture_dense(model,image);main=weighted_loss(criterion(outputs,[target]));dense=dense_billboard_loss(raw,target,None,1.)
 total=main+dense;total.backward();inactive=[i for i in range(616) if i!=133]
 for head in [model.class_embed,model.transformer.enc_out_class_embed[0]]:
  assert head.weight.grad is not None and bool(head.weight.grad[133].abs().sum())
  assert not bool(head.weight.grad[inactive].any()) and not bool(head.bias.grad[inactive].any())
 assert all(p.grad is None for name,p in model.named_parameters() if name not in allowed)
 check();assert fingerprint_frozen(model,allowed)==frozen
 unknown_target=dict(labels=torch.zeros(0,dtype=torch.int64),boxes=torch.zeros((0,4)),scope_negative_mask=torch.zeros(616,dtype=torch.bool))
 raw_unknown=dict(pred_logits=raw['pred_logits'].detach().clone().requires_grad_(),pred_boxes=raw['pred_boxes'].detach())
 zero=dense_billboard_loss(raw_unknown,unknown_target,None,1.);zero.backward()
 assert float(zero)==0 and not bool(raw_unknown['pred_logits'].grad.any())
 report=dict(status='loss-gradient-full-layout-and-selector-mask-preflight-passed',plan_sha256=sha(C/'PLAN.json'),tests=tests,
  fresh_unknown_logit_gradients_zero=True,selector_main_and_encoder_active_rows=[133],selector_inactive_gradients_zero=True,
  dense_unknown_scope_loss_and_gradient_zero=True,all_frozen_state_unchanged=True,optimizer_updates=0,test_photos_used=0,
  execution_order_deviation_ref=plan['execution_order_note_ref'],elapsed_seconds=round(time.monotonic()-started,2))
 with (C/'PREFLIGHT_REPORT.json').open('x',encoding='utf-8') as f:f.write(json.dumps(report,indent=2)+'\n')
 print(json.dumps(report),flush=True)
if __name__=='__main__':main()

