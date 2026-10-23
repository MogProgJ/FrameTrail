"""Shared exact-scope, archive, patch and qualification guards. No submission on import."""
import hashlib,json,re,tarfile
from pathlib import Path,PurePosixPath

CHECKPOINT='c1e7b571476a9bdc02533359dfe3f599afab98822aa90df265e9068f43f46bd3'
OLD_RELEASE='e43a2c7a415c4f82209a1fc2471d8677503f51315e71f422ec0d6665eac377b9'
KEYS=('class_embed.weight','class_embed.bias','transformer.enc_out_class_embed.0.weight','transformer.enc_out_class_embed.0.bias')
STEPS=(0,100,250,500,1000,1500)
def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def sha(p):
    with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def write(p,v):
    with Path(p).open('x',encoding='utf-8',newline='\n') as f:f.write(json.dumps(v,indent=2,allow_nan=False)+'\n')
def contained(base,name):
    relative=PurePosixPath(name)
    if relative.is_absolute() or '..' in relative.parts or '\\' in name or ':' in name:raise ValueError('Uncontained path')
    path=Path(base).joinpath(*relative.parts).resolve()
    if not path.is_relative_to(Path(base).resolve()):raise ValueError('Escaped path')
    return path
def verify_files(base,seal_name='package-files.json'):
    records=read(Path(base)/seal_name)
    for name,digest in records.items():
        p=contained(base,name)
        if p.is_symlink() or not p.is_file() or sha(p)!=digest:raise ValueError('Sealed file differs: '+name)
    return records
def validate_scope(s):
    exact=dict(method='M1-main-and-encoder-row133',seeds=[17,29],max_updates=1500,main_lr=.0001,encoder_lr=.00003,
      dense_encoder_weight=1,weight_decay=0,clip=.1,AMP=False,active_seconds=1800,finalization_seconds=480,
      array='0-1%2',cpus=2,memory_gib=8,wall_minutes=45,max_allocated_gpu_hours=1.5,
      validation_steps=list(STEPS),starting_checkpoint_sha256=CHECKPOINT,retries=0,test_photos_used_on_cluster=0)
    if any(s.get(k)!=v for k,v in exact.items()):raise ValueError('Changed exact experiment scope')
    if s.get('scoring_device')!='local-pinned-Torch-2.8.0+cpu' or s.get('production_adoption') is not False:raise ValueError('Scoring/adoption scope')
    return s
def validate_inputs(records,schedules):
    ids={r['image_id']:r for r in records}
    if len(ids)!=291:raise ValueError('Input identity/count differs')
    counts={k:sum(r['pool']==k for r in records) for k in ('fresh_positive','old_positive','fresh_absent','old_absent','fresh_validation','old_validation')}
    if list(counts.values())!=[30,17,30,47,32,135]:raise ValueError('Frozen pools differ')
    for r in records:
        role='val' if r['pool'].endswith('validation') else 'train'
        if r['row']['split']!=role or r['row']['image_id']!=r['image_id']:raise ValueError('Role/identity changed')
    for schedule in schedules:
        if len(schedule)!=1500:raise ValueError('Schedule length')
        for batch in schedule:
            if len(batch)!=4 or len(set(batch))!=4:raise ValueError('Four distinct TRAIN photos required')
            if [ids[i]['pool'] for i in batch]!=['fresh_positive','old_positive','fresh_absent','old_absent']:raise ValueError('TRAIN-only four slots changed')
    return ids
def tensor_digest(v):return hashlib.sha256(v.detach().cpu().contiguous().numpy().tobytes()).hexdigest()
def frozen_digest(state):
    h=hashlib.sha256()
    for k,v in sorted(state.items()):
        h.update(k.encode());a=v.detach().cpu()
        if k in KEYS:a=a[[i for i in range(616) if i!=133]]
        h.update(a.contiguous().numpy().tobytes())
    return h.hexdigest()
def make_patch(state,meta):return dict(metadata=meta,rows={k:state[k][133].detach().cpu().clone() for k in KEYS})
def check_patch(patch,scope_sha,seed,step,job=None):
    import torch
    m=patch['metadata'];rows=patch['rows']
    if set(rows)!=set(KEYS):raise ValueError('Patch keys may only contain two row133 heads')
    if (m.get('scope_sha256'),m.get('seed'),m.get('step'),m.get('starting_checkpoint_sha256'))!=(scope_sha,seed,step,CHECKPOINT):raise ValueError('Patch identity differs')
    if job is not None and m.get('actual_job_id')!=job:raise ValueError('Patch job differs')
    for k,v in rows.items():
        if v.dtype!=torch.float32 or tuple(v.shape)!=((256,) if k.endswith('weight') else ()) or not bool(torch.isfinite(v).all()):raise ValueError('Patch shape/dtype/finiteness')
    return m
def apply_patch_rows(model,patch):
    import torch
    with torch.no_grad():
        state=model.state_dict()
        for k,v in patch['rows'].items():state[k][133].copy_(v)
def qualification(old,fresh,original,current,start):
    from selection_policy import eligible
    retained=eligible(old,original) and eligible(old,current)
    cap=old['metrics']['unscored_predictions']<=530
    gain=fresh['complete_tp']-start['complete_tp'];extra=fresh['complete_fp']-start['complete_fp']
    return dict(retention_both_baselines=retained,original_unknown_cap_passed=cap,gain_hits=gain,extra_fp=extra,
                qualifies=retained and cap and gain>=3 and extra<=0)
def rank(item):
    f=item['fresh'];return (f['complete_f1'],f['complete_tp'],-f['complete_fp'],-item['step'],-item['index'])
def choose(conditions):
    eligible_methods=[]
    for method in ('M0','M1'):
        group=[c for c in conditions if c['method']==method]
        if len(group)==2 and {c['seed'] for c in group}=={17,29} and all(c['complete'] and c.get('best') for c in group):
            eligible_methods.extend(c['best'] for c in group)
    return max(eligible_methods,key=rank) if eligible_methods else None
def safe_extract(archive,destination,expected_sha=None,max_bytes=20_000_000):
    if expected_sha is not None and sha(archive)!=expected_sha:raise ValueError('Archive SHA differs')
    destination=Path(destination)
    if destination.exists():raise ValueError('Preserve existing extraction; no overwrite')
    with tarfile.open(archive,'r:gz') as tf:
        members=tf.getmembers();seen=set();total=0
        for m in members:
            contained(destination,m.name)
            if not m.isfile() or m.name in seen:raise ValueError('Only unique regular archive members accepted')
            seen.add(m.name);total+=m.size
            if total>max_bytes:raise ValueError('Archive exceeds bounded bytes')
        destination.mkdir(parents=True)
        for m in members:
            p=contained(destination,m.name);p.parent.mkdir(parents=True,exist_ok=True)
            with tf.extractfile(m) as src,p.open('xb') as dst:
                import shutil
                shutil.copyfileobj(src,dst)
    return destination
def valid_job(job):
    if not re.fullmatch(r'[1-9][0-9]*',job):raise ValueError('Numeric actual array job required')
    return job
