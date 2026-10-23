"""Verify recorded diagnostics and seal the read-only result and unapproved scope."""
import hashlib,json,math,random,shutil
from pathlib import Path
P=Path(__file__).resolve().parent
D=Path(r'C:\Users\nazee\Documents\Codex\2026-10-18\frametrail-continuation\outputs\training-signal-7780632-20261018-v1')
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):
    with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
inputs=read(P/'INPUT_INTEGRITY.json')['files'];assert all(sha(Path(i['path']))==i['sha256'] for i in inputs)
d=read(P/'DIAGNOSTIC.json');assert len(d['records'])==24 and d['optimizer_updates']==0 and not d['optimizer_created']
assert all(s['model_state_before']==s['model_state_after'] for s in d['state_checks'])
matches=0
for r in d['records']:
    assert r['row_gradient_reconstruction_max_error']<1e-5 and r['bias_gradient_reconstruction_max_error']<1e-5
    assert abs(r['weighted_total']-r['trainable_weighted_classification']-r['constant_weighted_loss'])<2e-5
    for stage in r['stages']:
        assert stage['normalizer']==max(r['targets'],1)
        assert stage['classification_trainable']==(stage['stage']!='encoder')
        for m in stage['matches']:
            expected=max(m['probability']**.25*m['iou']**.75,.01)
            assert abs(expected-m['soft_target'])<1e-6
            if m['actual_weighted_logit_gradient'] is not None:
                assert abs(m['actual_weighted_logit_gradient']-2*(m['probability']-m['soft_target'])/stage['normalizer'])<1e-5
            matches+=1
p=read(P/'proposed-protocol.json');identity=read(P/'PROPOSAL_IDENTITY.json')
assert p['experiment_approved'] is False and identity['status']=='not-approved'
assert sha(P/'proposed-protocol.json')==identity['protocol_sha256']
assert sha(P/'proposed-sampling-plan.json')==p['data']['schedule_sha256']
assert sha(P/'proposed-sampling-pools.json')==p['data']['pools_sha256']
pools=read(P/'proposed-sampling-pools.json');schedule=read(P/'proposed-sampling-plan.json')
def stream(ids,n,seed):
    rng=random.Random(seed);result=[]
    while len(result)<n:
        cycle=list(ids);rng.shuffle(cycle);result.extend(cycle)
    return result[:n]
bill=stream(pools['billboard'],2000,171019);wash=stream(pools['washing_machine'],2000,171020);negative=stream(pools['explicit_negative_for_both'],4000,171021)
assert schedule==[[bill[i],wash[i],negative[2*i],negative[2*i+1]] for i in range(2000)]
receipt=dict(status='complete-sealed-training-signal-diagnostic',job='7780632',photos=12,checkpoint_photo_backward_checks=24,
    matched_target_soft_score_and_gradient_checks=matches,input_files_rehashed=len(inputs),input_changes=0,
    optimizer_created=False,optimizer_updates=0,model_parameters_and_buffers_unchanged=True,validation_used=False,heldout_used=False,app_changed=False,
    proposal_sampler_reproduced=True,proposal_approved=False,GPU_job_submitted=False,training_runner_created=False,
    proposal_protocol_sha256=identity['protocol_sha256'])
(P/'FINAL_RECEIPT.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')
(P/'USE.txt').write_text('Read REPORT.md for the completed CPU loss/gradient check.\nPROPOSAL.md describes a separate proposed GPU continuation; it is not approved or submitted.\nThe proposed sampler is an unexecuted plan, not a training record. No model weights are included.\nPreserve this sealed evidence. Reproduction requires copying diagnostic scripts into a fresh work folder with the pinned local runtime and original input files.\n',encoding='utf-8')
assert not D.exists(),'Refusing to overwrite a published version'
D.mkdir(parents=True)
for source in P.iterdir():
    if source.is_file():shutil.copy2(source,D/source.name)
files=[dict(file=x.relative_to(D).as_posix(),bytes=x.stat().st_size,sha256=sha(x)) for x in sorted(D.rglob('*')) if x.is_file()]
(D/'files-sha256.json').write_text(json.dumps(files,indent=2)+'\n',encoding='utf-8')
assert all(sha(D/f['file'])==f['sha256'] for f in files)
print(json.dumps(dict(status='published-and-verified',output=str(D),files=len(files),receipt=receipt),indent=2))
