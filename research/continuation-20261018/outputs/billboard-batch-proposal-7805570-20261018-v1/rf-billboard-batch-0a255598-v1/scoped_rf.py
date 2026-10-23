"""RF detection-only mechanics prototype. No runner or release approval is provided."""
import torch
import torch.nn.functional as F
from torch import nn
from rfdetr.models.criterion import SetCriterion
from rfdetr.models.matcher import HungarianMatcher
from rfdetr.utilities import box_ops

STATES={'complete','absent','positive_only','unknown'}

def target_from_row(row, foreground_classes, device='cpu'):
    """Preserve canonical IDs. Only deterministic full-image resize is allowed here."""
    scope={int(k):v for k,v in row['scope'].items()}
    if any(k<0 or k>=foreground_classes or v not in STATES for k,v in scope.items()):
        raise ValueError('Invalid canonical scope')
    targets=row['targets']
    if any(scope.get(t['canonical_id'],'unknown') not in {'complete','positive_only'} for t in targets):
        raise ValueError('Positive target conflicts with scope')
    labels=torch.tensor([t['canonical_id'] for t in targets],dtype=torch.int64,device=device)
    boxes=torch.tensor([t['normalized_cxcywh'] for t in targets],dtype=torch.float32,device=device).reshape(-1,4)
    if not torch.isfinite(boxes).all() or (boxes<0).any() or (boxes>1).any() or (boxes[:,2:]<=0).any():
        raise ValueError('Invalid normalized target')
    negative_mask=torch.zeros(foreground_classes+1,dtype=torch.bool,device=device)
    for k,v in scope.items():
        if v in {'complete','absent'}:negative_mask[k]=True
    # Explicit extra background output is ignored; sparse/unknown canonical classes are ignored too.
    return dict(labels=labels,boxes=boxes,scope_negative_mask=negative_mask)

def remap_classifier(source, rows, foreground_classes, seed=17):
    """New Linear; copy exact semantic rows. No positional tiling or silent duplicates."""
    if source.out_features !=91:raise ValueError('Expected receipted sparse RF head width 91')
    if len(rows)!=80 or len({r['canonical_id'] for r in rows})!=80 or len({r['checkpoint_slot'] for r in rows})!=80:
        raise ValueError('Mapping must name 80 unique pretrained rows')
    if any(not 0<=r['canonical_id']<foreground_classes or not 0<=r['checkpoint_slot']<91 for r in rows):
        raise ValueError('Mapping outside classifier bounds')
    # fork_rng prevents initialization from perturbing other reproducible model operations.
    with torch.random.fork_rng(devices=[]):
        torch.manual_seed(seed)
        result=nn.Linear(source.in_features,foreground_classes+1,device='cpu',dtype=source.weight.dtype)
        with torch.no_grad():result.bias.fill_(-4.59511985)
    result=result.to(source.weight.device)
    with torch.no_grad():
        for row in rows:
            dst,src=row['canonical_id'],row['checkpoint_slot']
            result.weight[dst].copy_(source.weight[src]);result.bias[dst].copy_(source.bias[src])
    return result

class ScopedRFCriterion(SetCriterion):
    """Stock RF Hungarian/box losses with masked IA-BCE classification on every layer.

    Scope-complete/absent classes supervise all queries; incomplete classes supervise
    only their matched positive cells. Unknown cells have zero direct logit gradient.
    Shared backbone changes can still affect them: this is not regression protection.
    Single process/group only; distributed/grouped training fails closed in this prototype.
    """
    def __init__(self,foreground_classes):
        self.foreground_classes=foreground_classes
        super().__init__(num_classes=foreground_classes+1,
            matcher=HungarianMatcher(cost_class=2,cost_bbox=5,cost_giou=2,focal_alpha=.25),
            weight_dict={'loss_ce':2,'loss_bbox':5,'loss_giou':2},focal_alpha=.25,
            losses=['labels','boxes'],group_detr=1,ia_bce_loss=True)

    def _can_batch_detection_losses(self,*args):
        return False # stock fused branch cannot bypass our scope mask

    def forward(self,outputs,targets,num_boxes=None):
        if self.group_detr!=1 or (torch.distributed.is_initialized()):
            raise NotImplementedError('Only tested single-process, group-one detection is supported')
        layers=[outputs]+list(outputs.get('aux_outputs',[]))
        if 'enc_outputs' in outputs:layers.append(outputs['enc_outputs'])
        for layer in layers:
            logits,boxes=layer['pred_logits'],layer['pred_boxes']
            if logits.ndim!=3 or logits.shape[-1]!=self.foreground_classes+1 or boxes.shape!=(*logits.shape[:2],4) or len(targets)!=logits.shape[0]:
                raise ValueError('Changed RF output contract')
            if not torch.isfinite(logits).all() or not torch.isfinite(boxes).all():raise ValueError('Nonfinite model output')
        for t in targets:
            if set(t)!={'labels','boxes','scope_negative_mask'}:raise ValueError('Missing scopes or unsupported target format')
            mask=t['scope_negative_mask']
            if mask.dtype!=torch.bool or mask.shape!=(self.foreground_classes+1,) or mask[-1]:raise ValueError('Invalid supervision mask/background')
            if t['labels'].dtype!=torch.int64 or t['labels'].ndim!=1 or t['boxes'].shape!=(len(t['labels']),4):raise ValueError('Target shapes changed')
            if (t['labels']<0).any() or (t['labels']>=self.foreground_classes).any() or not torch.isfinite(t['boxes']).all():raise ValueError('Invalid target identity')
            if (t['boxes']<0).any() or (t['boxes']>1).any() or (t['boxes'][:,2:]<=0).any():raise ValueError('Invalid target geometry')
            if t['labels'].device!=outputs['pred_logits'].device or mask.device!=outputs['pred_logits'].device or t['boxes'].device!=outputs['pred_boxes'].device:raise ValueError('Target/output device mismatch')
        return super().forward(outputs,targets,num_boxes=num_boxes)

    def loss_labels(self,outputs,targets,indices,num_boxes,log=True,matched_targets=None):
        logits=outputs['pred_logits']
        idx=self._get_src_permutation_idx(indices)
        labels=torch.cat([t['labels'][j] for t,(_,j) in zip(targets,indices)])
        target_boxes=torch.cat([t['boxes'][j] for t,(_,j) in zip(targets,indices)])
        ious,_=box_ops.elementwise_box_iou(box_ops.box_cxcywh_to_xyxy(outputs['pred_boxes'][idx].detach()),box_ops.box_cxcywh_to_xyxy(target_boxes))
        probability=logits.sigmoid()
        pos_weights=torch.zeros_like(logits);neg_weights=probability.square()
        positive_index=(*idx,labels)
        score=(probability[positive_index].pow(self.focal_alpha)*ious.pow(1-self.focal_alpha)).clamp(min=.01).detach()
        pos_weights[positive_index]=score.to(logits.dtype)
        neg_weights[positive_index]=(1-score).to(logits.dtype)
        mask=torch.stack([t['scope_negative_mask'] for t in targets]).unsqueeze(1).expand_as(logits).clone()
        mask[positive_index]=True
        per_cell=neg_weights*logits-F.logsigmoid(logits)*(pos_weights+neg_weights)
        return {'loss_ce':(per_cell*mask.to(logits.dtype)).sum()/num_boxes}

def weighted_loss(losses):
    weights={'loss_ce':2,'loss_bbox':5,'loss_giou':2}
    return sum(value*next(weight for key,weight in weights.items() if name==key or name.startswith(key+'_')) for name,value in losses.items())
