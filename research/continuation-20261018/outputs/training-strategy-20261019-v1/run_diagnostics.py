"""Fixed exploratory TRAIN-only probes. No image inference, validation selection or saved model."""
import hashlib, json, sys, time
from pathlib import Path
ROOT=Path(__file__).resolve().parent
OUT=ROOT.parent
FROZEN=OUT/'frozen-head-cpu-7809335-20261018-v1'
TOOLS=OUT/'selector-batch-proposal-7809335-20261018-v1/rf-selector-a77d9663-v1'
DIAG=OUT/'selector-diagnosis-7818553-20261018-v1'
sys.path.insert(0,str(FROZEN))
from cache_engine import torch, replay
from scoped_rf import ScopedRFCriterion, target_from_row
from rfdetr.utilities import box_ops
from scipy.optimize import linear_sum_assignment
import torch.nn.functional as functional

def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):
    with p.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()
def save(name,value):(ROOT/name).write_text(json.dumps(value,indent=2,allow_nan=False)+'\n',encoding='utf-8')
def metrics(scores,labels,ids):
    order=torch.argsort(scores,descending=True,stable=True);ranked=labels[order]
    ap=float((ranked*(ranked.cumsum(0)/torch.arange(1,len(ranked)+1))).sum()/ranked.sum())
    predicted=scores>=.5;positive=labels==1;negative=~positive
    positive_ids=sorted({i for i,y in zip(ids,labels.tolist()) if y==1})
    negative_ids=sorted({i for i,y in zip(ids,labels.tolist()) if y==0})
    photo_hits=[];photo_alarms=[]
    for values,wanted,result in [(positive_ids,True,photo_hits),(negative_ids,False,photo_alarms)]:
        for image_id in values:
            mask=torch.tensor([i==image_id for i in ids]);result.append(float(predicted[mask].float().mean()) if wanted else float(predicted[mask].any()))
    return {'query_average_precision':ap,'positive_query_recall_at_0_5':float(predicted[positive].float().mean()),
            'negative_query_positive_fraction_at_0_5':float(predicted[negative].float().mean()),
            'positive_photo_macro_query_recall_at_0_5':sum(photo_hits)/len(photo_hits),
            'absent_photos_with_any_positive_query_at_0_5':sum(photo_alarms)/len(photo_alarms),
            'positive_queries':int(positive.sum()),'negative_queries':int(negative.sum()),'positive_photos':len(positive_ids),'negative_photos':len(negative_ids)}

