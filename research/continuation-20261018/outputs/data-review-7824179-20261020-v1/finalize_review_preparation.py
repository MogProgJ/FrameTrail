import hashlib,json
from collections import Counter,defaultdict
from pathlib import Path
D=Path(__file__).resolve().parent
P=D.parent/'billboard-targeted-intake-7824179-20261020-v1'
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def save(p,x):p.write_text(json.dumps(x,indent=2)+'\n',encoding='utf-8')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
rows=[r for f in sorted(D.glob('scene-triage-*.json')) for r in read(f)['records']]
assert len(rows)==len({r['id'] for r in rows})==200
initial=Counter((r['role'],r['disposition']) for r in rows)
follow=read(D/'ORIGINAL_IMAGE_FOLLOWUP.json')
index={r['id']:r for r in rows}
for r in follow['records']:
    assert r['id'] in index
    index[r['id']]=dict(index[r['id']],disposition=r['disposition'],original_followup_note=r['note'])
latest=Counter((r['role'],r['disposition']) for r in index.values())
save(D/'SCENE_TRIAGE_SUMMARY.json',dict(status='initial-review-complete-detailed-annotation-and-scene-clearance-incomplete',
    source_identity_eligible=200,source_held=40,
    initial_counts=[dict(role=a,disposition=b,photos=n) for (a,b),n in sorted(initial.items())],
    after_original_followup_counts=[dict(role=a,disposition=b,photos=n) for (a,b),n in sorted(latest.items())],
    plausible_positive_photos_by_role={role:sum(n for (a,b),n in latest.items() if a==role and b.startswith('positive-context')) for role in ('train','val','test')},
    scene_clearance_complete=False,box_review_complete=False,exhaustive_absence_review_complete=False,
    training_cleared_photos=0,approved_for_training=False,model_inference=False,training=False,
    near_duplicate_followup=dict(image='65e34de96ff0f728',prior='aa002b206c310671',dhash_distance=6,
      reviewed_originals=True,result='false-match-different-objects-and-scenes'),
    next_cohort_scope_sha256=sha(P/'SCOPE.json')))
tests=['contract-tests.txt','verifier-tests.txt','slurm-mocks.txt','upload-route-test.txt']
save(P/'CHECKS.json',dict(status='local-checks-passed-awaiting-direct-authenticated-upload-and-live-admission',
    selection_source_budget_contracts=10,safe_result_verifier_contracts=4,
    inert_scheduler_and_batch_cases=7,one_SCP_two_files_mock_passed=True,shell_syntax_passed=True,
    archive_members_verified=read(P/'archive-receipt.json')['archived_files_verified'],
    evidence=[dict(path=x,sha256=sha(P/x)) for x in tests],
    actual_network_connections_by_tests=0,actual_jobs_submitted=0,
    live_account_evidence='Not yet available; submit.sh requires successful nonempty user association, live partition/config/user queue, plus sbatch --test-only before one submission. Empty/failed evidence blocks. QoS listing is supplemental.',
    no_automatic_retry_requeue_or_replacement=True))
report="""Job7824179 completed successfully. The exact archive and all240 original images are verified locally.
The report's 'shortfalls' array lists requested/selected quotas; all match, so there were no actual collection shortfalls.

Source review:200 corroborated photo-specific source/owner records;36 unavailable pages and4 license mismatches are held.
Initial scene review covers all200 eligible pictures. Following original-image checks, plausible positive counts are TRAIN34,validation7,test10.
These are triage candidates, NOT exhaustive reviewed labels or a qualified release. All training clearance remains false.
Two source-eligible billboard records are multi-photo collages, so they cannot count as single independent scenes.
One dHash candidate was a false match (railway warning versus wall switch). Prior and cross-role scene comparison remains incomplete.
No test model predictions, fitting, fresh-test scoring, threshold changes or model adoption occurred.

The frozen strategy still requires30TRAIN/12validation/12test positive photos plus complete negatives and scene/source/identity checks.
We are not lowering these minima or broadening the definition to accept ambiguous name signs, paper posters, murals or vending wraps.
Prepare a new separate cohort of180 billboard candidates,36TRAIN/72validation/72test, from the existing pinned publisher TRAIN catalogue.
Exclude all2171 acquired photos and known resolved aliases. Keep original role assignments and all failed/ambiguous source evidence.
This is new data acquisition following a successful run, not an automatic retry or replacement job.
The other95 source-eligible contrast candidates already cover laundry, traffic signs and indoor frame/screen/board settings; detailed absence and family checks remain.
All candidate source pages, hashes and final partial/completed bundle are included in the same bounded job.
One CPU job:2cores,8GiB,45minutes,0GPUs,0inference/training,<=750MB original/partial bytes,<=360MB HTML. No requeue/retry/replacement.
No parallel array is useful for this single deterministic collection; additional training trials cannot fix missing reviewed positives.
Live authenticated account association and sbatch test-only are enforced before submission. Package prepared/tested; not submitted.

Next step: upload this small package with direct KIT authentication and launch once from the existing cluster terminal, because local checks passed and fresh reviewed positives still block useful training.
"""
(D/'REVIEW_REPORT.txt').write_text(report,encoding='utf-8')
(P/'README.txt').write_text(report,encoding='utf-8')
save(P/'FINAL_FILES_SHA256.json',{f.name:sha(f) for f in sorted(P.iterdir()) if f.is_file() and f.name!='FINAL_FILES_SHA256.json'})
print(json.dumps(dict(reviewed_initial_scenes=200,plausible_positives=dict(train=34,val=7,test=10),training_cleared=0,package_checks='passed',network_tests=0,jobs_submitted=0)))

