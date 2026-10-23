"""No activation without a separately recorded exact experiment approval."""
import argparse,hashlib,json
from pathlib import Path

def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def approval(tools):
    p=read(tools/'protocol.json');a=read(tools/'approval.json')
    if a.get('approved') is not True or a.get('protocol_sha256')!=sha(tools/'protocol.json') or a.get('candidate_sha256')!=p['candidate_sha256'] or a.get('scope')!='one-classifier-row-only-trial-600updates-1GPU-75minutes':raise ValueError('Exact new GPU scope approval missing or mismatched')
    if not a.get('user_authorization_evidence'):raise ValueError('Missing human authorization evidence')
    return a

def validate_draft(path,expected):
    path=Path(path).resolve();a=read(path)
    if sha(path)!=expected or a.get('approved_for_training') is not False or a.get('approved_for_application') is not False:raise ValueError('Draft identity/approval state changed')
    groups={};ids=set();hashes=set()
    for r in a['images']:
        if r['image_id'] in ids or r['image_sha256'] in hashes:raise ValueError('Duplicate identity/bytes')
        ids.add(r['image_id']);hashes.add(r['image_sha256'])
        if r['split'] not in ['train','val','test'] or groups.setdefault(r['identity_group'],r['split'])!=r['split']:raise ValueError('Invalid/leaking split')
        for key,expected_hash in [('source_path',r['image_sha256']),('rights_receipt_path',r['rights_receipt_sha256'])]:
            rel=Path(r[key]);p=(path.parent/rel).resolve(strict=True)
            if rel.is_absolute() or '..' in rel.parts or not p.is_relative_to(path.parent) or sha(p)!=expected_hash:raise ValueError('Changed/escaping release asset')
        evidence=read(path.parent/r['rights_receipt_path'])
        if evidence.get('rights_gate')!='pass-private-research' or evidence.get('image_sha256')!=r['image_sha256']:raise ValueError('Individual source gate missing')
        source=evidence.get('source_review');page=path.parent/'source-pages'/(r['image_id']+'.html.gz')
        if sha(page)!=(source['stored_sha256'] if source else evidence['source_gzip_sha256']):raise ValueError('Source page changed')
        for t in r['targets']:
            if r['scope'].get(str(t['canonical_id'])) not in ['complete','positive_only']:raise ValueError('Positive/scope conflict')
            q=t['normalized_cxcywh']
            if len(q)!=4 or not all(0<=x<=1 for x in q) or min(q[2:])<=0:raise ValueError('Invalid box')
        if not r['targets'] and not any(v=='absent' for v in r['scope'].values()):raise ValueError('Unreviewed negative scene')
    if len(a['images'])!=965:raise ValueError('Frozen draft count differs')
    return a

def activate(tools):
    approval(tools);p=read(tools/'protocol.json');draft=tools/'release/candidate-manifest-v2.json';a=validate_draft(draft,p['candidate_sha256']);out=draft.parent/'approved-core.json'
    if out.exists():
        existing=read(out)
        if existing.get('parent_candidate_sha256')!=p['candidate_sha256'] or existing.get('approval_sha256')!=sha(tools/'approval.json'):raise ValueError('Existing activation differs')
        return out
    a.update(approved_for_training=True,parent_candidate_sha256=p['candidate_sha256'],approval_sha256=sha(tools/'approval.json'))
    with out.open('x',encoding='utf-8') as f:json.dump(a,f,indent=2)
    return out
if __name__=='__main__':
    tools=Path(__file__).resolve().parent;print(activate(tools))
