import json,hashlib
from pathlib import Path
R=Path(__file__).parent
protocol=R/'rf-nextdata-tools-v1/protocol.json';h=hashlib.sha256(protocol.read_bytes()).hexdigest();assert h=='274fe648bd391eb80f62b68e4007f689045e99832642dc0531e58f7c575f7a4d'
v={'actual_job_id':'7780632','scheduler_status':'COMPLETED','exit_code':'0:0','evidence':'user-pasted show-output.sh output; no independent SSH poll','archive_sha256_expected':'ae4fcd247566cc0a9c2abe81f8e25a61626e1987d1f950d8af5ddecc2db8a3ff','protocol_sha256':h,'updates_reported':600,'best_step_reported':0,'new_candidate_selected_reported':False,'best_checkpoint_sha256_reported':'3a9adf74b11b851fba7393cc41b12b538a7aa1576b0a4e179468cc36c2279389','last_checkpoint_sha256_reported':'d280723323b4ae8b07f1631667f2d87a9744c3398a06cc94e71dcef04fae2a02','results_retrieved':False,'results_verified':False,'training_resubmitted':False,'export_or_adoption':'deferred','next':'User runs Retrieve-7780632.ps1 in Windows PowerShell and completes KIT authentication. Then inspect verified report and frozen held-out evaluation protocol.'}
(R/'COMPLETION_RECEIPT.json').write_text(json.dumps(v,indent=2)+'\n');print(json.dumps(v))
