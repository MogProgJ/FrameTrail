"""Run only after the human explicitly approves the newly proposed scope."""
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
if sha(T/'package-files.json')!=read(P/'PREPARATION_RECEIPT.json')['core_seal_sha256']:raise ValueError('Core seal differs from reviewed preparation')
for rel,h in read(T/'package-files.json')['files'].items():
    if sha(T/rel)!=h:raise ValueError('Changed core package '+rel)
for rel,h in read(P/'preparation-files.json')['files'].items():
    if sha(P/rel)!=h:raise ValueError('Changed prepared helper '+rel)
record=dict(approved=True,protocol_sha256=identity['protocol_sha256'],scope=protocol['scope'],active_classifier_rows=[133],active_classifier_heads=protocol['active_classifier_heads'],region_overlay_sha256=sha(T/'region-review.json'),user_authorization_evidence=evidence['verbatim_user_authorization'],recorded_at_UTC=datetime.datetime.now(datetime.timezone.utc).isoformat(),approved_batch=protocol['batch'],approved_for_application=False)
with (T/'approval.json').open('x',encoding='utf-8') as f:json.dump(record,f,indent=2)
print('Recorded exact new scope approval. No SSH or submission performed.')
