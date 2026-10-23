"""Build a reviewable, unapproved selector experiment. No SSH or submission."""
import hashlib,json,random,shutil
from pathlib import Path
HERE=Path(__file__).resolve().parent
OUT=HERE.parent
OLD=OUT/'billboard-batch-proposal-7805570-20261018-v1'
SOURCE=OLD/'rf-billboard-batch-0a255598-v1'
P=OUT/'selector-batch-proposal-7809335-20261018-v1'
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):
    with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def save(p,v):
    p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('x',encoding='utf-8',newline='\n') as f:f.write(v if isinstance(v,str) else json.dumps(v,indent=2,allow_nan=False)+'\n')
def main():
    P.mkdir(exist_ok=False)
    pools=read(SOURCE/'sampling-pools.json')
    review=OUT/'frozen-head-cpu-7809335-20261018-v1/reviewed-contrast/REGION_REVIEW.json'
    roi=read(review);pools['reviewed_region']=sorted(r['image_id'] for r in roi['regions'])
    def cycle(ids,seed):
        rng=random.Random(seed);result=[]
        while len(result)<3000:
            c=list(ids);rng.shuffle(c);result+=c
        return result[:3000]
    pos=cycle(pools['billboard'],171022);regions=cycle(pools['reviewed_region'],171024);rng=random.Random(171023)
    schedule=[[pos[i],*rng.sample(pools['explicit_negative'],2),regions[i]] for i in range(3000)]
    schedule_bytes=(json.dumps(schedule,indent=2)+'\n').encode();pool_bytes=(json.dumps(pools,indent=2)+'\n').encode()
    protocol=read(OLD/'protocol.json')
    protocol.update(status='selector-four-trial-proposal-awaiting-new-exact-cluster-approval',experiment_approved=False,previous_completed_array='7809335',active_classifier_heads=['class_embed','transformer.enc_out_class_embed.0'],active_classifier_rows=[133],frozen_components=['all backbone, transformer encoder/decoder and box-regressor parameters and buffers','all classifier rows except billboard row133 in the two specified heads'],parameter_invariance='Bitwise equality outside the two active rows. Changed proposal selection CAN change decoder features, box outputs and other detections; both-baseline retention remains mandatory.',scope='four-selector-trials-two-row133-heads-region-overlay-array0-3-percent2-max3000-45min-known-regression')
    protocol['data'].update(pools_sha256=hashlib.sha256(pool_bytes).hexdigest(),no_labels_or_scopes_changed=False,original_manifest_labels_and_scopes_unchanged=True,separate_training_region_overlay=dict(path='region-review.json',sha256=sha(review),photos=8,independent_human_review=False,supervision='Assistant-reviewed regulatory sign panels, billboard-negative queries at IoU>=.7 ONLY inside each panel; all outside scope remains unchanged/unknown'),sampled_training_photos=63)
    protocol['training'].update(lr='main row .0001; encoder row .00001 or .00003',accumulation=4,maximum_presentations=48000,per_update='1 billboard-positive +2 distinct explicitly absent +1 reviewed sign-region photo',sampling_seeds=[171022,171023,171024],model_mode='eval; main and encoder proposal billboard rows trainable',objective='Original scoped Hungarian IA-BCE main/aux/selected-encoder loss, plus dense encoder billboard IA-BCE weight1 on full proposal grid. One-to-one geometry Hungarian IoU>=.5 positives; absent/complete all-query negatives, unknown only positive matches/reviewed IoU>=.7 sign queries. Region penalty1 or3 on main/aux/selected and dense encoder classification.',dense_quality_target='Detached p^.25*IoU^.75, minimum.01, positive query matched by geometry only; dense coefficient2/max(1,billboard targets).',gradient_clip='Joint L2 norm .1 across both active head parameter groups')
    protocol['batch']['maximum_total_presentations']=48000
    protocol['variants']=[]
    for i,(lr,rw) in enumerate([(1e-5,1),(1e-5,3),(3e-5,1),(3e-5,3)]):
        protocol['variants'].append(dict(index=i,name=f'enc{lr:g}-region{rw}',main_lr=.0001,encoder_lr=lr,region_weight=rw,negative_presentations=2,accumulation=4,maximum_updates=3000,schedule_file=f'schedules/task-{i}.json',schedule_sha256=hashlib.sha256(schedule_bytes).hexdigest()))
    protocol['limits']=['Development references are consumed, and repeated local comparisons add selection pressure; no fresh generalization claim.','Proposal coverage52/54 versus36/54 selected is training geometry evidence, not an accuracy guarantee.','Only two billboard classifier rows may update. Frozen regressor parameters do not imply unchanged box outputs.','Eight assistant-reviewed TRAIN sign panels add region-only negatives; original release scopes and labels remain preserved.','The existing ONNX numerical hold remains; production adoption is false.']
    protocol['strict_gain_definition']='Eligible validation ranking must strictly beat current baseline; earlier checkpoint/lower array index wins exact ties. Any class can change through proposal selection, and each must pass both baselines.'
    protocol['rationale']='Two encoder learning rates by two region penalties; frozen-selector controls run locally from exact cached features. Four GPU trials isolate this new proposal mechanism without repeating cacheable controls. Additional grid points would add selection pressure before showing this mechanism works.'
    protocol['execution_package_status']='Prepared locally, no approval, archive, SSH or submission'
    protocol['selection']['across_variants']='After all four tasks terminal/audited select by predeclared validation ranking only, strict gain required, ties lower index. Known regression may veto adoption but never reselect. Failures preserved, no replacements.'
    protocol['local_controls']={'path':'local-evidence/CPU_CONTROLS_RECEIPT.json','roles':'Two main-head-only frozen-selector controls at region weights1/3, up to1500CPU updates. Dense encoder constant omitted because it has no main-head gradient.'}
    protocol['extra_guard']='Step0 must reproduce pinned current counts and retain original; all original per-class guards and aggregate unscored+5 against BOTH baselines retained.'
    protocol_bytes=(json.dumps(protocol,indent=2)+'\n').encode();digest=hashlib.sha256(protocol_bytes).hexdigest();name=f'rf-selector-{digest[:8]}-v1';T=P/name;T.mkdir()
    for rel,h in read(SOURCE/'package-files.json')['files'].items():
        if rel in ('protocol.json','sampling-pools.json','continuation_guard.py','train_balanced.py','package-files.json') or rel.startswith('schedules/'):continue
        assert sha(SOURCE/rel)==h,rel
        dest=T/rel;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(SOURCE/rel,dest)
    save(T/'protocol.json',protocol_bytes.decode());save(P/'protocol.json',protocol_bytes.decode());save(T/'sampling-pools.json',pool_bytes.decode());shutil.copy2(review,T/'region-review.json')
    for i in range(4):save(T/f'schedules/task-{i}.json',schedule_bytes.decode())
    shutil.copy2(HERE/'selector_mechanics.py',T/'selector_mechanics.py')
    for src,dst in [(HERE/'MECHANICS_RECEIPT.json','MECHANICS_RECEIPT.json'),(HERE/'CPU_CONTROLS_RECEIPT.json','CPU_CONTROLS_RECEIPT.json'),(OUT/'frozen-head-cpu-7809335-20261018-v1/PROPOSAL_COVERAGE.json','PROPOSAL_COVERAGE.json')]:
        if not src.exists():continue # preparation remains unsealed until controls finish
        dest=T/'local-evidence'/dst;dest.parent.mkdir(exist_ok=True);shutil.copy2(src,dest)
    for src,dst in [('guard_template.py','continuation_guard.py'),('trainer_template.py','train_balanced.py')]:
        save(T/dst,(HERE/src).read_text().replace('@@PROTOCOL_SHA@@',digest).replace('@@SCOPE@@',protocol['scope']))
    for filename in ('submit.sh','show-output.sh','run-array.sbatch','bundle_results.py','regression_stage.py'):
        path=T/filename;text=path.read_text().replace('rf-billboard-batch-0a255598-v1',name).replace('rf-billboard-batch','rf-selector')
        if filename=='show-output.sh':text=text.replace('echo "FRAMETRAIL_TASK_ARCHIVE=', 'printf \'\\n\'; echo "FRAMETRAIL_TASK_ARCHIVE=')
        path.write_text(text,encoding='utf-8',newline='\n')
    for filename in ('Invoke-KitScript.ps1','Launch-Approved-Run.ps1','Check-Run.ps1','Retrieve-Results.ps1','prepare_archive.py','bootstrap-template.sh','verify_results.py','compare_batch.py'):
        text=(OLD/filename).read_text().replace('rf-billboard-batch-0a255598-v1',name).replace('rf-billboard-batch','rf-selector').replace('0a255598b74eb1d29d83ee1be10d517ae407fbda2c57e4565b51028d615343fd',digest)
        if filename=='Retrieve-Results.ps1':
            text=text.replace("'C:/Users/nazee/Documents/Codex/2026-10-18/frametrail-continuation/outputs/billboard-batch-audit-7809335-20261018-v1/audit_batch.py'","(Join-Path $PSScriptRoot 'audit_batch.py')")
        if filename=='verify_results.py':text=text.replace("report['frozen_features_and_boxes_unchanged']","report['frozen_parameters_and_buffers_unchanged']")
        save(P/filename,text)
    text=(OUT/'billboard-batch-audit-7809335-20261018-v1/audit_batch.py').read_text()
    text=text.replace("BATCH=HERE.parent/'billboard-batch-proposal-7805570-20261018-v1'","BATCH=HERE").replace("TOOLS=BATCH/'rf-billboard-batch-0a255598-v1'",f"TOOLS=BATCH/'{name}'")
    text=text.replace("allowed={'class_embed.weight','class_embed.bias'}","allowed={'class_embed.weight','class_embed.bias','transformer.enc_out_class_embed.0.weight','transformer.enc_out_class_embed.0.bias'}")
    text=text.replace("f'verified-7809335_{i}/output/rf-billboard-batch-7809335_{i}'","f'verified-{job}_{i}/output/rf-selector-{job}_{i}'").replace("f'7809335_{i}'","f'{job}_{i}'")
    text=text.replace("output.mkdir(exist_ok=False);summary=[];selection_complete=True","job=retrieval.name.removeprefix('retrieval-');require(job.isdigit(),'Numeric actual array ID required');output.mkdir(exist_ok=False);summary=[];selection_complete=True")
    text=text.replace("gradient['only_main_classifier_gradients']","gradient['only_two_billboard_head_gradients']").replace("frozen_features_boxes_and_inactive_rows_identical=True","frozen_parameters_buffers_and_inactive_rows_identical=True").replace("actual_array_job_id='7809335'","actual_array_job_id=job")
    text=text.replace("default=BATCH/'retrieval-7809335'","required=True").replace("default=HERE/'audited-results-v1'","required=True")
    save(P/'audit_batch.py',text)
    save(P/'PROPOSAL_IDENTITY.json',dict(package_directory=name,protocol_sha256=digest,scope=protocol['scope'],approved=False,cluster_submitted=False))
    print(json.dumps(dict(proposal=str(P),package=name,protocol_sha256=digest)))
if __name__=='__main__':main()
