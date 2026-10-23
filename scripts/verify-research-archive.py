"""Check archived research bytes without running any experiment or inference."""
import argparse
import hashlib
import json
import subprocess
from pathlib import Path, PurePosixPath

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
parser.add_argument('--git-ref', help='Verify stored Git blobs at this commit instead of working files')
args = parser.parse_args()
archive = (args.root / 'research').resolve()
commit = None
batch = None
if args.git_ref:
    commit = subprocess.check_output(['git', 'rev-parse', '--verify', args.git_ref+'^{commit}'], cwd=args.root, text=True).strip()
    manifest = json.loads(subprocess.check_output(['git', 'show', commit+':research/SOURCE_MANIFEST.json'], cwd=args.root))
    batch = subprocess.Popen(['git', 'cat-file', '--batch'], cwd=args.root, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
else:
    manifest = json.loads((archive / 'SOURCE_MANIFEST.json').read_text(encoding='utf-8'))
failures = []
seen = set()
for row in manifest['files']:
    relative = row['path']
    logical = PurePosixPath(relative)
    if logical.is_absolute() or '..' in logical.parts or '\\' in relative or '\n' in relative or '\r' in relative or relative in seen:
        failures.append({'path': relative, 'reason': 'unsafe-or-duplicate-path'})
        continue
    path = archive / relative
    if not batch and not path.resolve().is_relative_to(archive):
        failures.append({'path': relative, 'reason': 'symlink-outside-archive'})
        continue
    seen.add(relative)
    if batch:
        batch.stdin.write((commit+':research/'+relative+'\n').encode('utf-8'))
        batch.stdin.flush()
        header = batch.stdout.readline().decode('utf-8').rstrip().split()
        if len(header) != 3 or header[1] != 'blob':
            failures.append({'path': relative, 'reason': 'missing-git-blob'})
            continue
        data = batch.stdout.read(int(header[2]))
        assert batch.stdout.read(1) == b'\n', 'Invalid Git batch delimiter'
    elif not path.is_file():
        failures.append({'path': relative, 'reason': 'missing'})
        continue
    else:
        data = path.read_bytes()
    if len(data) != row['bytes'] or hashlib.sha256(data).hexdigest() != row['sha256']:
        failures.append({'path': relative, 'reason': 'size-or-sha256-mismatch'})
if batch:
    batch.stdin.close()
    batch.stdout.close()
    if batch.wait() != 0:
        failures.append({'reason': 'git-cat-file-failed'})
print(json.dumps({'status': 'failed' if failures else 'passed', 'git_commit': commit,
                  'files_checked': len(manifest['files']), 'failures': failures}, indent=2))
raise SystemExit(bool(failures))
