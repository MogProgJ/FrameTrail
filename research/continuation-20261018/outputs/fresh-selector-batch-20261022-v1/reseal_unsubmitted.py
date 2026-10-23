"""Revise locally tested transport code before first submission; preserve prior seals/receipts."""
import sys,shutil,tarfile,time
from pathlib import Path
HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE/'tools'))
from batch_guard import *
base=HERE/'rf-fresh-selector-v1';receipt=read(HERE/'archive-receipt.json')
if (HERE/'SUBMISSION_USER_REPORT.json').exists():raise ValueError('User reported submission; never reseal or rebuild this scope')
if receipt['cluster_submitted'] or (base/'submitted-job-id.txt').exists() or (base/'submission-lock').exists():raise ValueError('Never reseal a submitted/ambiguous package')
history=HERE/'build-history'/str(time.time_ns());history.mkdir(parents=True)
for p in (HERE/'archive-receipt.json',base/'package-files.json',base/'verify_package.py',HERE/receipt['cluster_start_script']):shutil.copyfile(p,history/p.name)
for p in (HERE/'tools').iterdir():
    if p.is_file() and p.suffix in ('.py','.sh','.sbatch'):shutil.copyfile(p,base/p.name)
seal={p.relative_to(base).as_posix():sha(p) for p in sorted(base.rglob('*')) if p.is_file() and p.name!='package-files.json'}
(base/'package-files.json').write_text(json.dumps(seal,indent=2)+'\n',encoding='utf-8',newline='\n')
archive=HERE/receipt['archive']
with tarfile.open(archive,'w:gz') as tf:
    for p in sorted(base.rglob('*')):
        if p.is_file():tf.add(p,arcname=base.name+'/'+p.relative_to(base).as_posix(),recursive=False)
start=HERE/receipt['cluster_start_script'];text=start.read_text().replace(receipt['archive_sha256'],sha(archive)).replace(receipt['package_seal_sha256'],sha(base/'package-files.json'));start.write_text(text,encoding='utf-8',newline='\n')
receipt.update(archive_sha256=sha(archive),bytes=archive.stat().st_size,cluster_start_script_sha256=sha(start),package_seal_sha256=sha(base/'package-files.json'))
(HERE/'archive-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8',newline='\n')
print(json.dumps(receipt,indent=2))
