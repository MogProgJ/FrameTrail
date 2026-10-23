"""Run local checks after building/packaging; no cluster or application adoption."""
import json
import os
from pathlib import Path
import subprocess
import time

ROOT = Path(__file__).resolve().parent
OLD = ROOT.parent / 'native-unified-20261019-v1'
CTEST = Path(r'C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\Common7\IDE\CommonExtensions\Microsoft\CMake\CMake\bin\ctest.exe')


def main():
    temp = ROOT / 'runtime-temp'
    temp.mkdir(exist_ok=True)
    env = dict(os.environ, TEMP=str(temp), TMP=str(temp), QT_QPA_PLATFORM='offscreen', QT_SCALE_FACTOR='1')
    records = []

    def run(name, args, *, scaled=False, timeout=180):
        settings = dict(env, QT_SCALE_FACTOR='1.25' if scaled else '1')
        start = time.perf_counter()
        result = subprocess.run([str(a) for a in args], env=settings, capture_output=True, timeout=timeout)
        (ROOT / (name + '-console.txt')).write_bytes(result.stdout + result.stderr)
        record = {'name': name, 'exit_code': result.returncode, 'wall_seconds': time.perf_counter()-start}
        records.append(record)
        (ROOT / 'VERIFICATION_PROGRESS.json').write_text(json.dumps(records, indent=2)+'\n', encoding='utf-8')
        print(json.dumps(record), flush=True)
        if result.returncode:
            raise RuntimeError(name + ' failed; inspect its console output')
        return record

    run('regression-final', [CTEST, '--test-dir', ROOT/'build', '-C', 'Release', '--output-on-failure', '-R',
        '^(backend_contract|saved_run_contract|saved_analysis_inference|media_contract|preview_lifecycle|preview_reconfiguration|preview_tracking|desktop_analysis_intake|desktop_saved_review|desktop_controls|desktop_detection)$'])
    nano = ROOT / 'app/models/yolox_nano.onnx'
    run('guide-verified', [ROOT/'build/Release/frametrail_guide_tests.exe', nano, ROOT/'evidence/guide-verified'])
    run('guide-verified-scale125', [ROOT/'build/Release/frametrail_guide_tests.exe', nano, ROOT/'evidence/guide-verified-scale125'], scaled=True)
    long_video, short_video = OLD/'fixtures/workflow-long.mkv', OLD/'fixtures/workflow-short.mkv'
    run('unified-final', [ROOT/'build/Release/frametrail_unified_workspace_tests.exe', nano, long_video, short_video, ROOT/'evidence/unified-final'])
    run('unified-scale125', [ROOT/'build/Release/frametrail_unified_workspace_tests.exe', nano, long_video, short_video, ROOT/'evidence/unified-scale125'], scaled=True)
    run('full-cache-balanced', [ROOT/'build/Release/frametrail_cached_playback_tests.exe', ROOT/'optional/models/rfdetr_balanced7805570_step100.onnx', short_video, ROOT/'evidence/full-cache-balanced', 'balanced', '.35'])
    dog = ROOT / 'source/.deps/detection-samples/dog.jpg'
    smokes = []
    smokes.append(run('packaged-standard', [ROOT/'app/frametrail-desktop.exe', '--smoke-test', dog]))
    smokes.append(run('packaged-balanced', [ROOT/'app/frametrail-desktop.exe', '--rf-balanced', '--smoke-test', dog]))
    optional, held = ROOT/'optional', ROOT/'optional-hidden-for-test'
    assert optional.resolve().parent == ROOT.resolve() and held.resolve().parent == ROOT.resolve() and not held.exists()
    optional.rename(held)
    try:
        smokes.append(run('packaged-core-without-optional', [ROOT/'app/frametrail-desktop.exe', '--smoke-test', dog]))
    finally:
        held.rename(optional)
    (ROOT / 'PACKAGED_SMOKE.json').write_text(json.dumps(smokes, indent=2)+'\n', encoding='utf-8')
    print('All local checks completed', flush=True)


if __name__ == '__main__':
    main()
