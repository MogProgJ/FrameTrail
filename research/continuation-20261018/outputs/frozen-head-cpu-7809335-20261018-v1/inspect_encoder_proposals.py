"""Training-only encoder/decoder coverage diagnostic, no optimizer or selection."""
import json
from cache_engine import *
from build_cache import WEIGHTS,save
from verify_cache_parity import fingerprint
from scoped_engine import build_model,load_sample
from continuation_guard import read,sha
from scoped_metrics import iou
from determinism_policy import math_attention
import rfdetr.models.transformer as transformer_module
def xyxy(t):
    x,y,w,h=t;return [max(0.,x-w/2),max(0.,y-h/2),min(1.,x+w/2),min(1.,y+h/2)]
def coverage(boxes,target):return max((iou(xyxy(b),target) for b in boxes),default=0.)
@math_attention()
def run():
    torch.set_num_threads(2);torch.manual_seed(17);torch.use_deterministic_algorithms(True)
    model=build_model(WEIGHTS,TOOLS/'rf-mapping.json').cpu().eval();ck=torch.load(TOOLS/'inputs/selected-7805570.pt',map_location='cpu',weights_only=True);model.load_state_dict(ck['model_state_dict']);del ck
    for p in model.parameters():p.requires_grad_(False)
    before=fingerprint(model);release=read(TOOLS/'release/candidate-manifest-v2.json');rows={r['image_id']:r for r in release['images']};pools=read(TOOLS/'sampling-pools.json');records=[]
    original=transformer_module.gen_encoder_output_proposals
    for image_id in pools['billboard']:
        captured={};calls=[]
        def proposals(*args,**kwargs):
            result=original(*args,**kwargs);captured['proposals']=result[1].detach().clone();return result
        def hook(module,args,result):calls.append((args[0].detach().clone(),result.detach().clone()))
        transformer_module.gen_encoder_output_proposals=proposals
        handle=model.transformer.enc_out_class_embed[0].register_forward_hook(hook)
        row=rows[image_id];image,_=load_sample(TOOLS/'release',row)
        try:
            with torch.no_grad():outputs=model(image)
        finally:handle.remove();transformer_module.gen_encoder_output_proposals=original
        memory,logits=calls[0];prop=captured['proposals'];assert memory.shape[1]==prop.shape[1]
        with torch.no_grad():delta=model.transformer.enc_out_bbox_embed[0](memory)
        if model.bbox_reparam:boxes=torch.cat([delta[...,:2]*prop[...,2:]+prop[...,:2],delta[...,2:].exp()*prop[...,2:]],-1)
        else:boxes=(delta+prop).sigmoid()
        top=torch.topk(logits.max(-1)[0],300,dim=1).indices[0]
        selected=boxes[:,top];error=float((selected-outputs['enc_outputs']['pred_boxes']).abs().max())
        assert error<1e-5,'Raw encoder-box replay differs from actual selected proposals'
        all_boxes=boxes[0].tolist();chosen=selected[0].tolist();final=outputs['pred_boxes'][0].tolist();targets=[]
        for t in row['targets']:
            if t['canonical_id']!=133:continue
            x,y,w,h=t['normalized_cxcywh'];target=[x-w/2,y-h/2,x+w/2,y+h/2]
            targets.append(dict(all_encoder_max_IoU=coverage(all_boxes,target),selected_encoder_max_IoU=coverage(chosen,target),final_decoder_max_IoU=coverage(final,target)))
        records.append(dict(image_id=image_id,encoder_positions=memory.shape[1],selected_proposals=300,encoder_replay_error=error,targets=targets))
        print(f'Inspected training billboard proposals {len(records)}/20',flush=True)
    assert fingerprint(model)==before
    flat=[t for r in records for t in r['targets']]
    result=dict(status='training-only-proposal-coverage-inspected',images=20,known_targets=len(flat),all_encoder_covered=sum(t['all_encoder_max_IoU']>=.5 for t in flat),selected_encoder_covered=sum(t['selected_encoder_max_IoU']>=.5 for t in flat),final_decoder_covered=sum(t['final_decoder_max_IoU']>=.5 for t in flat),raw_coverage_lost_by_topk=sum(t['all_encoder_max_IoU']>=.5 and t['selected_encoder_max_IoU']<.5 for t in flat),threshold_IoU=.5,records=records,all_model_state_unchanged=True,optimizer_updates=0,validation_or_test_used=False,new_GPU_jobs=0,limits='Coverage upper bounds and proposal-stage comparison on training images only; not a proof that encoder fine-tuning will improve detection or retain old classes.')
    save(HERE/'PROPOSAL_COVERAGE.json',result);print(json.dumps({k:v for k,v in result.items() if k!='records'},indent=2))
if __name__=='__main__':run()
