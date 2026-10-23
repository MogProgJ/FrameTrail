"""New bounded cohort, not a retry of successful collection7824179."""
import hashlib,json,re,shutil,tarfile
from pathlib import Path
D=Path(__file__).resolve().parent
OUT=D.parent
OLD=OUT/'billboard-data-refresh-7818553-20261018-v1'
P=OUT/'billboard-targeted-intake-7824179-20261020-v1'
T=P/'data-tools-v1'
V=Path(r'C:\Users\nazee\.codex\visualizations\2026\10\15\01a141ae-c7a6-7303-a280-403af88736f3')
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,v):
    p.write_text(v if isinstance(v,str) else json.dumps(v,indent=2,ensure_ascii=False)+'\n',encoding='utf-8',newline='\n')
def main():
    T.mkdir(parents=True,exist_ok=False)
    previous=read(OLD/'data-tools-v1/exclusions.json')
    intake=read(OLD/'retrieval-7824179/verified-7824179/output/billboard-data-refresh-7824179/manifest.json')
    audit=read(D/'INTAKE_AUDIT.json')
    assert len(intake['images'])==240 and len(previous['images'])==1931
    images=list(previous['images'])
    for r in intake['images']:
        images.append(dict(id=r['id'],sha256=r['sha256'],dhash=r['dhash'],
                           group_id=r.get('group_id',''),author_alias=r.get('author_alias',''),
                           author_url=r['attribution'].get('author_url','')))
    assert len(images)==len({r['id'] for r in images})==2171
    groups=set(previous.get('known_current_identity_groups',[]))
    sources=[D/'source-review/source-evidence-review.json']+[V/x/'source-evidence-review.json' for x in
             ('scale-review-7752340-v1','nextdata-source-review-7769109-v1','gap363-source-review-7787611-v1')]
    for f in sources:
        for r in read(f)['images']:
            identity=r.get('identity_group','')
            if identity.startswith('flickr-nsid:'):
                groups.add('https://www.flickr.com/people/'+identity.split(':',1)[1]+'/')
            for u in (r.get('current_creator',{}).get('url'),r.get('canonical_page_url'),
                      r.get('source_url'),r.get('publisher_attribution',{}).get('author_url')):
                if u:groups.add(u)
    write(T/'exclusions.json',dict(images=images,known_current_identity_groups=sorted(groups),
          provenance=[dict(path=str(f),sha256=sha(f)) for f in sources],
          all_previous_intake_photos_included=True))
    shutil.copy2(OLD/'data-tools-v1/classes-source.json',T/'classes-source.json')
    plan=read(OLD/'SCOPE.json')
    plan.update(purpose='new-targeted-billboard-source-cohort-after-successful7824179',
        authorization='Standing continuous-work authorization18October plus20October request to apply data-first strategy; new bounded CPU cohort, not retry/replacement.',
        exclusions_sha256=sha(T/'exclusions.json'),selection_seed='frametrail-targeted-billboard-after7824179-20261020-v1',
        anchors=[dict(name='billboard',raw_id=46,quota=dict(train=36,val=72,test=72))],
        maximum_photos=180,maximum_original_bytes=750000000,maximum_HTML_bytes=360000000,
        collection_reason='First cohort initial scene review has34 plausible TRAIN,7validation,9test billboard-positive photos before detailed clearance; required30/12/12. Original-image follow-up adds one test candidate. Retain all boundary/scene/source holds. Deliberately oversample prospective validation/test; never change old roles or use predictions.',
        batch_reason='One sequential CPU acquisition with photo-specific source evidence, hashes, fixed selection, bounded automatic audit and final partial-or-complete archive. Other five contrast anchors already supplied95 source-eligible candidates. More training/capacity trials would not resolve the missing reviewed positive data.',
        no_training_until_readiness=True,
        maximum_allocated_CPU_core_hours=1.5,maximum_allocated_GPU_hours=0,
        previous_job='7824179',previous_job_succeeded=True,automatic_replacement_jobs=0)
    write(T/'collection-plan.json',plan);write(P/'SCOPE.json',plan)
    auth=dict(date='2026-10-20',verbatim_current_user_request='The supercluster is available again. So go ahead, apply your new strategy that you built up yesterday with my instructions.',
        standing_authorization='18October continuous bounded work supersedes routine approval requests; user retains direct KIT OTP/password entry.',
        scope_plan_sha256=sha(P/'SCOPE.json'),new_cohort_not_retry_or_replacement=True,
        GPUs=0,training=False,model_inference=False,photos=180,wall_minutes=45,CPUs=2,memory_GiB=8,
        live_authenticated_account_and_admission_required=True)
    write(P/'USER_AUTHORIZATION.json',auth);write(T/'AUTHORIZATION.json',auth)
    for name in ('photo_transport.py','source_transport.py','collector.py','test_collector.py','bundle.py','show-output.sh'):
        shutil.copy2(OLD/'data-tools-v1'/name,T/name)
    code=(T/'collector.py').read_text().replace("maximum_photos=240)","maximum_photos=plan['maximum_photos'])")
    assert code!=(T/'collector.py').read_text()
    write(T/'collector.py',code)
    h=sha(P/'SCOPE.json');remote='data-refresh-'+h[:8]+'-v1'
    oldremote=read(OLD/'PACKAGE_IDENTITY.json')['remote_directory']
    write(T/'run.sbatch',(OLD/'data-tools-v1/run.sbatch').read_text().replace(oldremote,remote))
    submit=(OLD/'data-tools-v1/submit.sh').read_text()
    start=submit.index('scontrol show config')
    end=submit.index('sbatch --test-only')
    submit=submit[:start]+'''# Authenticated evidence, not public partition maxima. Empty/failed association evidence blocks submission.
scontrol show config > "$task_tools/scheduler-config.txt" 2>&1
scontrol show partition cpu_il > "$task_tools/partition-live.txt" 2>&1
sacctmgr -nP show assoc where user="$(id -un)" format=User,Account,Partition,QOS,MaxJobs,MaxSubmitJobs,GrpTRES > "$task_tools/account-limits.txt" 2>&1
awk -F'|' -v user="$(id -un)" '$1==user && $2!="" { found=1 } END { exit !found }' "$task_tools/account-limits.txt" || { echo 'No authenticated account association; preserve evidence and stop.'; exit 1; }
squeue -u "$(id -un)" --format='%.18i %.24j %.9P %.8T %.10M %.6D %R' > "$task_tools/user-queue-before-submit.txt"
sacctmgr -nP show qos format=Name,MaxJobsPU,MaxSubmitJobsPU,MaxTRESPU,MaxWall > "$task_tools/qos-live.txt" 2>&1 || true
'''+submit[end:]
    write(T/'submit.sh',submit)
    # Test a new resolved-NSID/alias exclusion route in addition to existing selection/scope/budget contracts.
    tests=(T/'test_collector.py').read_text()
    at=tests.index('    def test_sources_stay_held')
    tests=tests[:at]+'''    def test_prior_cohort_and_resolved_aliases_excluded(self):
        first=self.select()
        blocked={r['id'] for r in first[:3]}
        self.excluded['images'] += [dict(id=r['id'],author_url=r['attribution']['author_url']) for r in first[:3]]
        self.excluded['known_current_identity_groups']=[first[3]['attribution']['author_url'].replace('/people/','/photos/')]
        self.assertFalse((blocked|{first[3]['id']}) & {r['id'] for r in self.select()})
'''+tests[at:]
    write(T/'test_collector.py',tests)
    write(T/'package-files.json',dict(files={f.name:sha(f) for f in sorted(T.iterdir()) if f.name!='package-files.json'}))
    archive=P/('frametrail-'+remote+'.tar.gz')
    with tarfile.open(archive,'x:gz') as tar:
        for f in sorted(T.iterdir()):tar.add(f,arcname=remote+'/'+f.name,recursive=False)
    digest=sha(archive)
    expected={f.name:sha(f) for f in T.iterdir()};seen=set()
    with tarfile.open(archive,'r:gz') as tar:
        for m in tar:
            assert m.isfile() and m.name.startswith(remote+'/')
            rel=m.name[len(remote)+1:];assert rel in expected and rel not in seen
            assert hashlib.file_digest(tar.extractfile(m),'sha256').hexdigest()==expected[rel];seen.add(rel)
    assert seen==set(expected)
    bootstrap=(OLD/'START_ON_CLUSTER.sh').read_text()
    oldreceipt=read(OLD/'archive-receipt.json')
    bootstrap=bootstrap.replace(oldreceipt['archive'],archive.name).replace(oldreceipt['archive_sha256'],digest).replace(oldremote,remote).replace(oldreceipt['package_seal_sha256'],sha(T/'package-files.json'))
    startname='frametrail-start-'+remote+'.sh'
    write(P/'START_ON_CLUSTER.sh',bootstrap);write(P/startname,bootstrap)
    receipt=dict(archive=archive.name,archive_sha256=digest,bytes=archive.stat().st_size,remote_directory=remote,
        plan_sha256=h,package_seal_sha256=sha(T/'package-files.json'),archived_files_verified=len(seen),
        cluster_start_script=startname,cluster_start_script_sha256=sha(P/startname),cluster_submitted=False)
    write(P/'archive-receipt.json',receipt)
    write(P/'PACKAGE_IDENTITY.json',receipt)
    write(P/(archive.name+'.sha256'),digest+'  '+archive.name+'\n')
    write(P/'CLUSTER_COMMAND.txt','bash "$(ws_find frametrail)/FrameTrail/output/'+startname+'"\n')
    for name in ('Upload-Data-Package.ps1','Retrieve-Data.ps1','verify_results.py','test_data_verifier.py'):
        shutil.copy2(OLD/name,P/name)
    mock=(OLD/'test-slurm-mocks.sh').read_text().replace(oldremote,remote)
    mock=mock.replace('preflight-fails test-only-reject normal ambiguous','preflight-fails account-missing test-only-reject normal ambiguous')
    needle='  cat > "$task_root/bin/sbatch"'
    mock=mock.replace(needle,'''  cat > "$task_root/bin/sacctmgr" <<'STUB'
#!/bin/bash
if [[ "$TEST_CASE" == account-missing ]]; then exit 0; fi
printf '%s|test-account|cpu_il|normal||||\\n' "$(id -un)"
STUB
'''+needle)
    write(P/'test-slurm-mocks.sh',mock)
    uploadtest=(OLD/'Test-Upload-Route.ps1').read_text()
    write(P/'Test-Upload-Route.ps1',uploadtest)
    write(P/'PREPARATION_RECEIPT.json',dict(status='new-targeted-cohort-sealed-awaiting-local-contracts',
        prior_photos_excluded=2171,known_alias_tokens=len(groups),maximum_new_photos=180,
        raw_label_is_not_ground_truth=True,source_identity_scene_and_complete_boxes_required=True,
        original_prospective_roles_unchanged=True,
        approved_for_training=False,model_inference=False,cluster_contact=False,cluster_submitted=False))
    print(json.dumps(receipt))
if __name__=='__main__':main()

