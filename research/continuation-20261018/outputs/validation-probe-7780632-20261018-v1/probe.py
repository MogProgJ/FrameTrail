"""Offline CPU diagnostic on existing validation misses. No training or export."""
import os,sys
from pathlib import Path
OUT=Path(__file__).resolve().parent
sys.dont_write_bytecode=True
os.environ.update(HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',HF_HUB_DISABLE_TELEMETRY='1',DO_NOT_TRACK='1',MPLCONFIGDIR=str(OUT/'runtime-cache'))
import collections,hashlib,importlib.metadata,json,socket,time
def no_network(*a,**k): raise RuntimeError('Network disabled for this offline diagnostic')
socket.create_connection=no_network
socket.socket.connect=no_network
OLD=Path(r'C:\Users\nazee\.codex\visualizations\2026\10\15\01a141ae-c7a6-7303-a280-403af88736f3')
TOOLS=OLD/'nextdata-rf-trial-7769109-v1/rf-nextdata-tools-v1'
WHEEL=Path(r'C:\Users\nazee\.codex\visualizations\2026\10\11\01a12a01-d564-7de0-91f4-a16484eea2cb\rf-comparison-package-20261013-v1\local-assignment-wheel\torch_hungarian-0.1.0rc0-py3-none-any.whl')
sys.path[:0]=[str(TOOLS),str(WHEEL)]
import numpy as np,torch
from scipy.optimize import linear_sum_assignment
from scoped_engine import build_model,load_sample
from scoped_metrics import decode,iou
from determinism_policy import math_attention
import rfdetr.models.transformer as transformer_module

BASE=Path(r'C:\Users\nazee\Documents\Codex\2026-10-18\frametrail-continuation\outputs')
RUN=BASE/'trial-results-7780632-20261018-v1/retrieval/verified-7780632/output/rf-nextdata-7780632'
AUDIT=BASE/'trial-audit-7780632-20261018-v1'
RELEASE=OLD/'nextdata-reviewed-release-7769109-v1'
WEIGHTS=Path(r'C:\Users\nazee\Documents\All Modules\FrameTrail\.deps\rfdetr-probe-assets\rf-detr-small.pth')
ACTIVE=[15,16,133,593]
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):
    with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def save(p,x):p.write_text(json.dumps(x,indent=2,allow_nan=False)+'\n',encoding='utf-8')
def xyxy(boxes,w,h):
    b=boxes.detach().cpu(); c,s=b[...,:2],b[...,2:]; result=torch.cat((c-s/2,c+s/2),dim=-1)
    return (result*torch.tensor([w,h,w,h])).clamp(min=0).minimum(torch.tensor([w,h,w,h])).numpy()
def overlaps(boxes,target):
    tl=np.maximum(boxes[:,:2],target[:2]);br=np.minimum(boxes[:,2:],target[2:]);wh=np.maximum(br-tl,0);inter=wh.prod(1)
    area=np.maximum(boxes[:,2:]-boxes[:,:2],0).prod(1);ta=(target[2]-target[0])*(target[3]-target[1])
    return inter/np.maximum(area+ta-inter,1e-10)
def describe(boxes,logits,target,cid):
    ov=overlaps(boxes,target);conf=logits[:,cid].sigmoid().numpy();top=logits[:,:615].argmax(-1).numpy()
    best=int(ov.argmax()); strongest=int(conf.argmax());covered=ov>=.5
    best_covered=int(np.where(covered,conf,-1).argmax()) if covered.any() else None
    def query(i):return dict(index=int(i),box=boxes[i].tolist(),iou=float(ov[i]),target_confidence=float(conf[i]),target_logit=float(logits[i,cid]),
        top_class=int(top[i]),top_class_confidence=float(logits[i,top[i]].sigmoid()))
    return dict(best_overlap=query(best),strongest_target_confidence=query(strongest),covering_queries=int(covered.sum()),
        best_covering_query=query(best_covered) if best_covered is not None else None,
        queries_meeting_class_and_geometry=int(((ov>=.5)&(conf>=.35)).sum()))
