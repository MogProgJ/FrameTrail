"""Training-only logit-preservation statistics, never inferred negative labels."""
import json,time
from cache_engine import *
from build_cache import WEIGHTS,save
from verify_cache_parity import fingerprint
from scoped_engine import build_model,load_sample
from scoped_metrics import iou
from continuation_guard import read,sha
from determinism_policy import math_attention
def xyxy(box):
    x,y,w,h=box;return [x-w/2,y-h/2,x+w/2,y+h/2]
@math_attention()
def run():
    out=HERE/'teacher-preservation';out.mkdir(exist_ok=False)
    release=read(TOOLS/'release/candidate-manifest-v2.json');rows=[r for r in release['images'] if r['split']=='train' and r['scope'].get('133','unknown')=='unknown'];assert len(rows)==645
    regions={r['image_id']:r for r in read(HERE/'reviewed-contrast/REGION_REVIEW.json')['regions']}
    plan=dict(status='frozen-before-further-local-model-fit-or-validation',method='Preserve selected-model row133 logits on unknown TRAIN cells using their frozen-feature covariance. This is a teacher regularizer, NOT negative ground truth.',training_unknown_photos=645,all_existing_train_photos=700,test_and_validation_in_covariance=False,excluded_supervision='Existing20billboard-positive and35explicit-absence photos are supervised; reviewed traffic-sign query regions are excluded from unknown preservation and supervised separately.',data_loss='Same37geometry-covered positive-query BCE +3*mean existing explicit-negative BCE +3*mean reviewed-region negative BCE.',teacher_penalty='0.5*lambda*(theta-theta0).T*C*(theta-theta0); C is equal-photo mean of query-feature outer products with appended bias1, unknown TRAIN queries only.',parameter_ridge=.0001,teacher_weights=[.01,.1,1.,10.],maximum_fit_iterations=200,maximum_fit_seconds_each=120,selection='Fit allfour before development evaluation. Same both-baseline strict gain/FP/retention/unscored530 rules and stable tie break.',original_labels_scopes_and_thresholds_unchanged=True,threshold=.35,all_other_model_state_frozen=True,new_GPU_jobs=0,production_adoption=False,limits='Conservative teacher preservation may suppress unlabelled true billboards too. It does not establish absence or independent accuracy. Development references are reused and no production/generalization claim is permitted.')
    save(out/'PLAN.json',plan)
    torch.set_num_threads(2);torch.manual_seed(17);torch.use_deterministic_algorithms(True)
    net=build_model(WEIGHTS,TOOLS/'rf-mapping.json').cpu().eval();ck=torch.load(TOOLS/'inputs/selected-7805570.pt',map_location='cpu',weights_only=True);net.load_state_dict(ck['model_state_dict']);del ck
    for p in net.parameters():p.requires_grad_(False)
    before=fingerprint(net);C=torch.zeros(257,257,dtype=torch.float64);inputs={};roi={};started=time.perf_counter()
    for i,row in enumerate(rows,1):
        if time.perf_counter()-started>1200:raise ValueError('Local teacher-statistics1200second cap; preserve output')
        path=TOOLS/'release'/row['source_path'];assert sha(path)==row['image_sha256']
        image,_=load_sample(TOOLS/'release',row)
        with torch.no_grad():cached,live=capture(net,image,full=False);rebuilt=replay(cached,net.class_embed.weight,net.class_embed.bias)
        assert max_output_error(live,rebuilt)==0
        h=cached['features'][-1,0].double();keep=torch.ones(300,dtype=torch.bool)
        if row['image_id'] in regions:
            box=xyxy(regions[row['image_id']]['region']);pred=[list(map(lambda v:max(0.,min(1.,v)),xyxy(b))) for b in cached['boxes'][-1,0].tolist()];q=[j for j,b in enumerate(pred) if iou(b,box)>=.7]
            if q:roi[row['image_id']]=h[q].float().clone();keep[q]=False
        h=h[keep];aug=torch.cat([h,torch.ones(len(h),1,dtype=torch.float64)],dim=1);C+=aug.T@aug/len(h)
        inputs[row['image_id']]=dict(source_sha256=row['image_sha256'],unknown_queries=int(keep.sum()),forward_max_error=0.)
        if i%40==0:print(f'Teacher-preservation statistics {i}/645 TRAIN photos; unknown cells remain unlabelled',flush=True)
    C/=len(rows);assert fingerprint(net)==before
    torch.save(dict(covariance=C,reviewed_roi_features=roi),out/'training-statistics.pt')
    save(out/'INPUTS.json',inputs)
    save(out/'STATISTICS_RECEIPT.json',dict(status='645-training-only-teacher-statistics-complete',photos=645,all_original_model_state_unchanged=True,all645_cached_forward_errors_zero=True,validation_or_test_used=False,unknowns_inferred_as_negative=False,optimizer_updates=0,new_GPU_jobs=0,seconds=time.perf_counter()-started,plan_sha256=sha(out/'PLAN.json'),statistics_sha256=sha(out/'training-statistics.pt')))
if __name__=='__main__':run()
