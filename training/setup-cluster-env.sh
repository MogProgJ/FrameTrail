#!/bin/bash -l
# Install binary wheels in a project environment; this does not start training.
set -euo pipefail
module load devel/miniforge/25.3.1-python-3.12
FT_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$FT_ROOT"
python -c 'import sys; assert sys.version_info[:2] == (3, 12), "Python 3.12 required"'
export PIP_CACHE_DIR="$FT_ROOT/.cache/pip"
export OMP_NUM_THREADS=4
export OPENBLAS_NUM_THREADS=4
if [[ ! -d .venv ]]; then
  python -m venv .venv
fi
test -x .venv/bin/python
.venv/bin/python -c 'import sys; assert sys.version_info[:2] == (3, 12), "Existing environment must use Python 3.12"'
.venv/bin/python -m pip install --only-binary=:all: torch==2.8.0 torchvision==0.23.0 \
  --index-url https://download.pytorch.org/whl/cu128
.venv/bin/python -m pip install --only-binary=:all: -r scripts/requirements-training.txt
.venv/bin/python -m pip check
.venv/bin/python -m pip freeze > .venv/installed-packages.txt
printf 'Environment installed. GPU execution will be checked inside the Slurm job.\n'