def run():
    started=time.monotonic();torch.set_num_threads(2);torch.manual_seed(17);torch.use_deterministic_algorithms(True)
    plan_hash=sha(ROOT/'DIAGNOSTIC_PLAN.json')
    manifest=TOOLS/'release/candidate-manifest-v2.json';checkpoint=TOOLS/'inputs/selected-7805570.pt'
    input_hashes={'manifest':sha(manifest),'checkpoint':sha(checkpoint)}
    rows={r['image_id']:r for r in read(manifest)['images'] if r['split']=='train'}
    coverage=read(FROZEN/'TRAIN_FEATURE_COVERAGE.json')['coverage'];positive_ids=[r['image_id'] for r in coverage]
    pools=read(TOOLS/'sampling-pools.json');overlay=read(DIAG/'TRAIN_CONTRAST_OVERLAY.json')['records']
    negatives=sorted(set(pools['explicit_negative'])|{r['image_id'] for r in overlay if r['supervision']=='whole_photo_billboard_absent'})
    held={r['image_id'] for r in read(DIAG/'TRAIN_POSITIVE_REVIEW.json')['records'] if r['disposition']=='category_boundary_hold'}
    index=read(FROZEN/'CACHE_INDEX_FULL_LAYOUT.json');extra={r['image_id']:r for r in read(DIAG/'local-contrast/CACHE_RECEIPT.json')['records']}
    head_file=FROZEN/'cache-full-layout/initial-head.pt';head=torch.load(head_file,map_location='cpu',weights_only=True)
    caches={};input_records=[]
    for image_id in sorted(set(positive_ids)|set(negatives)):
        assert image_id in rows
        if image_id in index:
            assert index[image_id]['split']=='train';path=FROZEN/'cache-full-layout'/(image_id+'.pt');expected=index[image_id]['cache_sha256']
        else:
            path=DIAG/'local-contrast/cache'/(image_id+'.pt');expected=extra[image_id]['cache_sha256']
        assert sha(path)==expected
        caches[image_id]=torch.load(path,map_location='cpu',weights_only=True)
        input_records.append({'image_id':image_id,'split':'train','cache_sha256':expected,'identity_group':rows[image_id]['identity_group']})
    matcher=ScopedRFCriterion(615).matcher;assignment=[]
    with torch.no_grad():
        for image_id in positive_ids:
            row=rows[image_id];cache=caches[image_id];outputs=replay(cache,head['weight'],head['bias']);target=target_from_row(row,615)
            q,t=matcher(outputs,[target])[0];target_mask=target['labels'][t]==133;q=q[target_mask];t=t[target_mask]
            billboard=target['boxes'][target['labels']==133]
            overlaps=box_ops.box_iou(box_ops.box_cxcywh_to_xyxy(outputs['pred_boxes'][0]),box_ops.box_cxcywh_to_xyxy(billboard))[0]
            oq,ot=linear_sum_assignment(-(overlaps.numpy()>=.5).astype(float)-overlaps.numpy()*1e-5)
            matched=box_ops.elementwise_box_iou(box_ops.box_cxcywh_to_xyxy(outputs['pred_boxes'][0,q]),box_ops.box_cxcywh_to_xyxy(target['boxes'][t]))[0]
            score=outputs['pred_logits'][0,:,133].sigmoid()
            assignment.append({'image_id':image_id,'targets':len(billboard),'scope':row['scope']['133'],
                'any_query_geometry_covered':int((overlaps.max(0).values>=.5).sum()),'one_to_one_geometry_covered':int((overlaps[oq,ot]>=.5).sum()),
                'actual_loss_matched_IoU_at_least_0_5':int((matched>=.5).sum()),'actual_loss_matched_IoU_below_0_35':int((matched<.35).sum()),
                'matched_scores':score[q].tolist(),'matched_ious':matched.tolist(),'maximum_billboard_score':float(score.max()),
                'unmatched_billboard_queries_supervised_negative':bool(target['scope_negative_mask'][133])})
    totals={k:sum(r[k] for r in assignment) for k in ('targets','any_query_geometry_covered','one_to_one_geometry_covered','actual_loss_matched_IoU_at_least_0_5','actual_loss_matched_IoU_below_0_35')}
    save('ASSIGNMENT_DIAGNOSIS.json',{'status':'TRAIN-only-baseline-matching-audited','plan_sha256':plan_hash,'totals':totals,'records':assignment,'production_model_changed':False})
    print('Assignment diagnostic:',json.dumps(totals),flush=True)
    # Only reviewed, whole-photo absence is negative. Positive-only photos
    # contribute covered positive queries, never their unlabelled queries.
    records={};selected={r['image_id']:r['selected_queries'] for r in coverage}
    for image_id in sorted((set(positive_ids)-held)|set(negatives)):
        x=caches[image_id]['features'][-1,0].float()
        if image_id in negatives:
            score=functional.linear(x,head['weight'][133:134],head['bias'][133:134]).flatten()
            hard=score.argsort(descending=True,stable=True)[:32].tolist();rest=[i for i in range(300) if i not in hard]
            uniform=[rest[round(k*(len(rest)-1)/31)] for k in range(32)]
            training=x[sorted(hard+uniform)];evaluation=x;y=0
        else:
            if not selected[image_id]:continue
            training=evaluation=x[selected[image_id]];y=1
        records[image_id]={'train':training,'eval':evaluation,'y':y,'group':rows[image_id]['identity_group']}
    groups={}
    for image_id,r in records.items():groups.setdefault(r['group'],[]).append(image_id)
    fold_ids=[[] for _ in range(4)];loads=[[0,0] for _ in range(4)];group_fold={}
    order=sorted(groups,key=lambda g:(-int(any(records[i]['y'] for i in groups[g])),hashlib.sha256(('17|'+g).encode()).hexdigest()))
    for group in order:
        positive=any(records[i]['y'] for i in groups[group]);column=0 if positive else 1
        fold=min(range(4),key=lambda f:(loads[f][column],sum(loads[f]),f));group_fold[group]=fold
        fold_ids[fold]+=groups[group]
        loads[fold][0]+=sum(records[i]['y'] for i in groups[group]);loads[fold][1]+=sum(1-records[i]['y'] for i in groups[group])
    save('FOLDS.json',{'plan_sha256':plan_hash,'identity_disjoint':True,'groups':group_fold,'held_photo_ids':fold_ids,'excluded_boundary_photo_ids':sorted(held),
                       'geometry_uncovered_positive_photos_excluded_from_classifier_probe':[i for i in positive_ids if i not in held and not selected[i]],'fold_photo_class_counts':loads})
    summary=[];predictions=[]
    for fold,test_ids in enumerate(fold_ids):
        train_ids=sorted(set(records)-set(test_ids));train_groups={records[i]['group'] for i in train_ids};test_groups={records[i]['group'] for i in test_ids};assert not train_groups & test_groups
        x=torch.cat([records[i]['train'] for i in train_ids]);y=torch.cat([torch.full((len(records[i]['train']),),float(records[i]['y'])) for i in train_ids])
        positive_photos=sum(records[i]['y'] for i in train_ids);negative_photos=len(train_ids)-positive_photos
        weights=torch.cat([torch.full((len(records[i]['train']),),.5/((positive_photos if records[i]['y'] else negative_photos)*len(records[i]['train']))) for i in train_ids])
        mean=x.mean(0);std=x.std(0).clamp_min(.1);z=(x-mean)/std
        tx=torch.cat([records[i]['eval'] for i in test_ids]);ty=torch.cat([torch.full((len(records[i]['eval']),),float(records[i]['y'])) for i in test_ids]);tids=[i for i in test_ids for _ in range(len(records[i]['eval']))];tz=(tx-mean)/std
        for kind in ('linear','mlp32'):
            torch.manual_seed(17)
            model=torch.nn.Linear(256,1) if kind=='linear' else torch.nn.Sequential(torch.nn.Linear(256,32),torch.nn.ReLU(),torch.nn.Linear(32,1))
            optimizer=torch.optim.AdamW(model.parameters(),lr=.003,weight_decay=.0001)
            for step in range(160):
                if time.monotonic()-started>480:raise TimeoutError('Predeclared diagnostic time cap; preserve completed evidence, no automatic retry')
                optimizer.zero_grad();logits=model(z).flatten();loss=(functional.binary_cross_entropy_with_logits(logits,y,reduction='none')*weights).sum();assert torch.isfinite(loss);loss.backward();optimizer.step()
            with torch.no_grad():
                train_scores=model(z).flatten().sigmoid();scores=model(tz).flatten().sigmoid()
            train_positives=y==1
            row={'fold':fold,'model':kind,'updates':160,'parameters':sum(p.numel() for p in model.parameters()),'train_weighted_BCE':float(loss.detach()),'training_positive_query_recall_at_0_5':float((train_scores[train_positives]>=.5).float().mean()),'held_TRAIN_fold':metrics(scores,ty,tids)}
            summary.append(row);predictions.append({'fold':fold,'model':kind,'scores':scores.tolist(),'labels':ty.tolist(),'image_ids':tids});save('CAPACITY_PROGRESS.json',summary);print(json.dumps(row),flush=True)
    assert sha(manifest)==input_hashes['manifest'] and sha(checkpoint)==input_hashes['checkpoint']
    save('TRAIN_FOLD_QUERY_PREDICTIONS.json',predictions)
    save('INPUT_AUDIT.json',{'plan_sha256':plan_hash,'manifest_sha256':input_hashes['manifest'],'checkpoint_sha256':input_hashes['checkpoint'],'initial_head_sha256':sha(head_file),'cache_records':input_records,'all_cache_reads_training_only':True,'cache_validation_or_test_reads':0,'image_inference_calls':0,'source_checkpoint_and_manifest_unchanged':True})
    save('CAPACITY_DIAGNOSIS.json',{'status':'fixed-TRAIN-identity-fold-capacity-diagnostic-complete','seconds':time.monotonic()-started,'records':summary,'participating_positive_photos':sum(r['y'] for r in records.values()),'participating_negative_photos':sum(1-r['y'] for r in records.values()),'limitations':['Reuses previously developed TRAIN data; exploratory, not unbiased or fresh generalization','Identity groups disjoint; cross-author scene similarity may remain','Only geometrically covered positive queries; not detector recall/AP/mAP','No threshold/optimizer tuning, no model saved or promoted','No old validation/test predictions used by this probe'],'new_cluster_jobs':0,'production_adoption':False})

if __name__=='__main__':run()
