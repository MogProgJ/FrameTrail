"""Summarize the frozen comparison and preserve a handoff; no inference."""
from pathlib import Path
import hashlib,json
HERE=Path(__file__).resolve().parent
def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def sha(p):
    with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def save(name,data):
    with (HERE/name).open('x',encoding='utf-8') as f:json.dump(data,f,indent=2,allow_nan=False)
def hits(m):return m['complete_tp']+m['partial_positive_hits']
def small(m):return {k:m[k] for k in ['complete_tp','complete_fp','complete_fn','partial_positive_hits','partial_positive_misses','unscored_predictions']}

c=read(HERE/'comparison.json');lock=read(HERE/'evaluation-lock.json')
assert c['evaluation_lock_sha256']==sha(HERE/'evaluation-lock.json')
roles=['original_baseline','continuation_baseline','candidate'];labels=list(lock['references'])
results={role:{label:read(HERE/role/label/'scoped-results.json') for label in labels} for role in roles}
changes=[];frames=[]
for baseline in roles[:2]:
    for label in labels:
        b=results[baseline][label];s=results['candidate'][label];ref=read(HERE/'references'/f'{label}.json')
        sources={f['id']:f for f in ref['frames']}
        zero=dict(complete_tp=0,complete_fp=0,complete_fn=0,partial_positive_hits=0,partial_positive_misses=0,unscored_predictions=0)
        for name in sorted(set(b['by_class'])|set(s['by_class'])):
            before=b['by_class'].get(name,zero);after=s['by_class'].get(name,zero)
            if small(before)!=small(after):changes.append(dict(baseline=baseline,reference=label,category=name,before=small(before),candidate=small(after)))
        before_frames={f['frame_id']:f for f in b['frames']}
        for f in s['frames']:
            prior=before_frames[f['frame_id']]
            if prior['counts']!=f['counts']:
                frames.append(dict(baseline=baseline,reference=label,frame_id=f['frame_id'],source=sources[f['frame_id']],baseline_outcomes=prior,candidate_outcomes=f))
save('class-differences.json',changes);save('frame-differences.json',frames)
lines=['# Held-out evaluation: job 7805570, selected step 100','',
    '**Decision: '+c['decision']+'.**','',
    'The checkpoint selected on validation was frozen before these measurements. Both pinned baselines were evaluated with the same fixed preprocessing, decoder, thresholds, and source references. No other checkpoint was considered after scoring.','',
    '## Primary held-out evidence','',
    '| Reference | Model | Complete TP / FP / FN | Partial known hits / targets | Unscored predictions |',
    '|---|---|---:|---:|---:|']
for label in ['heldout_photos','reserved_video']:
    for role in roles:
        m=c['metrics'][role][label]
        lines.append(f'| {label} | {role} | {m["complete_tp"]} / {m["complete_fp"]} / {m["complete_fn"]} | {m["partial_positive_hits"]} / {m["partial_positive_hits"]+m["partial_positive_misses"]} | {m["unscored_predictions"]} |')
lines+=['','Complete-scope FP counts apply only where completeness or absence was explicitly reviewed. Partial known-positive recall does not establish precision. Unknown predictions are unscored, not false positives.','',
    '## Priority classes on the 130 held-out photos','',
    '| Class | Original baseline hits / targets | Continuation baseline hits / targets | Candidate hits / targets |',
    '|---|---:|---:|---:|']
priority=[]
for name in ['cat','dog','billboard','washing machine']:
    values=[];row=dict(category=name)
    for role in roles:
        m=results[role]['heldout_photos']['by_class'].get(name,{})
        known=m.get('complete_tp',0)+m.get('partial_positive_hits',0)
        targets=known+m.get('complete_fn',0)+m.get('partial_positive_misses',0)
        values.append(f'{known} / {targets}');row[role]=dict(hits=known,targets=targets,complete_fp=m.get('complete_fp',0))
    lines.append('| '+name+' | '+' | '.join(values)+' |');priority.append(row)
lines+=['','The washing-machine denominator is 15 known targets in seven held-out photos; the billboard denominator is 19 known targets in five photos. Their positive photo scopes are partial, so these hit rates cannot establish class precision. Each class also has seven explicitly absent photo scopes. The reserved video contains no positive cats, dogs, billboards, or washing machines; it checks absence and other-class retention, not positive video recall for these four classes. Billboard and washing-machine absence is established on 20 of its 24 frames. REFERENCE_COVERAGE.json records the exact coverage.','',
    '## Retention decision','']
