"""Compare two scores from evaluate.py class by class, e.g. a trained run against the YOLOv8 baseline.

Writes a Markdown report: overall scores (flat and with parent classes), how many classes got better or worse,
the biggest gains and losses, the weakest classes, and a table of every class with its training and test counts,
so weak results on thin classes are easy to tell apart from real failures.

Example:
    python training/compare.py runs/pilot-small/eval-test.json runs/baseline-yolov8s-oiv7-pilot/eval-test.json \\
        --dataset data/pilot --out runs/pilot-small/compare-baseline.md
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

TIE = 0.01  # Differences in AP below this count as unchanged.
THIN_TRAIN, THIN_TEST = 100, 10  # Fewer training images or test boxes than this: the class is thin.


def fmt(value: float | None) -> str:
    return '–' if value is None else f'{value:.3f}'


def delta(value: float | None) -> str:
    return '–' if value is None else f'{value:+.3f}'


def compare(ours: dict, theirs: dict, train_counts: dict[str, int], names: tuple[str, str], top: int = 15) -> str:
    rows = []
    for name, entry in ours['per_class'].items():
        other = theirs['per_class'].get(name, {})
        a, b = entry['ap'], other.get('ap')
        rows.append({'name': name, 'ours': a, 'theirs': b, 'diff': None if a is None or b is None else a - b,
                     'test_boxes': entry['ground_truth'], 'train_images': train_counts.get(name)})
    both = [r for r in rows if r['diff'] is not None]
    better = sum(r['diff'] >= TIE for r in both)
    worse = sum(r['diff'] <= -TIE for r in both)
    thin = lambda r: (r['train_images'] is not None and r['train_images'] < THIN_TRAIN) or r['test_boxes'] < THIN_TEST
    lines = [f'# {names[0]} against {names[1]}', '',
             f"Test images: {ours.get('images')}; classes scored: {ours['classes_scored']} "
             f"(the other: {theirs['classes_scored']}).", '',
             f'| Score (mAP@0.5) | {names[0]} | {names[1]} | Difference |', '| --- | --- | --- | --- |']
    for label, a, b in (('All classes', ours['map50'], theirs['map50']),
                        ('People and vehicles', ours.get('map50_people_and_vehicles'),
                         theirs.get('map50_people_and_vehicles'))):
        lines.append(f'| {label} | {fmt(a)} | {fmt(b)} | {delta(None if a is None or b is None else a - b)} |')
    if 'hierarchy' in ours and 'hierarchy' in theirs:
        h, g = ours['hierarchy'], theirs['hierarchy']
        for label, a, b in (('All classes, with parent classes', h['map50'], g['map50']),
                            ('People and vehicles, with parent classes', h.get('map50_people_and_vehicles'),
                             g.get('map50_people_and_vehicles'))):
            lines.append(f'| {label} | {fmt(a)} | {fmt(b)} | {delta(None if a is None or b is None else a - b)} |')
    lines += ['', f'Classes scored by both: {len(both)}. Better by at least {TIE}: **{better}**; worse: **{worse}**; '
                  f'about the same: {len(both) - better - worse}. Thin classes (under {THIN_TRAIN} training images or '
                  f'{THIN_TEST} test boxes): {sum(thin(r) for r in rows)}.', '']

    def table(title: str, selected: list[dict]) -> None:
        lines.extend([f'## {title}', '', f'| Class | {names[0]} | {names[1]} | Difference | Training images | Test boxes |',
                      '| --- | --- | --- | --- | --- | --- |'])
        for r in selected:
            lines.append(f"| {r['name']}{' (thin)' if thin(r) else ''} | {fmt(r['ours'])} | {fmt(r['theirs'])} | "
                         f"{delta(r['diff'])} | {r['train_images'] if r['train_images'] is not None else '–'} | "
                         f"{r['test_boxes']} |")
        lines.append('')

    table('Biggest gains', sorted(both, key=lambda r: -r['diff'])[:top])
    table('Biggest losses', [r for r in sorted(both, key=lambda r: r['diff']) if r['diff'] < 0][:top])
    table(f'Weakest classes ({names[0]})', sorted((r for r in rows if r['ours'] is not None),
                                                  key=lambda r: r['ours'])[:top])
    table('Every class', sorted(rows, key=lambda r: r['name'].lower()))
    return '\n'.join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('ours', type=Path, help="evaluate.py result of the model being judged")
    parser.add_argument('theirs', type=Path, help='evaluate.py result to compare against (e.g. the baseline)')
    parser.add_argument('--dataset', type=Path, help='dataset folder, for training image counts per class')
    parser.add_argument('--names', nargs=2, help='display names; default: the two folder names')
    parser.add_argument('--out', type=Path, required=True, help='Markdown report')
    args = parser.parse_args(argv)
    ours, theirs = (json.loads(p.read_text(encoding='utf-8')) for p in (args.ours, args.theirs))
    train_counts = {}
    summary = (args.dataset or Path(ours.get('dataset', ''))) / 'dataset.json'
    if summary.is_file():
        per_class = json.loads(summary.read_text(encoding='utf-8'))['roles']['train']['images_and_boxes_per_class']
        train_counts = {name: counts[0] for name, counts in per_class.items()}
    names = tuple(args.names or (args.ours.parent.name, args.theirs.parent.name))
    report = compare(ours, theirs, train_counts, names)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(report + '\n', encoding='utf-8')
    print('\n'.join(report.splitlines()[:12]))
    return 0


if __name__ == '__main__':
    sys.exit(main())
