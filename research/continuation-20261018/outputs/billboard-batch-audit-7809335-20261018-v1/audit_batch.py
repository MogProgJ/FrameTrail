"""Independent local result audit. No inference, optimizer, SSH or adoption."""
import argparse,hashlib,json,math,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
BATCH=HERE.parent/'billboard-batch-proposal-7805570-20261018-v1'
TOOLS=BATCH/'rf-billboard-batch-0a255598-v1'
sys.path.insert(0,str(TOOLS))
from continuation_guard import inputs,approval,counts_equal,read,sha,variant
from selection_policy import evaluate,eligible,ranking
from score_video_reference import score
from regression_stage import gate

def require(condition,message):
    if not condition:raise ValueError(message)
def save(p,value):
    with p.open('x',encoding='utf-8') as f:json.dump(value,f,indent=2,allow_nan=False)

def replay_validation(rows,records,original,resume):
    require(records and records[0]['step']==0,'Need step-zero validation')
    baseline=records[0];best=baseline;best_step=0;trace=[]
    for current in records:
        step=current['step'];rescored=evaluate(rows,current['predictions'])
        require(current['metrics']==rescored['metrics'] and current['per_class']==rescored['per_class'],f'Validation metrics differ on independent rescore at {step}')
        if step==0:require(counts_equal(current,resume) and eligible(current,original),'Starting validation differs from the pinned selected baseline')
        ok=eligible(current,baseline) and eligible(current,original)
        require(current['eligible']==ok,f'Eligibility differs at {step}')
        if ok and ranking(current)>ranking(best) and ranking(current)>ranking(original):best=current;best_step=step
        trace.append(dict(step=step,eligible=ok,ranking=list(ranking(current))))
    return best_step,best,trace

def tensor_check(reference,other,allow_active_change):
    import torch
    require(set(reference)==set(other),'Checkpoint state keys differ')
    allowed={'class_embed.weight','class_embed.bias'};inactive=[i for i in range(616) if i!=133];changed=[]
    for key,a in reference.items():
        b=other[key];require(a.shape==b.shape and a.dtype==b.dtype,'Tensor shape/dtype differs: '+key)
        if a.is_floating_point():require(bool(torch.isfinite(b).all()),'Nonfinite tensor: '+key)
        if not torch.equal(a,b):changed.append(key)
        if key in allowed:require(torch.equal(a[inactive],b[inactive]),'Inactive classifier rows changed: '+key)
        else:require(torch.equal(a,b),'Frozen model state changed: '+key)
    require(allow_active_change or not changed,'Step-zero selected checkpoint changed weights')
    return changed

def replay_regression(out,report):
    r=read(out/'known-regression.json');lock=read(out/'regression-lock.json')
    require(lock['best_checkpoint_sha256']==report['best_checkpoint_sha256']==r['best_checkpoint_sha256'],'Regression checkpoint identity differs')
    if not report['new_candidate_selected']:
        require(r['status']=='step-zero-unchanged-reuse-pinned-current-scores' and r['scored_new_images']==0 and r['retention_passed'] is True,'Wrong unchanged-model regression receipt')
        return dict(status='unchanged-model-current-scores-reused',passed=True,new_inference=False)
    predictions=read(out/'known-regression-predictions.json');images=read(TOOLS/'known-regression/images.json')
    require(set(predictions)==set(images),'Missing or extra known-regression image predictions')
    checks={}
    for path in sorted((TOOLS/'known-regression/references').glob('*.json')):
        ref=read(path);payload=dict(reference_sha256=ref['source_sha256'],class_namespace='native-canonical',vocabulary_sha256=ref['vocabulary_sha256'],confidence_threshold=.35,frames=[dict(frame_id=f['id'],detections=predictions[f['sha256']]) for f in ref['frames']])
        result=score(ref,payload,ref['source_sha256'])
        require(result==read(out/('known-scored-'+path.stem+'.json')),'Independent known-regression rescore differs: '+path.stem)
        checks[path.stem]={b:gate(read(TOOLS/'known-regression'/f'{b}-{path.stem}.json'),result) for b in ('original','current')}
    passed=all(c['passed'] for group in checks.values() for c in group.values())
    require(checks==r['checks'] and passed==r['retention_passed'],'Regression gate differs')
    return dict(status='six-known-references-independently-rescored',passed=passed,checks=checks,unique_images=len(predictions),fresh_independent_evidence=False)

