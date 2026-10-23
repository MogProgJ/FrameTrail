"""Finish code/test preparation; deliberately does not record user approval."""
import ast,hashlib,json,re,shutil
from pathlib import Path
HERE=Path(__file__).resolve().parent;OUT=HERE.parent;P=OUT/'selector-batch-proposal-7809335-20261018-v1';OLD=OUT/'billboard-batch-proposal-7805570-20261018-v1'
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):
    with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def write(p,v):p.write_text(v if isinstance(v,str) else json.dumps(v,indent=2)+'\n',encoding='utf-8',newline='\n')
def main():
    identity=read(P/'PROPOSAL_IDENTITY.json');T=P/identity['package_directory'];digest=identity['protocol_sha256']
    path=T/'preflight.py';text=path.read_text();text=text.replace("p=read(T/'protocol.json') if preparation_only else approval(T)[1];runtime=read(T/'runtime-lock.json');import torch","p=read(T/'protocol.json') if preparation_only else approval(T)[1];runtime=read(T/'runtime-lock.json');import torch\n    from scipy.optimize import linear_sum_assignment\n    if list(linear_sum_assignment([[1,0],[0,1]])[1])!=[1,0]:raise ValueError('Dense proposal assignment unavailable')")
    write(path,text)
    path=P/'verify_results.py';text=path.read_text();needle="if pre['actual_job_id']!=job"
    text=text.replace(needle,"if pre.get('active_classifier_heads')!=['class_embed','transformer.enc_out_class_embed.0'] or report.get('active_classifier_heads')!=pre['active_classifier_heads'] or pre.get('region_overlay_sha256')!=read(Path(__file__).with_name('protocol.json'))['data']['separate_training_region_overlay']['sha256']:raise ValueError('Two-head/region scope differs')\n        "+needle)
    write(path,text)
    path=P/'audit_batch.py';text=path.read_text();text=text.replace("require(pre['candidate_sha256']==sha(TOOLS/'release/candidate-manifest-v2.json'),'Wrong training release')","require(pre['candidate_sha256']==sha(TOOLS/'release/candidate-manifest-v2.json'),'Wrong training release')\n        require(pre['active_classifier_heads']==report['active_classifier_heads']==['class_embed','transformer.enc_out_class_embed.0'] and pre['region_overlay_sha256']==sha(TOOLS/'region-review.json'),'Wrong two-head/region scope')")
    write(path,text)
    text=(OLD/'test_batch.py').read_text().replace('rf-billboard-batch','rf-selector').replace('frozen_features_and_boxes_unchanged','frozen_parameters_and_buffers_unchanged').replace('from head_policy import configure','from selector_mechanics import configure')
    start=text.index('    def test_paired_schedules_');end=text.index('    def test_index_',start)
    text=text[:start]+'''    def test_paired_schedules_isolate_encoder_lr_and_region_weight(self):
        s=[f[1] for f in self.fixtures];self.assertTrue(all(x==s[0] for x in s))
        self.assertEqual({(v['encoder_lr'],v['region_weight']) for v in read(T/'protocol.json')['variants']},{(.00001,1),(.00001,3),(.00003,1),(.00003,3)})
        overlay=read(T/'region-review.json');self.assertEqual(len(overlay['regions']),8)
        self.assertEqual(s[0][:1500],read(HERE.parent/'selector-stage-7809335-20261018-v1/CPU_CONTROL_SCHEDULE.json'))
'''+text[end:]
    text=text.replace("'Explicit user approval'","'Explicit approval'")
    start=text.index('    def test_synthetic_updates_');end=text.index('    def test_windows_',start)
    text=text[:start]+'''    def test_synthetic_updates_only_both_row133s(self):
        from selector_mechanics import fingerprint_frozen
        for lr in (.00001,.00003):
            net=torch.nn.Module();net.class_embed=torch.nn.Linear(4,616);net.backbone=torch.nn.Linear(4,4);net.transformer=torch.nn.Module();net.transformer.enc_out_class_embed=torch.nn.ModuleList([torch.nn.Linear(4,616)])
            opt,check,allowed=configure(net,lr);frozen=fingerprint_frozen(net,allowed);before={k:v.clone() for k,v in net.state_dict().items()}
            (net.class_embed(torch.ones(2,4)).square().sum()+net.transformer.enc_out_class_embed[0](torch.ones(2,4)).square().sum()).backward();opt.step();check()
            self.assertEqual(frozen,fingerprint_frozen(net,allowed))
            for key in allowed:self.assertFalse(torch.equal(before[key][133],net.state_dict()[key][133]))
'''+text[end:]
    text=text.replace("with self.assertRaises(ValueError):verifier.verify_schedule(s,'123_1')","verifier.verify_schedule(s,'123_1') # paired schedule deliberately identical")
    text=text.replace("pre=dict(actual_job_id=job,","pre=dict(active_classifier_heads=['class_embed','transformer.enc_out_class_embed.0'],region_overlay_sha256=sha(T/'region-review.json'),actual_job_id=job,")
    text=text.replace("report=dict(actual_job_id=job,","report=dict(active_classifier_heads=['class_embed','transformer.enc_out_class_embed.0'],actual_job_id=job,")
    write(P/'test_batch.py',text)
    write(P/'test-slurm-mocks.sh',(OLD/'test-slurm-mocks.sh').read_text().replace('rf-billboard-batch-0a255598-v1',T.name))
    write(P/'Validate-Helpers.ps1',r'''$ErrorActionPreference = 'Stop'
$taskFailures = @()
Get-ChildItem -LiteralPath $PSScriptRoot -Filter *.ps1 | ForEach-Object {
    $taskTokens=$null; $taskErrors=$null
    [System.Management.Automation.Language.Parser]::ParseFile($_.FullName,[ref]$taskTokens,[ref]$taskErrors) | Out-Null
    if ($taskErrors.Count) { $taskFailures += $taskErrors }
}
if ($taskFailures.Count) { $taskFailures | Format-List; throw 'PowerShell syntax failed.' }
Write-Host 'All PowerShell helpers parse successfully.'
''')
    write(P/'record_approval.py','''"""Run only after the human explicitly approves the newly proposed scope."""
import argparse,datetime,hashlib,json
from pathlib import Path
P=Path(__file__).resolve().parent
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):
    with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
ap=argparse.ArgumentParser();ap.add_argument('--authorization-file',type=Path,required=True);a=ap.parse_args()
evidence=read(a.authorization_file)
if evidence.get('human_approved_exact_selector_scope') is not True or not evidence.get('verbatim_user_authorization'):raise ValueError('Human scope approval required')
identity=read(P/'PROPOSAL_IDENTITY.json');T=P/identity['package_directory'];protocol=read(T/'protocol.json')
if evidence.get('protocol_sha256')!=identity['protocol_sha256'] or sha(T/'protocol.json')!=identity['protocol_sha256']:raise ValueError('Wrong approved protocol')
for rel,h in read(T/'package-files.json')['files'].items():
    if sha(T/rel)!=h:raise ValueError('Changed core package '+rel)
for rel,h in read(P/'preparation-files.json')['files'].items():
    if sha(P/rel)!=h:raise ValueError('Changed prepared helper '+rel)
record=dict(approved=True,protocol_sha256=identity['protocol_sha256'],scope=protocol['scope'],active_classifier_rows=[133],active_classifier_heads=protocol['active_classifier_heads'],region_overlay_sha256=sha(T/'region-review.json'),user_authorization_evidence=evidence['verbatim_user_authorization'],recorded_at_UTC=datetime.datetime.now(datetime.timezone.utc).isoformat(),approved_batch=protocol['batch'],approved_for_application=False)
with (T/'approval.json').open('x',encoding='utf-8') as f:json.dump(record,f,indent=2)
print('Recorded exact new scope approval. No SSH or submission performed.')
''')
    for path in list(T.glob('*.py'))+list(P.glob('*.py')):ast.parse(path.read_text(encoding='utf-8-sig'),filename=str(path))
    print('Prepared new trainer, result audit, twelve contracts, six inert Slurm mocks, transport and explicit approval recorder. Unsealed pending CPU controls.')
if __name__=='__main__':main()
