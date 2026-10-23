"""Record already observed local checks and independently inspect final seals."""
import ast,hashlib,json
from pathlib import Path
HERE=Path(__file__).resolve().parent;P=HERE.parent/'selector-batch-proposal-7809335-20261018-v1'
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):
    with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def main():
    identity=read(P/'PROPOSAL_IDENTITY.json');T=P/identity['package_directory'];text=(P/'contract-tests.txt').read_text(encoding='utf-8-sig');assert 'Ran 12 tests' in text and '\nOK\n' in text
    for rel,digest in read(T/'package-files.json')['files'].items():assert sha(T/rel)==digest,rel
    for rel,digest in read(P/'preparation-files.json')['files'].items():assert sha(P/rel)==digest,rel
    for path in list(P.glob('*.py'))+list(T.glob('*.py')):ast.parse(path.read_text(encoding='utf-8-sig'))
    assert not (T/'approval.json').exists() and not list(P.glob('*.tar.gz')) and not (P/'run-receipt.json').exists()
    guard=(P/'missing-approval-guard.txt').read_text(encoding='utf-8-sig');assert 'required before packaging or SSH' in guard
    fixture=P/'slurm-mock-fixtures'
    assert (fixture/'normal/sbatch-calls.txt').read_text().count('called')==1
    assert (fixture/'ambiguous/sbatch-calls.txt').read_text().count('called')==1 and list((fixture/'ambiguous/FrameTrail/output/training-general-v1').glob('*/submission-lock'))
    assert not (fixture/'preflight-fails/sbatch-calls.txt').exists() and not (fixture/'test-only-reject/sbatch-calls.txt').exists()
    assert (fixture/'batch-entry/normal-calls.txt').read_text().splitlines()==['verify_package.py','train_balanced.py','regression_stage.py','bundle_results.py']
    assert (fixture/'batch-entry/training-failure-calls.txt').read_text().splitlines()==['verify_package.py','train_balanced.py','bundle_results.py']
    checks=dict(status='final-local-preparation-checks-passed',protocol_sha256=identity['protocol_sha256'],contracts_passed=12,inert_Slurm_mock_cases=6,PowerShell_51_helpers_parse=True,missing_approval_launcher_stops_before_SSH=True,real_CPU_four_photo_update=read(P/'REAL_CPU_UPDATE.json')['status'],all_core_and_preparation_file_hashes_verified=True,CPU_controls_independently_audited=read(HERE/'CPU_CONTROLS_AUDIT.json')['status'],new_cluster_approval=False,SSH_contacted=False,cluster_submitted=False,production_adoption=False)
    with (P/'CHECKS.json').open('x',encoding='utf-8') as f:json.dump(checks,f,indent=2)
    print(json.dumps(checks,indent=2))
if __name__=='__main__':main()
