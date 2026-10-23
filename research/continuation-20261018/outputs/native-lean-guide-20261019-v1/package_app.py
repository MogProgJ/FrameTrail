"""Build a standalone core folder and separate optional models; never delete originals."""
from pathlib import Path
import hashlib
import json
import re
import shutil

ROOT = Path(__file__).resolve().parent
OLD = ROOT.parent / 'native-unified-20261019-v1'
CORE_MODELS = {'yolox_nano.onnx', 'yolox_s.onnx', 'yolo_world_s.onnx', 'yolo_openimages.onnx'}


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def save(name, obj):
    (ROOT / name).write_text(json.dumps(obj, indent=2) + '\n', encoding='utf-8')


def main():
    build = ROOT / 'build/Release'
    assert (build / 'frametrail-desktop.exe').is_file() and (build / 'frametrail.exe').is_file()
    app = ROOT / 'app'
    optional = ROOT / 'optional/models'
    for directory in (app, optional):
        assert directory.resolve().is_relative_to(ROOT.resolve())
        directory.mkdir(parents=True, exist_ok=True)
    baseline_models = json.loads((OLD / 'MODEL_INTEGRITY.json').read_text())
    models = []
    for old in (OLD / 'app').rglob('*'):
        if not old.is_file():
            continue
        relative = old.relative_to(OLD / 'app')
        if old.name == 'Qt6Test.dll':
            continue  # Linked only by test executables, not the desktop/CLI runtime.
        target = (optional / old.name) if relative.parts[0] == 'models' and old.name not in CORE_MODELS else (app / relative)
        target.parent.mkdir(parents=True, exist_ok=True)
        source = (build / old.name) if old.suffix == '.exe' else old
        shutil.copy2(source, target)
        if relative.parts[0] == 'models':
            expected = next(m['sha256'] for m in baseline_models if m['file'] == old.name)
            assert sha(target) == expected == sha(old)
            models.append({'file': old.name, 'relative_path': str(target.relative_to(ROOT)),
                           'sha256': expected, 'bytes': target.stat().st_size,
                           'core': old.name in CORE_MODELS, 'unchanged': True})
    vocabulary = (ROOT / 'source/src/recognition_vocabulary.hpp').read_text()
    names = re.findall(r'"([^"]+)"', vocabulary.split('labels[]={', 1)[1].split('};', 1)[0])
    broad = {int(n) for n in re.findall(r'\d+', vocabulary.split('openimages_ids', 1)[1].split('{', 1)[1].split('}', 1)[0])}
    core_ids = set(range(100)) | broad  # World-S includes the first 100 canonical labels.
    assert len(core_ids) == len(names) == 615
    save('MODEL_COVERAGE.json', {'core_profiles': sorted(CORE_MODELS), 'unique_labels': len(core_ids),
                                'billboard_available': names.index('billboard') in broad,
                                'washing_machine_available': names.index('washing machine') in broad,
                                'six_labels_needing_world_s': [names[i] for i in range(80, 100) if i not in broad],
                                'warning': 'Category-list coverage, not measured detection accuracy. Existing experimental status is unchanged.'})
    save('MODEL_INTEGRITY.json', models)
    old_size = sum(p.stat().st_size for p in (OLD / 'app').rglob('*') if p.is_file())
    core_size = sum(p.stat().st_size for p in app.rglob('*') if p.is_file())
    optional_size = sum(p.stat().st_size for p in optional.rglob('*') if p.is_file())
    save('PACKAGE_SIZE.json', {'previous_app_bytes': old_size, 'core_app_bytes': core_size,
                              'optional_models_bytes': optional_size, 'core_reduction_bytes': old_size-core_size,
                              'core_reduction_percent': (old_size-core_size)/old_size*100,
                              'total_core_plus_optional_bytes': core_size+optional_size,
                              'limits': 'Optional model bytes still exist outside app. This reduces the core distribution, not total storage when all packs/history are retained. No inference speed or working-memory reduction is claimed.'})
    for name, args in [('Run-FrameTrail.cmd', ''), ('Run-Balanced-Preview.cmd', '--rf-balanced ')]:
        script = '@echo off\r\nsetlocal\r\n'
        if args:
            script += 'if not exist "%~dp0optional\\models\\rfdetr_balanced7805570_step100.onnx" if not exist "%~dp0app\\models\\rfdetr_balanced7805570_step100.onnx" (\r\n  echo The balanced preview needs the optional RF model pack next to the app folder.\r\n  exit /b 2\r\n)\r\n'
        script += f'start "" "%~dp0app\\frametrail-desktop.exe" {args}%*\r\n'
        (ROOT / name).write_bytes(script.encode('utf-8'))
    (ROOT / 'READ-ME.txt').write_text('''FrameTrail: lean app and Quick Guide

Run Run-FrameTrail.cmd. The usual default is unchanged.
Press Ctrl+K or F1, or click Quick Guide, to find tasks and shortcuts.
Type billboard or washing machine to find a model that lists that object.
Use the guide button to choose that model in Preview.
Category support does not guarantee correct detections; check the results.

Keep app/ for the main program and its four core models.
optional/models/ contains the three larger/experimental alternatives.
The app finds that sibling folder automatically. Keep it in this layout if
you want those choices. Without it, they appear as not installed.
The balanced preview launcher needs the optional RF model.
No model is downloaded automatically. All processing stays on your device.

The smaller core folder does not mean that model inference is faster.
Including every optional model still uses approximately the former total size.
Old packages and scientific records are preserved separately.
''', encoding='utf-8')
    changes = []
    for path in (ROOT / 'source').rglob('*'):
        if not path.is_file():
            continue
        relative = path.relative_to(ROOT / 'source')
        old = OLD / 'source' / relative
        if not old.is_file() or sha(old) != sha(path):
            changes.append({'file': str(relative), 'sha256': sha(path), 'new': not old.exists()})
    assert not any(r['file'].startswith(('src\\', 'include\\')) for r in changes)
    save('source-changes.json', changes)
    print(json.dumps({'core_app_bytes': core_size, 'optional_bytes': optional_size,
                      'core_reduction_percent': (old_size-core_size)/old_size*100, 'models_unchanged': len(models)}))


if __name__ == '__main__':
    main()
