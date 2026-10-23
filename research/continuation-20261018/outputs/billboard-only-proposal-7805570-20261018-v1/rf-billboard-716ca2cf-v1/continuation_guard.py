"""One-row scope, exact assets, fixed sampler; cluster approval is mandatory."""
import hashlib,json,random
from pathlib import Path
from release_guard import validate_draft
from selection_policy import eligible,ranking
PROTOCOL_SHA='716ca2cf411984698e6d096f00fd5ef01995bee9ed4fe0c82a742e26c4bc6e1c'
SCOPE='one-billboard-row-negative-calibration-max3000-oneGPU-45minutes'
COUNT_KEYS=('complete_tp','complete_fp','complete_fn','partial_hits','partial_misses','unscored_predictions')
def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def sha(p):
    with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def approval(t):
    if not (t/'approval.json').exists():raise ValueError('Explicit user approval for this exact new cluster job is missing; no submission')
    p=read(t/'protocol.json');a=read(t/'approval.json')
    if sha(t/'protocol.json')!=PROTOCOL_SHA or a.get('protocol_sha256')!=PROTOCOL_SHA or a.get('approved') is not True or a.get('scope')!=SCOPE or not a.get('user_authorization_evidence'):raise ValueError('Exact separate cluster approval missing or changed')
    if a.get('active_classifier_rows')!=[133] or p['active_classifier_rows']!=[133] or p['training']['maximum_updates']!=3000 or p['training']['lr']!=.0001:raise ValueError('Scope changed')
    return a,p
def counts_equal(a,b):
    if set(a['per_class'])!=set(b['per_class']):return False
    return all(a['metrics'][k]==b['metrics'][k] for k in COUNT_KEYS) and all(a['per_class'][c][k]==b['per_class'][c][k] for c in a['per_class'] for k in COUNT_KEYS if k!='unscored_predictions')
def inputs(t,require_approval=True):
    if require_approval:_,p=approval(t)
    else:
        p=read(t/'protocol.json')
        if sha(t/'protocol.json')!=PROTOCOL_SHA:raise ValueError('Proposed protocol changed')
    release=validate_draft(t/'release/candidate-manifest-v2.json',p['candidate_sha256'])
    pools=read(t/'sampling-pools.json');schedule=read(t/'sampling-plan.json')
    if sha(t/'sampling-pools.json')!=p['data']['pools_sha256'] or sha(t/'sampling-plan.json')!=p['data']['schedule_sha256']:raise ValueError('Sampler seal changed')
    train={r['image_id']:r for r in release['images'] if r['split']=='train'}
    expected=dict(billboard=sorted(i for i,r in train.items() if any(x['canonical_id']==133 for x in r['targets'])),explicit_negative=sorted(i for i,r in train.items() if r['scope'].get('133')=='absent'))
    if pools!=expected or len(pools['billboard'])!=20 or len(pools['explicit_negative'])!=35:raise ValueError('Pools changed or include unreviewed absence')
    rng=random.Random(171022);positive=[]
    while len(positive)<3000:
        cycle=list(pools['billboard']);rng.shuffle(cycle);positive.extend(cycle)
    rng=random.Random(171023);expected_schedule=[[positive[i],*rng.sample(pools['explicit_negative'],3)] for i in range(3000)]
    if schedule!=expected_schedule or any(set(batch)-set(train) or len(set(batch))!=4 for batch in schedule):raise ValueError('Sampling changed or escaped training partition')
    if sha(t/'inputs/selected-7805570.pt')!=p['starting_checkpoint']['sha256']:raise ValueError('Starting checkpoint changed')
    original=read(t/'inputs/validation-original.json');resume=read(t/'inputs/validation-resume.json')
    if not eligible(resume,original) or ranking(resume)<=ranking(original):raise ValueError('Pinned current baseline did not retain and improve original baseline')
    return release,schedule,original,resume
def activate(t):
    a,p=approval(t);release,_,_,_=inputs(t);out=t/'release/approved-core.json'
    expected=dict(release,approved_for_training=True,parent_candidate_sha256=p['candidate_sha256'],approval_sha256=sha(t/'approval.json'))
    if out.exists():
        if read(out)!=expected:raise ValueError('Existing activation differs from exact approved draft')
    else:
        with out.open('x',encoding='utf-8') as f:json.dump(expected,f,indent=2,allow_nan=False)
    return out
def stop_without_gain(step,best_step):return step==1500 and best_step==0