def audit(retrieval,output):
    import torch
    torch.set_num_threads(2)
    approval(TOOLS)
    for rel,h in read(TOOLS/'package-files.json')['files'].items():require(sha(TOOLS/rel)==h,'Prepared package changed: '+rel)
    output.mkdir(exist_ok=False);summary=[];selection_complete=True
    reference=torch.load(TOOLS/'inputs/selected-7805570.pt',map_location='cpu',weights_only=True)['model_state_dict']
    for i in range(4):
        matches=list((retrieval/f'task-{i}').glob(f'verified-7809335_{i}/output/rf-billboard-batch-7809335_{i}'))
        require(len(matches)==1,'Need verified actual array output for task '+str(i));out=matches[0]
        verification=read(out.parents[2]/'verification-receipt.json')
        require(verification['actual_job_id']==f'7809335_{i}' and verification['output']==str(out),'Wrong structural verification identity')
        transfer=read(out/'transfer.json')
        if transfer['training_exit_code']!=0:
            summary.append(dict(index=i,status='failed-or-partial-training-preserved',training_exit=transfer['training_exit_code']));selection_complete=False;continue
        release,schedule,original,resume=inputs(TOOLS,task_index=i);rows=[r for r in release['images'] if r['split']=='val']
        pre=read(out/'preflight.json');report=read(out/'experiment-report.json');v=variant(TOOLS,i)
        require(pre['actual_job_id']==report['actual_job_id']==f'7809335_{i}' and pre['variant']==report['variant']==v,'Wrong task configuration')
        require(pre['approval_sha256']==sha(TOOLS/'approval.json') and pre['protocol_sha256']==sha(TOOLS/'protocol.json'),'Wrong approved protocol/approval')
        require(pre['candidate_sha256']==sha(TOOLS/'release/candidate-manifest-v2.json'),'Wrong training release')
        count=report['updates'];require(count in (1500,3000),'Wrong completion budget')
        require(read(out/'sampling-plan.json')==schedule,'Returned fixed sampler differs')
        for step in range(1,count+1):
            record=read(out/f'step-{step:04}.json')
            require(record['step']==step and record['train_ids']==schedule[step-1],'Step trace escaped schedule')
            require(all(math.isfinite(record[k]) for k in ('loss','gradient_norm')),'Nonfinite step trace')
        validations=[read(out/f'validation-{step:04}.json') for step in range(0,count+1,100)]
        best_step,best,trace=replay_validation(rows,validations,original,resume)
        require(best_step==report['best_step'] and report['new_candidate_selected']==(best_step>0),'Independent selected step differs')
        require((count==1500 and best_step==0) or (count==3000 and best_step>0),'Incorrect early-stop/max completion')
        tensors=[]
        for filename,step in [('best.pt',best_step),('last.pt',count)]:
            require(sha(out/filename)==report['best_checkpoint_sha256' if filename=='best.pt' else 'last_checkpoint_sha256'],'Returned checkpoint hash differs')
            ck=torch.load(out/filename,map_location='cpu',weights_only=True)
            require(ck['step']==step and ck['frametrail']==pre and ck['approved_for_application'] is False,'Wrong checkpoint provenance')
            changed=tensor_check(reference,ck['model_state_dict'],step>0)
            tensors.append(dict(file=filename,step=step,changed_state_keys=changed,frozen_features_boxes_and_inactive_rows_identical=True));del ck
        gradient=read(out/'gradient-probe.json');require(gradient['active_rows']==[133] and gradient['inactive_row_gradients_zero'] is True and gradient['only_main_classifier_gradients'] is True,'Wrong gradient scope')
        regression=replay_regression(out,report) if transfer['postprocessing_exit_code']==0 else dict(status='postprocessing-failed-local-followup-required',passed=None)
        item=dict(index=i,status='training-and-selection-independently-audited',selected_step=best_step,strict_gain=best_step>0,ranking=list(ranking(best)),checkpoint_sha256=report['best_checkpoint_sha256'],validation_records_rescored=len(validations),tensor_checks=tensors,known_regression=regression,trace=trace)
        save(output/f'task-{i}-audit.json',item);summary.append(item)
        print(f'Independent audit task {i}: selected step {best_step}; {len(validations)} validations rescored; frozen tensors verified',flush=True)
    candidates=[r for r in summary if r.get('strict_gain')]
    winner=max(candidates,key=lambda r:(tuple(r['ranking']),-r['index'])) if selection_complete and candidates else None
    receipt=dict(status='batch-independently-audited' if selection_complete else 'incomplete-batch-preserve-failures',actual_array_job_id='7809335',tasks=summary,validation_only_winner_index=winner['index'] if winner else None,validation_selected_winner_known_regression_passed=winner['known_regression']['passed'] if winner else None,regression_never_reselects=True,independent_fresh_test_available=False,strict_ONNX_hold_not_waived=True,production_adoption=False,training_updates=0,GPU_inference=False,new_cluster_jobs=0)
    save(output/'AUDIT.json',receipt)
    print(json.dumps({k:v for k,v in receipt.items() if k!='tasks'},indent=2))
if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--retrieval',type=Path,default=BATCH/'retrieval-7809335');ap.add_argument('--output',type=Path,default=HERE/'audited-results-v1');a=ap.parse_args();audit(a.retrieval,a.output)
