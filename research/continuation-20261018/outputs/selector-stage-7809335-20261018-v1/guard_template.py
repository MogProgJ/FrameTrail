"""Exact new two-head scope, sealed region overlay and fixed paired schedule."""
import hashlib,json,random
from pathlib import Path
from release_guard import validate_draft
from selection_policy import eligible,ranking
PROTOCOL_SHA='@@PROTOCOL_SHA@@'
SCOPE='@@SCOPE@@'
COUNT_KEYS=('complete_tp','complete_fp','complete_fn','partial_hits','partial_misses','unscored_predictions')
HEADS=['class_embed','transformer.enc_out_class_embed.0']
def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def sha(p):
    with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def approval(t):
    if not (t/'approval.json').exists():raise ValueError('Explicit approval for this NEW selector scope missing; no submission')
    p=read(t/'protocol.json');a=read(t/'approval.json')
    if sha(t/'protocol.json')!=PROTOCOL_SHA or a.get('protocol_sha256')!=PROTOCOL_SHA or a.get('approved') is not True or a.get('scope')!=SCOPE or not a.get('user_authorization_evidence'):raise ValueError('Exact new cluster approval missing or changed')
    if a.get('active_classifier_heads')!=HEADS or a.get('active_classifier_rows')!=[133] or p['active_classifier_heads']!=HEADS or p['training']['maximum_updates']!=3000 or p['batch']['array']!='0-3%2':raise ValueError('New scope differs')
    return a,p
def counts_equal(a,b):
    return set(a['per_class'])==set(b['per_class']) and all(a['metrics'][k]==b['metrics'][k] for k in COUNT_KEYS) and all(a['per_class'][c][k]==b['per_class'][c][k] for c in a['per_class'] for k in COUNT_KEYS if k!='unscored_predictions')
def variant(t,index=None):
    import os
    if index is None:
        raw=os.environ.get('SLURM_ARRAY_TASK_ID')
        if raw not in ('0','1','2','3'):raise ValueError('Exact task0-3 required')
        index=int(raw)
    if type(index) is not int or not 0<=index<4:raise ValueError('Unknown task')
    return read(t/'protocol.json')['variants'][index]
def inputs(t,require_approval=True,task_index=None):
    p=approval(t)[1] if require_approval else read(t/'protocol.json')
    if sha(t/'protocol.json')!=PROTOCOL_SHA:raise ValueError('Protocol changed')
    release=validate_draft(t/'release/candidate-manifest-v2.json',p['candidate_sha256']);train={r['image_id']:r for r in release['images'] if r['split']=='train'}
    overlay=read(t/'region-review.json');regions={r['image_id']:r for r in overlay['regions']}
    if sha(t/'region-review.json')!=p['data']['separate_training_region_overlay']['sha256'] or len(regions)!=8:raise ValueError('Reviewed overlay changed')
    for i,r in regions.items():
        row=train[i]
        if row['scope'].get('133','unknown')!='unknown' or r['image_sha256']!=row['image_sha256'] or r['split']!='train' or r['query_minimum_IoU']!=.7:raise ValueError('Region escaped original training-only unknown scope')
        if not any(x['canonical_id']==r['existing_region_canonical_id'] and x['normalized_cxcywh']==r['region'] for x in row['targets']):raise ValueError('Region differs from reviewed existing sign box')
    expected=dict(billboard=sorted(i for i,r in train.items() if any(x['canonical_id']==133 for x in r['targets'])),explicit_negative=sorted(i for i,r in train.items() if r['scope'].get('133')=='absent'),reviewed_region=sorted(regions))
    pools=read(t/'sampling-pools.json');v=variant(t,task_index);schedule=read(t/v['schedule_file'])
    if pools!=expected or [len(pools[k]) for k in ('billboard','explicit_negative','reviewed_region')]!=[20,35,8] or len(set(sum(pools.values(),[])))!=63:raise ValueError('Pools changed or overlap')
    if sha(t/'sampling-pools.json')!=p['data']['pools_sha256'] or sha(t/v['schedule_file'])!=v['schedule_sha256']:raise ValueError('Sampler seal changed')
    def cycle(ids,seed):
        rng=random.Random(seed);result=[]
        while len(result)<3000:
            c=list(ids);rng.shuffle(c);result+=c
        return result[:3000]
    pos=cycle(pools['billboard'],171022);rois=cycle(pools['reviewed_region'],171024);rng=random.Random(171023)
    expected_schedule=[[pos[i],*rng.sample(pools['explicit_negative'],2),rois[i]] for i in range(3000)]
    if schedule!=expected_schedule or any(set(b)-set(train) or len(set(b))!=4 for b in schedule):raise ValueError('Sampler escaped paired training-only schedule')
    if sha(t/'inputs/selected-7805570.pt')!=p['starting_checkpoint']['sha256']:raise ValueError('Starting checkpoint changed')
    original=read(t/'inputs/validation-original.json');resume=read(t/'inputs/validation-resume.json')
    if not eligible(resume,original) or ranking(resume)<=ranking(original):raise ValueError('Pinned baseline differs')
    return release,schedule,original,resume
def activate(t):
    a,p=approval(t);release,_,_,_=inputs(t);out=t/'release'/('approved-core-task-'+str(variant(t)['index'])+'.json')
    expected=dict(release,approved_for_training=True,parent_candidate_sha256=p['candidate_sha256'],approval_sha256=sha(t/'approval.json'))
    if out.exists():
        if read(out)!=expected:raise ValueError('Activation differs')
    else:
        with out.open('x',encoding='utf-8') as f:json.dump(expected,f,indent=2,allow_nan=False)
    return out
def stop_without_gain(step,best_step):return step==1500 and best_step==0
