"""Replay a frozen RF decoder's exact linear classifier; no training runner."""
import copy,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
TOOLS=HERE.parent/'billboard-batch-proposal-7805570-20261018-v1/rf-billboard-batch-0a255598-v1'
WHEEL=Path(r'C:\Users\nazee\.codex\visualizations\2026\10\11\01a12a01-d564-7de0-91f4-a16484eea2cb\rf-comparison-package-20261013-v1\local-assignment-wheel\torch_hungarian-0.1.0rc0-py3-none-any.whl')
sys.path[:0]=[str(TOOLS),str(WHEEL)]
import torch
import torch.nn.functional as F
from scoped_rf import ScopedRFCriterion,weighted_loss
from scoped_metrics import decode

def detached(value):
    if isinstance(value,torch.Tensor):return value.detach().cpu().clone()
    if isinstance(value,dict):return {k:detached(v) for k,v in value.items()}
    if isinstance(value,list):return [detached(v) for v in value]
    return copy.deepcopy(value)

def capture(model,image,full=True):
    captured=[]
    hook=model.class_embed.register_forward_pre_hook(lambda module,args:captured.append(args[0].detach()))
    try:outputs=model(image)
    finally:hook.remove()
    if len(captured)!=1 or captured[0].ndim!=4:raise ValueError('Unexpected final-head invocation contract')
    hs=captured[0];layers=list(outputs.get('aux_outputs',[]))+[outputs]
    if hs.shape[:3]!=(len(layers),1,300) or hs.shape[-1]!=model.class_embed.in_features:raise ValueError('Decoder/aux feature layout differs')
    # Preserve the complete Linear input layout even for validation. Reducing the
    # layer dimension can select a different GEMM path and alter FP32 rounding.
    cache=dict(features=detached(hs),boxes=detached(torch.stack([o['pred_boxes'] for o in layers])))
    if full and 'enc_outputs' in outputs:cache['enc_outputs']=detached(outputs['enc_outputs'])
    return cache,outputs

def replay(cache,weight,bias):
    logits=F.linear(cache['features'],weight,bias);boxes=cache['boxes']
    out=dict(pred_logits=logits[-1],pred_boxes=boxes[-1])
    if len(logits)>1:out['aux_outputs']=[dict(pred_logits=l,pred_boxes=b) for l,b in zip(logits[:-1],boxes[:-1])]
    if 'enc_outputs' in cache:out['enc_outputs']=cache['enc_outputs']
    return out

def loss(outputs,target):
    values=ScopedRFCriterion(615)(outputs,[target]);return weighted_loss(values)

def max_output_error(a,b):
    layers_a=list(a.get('aux_outputs',[]))+[a];layers_b=list(b.get('aux_outputs',[]))+[b]
    if len(layers_a)!=len(layers_b):raise ValueError('Output layers differ')
    return max(float((x[k].detach()-y[k].detach()).abs().max()) for x,y in zip(layers_a,layers_b) for k in ('pred_logits','pred_boxes'))
