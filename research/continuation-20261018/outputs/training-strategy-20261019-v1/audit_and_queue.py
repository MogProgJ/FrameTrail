import hashlib, json, math
from pathlib import Path
ROOT=Path(__file__).resolve().parent;OUT=ROOT.parent
OLD=Path(r'C:\Users\nazee\.codex\visualizations\2026\10\15\01a141ae-c7a6-7303-a280-403af88736f3')
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def save(name,j):(ROOT/name).write_text(json.dumps(j,indent=2,allow_nan=False)+'\n',encoding='utf-8')
def sha(p):
    with p.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()

# Recompute query metrics with plain Python, independently of torch/training.
predictions=read(ROOT/'TRAIN_FOLD_QUERY_PREDICTIONS.json');capacity=read(ROOT/'CAPACITY_DIAGNOSIS.json')
lookup={(r['fold'],r['model']):r for r in capacity['records']};aggregate={};checked=[]
for row in predictions:
    values=list(zip(row['scores'],row['labels'],row['image_ids']));ordered=sorted(enumerate(values),key=lambda item:(-item[1][0],item[0]))
    total_positive=sum(y for _,y,_ in values);tp=0;area=0
    for rank,(_,(_,y,_)) in enumerate(ordered,1):
        if y:tp+=1;area+=tp/rank
    ap=area/total_positive
    matched=lookup[row['fold'],row['model']]['held_TRAIN_fold'];assert abs(ap-matched['query_average_precision'])<2e-6
    positive_hits=sum(s>=.5 for s,y,_ in values if y);negative_ids={i for _,y,i in values if not y};alarms={i for s,y,i in values if not y and s>=.5}
    assert abs(positive_hits/total_positive-matched['positive_query_recall_at_0_5'])<2e-6
    assert abs(len(alarms)/len(negative_ids)-matched['absent_photos_with_any_positive_query_at_0_5'])<1e-12
    accum=aggregate.setdefault(row['model'],{'positive_queries':0,'positive_hits':0,'negative_photos':0,'negative_photos_with_positive_query':0,'fold_AP':[]})
    accum['positive_queries']+=int(total_positive);accum['positive_hits']+=positive_hits;accum['negative_photos']+=len(negative_ids);accum['negative_photos_with_positive_query']+=len(alarms);accum['fold_AP'].append(ap)
    checked.append({'fold':row['fold'],'model':row['model'],'AP':ap,'positive_hits':positive_hits,'positive_queries':int(total_positive),'negative_photos_with_positive_query':len(alarms),'negative_photos':len(negative_ids)})
folds=read(ROOT/'FOLDS.json');inputs=read(ROOT/'INPUT_AUDIT.json');identity={r['image_id']:r['identity_group'] for r in inputs['cache_records']};seen=set()
for ids in folds['held_photo_ids']:
    groups={identity[i] for i in ids};assert not groups & seen;seen.update(groups)
assert inputs['all_cache_reads_training_only'] and inputs['cache_validation_or_test_reads']==0
for model,a in aggregate.items():a.update(mean_fold_AP=sum(a['fold_AP'])/4,positive_query_recall=a['positive_hits']/a['positive_queries'],absent_photo_query_alarm_fraction=a['negative_photos_with_positive_query']/a['negative_photos'])
save('INDEPENDENT_AUDIT.json',{'status':'query-metrics-and-identity-folds-independently-recomputed','checks':checked,'aggregate':aggregate,'all_cache_reads_TRAIN_only':True,'threshold_warning':'0.5 binary probe scores are not calibrated app probabilities or final detector FP rates','no_candidate_selected':True})

sources=[('main-row convex probes', 'frozen-head-cpu-7809335-20261018-v1/LOCAL_PROBE_RECEIPT.json'),
('reviewed-region convex probes','frozen-head-cpu-7809335-20261018-v1/reviewed-contrast/RECEIPT.json'),
('teacher-preserved convex probes','frozen-head-cpu-7809335-20261018-v1/teacher-preservation/RECEIPT.json'),
('RMS-constrained convex probe','frozen-head-cpu-7809335-20261018-v1/rms-constrained/RECEIPT.json'),
('cached optimizer controls','selector-stage-7809335-20261018-v1/CPU_CONTROLS_AUDIT.json'),
('expanded contrast probes','selector-diagnosis-7818553-20261018-v1/local-contrast/RECEIPT.json'),
('cluster main-row array7809335','billboard-batch-proposal-7805570-20261018-v1/retrieval-7809335/independent-audit/AUDIT.json'),
('cluster two-head array7818553','selector-batch-proposal-7809335-20261018-v1/retrieval-7818553/independent-audit/AUDIT.json')]
ledger=[]
for family,name in sources:
    path=OUT/name;j=read(path);records=j.get('trials',j.get('tasks',j.get('controls')))
    ledger.append({'family':family,'source':str(path),'sha256':sha(path),'status':j['status'],'configurations':len(records) if records is not None else 1,'records':records if isinstance(records,list) else records})
