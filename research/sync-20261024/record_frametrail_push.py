"""Record a verified publication after pushing; never pushes or reruns science."""
from pathlib import Path
from datetime import datetime,timezone
import json,subprocess

APP=Path(r'C:\Users\nazee\Documents\All Modules\FrameTrail')
CONT=Path(r'C:\Users\nazee\Documents\Codex\2026-10-18\frametrail-continuation')
STAGE=Path(__file__).parent
def cmd(args):return subprocess.check_output(args,cwd=APP,text=True).strip()
head=cmd(['git','rev-parse','HEAD'])
remote=cmd(['git','ls-remote','origin','refs/heads/main']).split()[0]
api=cmd(['gh','api','repos/MogProgJ/FrameTrail/commits/main','--jq','.sha'])
audit=json.loads((STAGE/'github-sync-git-blob-verify.json').read_text(encoding='utf-8-sig'))
if head!=remote or head!=api or audit['git_commit']!=head or audit['status']!='passed':raise RuntimeError('GitHub or committed-archive verification mismatch')
manifest=json.loads((APP/'research/SOURCE_MANIFEST.json').read_text(encoding='utf-8'))
receipt={'schema':1,'verified_at_utc':datetime.now(timezone.utc).isoformat(),'repository':'https://github.com/MogProgJ/FrameTrail','branch':'main','verified_content_commit':head,'git_remote_main':remote,'github_api_main':api,'committed_archive_sha256_check':audit,'original_source_files_archived':len(manifest['files']),'current_source_consolidated':True,'test_evidence':'VALIDATION_RECEIPT.json','local_binary_assets_uploaded':False,'production_adoption':False,'receipt_note':'This receipt is committed as a descendant of the verified content commit. Its own commit hash is intentionally not self-referential.','next_step':'Qualify unused local candidates for 11 TRAIN, 6 validation and 4 TEST truly absent additions under the expanded billboard definition before any new baseline or fit.'}
text=json.dumps(receipt,indent=2)+'\n'
(APP/'research/sync-20261024/PUSH_RECEIPT.json').write_text(text,encoding='utf-8')
(CONT/'GITHUB_SYNC_20261024.json').write_text(text,encoding='utf-8')
note=f'''# GitHub sync verified — 24 October 2026

User requested that all FrameTrail code and findings be current on GitHub. The private repository https://github.com/MogProgJ/FrameTrail, branch main, now contains verified content commit {head}. Git remote and GitHub API agreed; all {len(manifest['files']):,} archived source/evidence files match their original SHA-256 values in the committed Git blobs. Publication receipts are under research/sync-20261024/. Models, raw media, caches, SDK/build/package binaries and authentication/runtime artifacts remain local; their project artifact inventory and available scientific hash receipts are on GitHub. No binary backup or data/model release is claimed.

The main source checkout C:/Users/nazee/Documents/All Modules/FrameTrail now includes the previously verified latest single-window workspace and Quick Guide source from native-lean-guide-20261019-v1/source. Preserve e73759e as the earlier checkout revision and every historical source snapshot. The consolidated source passed 37 native checks; existing Python tooling passed 120 checks; Quick Guide checks passed at normal and 125% scale; the unified workflow passed. These were application fixture checks, not a scientific evaluation or new training. No camera, cluster job, model promotion or scientific TEST prediction was performed. Production remains YOLOX-S default, explicit held RF preview and production_adoption=false.

Canonical research receipts and the existing launcher/package remain under C:/Users/nazee/Documents/Codex/2026-10-18/frametrail-continuation. Read PROJECT_PROGRESS.md in the Git checkout for the GitHub entry point; the scientific status and existing authorizations below remain current. Continue ignoring MiniERP, Carrington Event and all unrelated projects. The publication receipt commit follows the content commit; use the live main ref for the latest publication metadata.

Next step: qualify unused local candidates for 11 TRAIN, 6 validation and 4 TEST truly absent additions, including the five TRAIN shop confusers and one traffic confuser, because the expanded definition needs trustworthy coverage before a new baseline or fit.

---

'''
for root in [APP,CONT]:
 p=root/'CURRENT_HANDOFF.md';old=p.read_text(encoding='utf-8')
 if old.startswith('# GitHub sync verified'):raise RuntimeError('Publication note already recorded')
 p.write_text(note+old,encoding='utf-8')
(APP/'research/sync-20261024/git-blob-verification.json').write_text(json.dumps(audit,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'verified_content_commit':head,'remote_and_api_match':True,'archived_files_verified':len(manifest['files'])}))
