"""Replay all saved detections through the pinned scorer, without model inference."""
import hashlib,json,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
OLD=Path(r'C:\Users\nazee\.codex\visualizations\2026\10\11\01a12a01-d564-7de0-91f4-a16484eea2cb')
sys.dont_write_bytecode=True;sys.path.insert(0,str(OLD))
import score_video_reference as scorer
def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def sha(p):
    with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
lock=read(HERE/'evaluation-lock.json');result=read(HERE/'comparison.json');locksha=sha(HERE/'evaluation-lock.json')
assert locksha==result['evaluation_lock_sha256']
for p,h in {**lock['input_hashes'],**lock['scoring_modules']}.items():assert sha(p)==h
checked=0;sets={}
for role,ck in lock['checkpoints'].items():
    predictions={}
    for digest in lock['images']:
        r=read(HERE/role/'images'/f'{digest}.json');checked+=1
        assert r['image_sha256']==digest and r['identity']['checkpoint_sha256']==ck['sha256']
        assert r['identity']['evaluation_lock_sha256']==locksha and r['identity']['role']==role
        predictions[digest]=r['detections']
    sets[role]={}
    for label,source in lock['references'].items():
        refpath=HERE/'references'/f'{label}.json';assert sha(refpath)==source['adapter_sha256']
        ref=read(refpath);payload=read(HERE/role/label/'predictions.json')
        assert payload['frames']==[dict(frame_id=f['id'],detections=predictions[f['sha256']]) for f in ref['frames']]
        rescored=scorer.score(ref,payload,source['sha256']);saved=read(HERE/role/label/'scoped-results.json')
        for key in ['aggregate','by_class','by_sequence','frames']:assert rescored[key]==saved[key]
        assert rescored['aggregate']==result['metrics'][role][label]
        sets[role][label]=rescored
assert checked==result['total_forward_records']==606
retained=True;strict=True
for baseline in ['original_baseline','continuation_baseline']:
    for label in lock['references']:
        b=sets[baseline][label]['by_class'];c=sets['candidate'][label]['by_class'];fail=[]
        for name in sorted(set(b)|set(c)):
            for key in ['complete_tp','partial_positive_hits','complete_fp']:
                before=b.get(name,{}).get(key,0);after=c.get(name,{}).get(key,0)
                if (key=='complete_fp' and after>before) or (key!='complete_fp' and after<before):
                    fail.append(dict(category=name,metric=key,baseline=before,candidate=after))
        assert result['retention_gates'][baseline][label]==dict(passed=not fail,failures=fail)
        retained=retained and not fail
    def hits(role):return sum(sets[role][label]['aggregate']['complete_tp']+sets[role][label]['aggregate']['partial_positive_hits'] for label in lock['useful_gain_sets'])
    before,after=hits(baseline),hits('candidate')
    assert result['heldout_strict_gain'][baseline]==dict(baseline=before,candidate=after,strict_gain=after>before)
    strict=strict and after>before
assert result['evidence_gate_passed']==bool(retained and strict)
assert result['training_updates']==0 and result['new_GPU_jobs']==0 and result['approved_for_application'] is False
validation=dict(status='all-saved-evidence-replayed-and-verified',inference_records_checked=checked,
    scoped_reports_recomputed=18,retention_and_gain_gates_recomputed=True,input_hashes_unchanged=True,
    original_scoring_modules_unchanged=True,comparison_sha256=sha(HERE/'comparison.json'),
    evaluation_lock_sha256=locksha,scoring_contracts_passed=6,new_inference_calls=0)
with (HERE/'VALIDATION_RECEIPT.json').open('x',encoding='utf-8') as f:json.dump(validation,f,indent=2)
print(json.dumps(validation,indent=2))
