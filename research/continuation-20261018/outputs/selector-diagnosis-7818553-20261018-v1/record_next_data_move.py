"""Finish local audits and preserve the exact next CPU collection handoff."""
import ast,hashlib,json,shutil,sys
from pathlib import Path
D=Path(__file__).resolve().parent;OUT=D.parent;P=OUT/'billboard-data-refresh-7818553-20261018-v1';B=OUT/'selector-batch-proposal-7809335-20261018-v1';T=B/'rf-selector-a77d9663-v1';R=B/'retrieval-7818553'
sys.path.insert(0,str(T))
from selection_policy import evaluate,eligible,ranking
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,v):
    with p.open('x',encoding='utf-8',newline='\n') as f:f.write(v if isinstance(v,str) else json.dumps(v,indent=2)+'\n')
def main():
    assert read(R/'independent-audit/AUDIT.json')['status']=='batch-independently-audited'
    result=read(D/'local-contrast/RECEIPT.json');assert result['selected_index'] is None
    rows=[r for r in read(T/'release/candidate-manifest-v2.json')['images'] if r['split']=='val'];original=read(T/'inputs/validation-original.json');current=read(T/'inputs/validation-resume.json');audited=[]
    for record in result['trials']:
        i=record['index'];v=read(D/f'local-contrast/validation-{i}.json');rescored=evaluate(rows,v['predictions']);assert v['metrics']==rescored['metrics'] and v['per_class']==rescored['per_class'];ok=eligible(rescored,current) and eligible(rescored,original);assert record['eligible']==ok and not ok
        audited.append(dict(index=i,metrics_independently_rescored=True,eligible=False,strict_gain=False,ranking=list(ranking(rescored))))
    save(D/'LOCAL_CONTRAST_AUDIT.json',dict(status='four-local-contrast-predictions-rescored-gates-replayed',trials=audited,original_selection_policy_unchanged=True,new_GPU_jobs=0))
    ar=read(P/'archive-receipt.json');assert sha(P/ar['archive'])==ar['archive_sha256'] and sha(P/ar['cluster_start_script'])==ar['cluster_start_script_sha256']
    for rel,h in read(P/'data-tools-v1/package-files.json')['files'].items():assert sha(P/'data-tools-v1'/rel)==h,rel
    for path in list((P/'data-tools-v1').glob('*.py'))+list(P.glob('*.py')):ast.parse(path.read_text(encoding='utf-8-sig'))
    assert 'Ran 9 tests' in (P/'contract-tests.txt').read_text() and '\nOK\n' in (P/'contract-tests.txt').read_text()
    assert 'Ran 4 tests' in (P/'verifier-tests.txt').read_text() and '\nOK\n' in (P/'verifier-tests.txt').read_text()
    assert (P/'slurm-mocks.txt').read_text().count('PASS')==6 and 'PASS: one inert SCP invocation' in (P/'upload-route-test.txt').read_text()
    assert not (P/'run-receipt.json').exists()
    qc=dict(status='CPU-data-collection-package-ready-under-standing-authorization',unit_contracts=9,result_verifier_contracts=4,inert_Slurm_mock_cases=6,single_connection_two_file_upload_mock_passed=True,final_bootstrap_syntax_passed=True,all_python_sources_parse=True,archive_members_verified=ar['archived_files_verified'],package_and_start_script_hashes_verified=True,plan_sha256=ar['plan_sha256'],archive_sha256=ar['archive_sha256'],SSH_contacted=False,cluster_submitted=False,live_account_limits_verified=False,GPUs=0,training=False,approved_for_training=False)
    save(P/'CHECKS.json',qc)
    diag=read(D/'DIAGNOSIS.json');effect=read(D/'SELECTOR_EFFECT.json');table='\n'.join(f"| {r['index']} | {r['maximum_billboard_hits']}/11 | {r['final']['billboard_complete_fp']} | {r['final']['unscored']} | 0 |" for r in diag['trials'])
    localtable='\n'.join(f"| {r['index']} | {r['positive_policy']} | {r['teacher_weight']:g} | {r['billboard_hits']}/11 | {r['billboard_complete_fp']} | {r['unscored_predictions']} |" for r in result['trials'])
    report=f'''# FrameTrail: audited selector results and the next data move

Retrieval and independent audit succeeded for all four tasks in array 7818553. All 64 validation records were independently rescored; selection was replayed; all best/last model tensors and fixed update schedules were checked. Each best checkpoint contains the unchanged job 7805570 step 100 weights, despite different serialized provenance hashes. All last checkpoints changed only the two allowed billboard rows. The current model remains selected; no new model is adopted.

| Trial | Maximum validation billboard hits | Final measured complete FP | Final unscored predictions | Selected step |
| --- | --- | --- | --- | --- |
{table}

The effective unscored cap is 530, from original baseline 525 plus five. The current baseline is 528, so its separate cap is 533; both apply. Every checkpoint with billboard gains exceeded at least the stricter cap. Three final trials also added a measured billboard FP. Unknown predictions are not automatically false positives. Other reviewed classes passed their individual retention counts.

## What the selector actually changed

Post-run CPU inspection of all 20 billboard TRAIN photos confirms that proposal selection changed. At the larger encoder learning rate, the final boxes provided an IoU>=0.5 covering box for 50/54 training targets, compared with 37/54 at the starting checkpoint. Both larger-rate trials changed proposal sets on all 20 photos. The lower-rate trials covered 38/54. This measures training geometry coverage, not detection accuracy or independent generalization. Improving this training geometry did not produce an eligible validation checkpoint.

## Local error and annotation review

All 30 validation photos containing new unknown-scope billboard predictions were visually inspected. Scene triage found 22 non-billboard contexts, seven ambiguous cases and one scene containing an unlabelled physical advertisement. Examples include projected slides, framed art, consumer packaging, laundry notices, shop lettering, road signs and ordinary indoor surfaces. This is posthoc scene triage, not per-box ground truth. No validation labels, original scores or selection gates were changed, and no validation photos entered training.

All 20 positive TRAIN photos were reviewed. Three business-name/direction-board cases were held in a separate local contrast comparison because their category boundary is uncertain. Five Times Square photos account for 28 of the 54 original TRAIN billboard targets, illustrating scene concentration. Original labels and scopes remain preserved.

Twenty-four further existing TRAIN photos were reviewed separately: 12 laundry/household photos support billboard absence across the photo; 12 road-sign photos support negative queries only inside reviewed sign panels. Two road scenes also contain visible advertising boards outside the sign region; those remain unknown. These separate overlays do not mutate the original sealed release.

Four predeclared CPU fits tested expanded negative coverage with original 20 versus boundary-held 17 positive photos, crossed with two training-only teacher-preservation strengths. All four fits preceded any new validation outcome. All 24 new feature caches exactly reproduced the full-model outputs; frozen model state and the source checkpoint were unchanged. Each stored validation prediction set was independently rescored and its gates replayed:

| Fit | Positive policy | Teacher weight | Billboard hits | Measured complete FP | Unscored |
| --- | --- | --- | --- | --- | --- |
{localtable}

None qualified. The conservative expanded-data fit reached 6/11 with zero measured FP and 539 unscored predictions, still nine above the effective cap. Repeated development comparisons do not create fresh test evidence. Existing references are consumed and no thresholds/gates were relaxed.

## Next move: bounded data refresh before more training

A sealed CPU-only collection package is ready under the latest standing user authorization. Maximum 240 unreviewed candidates: 120 billboard anchors plus 24 each for traffic signs, washing machines, picture frames, computer monitors and whiteboards. It excludes all 1,931 previously acquired photos and their known author aliases. At most one photo per author alias; prospective train/validation/test quotas are assigned before downloading images or producing model predictions. Missing candidates remain explicit shortfalls, with no silent replacements or category substitutions.

This uses the existing pinned publisher TRAIN SQLite catalogue on KIT, avoiding another large metadata download. The [Open Images documentation](https://storage.googleapis.com/openimages/web/factsfigures_v7.html) distinguishes explicitly verified negative labels from unannotated classes; publisher contrast anchors therefore never establish billboard absence automatically. Every collected photo stays unreviewed and unapproved for training. Source-specific evidence, resolved NSID/alias identity, exact/perceptual duplicates against prior intakes AND all known regression images, scene/session overlap, content and boxes must pass review before any release. Prospective held-out groups remain outside training; no fresh accuracy claim exists yet.

One job on cpu_il, two CPUs, 8 GiB, 45 minutes wall, 2,400 seconds active collection, zero GPUs and no inference/training. Maximum 1 GB of original/partial image bytes and 480 MB source HTML, with existing per-image/decode/source limits. Each image/source is attempted once. Partial data and failures are archived; no retries, requeue or replacement jobs. Scheduler/account evidence and sbatch --test-only precede the single real submission. Account entitlements remain uninspected until authenticated submission.

Package checks passed: nine synthetic selection/source/budget contracts, four safe result-verifier contracts, six inert scheduler/trap cases, final shell syntax, and an upload mock proving that the archive plus start script use one SCP invocation. Archive members were read back and hash verified. No SSH, upload or new submission has occurred. The package is about 190 KiB; no training images/models are uploaded.

Windows PowerShell upload (one authenticated connection for both files):

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File "{P/'Upload-Data-Package.ps1'}"
```

Then run in the already authenticated cluster terminal:

```bash
bash "$(ws_find frametrail)/FrameTrail/output/{ar['cluster_start_script']}"
```

The cluster start command validates the exact archive and seal, records scheduler/account evidence, checks admission and submits once. Keep that cluster session open for later status checks; it avoids repeated OTP/password logins. Never paste credentials into chat. Model, data and adoption gates remain in force; current default YOLOX-S and explicit native preview are unchanged, strict ONNX numerical qualification remains held and production_adoption=false.

Next step: upload the small collection package, then start it from the existing cluster session, because local diagnosis and package checks are complete and direct KIT authentication is the remaining input.
'''
    save(D/'REPORT.md',report);save(P/'README.md',report)
    state=dict(status='selector-batch-fully-audited-no-candidate-data-refresh-prepared-awaiting-authenticated-upload',completed_array='7818553',retrieval_audit_complete=True,audit_sha256=sha(R/'independent-audit/AUDIT.json'),selected_checkpoint_job='7805570',selected_checkpoint_step=100,new_model_selected=False,selector_training_coverage_before='37/54',selector_training_coverage_after_high_lr='50/54',additional_TRAIN_photos_reviewed=24,additional_CPU_fits=4,additional_qualifying_CPU_candidates=0,next_package=str(P),maximum_collection_photos=240,GPUs_requested=0,CPU_cores=2,host_memory_GiB=8,wall_minutes=45,source_rights_or_training_clearance=False,archive_sha256=ar['archive_sha256'],cluster_submitted=False,new_cluster_job_id=None,standing_authorization='User explicitly removed routine approval pauses for bounded FrameTrail continuation; latest AGENTS.md applies. Preserve limits, exact scopes/provenance, batching, no retries/replacements and all model/data gates. Human input is currently needed only for direct authentication.',strict_ONNX_hold=True,production_adoption=False,next_step='Upload-Data-Package.ps1 once, then the short bash command in the existing KIT session; no new approval required.')
    save(D/'CURRENT_STATE.json',state);save(OUT/'LATEST_FRAMETRAIL_STATE_DATA_REFRESH_READY.json',state)
    root=D.parents[1];shutil.copy2(root/'CURRENT_HANDOFF.md',D/'HANDOFF_BEFORE_DIAGNOSIS.md');(root/'CURRENT_HANDOFF.md').write_text(report+'\nLatest state: '+str(D/'CURRENT_STATE.json')+'\n',encoding='utf-8')
    shutil.copy2(Path(r'C:\Users\nazee\.codex\attachments\361022b2-d3d2-44d0-9293-352181d7cd57\Pasted text.txt'),D/'retrieval-and-audit-console-from-user.txt')
    save(P/'final-files-sha256.json',dict(plan_sha256=ar['plan_sha256'],core_seal_sha256=sha(P/'data-tools-v1/package-files.json'),archive_sha256=ar['archive_sha256'],files={p.name:sha(p) for p in sorted(P.iterdir()) if p.is_file() and p.name!='final-files-sha256.json'}))
    save(D/'research-files-sha256.json',dict(files={p.relative_to(D).as_posix():sha(p) for p in sorted(D.rglob('*')) if p.is_file() and p.name!='research-files-sha256.json'}))
    print(json.dumps(dict(status=state['status'],checks=qc,upload_helper=str(P/'Upload-Data-Package.ps1'),cluster_command=(P/'CLUSTER_COMMAND.txt').read_text().strip()),indent=2))
if __name__=='__main__':main()
