"""Proposal-row and reviewed-region mechanics. No runner, approval or submission."""
import hashlib
import torch
from scipy.optimize import linear_sum_assignment
from scoped_rf import ScopedRFCriterion
from rfdetr.utilities import box_ops
import torch.nn.functional as F
import rfdetr.models.transformer as transformer_module

def region_queries(boxes,region):
    roi=torch.as_tensor(region,dtype=boxes.dtype,device=boxes.device).reshape(1,4)
    pred=box_ops.box_cxcywh_to_xyxy(boxes.detach()[0]).clamp(0,1);gt=box_ops.box_cxcywh_to_xyxy(roi)
    overlaps,_=box_ops.box_iou(pred,gt)
    return overlaps[:,0]>=.7

class RegionCriterion(ScopedRFCriterion):
    def __init__(self,region=None,region_weight=1.):
        super().__init__(615);self.region=region;self.region_weight=float(region_weight)
    def loss_labels(self,outputs,targets,indices,num_boxes,log=True,matched_targets=None):
        logits=outputs['pred_logits'];idx=self._get_src_permutation_idx(indices)
        labels=torch.cat([t['labels'][j] for t,(_,j) in zip(targets,indices)])
        target_boxes=torch.cat([t['boxes'][j] for t,(_,j) in zip(targets,indices)])
        ious,_=box_ops.elementwise_box_iou(box_ops.box_cxcywh_to_xyxy(outputs['pred_boxes'][idx].detach()),box_ops.box_cxcywh_to_xyxy(target_boxes))
        probability=logits.sigmoid();pos=torch.zeros_like(logits);neg=probability.square();positive_index=(*idx,labels)
        score=(probability[positive_index].pow(self.focal_alpha)*ious.pow(1-self.focal_alpha)).clamp(min=.01).detach()
        pos[positive_index]=score.to(logits.dtype);neg[positive_index]=(1-score).to(logits.dtype)
        mask=torch.stack([t['scope_negative_mask'] for t in targets]).unsqueeze(1).expand_as(logits).clone();mask[positive_index]=True
        weights=torch.ones_like(logits)
        if self.region is not None:
            if len(targets)!=1 or bool((targets[0]['labels']==133).any()) or bool(targets[0]['scope_negative_mask'][133]):raise ValueError('Region overlay requires original billboard-unknown training photo')
            q=region_queries(outputs['pred_boxes'],self.region)
            if self.region_weight>0:mask[0,q,133]=True;weights[0,q,133]=self.region_weight
        per_cell=neg*logits-F.logsigmoid(logits)*(pos+neg)
        return {'loss_ce':(per_cell*mask.to(logits.dtype)*weights).sum()/num_boxes}

def capture_dense(model,image):
    captured={};original=transformer_module.gen_encoder_output_proposals
    def proposals(*args,**kwargs):
        result=original(*args,**kwargs);captured['proposals']=result[1].detach();return result
    def hook(module,args,result):
        if 'features' not in captured:captured['features']=args[0].detach();captured['pred_logits']=result
    transformer_module.gen_encoder_output_proposals=proposals
    handle=model.transformer.enc_out_class_embed[0].register_forward_hook(hook)
    try:outputs=model(image)
    finally:handle.remove();transformer_module.gen_encoder_output_proposals=original
    features=captured['features'];proposal=captured['proposals']
    if features.shape[1]<=300:raise ValueError('Expected additional unselected proposal positions')
    with torch.no_grad():
        delta=model.transformer.enc_out_bbox_embed[0](features)
        if model.bbox_reparam:boxes=torch.cat([delta[...,:2]*proposal[...,2:]+proposal[...,:2],delta[...,2:].exp()*proposal[...,2:]],-1)
        else:boxes=(delta+proposal).sigmoid()
    return outputs,dict(pred_logits=captured['pred_logits'],pred_boxes=boxes)

def dense_billboard_loss(raw,target,region=None,region_weight=1.):
    logits=raw['pred_logits'][0,:,133];p=logits.sigmoid();positive=torch.zeros_like(logits);negative=p.square()
    mask=torch.full_like(logits,bool(target['scope_negative_mask'][133]),dtype=torch.bool);weights=torch.ones_like(logits)
    wanted=target['boxes'][target['labels']==133];count=len(wanted)
    if count:
        overlaps,_=box_ops.box_iou(box_ops.box_cxcywh_to_xyxy(raw['pred_boxes'][0].detach()).clamp(0,1),box_ops.box_cxcywh_to_xyxy(wanted))
        q,t=linear_sum_assignment(-overlaps.detach().cpu().numpy())
        for query,gt in zip(q,t):
            ov=overlaps[query,gt]
            if float(ov)<.5:continue
            score=(p[query].pow(.25)*ov.pow(.75)).clamp(min=.01).detach();positive[query]=score;negative[query]=1-score;mask[query]=True
    if region is not None:
        if count or bool(target['scope_negative_mask'][133]):raise ValueError('Expected original unknown billboard scope for region')
        q=region_queries(raw['pred_boxes'],region)
        if region_weight>0:mask[q]=True;weights[q]=region_weight
    per_cell=negative*logits-F.logsigmoid(logits)*(positive+negative)
    return 2*(per_cell*mask.to(logits.dtype)*weights).sum()/max(1,count)

def configure(model,encoder_lr,main_lr=.0001):
    for p in model.parameters():p.requires_grad_(False)
    modules=[('class_embed',model.class_embed,main_lr)]
    if encoder_lr>0:modules.append(('transformer.enc_out_class_embed.0',model.transformer.enc_out_class_embed[0],encoder_lr))
    initial={k:v.detach().clone() for k,v in model.state_dict().items() if k.endswith('class_embed.weight') or k.endswith('class_embed.bias') or k.startswith('transformer.enc_out_class_embed.0.')}
    groups=[];allowed=set()
    for name,module,lr in modules:
        mask=torch.zeros(616,device=module.weight.device);mask[133]=1
        module.weight.requires_grad_(True);module.bias.requires_grad_(True)
        module.weight.register_hook(lambda g,m=mask:g*m[:,None]);module.bias.register_hook(lambda g,m=mask:g*m)
        groups.append(dict(params=list(module.parameters()),lr=lr));allowed.update({name+'.weight',name+'.bias'})
    optimizer=torch.optim.AdamW(groups,weight_decay=0,foreach=False);inactive=[i for i in range(616) if i!=133]
    def check():
        state=model.state_dict()
        for name,before in initial.items():
            if name in allowed:
                if not torch.equal(before[inactive],state[name][inactive]):raise ValueError('Inactive classifier row changed: '+name)
            elif not torch.equal(before,state[name]):raise ValueError('Frozen classifier changed: '+name)
    return optimizer,check,allowed

def fingerprint_frozen(model,allowed):
    digest=hashlib.sha256()
    for name,value in sorted(model.state_dict().items()):
        if name in allowed:continue
        digest.update(name.encode());digest.update(value.detach().cpu().contiguous().numpy().tobytes())
    return digest.hexdigest()
