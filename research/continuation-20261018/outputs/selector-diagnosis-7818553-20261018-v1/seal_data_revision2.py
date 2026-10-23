import hashlib,json,shutil,subprocess,tarfile
from pathlib import Path
D=Path(__file__).resolve().parent;P=D.parent/'billboard-data-refresh-7818553-20261018-v1';T=P/'data-tools-v1'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,v):p.write_text(v if isinstance(v,str) else json.dumps(v,indent=2)+'\n',encoding='utf-8',newline='\n')
old=json.loads((P/'archive-receipt.json').read_text());history=P/'history-before-bytecap-fix';history.mkdir(exist_ok=False)
for name in ('archive-receipt.json','START_ON_CLUSTER.sh','PACKAGE_IDENTITY.json'):shutil.copy2(P/name,history/name)
for name in ('collector.py','test_collector.py'):shutil.copy2(D/name,T/name)
python=Path(r'C:\Users\nazee\Documents\All Modules\FrameTrail\.deps\rfdetr-probe-cpu\Scripts\python.exe')
r=subprocess.run([str(python),'-B','-X','utf8',str(T/'test_collector.py')],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
write(P/'contract-tests.txt',r.stdout)
if r.returncode:raise ValueError(r.stdout)
seal=dict(files={p.relative_to(T).as_posix():sha(p) for p in sorted(T.rglob('*')) if p.is_file() and p.name!='package-files.json'});write(T/'package-files.json',seal)
archive=P/old['archive'].replace('.tar.gz','-r2.tar.gz');remote=old['remote_directory']
with tarfile.open(archive,'x:gz') as tar:
    for p in sorted(T.iterdir()):
        if p.is_file():tar.add(p,arcname=remote+'/'+p.name,recursive=False)
expected=dict(seal['files'],**{'package-files.json':sha(T/'package-files.json')});seen=set()
with tarfile.open(archive,'r:gz') as tar:
    for member in tar:
        assert member.isfile() and member.name.startswith(remote+'/');rel=member.name[len(remote)+1:];assert rel in expected and rel not in seen
        with tar.extractfile(member) as stream:assert hashlib.file_digest(stream,'sha256').hexdigest()==expected[rel]
        seen.add(rel)
assert seen==set(expected)
receipt=dict(old,archive=archive.name,archive_sha256=sha(archive),bytes=archive.stat().st_size,package_seal_sha256=sha(T/'package-files.json'),code_revision=2)
bootstrap=(P/'START_ON_CLUSTER.sh').read_text().replace(old['archive'],receipt['archive']).replace(old['archive_sha256'],receipt['archive_sha256']).replace(old['package_seal_sha256'],receipt['package_seal_sha256'])
write(P/'START_ON_CLUSTER.sh',bootstrap);write(P/receipt['cluster_start_script'],bootstrap);receipt['cluster_start_script_sha256']=sha(P/receipt['cluster_start_script']);write(P/'archive-receipt.json',receipt);write(P/(archive.name+'.sha256'),receipt['archive_sha256']+'  '+archive.name+'\n')
identity=json.loads((P/'PACKAGE_IDENTITY.json').read_text());identity.update(archive_sha256=receipt['archive_sha256'],code_revision=2);write(P/'PACKAGE_IDENTITY.json',identity)
print(json.dumps(dict(tests=9,archive=archive.name,bytes=receipt['bytes'],archive_members_verified=len(seen),scope_unchanged=True,old_artifacts_preserved=True)))
