#!/bin/bash -l
# Persist an intake selection only; no photographs, GPU or training.
#SBATCH --job-name=frametrail-selection
#SBATCH --partition=cpu_il
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --mem=4G
#SBATCH --time=00:30:00
#SBATCH --output=frametrail-selection-%j.log
set -euo pipefail
module load devel/miniforge/25.3.1-python-3.12
: "${SLURM_JOB_ID:?Submit through sbatch}"
: "${SLURM_SUBMIT_DIR:?Submit from the existing FrameTrail project}"
: "${FT_CATALOGUE_JOB:?Set the actual completed metadata job ID using sbatch --export}"
[[ "$FT_CATALOGUE_JOB" =~ ^[0-9]+$ ]]
cd "$SLURM_SUBMIT_DIR"
FT_PYTHON="$SLURM_SUBMIT_DIR/.venv/bin/python"
FT_SOURCE="$SLURM_SUBMIT_DIR/output/training-general-v1/catalogue-$FT_CATALOGUE_JOB"
FT_SCOPE="$SLURM_SUBMIT_DIR/output/training-general-v1/metadata-tools-v1/general-intake-pilot.json"
FT_OUTPUT="$SLURM_SUBMIT_DIR/output/training-general-v1/pilot-selection-$SLURM_JOB_ID"
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
printf 'Selection job: %s\nSource catalogue job: %s\nOutput: %s\n' "$SLURM_JOB_ID" "$FT_CATALOGUE_JOB" "$FT_OUTPUT"
srun "$FT_PYTHON" -B - "$FT_SOURCE" "$FT_SCOPE" <<'PY'
import json
from pathlib import Path
import sys
from scripts.training_data import digest
source, scope = Path(sys.argv[1]), Path(sys.argv[2])
report = json.loads((source / 'preparation.json').read_text())
inventory = json.loads((source / 'inventory.json').read_text())
if report['status'] != 'completed' or report['publisher_split'] != 'train':
    raise ValueError('Require a completed publisher-train catalogue')
if report['scope_sha256'] != digest(scope):
    raise ValueError('Pilot policy changed since metadata preparation')
if report['catalogue_sha256'] != digest(source / 'openimages-train.sqlite'):
    raise ValueError('Catalogue changed since preparation')
print('Classes without publisher-train boxes:',
      [item['name'] for item in inventory['classes'] if item['annotated_images'] == 0], flush=True)
PY
srun "$FT_PYTHON" -B scripts/prepare-dataset.py sample \
  --catalogue "$FT_SOURCE/openimages-train.sqlite" \
  --scope "$FT_SCOPE" --output "$FT_OUTPUT" \
  --exclude-manifest output/training-0.13/general-smoke-bundle/manifest.json
srun "$FT_PYTHON" -B - "$FT_OUTPUT" "$FT_CATALOGUE_JOB" <<'PY'
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys
output = Path(sys.argv[1])
selection = json.loads((output / 'selection.json').read_text())
images, scope = selection['images'], selection['scope']
domains = Counter(item['selected_domain'] for item in images)
categories = Counter(item['selected_category'] for item in images)
if (selection['source']['publisher_split'] != 'train' or not 0 < len(images) <= 600
        or len({item['id'] for item in images}) != len(images)
        or set(domains) != set(scope['domains'])):
    raise ValueError('Selection violates the publisher, image count, uniqueness or six-domain gate')
anchors = [name for names in scope['domains'].values() for name in names]
summary = {'schema': 1, 'status': 'completed', 'source_catalogue_job': sys.argv[2],
           'publisher_split': 'train', 'selected_candidates': len(images),
           'selected_domains': dict(domains), 'selected_anchor_categories': len(categories),
           'anchor_shortfalls': {name: categories.get(name, 0) for name in anchors
                                 if categories.get(name, 0) < scope['images_per_category']},
           'photographs_downloaded': 0, 'approved_for_training': False,
           'limits': 'Selection quotas count acquisition anchors, not complete object annotations or accuracy.',
           'selection_sha256': hashlib.sha256((output / 'selection.json').read_bytes()).hexdigest()}
(output / 'selection-summary.json').write_text(json.dumps(summary, indent=2) + '\n')
print(json.dumps(summary, indent=2), flush=True)
PY
printf 'Completed metadata-only selection. Results: %s\n' "$FT_OUTPUT"
