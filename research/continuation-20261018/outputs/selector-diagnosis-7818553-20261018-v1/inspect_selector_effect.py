"""Measure actual proposal changes on TRAIN photos after the completed array."""
import sys,json,time
from pathlib import Path
D=Path(__file__).resolve().parent;P=D.parent/'selector-batch-proposal-7809335-20261018-v1';T=P/'rf-selector-a77d9663-v1';FROZEN=D.parent/'frozen-head-cpu-7809335-20261018-v1'
sys.path[:0]=[str(FROZEN),str(T)]
from cache_engine import *
from scoped_engine import build_model,load_sample
from scoped_metrics import iou
from determinism_policy import math_attention
from continuation_guard import read,sha
def coverage(boxes,row):
    def xyxy(b):
        x,y,w,h=b;return [max(0,x-w/2),max(0,y-h/2),min(1,x+w/2),min(1,y+h/2)]
    pred=[xyxy(b) for b in boxes.tolist()];targets=[xyxy(t['normalized_cxcywh']) for t in row['targets'] if t['canonical_id']==133]
    return sum(max(iou(p,t) for p in pred)>=.5 for t in targets)
@math_attention()
def run():
    torch.set_num_threads(2);torch.manual_seed(17);torch.use_deterministic_algorithms(True);started=time.monotonic()
    weights=Path(r'C:\Users\nazee\Documents\All Modules\FrameTrail\.deps\rfdetr-probe-assets\rf-detr-small.pth');model=build_model(weights,T/'rf-mapping.json').cpu().eval();initial=torch.load(T/'inputs/selected-7805570.pt',map_location='cpu',weights_only=True)['model_state_dict']
    for p in model.parameters():p.requires_grad_(False)
    rows={r['image_id']:r for r in read(T/'release/candidate-manifest-v2.json')['images']};ids=read(T/'sampling-pools.json')['billboard'];baseline={};results=[]
    for index in (-1,0,1,2,3):
        if index==-1:state=initial
        else:
            out=P/f'retrieval-7818553/task-{index}/verified-7818553_{index}/output/rf-selector-7818553_{index}';report=read(out/'experiment-report.json');assert sha(out/'last.pt')==report['last_checkpoint_sha256'];state=torch.load(out/'last.pt',map_location='cpu',weights_only=True)['model_state_dict']
        model.load_state_dict(state,strict=True);changes=[];covered=0
        for i in ids:
            assert rows[i]['split']=='train';raw=[]
            def hook(module,args,output):
                if not raw:raw.append(output.detach())
            handle=model.transformer.enc_out_class_embed[0].register_forward_hook(hook)
            try:
                with torch.inference_mode():image,_=load_sample(T/'release',rows[i]);cached,output=capture(model,image,full=True)
            finally:handle.remove()
            order=torch.topk(raw[0].max(-1)[0],300,dim=1)[1][0].tolist();covered+=coverage(output['pred_boxes'][0],rows[i])
            if index==-1:baseline[i]=dict(order=order,features=cached['features'],boxes=cached['boxes'])
            else:
                b=baseline[i];changes.append(dict(image_id=i,proposal_order_changed=order!=b['order'],new_selected_proposals=len(set(order)-set(b['order'])),max_decoder_feature_change=float((cached['features']-b['features']).abs().max()),max_box_coordinate_change=float((cached['boxes']-b['boxes']).abs().max())))
        if index==-1:baseline_covered=covered
        else:
            item=dict(index=index,TRAIN_photos=20,targets=54,baseline_final_box_covered=baseline_covered,final_box_covered=covered,photos_with_proposal_order_changed=sum(r['proposal_order_changed'] for r in changes),photos_with_new_selected_proposals=sum(r['new_selected_proposals']>0 for r in changes),total_new_proposals=sum(r['new_selected_proposals'] for r in changes),records=changes);results.append(item);print(json.dumps({k:v for k,v in item.items() if k!='records'}),flush=True)
        if index>=0:del state
    result=dict(status='actual-selector-effect-measured-on-training-photos',trials=results,validation_or_test_photos_used=0,optimizer_updates=0,new_GPU_jobs=0,production_adoption=False,elapsed_seconds=time.monotonic()-started)
    with (D/'SELECTOR_EFFECT.json').open('x',encoding='utf-8') as f:json.dump(result,f,indent=2)
if __name__=='__main__':run()