def compare_decoded(actual,expected):
    if len(actual)!=len(expected):return dict(passed=False,reason='count',cpu_count=len(actual),saved_count=len(expected))
    if not actual:return dict(passed=True,cpu_count=0,saved_count=0)
    cost=np.array([[1-iou(a['box'],b['box']) if a['canonical_id']==b['canonical_id'] else 1000 for b in expected] for a in actual])
    ai,bi=linear_sum_assignment(cost);minimum=min(iou(actual[i]['box'],expected[j]['box']) for i,j in zip(ai,bi));diff=max(abs(actual[i]['confidence']-expected[j]['confidence']) for i,j in zip(ai,bi))
    return dict(passed=minimum>=.99 and diff<=.002,cpu_count=len(actual),saved_count=len(expected),minimum_iou=minimum,max_confidence_difference=diff)

@math_attention()
def main():
    started=time.monotonic();torch.set_num_threads(2);torch.set_num_interop_threads(1);torch.manual_seed(17);torch.use_deterministic_algorithms(True)
    manifest_path=RELEASE/'candidate-manifest-v2.json';manifest=read(manifest_path)
    assert sha(manifest_path)=='e43a2c7a415c4f82209a1fc2471d8677503f51315e71f422ec0d6665eac377b9'
    misses=read(AUDIT/'validation-misses.json')['misses'];ids=sorted({m['image_id'] for m in misses})
    rows={r['image_id']:r for r in manifest['images'] if r['image_id'] in ids};assert len(rows)==len(ids) and all(r['split']=='val' for r in rows.values())
    inputs=[manifest_path,AUDIT/'validation-misses.json',WEIGHTS,TOOLS/'rf-mapping.json',TOOLS/'scoped_engine.py',TOOLS/'scoped_metrics.py',TOOLS/'scoped_rf.py',TOOLS/'determinism_policy.py',WHEEL,RUN/'best.pt',RUN/'last.pt',RUN/'validation-0000.json',RUN/'validation-0600.json']
    for r in rows.values():
        path=RELEASE/r['source_path'];assert sha(path)==r['image_sha256'];inputs.append(path)
    integrity=[dict(path=str(p),sha256=sha(p),bytes=p.stat().st_size) for p in inputs]
    save(OUT/'INPUT_INTEGRITY.json',dict(files=integrity))
    print(f'Building offline pinned RF model; {len(ids)} validation images, {len(misses)} known misses',flush=True)
    net=build_model(WEIGHTS,TOOLS/'rf-mapping.json').cpu().eval();net.requires_grad_(False)
    captures={}
    original_gen=transformer_module.gen_encoder_output_proposals
    def observe_proposals(*args,**kwargs):
        result=original_gen(*args,**kwargs);captures['proposal_bases']=result[1].detach().clone();return result
    transformer_module.gen_encoder_output_proposals=observe_proposals
    def observe_class(module,args,result):
        if 'all_logits' not in captures:
            captures['all_memory']=args[0].detach().clone();captures['all_logits']=result.detach().clone()
    hook=net.transformer.enc_out_class_embed[0].register_forward_hook(observe_class)
    all_cases=[];images=[];raw_dir=OUT/'raw';raw_dir.mkdir(exist_ok=False)
    reference_boxes={};reference_enc={};reference_all={}
    try:
        for step,ckpt_path in [(0,RUN/'best.pt'),(600,RUN/'last.pt')]:
            ckpt=torch.load(ckpt_path,map_location='cpu',weights_only=True);assert ckpt['step']==step
            net.load_state_dict(ckpt['model_state_dict'],strict=True);del ckpt
            saved=read(RUN/f'validation-{step:04}.json')['predictions']
            for j,image_id in enumerate(ids,1):
                row=rows[image_id];captures.clear();t=time.monotonic()
                with torch.inference_mode():
                    image,_=load_sample(RELEASE,row,'cpu');out=net(image)
                    assert out['pred_logits'].shape==(1,300,616) and out['pred_boxes'].shape==(1,300,4)
                    memory=captures['all_memory'];all_logits=captures['all_logits'];bases=captures['proposal_bases']
                    delta=net.transformer.enc_out_bbox_embed[0](memory)
                    if net.bbox_reparam:all_boxes=torch.cat((delta[...,:2]*bases[...,2:]+bases[...,:2],delta[...,2:].exp()*bases[...,2:]),dim=-1)
                    else:all_boxes=(delta+bases).sigmoid()
                    selected=all_logits.max(-1)[0].topk(300,dim=1).indices
                    gathered_boxes=all_boxes.gather(1,selected.unsqueeze(-1).expand(-1,-1,4))
                    gathered_logits=all_logits.gather(1,selected.unsqueeze(-1).expand(-1,-1,616))
                    box_error=float((gathered_boxes-out['enc_outputs']['pred_boxes']).abs().max());logit_error=float((gathered_logits-out['enc_outputs']['pred_logits']).abs().max())
                    assert box_error<1e-5 and logit_error<1e-5
                    db=xyxy(out['pred_boxes'][0],row['width'],row['height']);dl=out['pred_logits'][0].cpu()
                    eb=xyxy(out['enc_outputs']['pred_boxes'][0],row['width'],row['height']);el=out['enc_outputs']['pred_logits'][0].cpu()
                    ab=xyxy(all_boxes[0],row['width'],row['height']);al=all_logits[0].cpu()
                    assert torch.isfinite(dl).all() and torch.isfinite(el).all() and np.isfinite(db).all() and np.isfinite(ab).all()
                    parity=compare_decoded(decode(out,row['width'],row['height']),saved[image_id])
                    if not parity['passed']:raise ValueError(f'CPU diagnostic differs materially from saved KIT output: {step}/{image_id}: {parity}')
                    unchanged=None
                    if step==0:reference_boxes[image_id]=db.copy();reference_enc[image_id]=eb.copy();reference_all[image_id]=ab.copy()
                    else:
                        unchanged=dict(decoder_boxes=np.array_equal(db,reference_boxes[image_id]),selected_encoder_boxes=np.array_equal(eb,reference_enc[image_id]),all_encoder_boxes=np.array_equal(ab,reference_all[image_id]))
                        assert all(unchanged.values())
                    raw={}
                    for prefix,boxes,logits in [('decoder',db,dl),('encoder_selected',eb,el),('encoder_all',ab,al)]:
                        top=logits[:,:615].max(-1)
                        raw.update({prefix+'_boxes_xyxy':boxes,prefix+'_active_logits':logits[:,ACTIVE].numpy(),prefix+'_top_class':top.indices.numpy(),prefix+'_top_logit':top.values.numpy()})
                    raw['encoder_selected_indices']=selected[0].numpy();raw['active_class_ids']=np.array(ACTIVE)
                    np.savez_compressed(raw_dir/f'step-{step:04}-{image_id}.npz',**raw)
                    for index,miss in enumerate(misses):
                        if miss['image_id']!=image_id:continue
                        all_cases.append(dict(miss_index=index,step=step,image_id=image_id,canonical_id=miss['canonical_id'],scope=miss['scope'],target_xyxy=miss['target_xyxy'],
                            decoder=describe(db,dl,miss['target_xyxy'],miss['canonical_id']),encoder_selected=describe(eb,el,miss['target_xyxy'],miss['canonical_id']),encoder_all=describe(ab,al,miss['target_xyxy'],miss['canonical_id'])))
                images.append(dict(image_id=image_id,step=step,photo_number=row.get('photo_number'),parity=parity,encoder_reconstruction_max_box_error=box_error,encoder_reconstruction_max_logit_error=logit_error,
                    boxes_identical_to_step_zero=unchanged,all_encoder_positions=len(ab),seconds=time.monotonic()-t))
                print(f'step {step}: {j}/{len(ids)} {image_id}, CPU/saved parity passed, {time.monotonic()-t:.2f}s',flush=True)
                save(OUT/'progress.json',dict(step=step,completed_image=j,total_images=len(ids),seconds=time.monotonic()-started))
    finally:
        hook.remove();transformer_module.gen_encoder_output_proposals=original_gen
    assert len(all_cases)==56 and len(images)==len(ids)*2
    assert all(sha(Path(x['path']))==x['sha256'] for x in integrity)
    save(OUT/'PROBE.json',dict(status='complete-offline-cpu-validation-diagnostic',job='7780632',steps=[0,600],images=len(ids),known_misses=28,new_class_misses=24,cases=all_cases,image_checks=images,
        runtime={k:importlib.metadata.version(k) for k in ['torch','torchvision','rfdetr','numpy']},device='cpu',math_attention_only=True,
        input_hashes_unchanged=True,network_disabled=True,training_run=False,heldout_used=False,application_changed=False,seconds=time.monotonic()-started,
        limits='Validation failure subset only; per-target any-query overlap is an oracle localization diagnostic, not detection recall. No threshold tuning or production accuracy claim.'))
    print('Probe complete; source hashes unchanged.',flush=True)
if __name__=='__main__':main()
