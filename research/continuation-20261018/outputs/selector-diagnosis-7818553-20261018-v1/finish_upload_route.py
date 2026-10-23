import hashlib,json,shutil
from pathlib import Path
P=Path(__file__).resolve().parent.parent/'billboard-data-refresh-7818553-20261018-v1'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
receipt=json.loads((P/'archive-receipt.json').read_text());name='frametrail-start-'+receipt['remote_directory']+'.sh';shutil.copy2(P/'START_ON_CLUSTER.sh',P/name)
receipt.update(cluster_start_script=name,cluster_start_script_sha256=sha(P/name))
(P/'archive-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')
path=P/'Upload-Data-Package.ps1';text=path.read_text();text=text.replace("Write-Host 'Upload only.","$taskStart=Join-Path $PSScriptRoot $taskReceipt.cluster_start_script\nif ((Get-FileHash -LiteralPath $taskStart -Algorithm SHA256).Hash.ToLowerInvariant() -ne $taskReceipt.cluster_start_script_sha256) { throw 'Start script checksum differs; no upload.' }\nWrite-Host 'Upload only.")
text=text.replace('& scp -o StrictHostKeyChecking=yes $taskPath ', '& scp -o StrictHostKeyChecking=yes $taskPath $taskStart ')
text=text.replace("Write-Host 'Upload finished. Run the command in START_ON_CLUSTER.sh from the already authenticated cluster terminal.'", "Write-Host ('Upload finished. In your existing cluster terminal: bash '+[char]34+'$(ws_find frametrail)/FrameTrail/output/'+$taskReceipt.cluster_start_script+[char]34)")
path.write_text(text,encoding='utf-8',newline='\n')
(P/'CLUSTER_COMMAND.txt').write_text('bash "$(ws_find frametrail)/FrameTrail/output/'+name+'"\n',encoding='utf-8')
print('One upload connection for archive plus start script; submission uses the existing cluster login.')
