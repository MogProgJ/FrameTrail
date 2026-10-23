import ast,json
from pathlib import Path
D=Path(__file__).resolve().parent;P=D.parent/'billboard-data-refresh-7818553-20261018-v1';old=D.parent/'billboard-batch-proposal-7805570-20261018-v1/test-slurm-mocks.sh';remote=json.loads((P/'PACKAGE_IDENTITY.json').read_text())['remote_directory']
text=old.read_text().replace('task_name=rf-billboard-batch-0a255598-v1','task_name='+remote).replace('task_tools="$task_base/$task_name"','task_tools="$task_base/data-tools-v1"').replace('run-array.sbatch','run.sbatch')
text=text.replace('verify_package.py train_balanced.py regression_stage.py bundle_results.py','collector.py bundle.py').replace('train_balanced.py','collector.py').replace('bundle_results.py','bundle.py')
text=text.replace("$'verify_package.py\\ncollector.py\\nregression_stage.py\\nbundle.py'","$'collector.py\\nbundle.py'").replace("$'verify_package.py\\ncollector.py\\nbundle.py'","$'collector.py\\nbundle.py'")
(P/'test-slurm-mocks.sh').write_text(text,encoding='utf-8',newline='\n')
for path in list((P/'data-tools-v1').glob('*.py'))+list(P.glob('*.py')):ast.parse(path.read_text())
print('All collection Python files parse; prepared six inert Slurm cases.')