failures=[]
for baseline,sets in c['retention_gates'].items():
    lines.append(f'Against **{baseline}**:')
    lines.append('')
    for label,g in sets.items():
        lines.append(f'- {label}: '+('PASS' if g['passed'] else 'FAIL'))
        for f in g['failures']:
            failures.append(dict(baseline=baseline,reference=label,**f))
            lines.append(f'  - {f["category"]}, {f["metric"]}: {f["baseline"]} → {f["candidate"]}.')
    lines.append('')
for baseline,g in c['heldout_strict_gain'].items():
    lines.append(f'Primary known-positive hits versus {baseline}: **{g["baseline"]} → {g["candidate"]}**; strict gain '+('PASS' if g['strict_gain'] else 'FAIL')+'.')
    lines.append('')
lines+=['## Older regression evidence','',
    '| Reference | Original TP / FP / FN; partial hits | Continuation TP / FP / FN; partial hits | Candidate TP / FP / FN; partial hits |',
    '|---|---:|---:|---:|']
for label in ['internal_regression','old_video','recent_video','scale_video']:
    values=[]
    for role in roles:
        m=c['metrics'][role][label];values.append(f'{m["complete_tp"]} / {m["complete_fp"]} / {m["complete_fn"]}; {m["partial_positive_hits"]}')
    lines.append('| '+label+' | '+' | '.join(values)+' |')
lines+=['','The eight internal regression photos overlap the 130-photo set and are reported as a separate regression view, not additional independent evidence or additional primary hits.','',
    '## Verification and limits','',
    '- Six scoring contracts passed before inference.',
    '- 202 unique images × three fixed checkpoints = 606 full CPU inference records. Duplicate image bytes reused only within the same model identity.',
    '- All original input hashes were preserved. Complete model-state fingerprints were unchanged by inference for all three models.',
    '- PyTorch 2.8.0 CPU, RF-DETR 1.11.2, FP32/math attention, two CPU threads, 512×512 normalized RGB; confidence 0.35, NMS IoU 0.45, match IoU 0.5, top 300 query/class pairs, maximum 100 detections.',
    '- No optimizer updates, new GPU job, checkpoint or threshold reselection, model export, or application adoption.',
    '- Small purposive, assistant-reviewed evidence without independent human recheck. No representative overall accuracy, statistical significance, tracking accuracy, full-vocabulary AP, or source/pretraining independence claim.',
    '- The reserved photos and frames are now consumed evidence. Keep them fixed as regression references; do not call them fresh in future cycles.','',
    'Selected checkpoint SHA-256: `'+c['selected_checkpoint_sha256']+'`.','',
    'Evaluation lock SHA-256: `'+c['evaluation_lock_sha256']+'`.','',
    'Detailed per-class movements are in class-differences.json; changed-frame evidence and source paths are in frame-differences.json.','',
    '## Next step','']
if c['evidence_gate_passed']:
    nextstep='Prepare the separate export, numerical parity, and native runtime performance checks for this exact frozen checkpoint; passing held-out evidence does not by itself approve app adoption.'
else:
    nextstep='Hold this candidate and perform a bounded training-only review of the implicated classes and explicit negatives before proposing another experiment. Preserve the frozen evaluation outcome; do not reselect a checkpoint or tune thresholds using it.'
lines += [nextstep,'']
(HERE/'REPORT.md').write_text('\n'.join(lines),encoding='utf-8',newline='\n')
save('FINAL_RECEIPT.json',dict(status=c['status'],decision=c['decision'],job='7805570',selected_step=100,
    priority_photo_results=priority,gate_failures=failures,heldout_strict_gain=c['heldout_strict_gain'],
    verified_inputs_unchanged=True,scoring_contracts_passed=6,forward_records=606,training_updates=0,new_GPU_jobs=0,
    checkpoint_reselected=False,thresholds_changed=False,model_exported=False,approved_for_application=False,
    comparison_sha256=sha(HERE/'comparison.json'),report_sha256=sha(HERE/'REPORT.md')))
save('CONTINUATION_STATE.json',dict(project='FrameTrail',actual_job_id='7805570',status=c['status'],decision=c['decision'],
    selected_checkpoint_sha256=c['selected_checkpoint_sha256'],heldout_evaluated=True,heldout_consumed=True,
    report=str(HERE/'REPORT.md'),comparison=str(HERE/'comparison.json'),next_step=nextstep,
    approved_for_application=False,communication_preference='End every user-facing FrameTrail response with the single best concrete next step and briefly why; continue authorized work autonomously.'))
save('files-sha256.json',{str(p.relative_to(HERE)):sha(p) for p in HERE.rglob('*') if p.is_file()})
print(json.dumps(dict(decision=c['decision'],priority=priority,failures=failures,next_step=nextstep),indent=2))
