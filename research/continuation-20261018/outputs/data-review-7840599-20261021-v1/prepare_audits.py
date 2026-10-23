"""Prepare offline source/pixel/identity audits for completed intake7840599."""
from pathlib import Path
import json
R=Path(__file__).resolve().parent
O=R.parent/'data-review-7824179-20261020-v1'
P=R.parent/'billboard-targeted-intake-7824179-20261020-v1'
B=P/'retrieval-7840599/verified-7840599/output/billboard-data-refresh-7840599'
source=(O/'review_sources.py').read_text(encoding='utf-8-sig')
oldroot="R=Path("+repr(str(O))+")"
oldbase="BASE=Path("+repr(str(O.parent/'billboard-data-refresh-7818553-20261018-v1/retrieval-7824179/verified-7824179/output/billboard-data-refresh-7824179'))+")"
assert oldroot in source and oldbase in source
source=source.replace(oldroot,"R=Path("+repr(str(R))+")").replace(oldbase,"BASE=Path("+repr(str(B))+")")
source=source.replace('be48baf7c20e5ead0e211c27cf5e0e12c5ce247a6553fe1d349d30630dc370bd','0bd27558ab9ae9f5005492db719e90af37883ee9b9577e5fb0a3afa51028fbd8')
source=source.replace('==240','==180').replace('/240','/180').replace("'7824179'","'7840599'")
with (R/'review_sources.py').open('x',encoding='utf-8') as f:f.write(source)
audit=(O/'audit_intake.py').read_text(encoding='utf-8-sig')
audit=audit.replace("OUT / 'billboard-data-refresh-7818553-20261018-v1'","OUT / 'billboard-targeted-intake-7824179-20261020-v1'")
audit=audit.replace('retrieval-7824179/verified-7824179/output/billboard-data-refresh-7824179','retrieval-7840599/verified-7840599/output/billboard-data-refresh-7840599')
audit=audit.replace('frametrail-data-refresh-results-7824179.tar.gz','frametrail-data-refresh-results-7840599.tar.gz')
audit=audit.replace('retrieval-7824179/frametrail-data-refresh-results-7840599.tar.gz','retrieval-7840599/frametrail-data-refresh-results-7840599.tar.gz')
audit=audit.replace('== 240','== 180').replace('== 1931','== 2171')
needle="    release = read(OUT/"
at=audit.index(needle)
audit=audit[:at]+"""    previous_source = OUT/'data-review-7824179-20261020-v1/source-review/source-evidence-review.json'
    evidence_sources.append({'path':str(previous_source),'sha256':sha(previous_source)})
    for prior_row in read(previous_source)['images']:
        if prior_row.get('identity_group'):
            prior_owner_ids[prior_row['identity_group']].add(prior_row['image_id'])
"""+audit[at:]
with (R/'audit_intake.py').open('x',encoding='utf-8') as f:f.write(audit)
with (R/'make_review_sheets.py').open('x',encoding='utf-8') as f:f.write((O/'make_review_sheets.py').read_text())
print(json.dumps(dict(prepared=3,network_requests=0,training=False)))

