"""Pack the sealed assets only after exact human cluster-scope approval."""
import hashlib,json,tarfile
from pathlib import Path
HERE=Path(__file__).resolve().parent
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):
    with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
identity=read(HERE/'PROPOSAL_IDENTITY.json');tools=HERE/identity['package_directory']
import sys
sys.path.insert(0,str(tools))
from continuation_guard import approval
approval(tools)
seal=read(tools/'package-files.json')
for name,h in seal['files'].items():
    p=Path(name)
    if p.is_absolute() or '..' in p.parts or sha(tools/p)!=h:raise ValueError('Package seal differs')
archive=HERE/('frametrail-'+tools.name+'.tar.gz')
with archive.open('xb') as output,tarfile.open(fileobj=output,mode='w:gz',compresslevel=5) as tar:
    for name in [*sorted(seal['files']),'package-files.json','approval.json']:
        path=tools/name
        if not path.is_file() or path.is_symlink():raise ValueError('Unexpected non-regular package file')
        tar.add(path,arcname=tools.name+'/'+name,recursive=False)
digest=sha(archive)
(HERE/(archive.name+'.sha256')).write_text(digest+'  '+archive.name+'\n',encoding='ascii')
script=(HERE/'bootstrap-template.sh').read_text().replace('@@ARCHIVE@@',archive.name).replace('@@ARCHIVE_SHA@@',digest).replace('@@SEAL_SHA@@',sha(tools/'package-files.json'))
(HERE/'bootstrap-approved.sh').write_text(script,encoding='utf-8',newline='\n')
receipt=dict(archive=archive.name,archive_sha256=digest,bytes=archive.stat().st_size,package_seal_sha256=sha(tools/'package-files.json'),approval_sha256=sha(tools/'approval.json'),protocol_sha256=identity['protocol_sha256'])
with (HERE/'archive-receipt.json').open('x',encoding='utf-8') as f:json.dump(receipt,f,indent=2)
print(json.dumps(receipt,indent=2))