save('EXPERIMENT_LEDGER.json',{'families':ledger,'scope':'Previously audited billboard configurations/controls only. Reused data; these are not independent replications or fresh datasets.'})

intake=OLD/'nextdata-acquisition-7768932-v1/results-7769109/retrieved/output/training-general-v1/next-photo-7768932-v1'
source_review=OLD/'nextdata-source-review-7769109-v1/source-evidence-review.json'
release=OUT/'selector-batch-proposal-7809335-20261018-v1/rf-selector-a77d9663-v1/release/candidate-manifest-v2.json'
used_rows=read(release)['images'];used_ids={r['image_id'] for r in used_rows};used_hashes={r['image_sha256'] for r in used_rows};all_groups={r['identity_group'] for r in used_rows};held_groups={r['identity_group'] for r in used_rows if r['split']!='train'}
reviews={r['image_id']:r for r in read(source_review)['images']};queue=[]
for row in read(intake/'manifest.json')['images']:
    review=reviews[row['id']]
    if row['selected_category']!='billboard' or row['id'] in used_ids or row['sha256'] in used_hashes:continue
    if review['status']!='photo-specific-license-corroborated' or review['identity_group'] in all_groups:continue
    image=intake/row['path'];assert sha(image)==row['sha256']
    queue.append({'image_id':row['id'],'source_path':str(image),'image_sha256':row['sha256'],'publisher_boxes':row['publisher_boxes'],'width':row['width'],'height':row['height'],
                  'identity_group':review['identity_group'],'source_evidence_status':review['status'],'not_in_current_release_exact_or_known_identity':True,
                  'rights_verified':False,'approved_for_training':False,'content_review':'pending','scene_duplicate_review':'pending','split':'unassigned',
                  'eligible_use_after_all_checks':'TRAIN-only candidate; not fresh validation or test evidence'})
save('LOCAL_REVIEW_QUEUE.json',{'status':'local-unused-billboard-candidates-staged-not-cleared','source_manifest_sha256':sha(intake/'manifest.json'),'source_review_sha256':sha(source_review),'records':queue,'limitations':'Unused residual intake, not representative publisher sampling. No model predictions used in this review. Perceptual/scene/source and box review remain mandatory.'})

app=OUT/'native-unified-20261019-v1/app';files=[p for p in app.rglob('*') if p.is_file()];models=[p for p in files if 'models' in p.relative_to(app).parts]
save('APP_BLOAT_BASELINE.json',{'priority':'secondary; no app deletions or feature edits in this strategy pass','total_bytes':sum(p.stat().st_size for p in files),'model_bytes':sum(p.stat().st_size for p in models),'file_count':len(files),'model_files':[{'file':str(p.relative_to(app)),'bytes':p.stat().st_size} for p in models],
    'largest_non_model_files':[{'file':str(p.relative_to(app)),'bytes':p.stat().st_size} for p in sorted((f for f in files if f not in models),key=lambda p:-p.stat().st_size)[:12]],
    'recommended_next_app_scope':'Audit the minimum model set needed for actual project categories before any deletion; default YOLOX-S alone is not established as sufficient for billboard/washer coverage. Build a reversible lean CPU package with optional models/backends, preserving research evidence. Measure size, launch/memory and workflows separately; smaller distribution is not an inference speed claim. Add a small local guide/section jump without a new runtime dependency.'})
print(json.dumps({'aggregate':aggregate,'past_configuration_count':sum(r['configurations'] for r in ledger),'local_review_candidates':len(queue),'app_bytes':sum(p.stat().st_size for p in files),'model_bytes':sum(p.stat().st_size for p in models)}))
