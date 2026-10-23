"""Training-only CPU loss/gradient observations. No optimizer or parameter updates."""
import os,sys
from pathlib import Path
P=Path(__file__).resolve().parent
sys.dont_write_bytecode=True
os.environ.update(HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',HF_HUB_DISABLE_TELEMETRY='1',DO_NOT_TRACK='1',MPLCONFIGDIR=str(P/'runtime-cache'))
import hashlib,importlib.metadata,json,socket,time,types
def no_network(*a,**k):raise RuntimeError('Network disabled for offline diagnostic')
socket.create_connection=no_network;socket.socket.connect=no_network
OLD=Path(r'C:\Users\nazee\.codex\visualizations\2026\10\15\01a141ae-c7a6-7303-a280-403af88736f3')
T=OLD/'nextdata-rf-trial-7769109-v1/rf-nextdata-tools-v1'
WHEEL=Path(r'C:\Users\nazee\.codex\visualizations\2026\10\11\01a12a01-d564-7de0-91f4-a16484eea2cb\rf-comparison-package-20261013-v1\local-assignment-wheel\torch_hungarian-0.1.0rc0-py3-none-any.whl')
sys.path[:0]=[str(T),str(WHEEL)]
import torch
from scoped_engine import build_model,load_sample
from scoped_rf import ScopedRFCriterion,weighted_loss
from determinism_policy import math_attention
from rfdetr.utilities import box_ops
import rfdetr.models.criterion as criterion_module
import rfdetr.models.matcher as matcher_module

BASE=Path(r'C:\Users\nazee\Documents\Codex\2026-10-18\frametrail-continuation\outputs')
PRIOR=BASE/'validation-probe-7780632-20261018-v1'
RUN=BASE/'trial-results-7780632-20261018-v1/retrieval/verified-7780632/output/rf-nextdata-7780632'
RELEASE=OLD/'nextdata-reviewed-release-7769109-v1'
WEIGHTS=Path(r'C:\Users\nazee\Documents\All Modules\FrameTrail\.deps\rfdetr-probe-assets\rf-detr-small.pth')
ACTIVE=[15,16,133,593]
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def save(name,data):(P/name).write_text(json.dumps(data,indent=2,allow_nan=False)+'\n',encoding='utf-8')
def sha(p):
    with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def state_sha(net):
    d=hashlib.sha256()
    for name,tensor in net.state_dict().items():d.update(name.encode());d.update(tensor.detach().cpu().contiguous().numpy().tobytes())
    return d.hexdigest()

@math_attention()
def main():
    started=time.monotonic();torch.set_num_threads(2);torch.set_num_interop_threads(1);torch.manual_seed(17);torch.use_deterministic_algorithms(True)
    selected_path=PRIOR/'training-diagnostic-sample-selection.json';selection=read(selected_path)['selection']
    prior_hashes={r['file']:r['sha256'] for r in read(PRIOR/'files-sha256.json')};assert sha(selected_path)==prior_hashes[selected_path.name]
    manifest_path=RELEASE/'candidate-manifest-v2.json';assert sha(manifest_path)=='e43a2c7a415c4f82209a1fc2471d8677503f51315e71f422ec0d6665eac377b9'
    rows={r['image_id']:r for r in read(manifest_path)['images'] if r['image_id'] in {s['image_id'] for s in selection}}
    assert len(rows)==12 and all(r['split']=='train' for r in rows.values())
    for s in selection:
        r=rows[s['image_id']];assert r['image_sha256']==s['image_sha256'] and sha(RELEASE/r['source_path'])==s['image_sha256']
        assert (any(t['canonical_id']==s['canonical_id'] for t in r['targets']) if s['role']=='positive' else r['scope'].get(str(s['canonical_id']))=='absent')
    inputs=[selected_path,PRIOR/'TRAINING_DIAGNOSTIC_PLAN.md',manifest_path,WEIGHTS,WHEEL,RUN/'best.pt',RUN/'last.pt',
        *[T/n for n in ['scoped_rf.py','scoped_engine.py','rf-mapping.json','head_policy.py','determinism_policy.py','protocol.json','train_nextdata.py']],
        Path(criterion_module.__file__),Path(matcher_module.__file__),*[RELEASE/r['source_path'] for r in rows.values()]]
    integrity=[dict(path=str(p),sha256=sha(p),bytes=p.stat().st_size) for p in inputs];save('INPUT_INTEGRITY.json',dict(files=integrity))
    print('Building pinned CPU model for 12 training-only photos at two checkpoints',flush=True)
    net=build_model(WEIGHTS,T/'rf-mapping.json').cpu().eval();net.requires_grad_(False)
    head=net.class_embed;head.requires_grad_(True)
    mask=torch.zeros(616);mask[ACTIVE]=1
    hooks=[head.weight.register_hook(lambda g:g*mask[:,None]),head.bias.register_hook(lambda g:g*mask)]
    inactive=[i for i in range(616) if i not in ACTIVE]
    snapshots={};records=[];checks=[];captures={}
    def head_capture(module,args,result):captures['hidden']=args[0].detach()
    hooks.append(head.register_forward_hook(head_capture))
    criterion=ScopedRFCriterion(615)
    original_labels=criterion.loss_labels
    observed=[]
    def observe_labels(self,outputs,targets,indices,num_boxes,log=True,matched_targets=None):
        result=original_labels(outputs,targets,indices,num_boxes,log=log,matched_targets=matched_targets)
        logits=outputs['pred_logits'];idx=self._get_src_permutation_idx(indices)
        labels=torch.cat([t['labels'][j] for t,(_,j) in zip(targets,indices)])
        target_boxes=torch.cat([t['boxes'][j] for t,(_,j) in zip(targets,indices)])
        overlaps,_=box_ops.elementwise_box_iou(box_ops.box_cxcywh_to_xyxy(outputs['pred_boxes'][idx].detach()),box_ops.box_cxcywh_to_xyxy(target_boxes))
        probs=logits.detach().sigmoid();positive=(*idx,labels)
        scores=(probs[positive].pow(.25)*overlaps.pow(.75)).clamp(min=.01)
        expected_mask=torch.stack([t['scope_negative_mask'] for t in targets]).unsqueeze(1).expand_as(logits).clone();expected_mask[positive]=True
        if logits.requires_grad:logits.retain_grad()
        observed.append(dict(logits=logits,mask=expected_mask,indices=indices,num_boxes=float(num_boxes),loss=float(result['loss_ce'].detach()),
            matches=[dict(query=int(q),target_index=int(j),canonical_id=int(label),iou=float(overlap),probability=float(prob),soft_target=float(score),
                expected_weighted_logit_gradient=float(2*(prob-score)/num_boxes)) for q,j,label,overlap,prob,score in zip(idx[1],indices[0][1],labels,overlaps,probs[positive],scores)]))
        return result
    criterion.loss_labels=types.MethodType(observe_labels,criterion)
    try:
        for step,ckpt_path in [(0,RUN/'best.pt'),(600,RUN/'last.pt')]:
            ckpt=torch.load(ckpt_path,map_location='cpu',weights_only=True);assert ckpt['step']==step
            net.load_state_dict(ckpt['model_state_dict'],strict=True);del ckpt
            initial=state_sha(net);snapshots[str(step)]=initial
            for n,(image_id,row) in enumerate(sorted(rows.items()),1):
                t=time.monotonic();observed.clear();captures.clear();net.zero_grad(set_to_none=True)
                image,target=load_sample(RELEASE,row,'cpu');out=net(image)
                losses=criterion(out,[target]);total=weighted_loss(losses)
                assert torch.isfinite(total)
                ce_keys=[k for k in losses if k=='loss_ce' or k.startswith('loss_ce_')]
                trainable_ce=sum(2*v for k,v in losses.items() if k in ce_keys and v.requires_grad)
                const_loss=sum(v*next(w for prefix,w in [('loss_ce',2),('loss_bbox',5),('loss_giou',2)] if k==prefix or k.startswith(prefix+'_')) for k,v in losses.items() if not v.requires_grad)
                assert abs(float((trainable_ce+const_loss-total).detach()))<2e-5
                assert all(not v.requires_grad for k,v in losses.items() if k.startswith(('loss_bbox','loss_giou')) or k.endswith('_enc'))
                total.backward()
                assert all(p.grad is None for name,p in net.named_parameters() if name not in ['class_embed.weight','class_embed.bias'])
                assert torch.isfinite(head.weight.grad).all() and torch.isfinite(head.bias.grad).all()
                assert not bool(head.weight.grad[inactive].any()) and not bool(head.bias.grad[inactive].any())
                stage_records=[];weight_sum=torch.zeros_like(head.weight);bias_sum=torch.zeros_like(head.bias)
                for i,o in enumerate(observed):
                    stage='main' if i==0 else 'encoder' if i==len(observed)-1 else f'auxiliary-{i-1}'
                    logits=o['logits'];grad=logits.grad if logits.requires_grad else None
                    if grad is not None:
                        assert not bool(grad[~o['mask']].any())
                        main_index=-1 if stage=='main' else i-1
                        hidden=captures['hidden'][main_index]
                        gw=torch.einsum('bqc,bqd->cd',grad,hidden)*mask[:,None];gb=grad.sum((0,1))*mask
                        weight_sum+=gw;bias_sum+=gb
                    class_rows={}
                    for cid in ACTIVE:
                        matched={m['query'] for m in o['matches'] if m['canonical_id']==cid}
                        unmatched=torch.tensor([q for q in range(300) if q not in matched])
                        negative_grad=None
                        if grad is not None:
                            if row['scope'].get(str(cid)) in ('complete','absent'):
                                values=grad[0,unmatched,cid];assert bool((values>=-1e-8).all());negative_grad=float(values.sum())
                            elif row['scope'].get(str(cid),'unknown') in ('positive_only','unknown'):
                                assert not bool(grad[0,unmatched,cid].any())
                        class_rows[str(cid)]=dict(scope=row['scope'].get(str(cid),'unknown'),matches=len(matched),
                            weight_gradient_l2=float(gw[cid].norm()) if grad is not None else 0,
                            bias_gradient=float(gb[cid]) if grad is not None else 0,unmatched_negative_logit_gradient_sum=negative_grad)
                    matches=[]
                    for m in o['matches']:
                        if m['canonical_id'] not in ACTIVE:continue
                        actual=float(grad[0,m['query'],m['canonical_id']]) if grad is not None else None
                        if actual is not None:assert abs(actual-m['expected_weighted_logit_gradient'])<1e-5
                        matches.append(dict(m,actual_weighted_logit_gradient=actual,descent_would_raise_matched_logit=(actual<0) if actual is not None else None))
                    stage_records.append(dict(stage=stage,normalizer=o['num_boxes'],classification_loss=o['loss'],classification_trainable=grad is not None,classes=class_rows,matches=matches))
                max_error=float((weight_sum-head.weight.grad).abs().max());bias_error=float((bias_sum-head.bias.grad).abs().max())
                assert max_error<1e-5 and bias_error<1e-5
                rec=dict(step=step,image_id=image_id,selection_roles=[s for s in selection if s['image_id']==image_id],targets=len(target['labels']),
                    loss_components={k:dict(value=float(v.detach()),trainable=v.requires_grad) for k,v in losses.items()},weighted_total=float(total.detach()),
                    trainable_weighted_classification=float(trainable_ce.detach()),constant_weighted_loss=float(const_loss.detach()),
                    head_gradients={str(cid):dict(weight_l2=float(head.weight.grad[cid].norm()),bias=float(head.bias.grad[cid])) for cid in ACTIVE},
                    global_head_gradient_norm=float(torch.sqrt(head.weight.grad.square().sum()+head.bias.grad.square().sum())),
                    row_gradient_reconstruction_max_error=max_error,bias_gradient_reconstruction_max_error=bias_error,stages=stage_records,seconds=time.monotonic()-t)
                records.append(rec)
                save(f'step-{step:04}-{image_id}.json',rec)
                print(f'step {step}: {n}/12 {image_id}, scoped gradients checked, {rec["seconds"]:.2f}s',flush=True)
            after=state_sha(net);assert after==initial
            checks.append(dict(step=step,model_state_before=initial,model_state_after=after,parameters_and_buffers_unchanged=True))
    finally:
        for h in hooks:h.remove()
    assert all(sha(Path(x['path']))==x['sha256'] for x in integrity)
    save('DIAGNOSTIC.json',dict(status='complete-training-only-loss-gradient-diagnostic',job='7780632',photos=12,checkpoint_photo_checks=len(records),steps=[0,600],records=records,state_checks=checks,
        cpu=True,runtime={k:importlib.metadata.version(k) for k in ['torch','rfdetr','torchvision']},network_disabled=True,optimizer_created=False,optimizer_updates=0,weights_changed=False,
        input_files_unchanged=True,validation_used=False,heldout_used=False,model_exported=False,application_changed=False,seconds=time.monotonic()-started,
        limits='Fixed small training-only diagnostic, not an accuracy benchmark or a parameter-update experiment. Per-logit descent directions do not guarantee the direction of coupled shared-row updates on other queries.'))
    print('Loss and gradient diagnostic complete; all weights and source hashes unchanged.',flush=True)
if __name__=='__main__':main()
