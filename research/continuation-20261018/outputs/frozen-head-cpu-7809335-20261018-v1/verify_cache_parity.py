"""Four training-photo forward/loss/gradient checks, no optimizer updates."""
import hashlib,importlib.metadata,json,time
from pathlib import Path
from cache_engine import *
from scoped_engine import build_model,load_sample
from continuation_guard import read,sha
from determinism_policy import math_attention
WEIGHTS=Path(r'C:\Users\nazee\Documents\All Modules\FrameTrail\.deps\rfdetr-probe-assets\rf-detr-small.pth')
def save(p,v):
    with p.open('x',encoding='utf-8') as f:json.dump(v,f,indent=2,allow_nan=False)
def fingerprint(net):
    h=hashlib.sha256()
    for k,v in sorted(net.state_dict().items()):h.update(k.encode());h.update(v.detach().cpu().contiguous().numpy().tobytes())
    return h.hexdigest()
@math_attention()
def run():
    torch.set_num_threads(2);torch.manual_seed(17);torch.use_deterministic_algorithms(True)
    if str(torch.__version__)!='2.8.0+cpu' or importlib.metadata.version('rfdetr')!='1.11.2':raise ValueError('Pinned local CPU runtime differs')
    net=build_model(WEIGHTS,TOOLS/'rf-mapping.json').cpu().eval();ck=read(TOOLS/'protocol.json')['starting_checkpoint']['sha256'];path=TOOLS/'inputs/selected-7805570.pt'
    assert sha(path)==ck
    net.load_state_dict(torch.load(path,map_location='cpu',weights_only=True)['model_state_dict']);before=fingerprint(net)
    for p in net.parameters():p.requires_grad_(False)
    net.class_embed.weight.requires_grad_(True);net.class_embed.bias.requires_grad_(True)
    mask=torch.zeros(616);mask[133]=1
    net.class_embed.weight.register_hook(lambda g:g*mask[:,None]);net.class_embed.bias.register_hook(lambda g:g*mask)
    release=read(TOOLS/'release/candidate-manifest-v2.json');rows={r['image_id']:r for r in release['images']};pools=read(TOOLS/'sampling-pools.json')
    ids=pools['billboard'][:2]+pools['explicit_negative'][:2];records=[]
    for image_id in ids:
        row=rows[image_id];image,target=load_sample(TOOLS/'release',row);net.zero_grad(set_to_none=True)
        started=time.perf_counter();cache,live=capture(net,image,full=True);full_loss=loss(live,target);full_loss.backward()
        gradw=net.class_embed.weight.grad.clone();gradb=net.class_embed.bias.grad.clone()
        w=net.class_embed.weight.detach().clone().requires_grad_(True);b=net.class_embed.bias.detach().clone().requires_grad_(True)
        w.register_hook(lambda g:g*mask[:,None]);b.register_hook(lambda g:g*mask)
        rebuilt=replay(cache,w,b);replayed_loss=loss(rebuilt,target);replayed_loss.backward()
        error=max_output_error(live,rebuilt);loss_error=abs(float(full_loss.detach()-replayed_loss.detach()));grad_error=max(float((gradw-w.grad).abs().max()),float((gradb-b.grad).abs().max()))
        decoded_equal=decode(live,row['width'],row['height'])==decode(rebuilt,row['width'],row['height'])
        passed=error<=1e-6 and loss_error<=1e-5 and grad_error<=1e-5 and decoded_equal
        record=dict(image_id=image_id,role='positive' if image_id in pools['billboard'] else 'explicit-negative',feature_shape=list(cache['features'].shape),max_output_error=error,loss_error=loss_error,gradient_max_error=grad_error,decoded_detections_identical=decoded_equal,passed=passed,seconds=time.perf_counter()-started)
        records.append(record);print(json.dumps(record),flush=True)
        if not passed:raise ValueError('Frozen-head replay failed strict CPU forward/loss/gradient parity')
    assert fingerprint(net)==before
    save(HERE/'CACHE_PARITY_FULL_LAYOUT.json',dict(status='frozen-head-CPU-forward-loss-gradient-parity-passed',records=records,images=4,only_training_images=True,optimizer_created=False,optimizer_updates=0,all_model_state_unchanged=True,new_cluster_jobs=0,checkpoint_sha256=ck,cache_engine_sha256=sha(HERE/'cache_engine.py')))
if __name__=='__main__':run()
