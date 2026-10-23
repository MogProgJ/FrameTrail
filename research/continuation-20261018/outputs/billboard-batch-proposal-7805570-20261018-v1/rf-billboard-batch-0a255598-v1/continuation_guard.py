"""One-row scope, exact assets, fixed sampler; cluster approval is mandatory."""
import hashlib,json,random
from pathlib import Path
from release_guard import validate_draft
from selection_policy import eligible,ranking
PROTOCOL_SHA='0a255598b74eb1d29d83ee1be10d517ae407fbda2c57e4565b51028d615343fd'
SCOPE='four-billboard-trials-array0-3-percent2-max3000-45min-each-known-regression'
COUNT_KEYS=('complete_tp','complete_fp','complete_fn','partial_hits','partial_misses','unscored_predictions')
def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def sha(p):
    with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def approval(t):
    if not (t/'approval.json').exists():raise ValueError('Explicit user approval for this exact new cluster job is missing; no submission')
    p=read(t/'protocol.json');a=read(t/'approval.json')
    if sha(t/'protocol.json')!=PROTOCOL_SHA or a.get('protocol_sha256')!=PROTOCOL_SHA or a.get('approved') is not True or a.get('scope')!=SCOPE or not a.get('user_authorization_evidence'):raise ValueError('Exact separate cluster approval missing or changed')
    if a.get('active_classifier_rows')!=[133] or p['active_classifier_rows']!=[133] or p['training']['maximum_updates']!=3000 or p['batch']['array']!='0-3%2':raise ValueError('Scope changed')
    return a,p
def counts_equal(a,b):
    if set(a['per_class'])!=set(b['per_class']):return False
    return all(a['metrics'][k]==b['metrics'][k] for k in COUNT_KEYS) and all(a['per_class'][c][k]==b['per_class'][c][k] for c in a['per_class'] for k in COUNT_KEYS if k!='unscored_predictions')
def variant(t,index=None):
    import os
    if index is None:
        raw=os.environ.get('SLURM_ARRAY_TASK_ID')
        if raw not in ('0','1','2','3'):raise ValueError('Exact array task index required')
        index=int(raw)
    if type(index) is not int or not 0<=index<4:raise ValueError('Unknown array task index')
    return read(t/'protocol.json')['variants'][index]

def inputs(t,require_approval=True,task_index=None):
    if require_approval:_,p=approval(t)
    else:
        p=read(t/'protocol.json')
        if sha(t/'protocol.json')!=PROTOCOL_SHA:raise ValueError('Proposed protocol changed')
    release=validate_draft(t/'release/candidate-manifest-v2.json',p['candidate_sha256'])
    v=variant(t,task_index);pools=read(t/'sampling-pools.json');schedule=read(t/v['schedule_file'])
    if sha(t/'sampling-pools.json')!=p['data']['pools_sha256'] or sha(t/v['schedule_file'])!=v['schedule_sha256']:raise ValueError('Sampler seal changed')
    train={r['image_id']:r for r in release['images'] if r['split']=='train'}
    expected=dict(billboard=sorted(i for i,r in train.items() if any(x['canonical_id']==133 for x in r['targets'])),explicit_negative=sorted(i for i,r in train.items() if r['scope'].get('133')=='absent'))
    if pools!=expected or len(pools['billboard'])!=20 or len(pools['explicit_negative'])!=35:raise ValueError('Pools changed or include unreviewed absence')
    rng=random.Random(171022);positive=[]
    while len(positive)<3000:
        cycle=list(pools['billboard']);rng.shuffle(cycle);positive.extend(cycle)
    rng=random.Random(171023);negatives=[rng.sample(pools['explicit_negative'],3) for _ in range(3000)];expected_schedule=[[positive[i],*negatives[i][:v['negative_presentations']]] for i in range(3000)]
    if schedule!=expected_schedule or any(set(batch)-set(train) or len(set(batch))!=v['accumulation'] for batch in schedule):raise ValueError('Sampling changed or escaped training partition')
    if sha(t/'inputs/selected-7805570.pt')!=p['starting_checkpoint']['sha256']:raise ValueError('Starting checkpoint changed')
    original=read(t/'inputs/validation-original.json');resume=read(t/'inputs/validation-resume.json')
    if not eligible(resume,original) or ranking(resume)<=ranking(original):raise ValueError('Pinned current baseline did not retain and improve original baseline')
    return release,schedule,original,resume
def activate(t):
    a,p=approval(t);release,_,_,_=inputs(t);out=t/'release'/('approved-core-task-'+str(variant(t)['index'])+'.json')
    expected=dict(release,approved_for_training=True,parent_candidate_sha256=p['candidate_sha256'],approval_sha256=sha(t/'approval.json'))
    if out.exists():
        if read(out)!=expected:raise ValueError('Existing activation differs from exact approved draft')
    else:
        with out.open('x',encoding='utf-8') as f:json.dump(expected,f,indent=2,allow_nan=False)
    return out
def stop_without_gain(step,best_step):return step==1500 and best_step==0
