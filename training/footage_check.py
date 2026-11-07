"""Does a model find what YOLOX-S confidently sees on your own videos?

Open Images test photos cannot tell whether a model works on your footage (the Phase 2 model scores 0.69 there and
still finds none of the handbags and backpacks YOLOX-S boxes on a street clip). This check uses your clips instead:
the *reference* is YOLOX-S's confident boxes (score >= --ref-score), and for each candidate model it reports how many
of them the model also boxes (IoU >= 0.5, same class or a parent/child class such as car and taxi).

It is agreement with YOLOX-S, not accuracy: YOLOX-S knows only 80 classes and makes mistakes of its own. What it
measures is recall of the objects you have already seen YOLOX-S get right. Precision stays the job of Review (C and X
in the Analysis section). The `extra` column counts candidate boxes with no reference partner; most are classes
YOLOX-S cannot name (footwear, wheels, ...), so it is not an error count.

Input is the `--detections` CSV of `frametrail inspect` (see scripts/footage-check.ps1, which runs it for you):

    python training/footage_check.py --reference yolox.csv --candidate "trained=trained.csv" \\
        --candidate "combined=combined.csv" --out report.md
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HIERARCHY = ROOT / 'src' / 'recognition_hierarchy.hpp'
VOCABULARY = ROOT / 'dependencies' / 'recognition-vocabulary.json'
# Models mix these up on one object, and for finding it the label hardly matters: they count as one group.
ROAD_VEHICLES = ('car', 'taxi', 'van', 'limousine', 'truck', 'ambulance')
Box = tuple[float, float, float, float]


def read_detections(path: Path) -> dict[int, list[tuple[int, str, float, Box]]]:
    """Frame sequence -> [(class id, label, score, (left, top, right, bottom))] from a `--detections` CSV."""
    frames: dict[int, list] = defaultdict(list)
    with path.open(encoding='utf-8-sig', newline='') as handle:
        for row in csv.DictReader(handle):
            frames[int(row['sequence'])].append((int(row['class_id']), row['label'], float(row['confidence']),
                                                 tuple(float(row[k]) for k in ('left', 'top', 'right', 'bottom'))))
    return frames


def read_hierarchy(path: Path = HIERARCHY) -> set[tuple[int, int]]:
    """Pairs of app class IDs that count as the same object: (category, direct or indirect ancestor) from the header the
    app itself uses, plus every pair of ROAD_VEHICLES. The app's own `related_classes` is wider (it relates a handbag to
    footwear through "clothing"), which would flatter the recall."""
    pairs = {(int(a), int(b)) for a, b in re.findall(r'\{(\d+),(\d+)\}', path.read_text(encoding='utf-8'))}
    names = json.loads(VOCABULARY.read_text(encoding='utf-8'))['classes']
    group = [names.index(n) for n in ROAD_VEHICLES if n in names]
    return pairs | {(a, b) for a in group for b in group if a != b}


def related(a: int, b: int, pairs: set[tuple[int, int]]) -> bool:
    return a == b or (a, b) in pairs or (b, a) in pairs


def iou(a: Box, b: Box) -> float:
    width, height = min(a[2], b[2]) - max(a[0], b[0]), min(a[3], b[3]) - max(a[1], b[1])
    if width <= 0 or height <= 0:
        return 0.0
    inside = width * height
    return inside / ((a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inside)


def compare(reference: dict, candidate: dict, ref_score: float, cand_score: float, pairs: set[tuple[int, int]]) -> dict:
    """Per reference class: boxes, how many the candidate also has. Plus candidate boxes without a reference partner."""
    per_class: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    extra = total = 0
    for frame in set(reference) | set(candidate):
        wanted = [d for d in reference.get(frame, ()) if d[2] >= ref_score]
        found = [d for d in candidate.get(frame, ()) if d[2] >= cand_score]
        for class_id, label, _, box in wanted:
            per_class[label][0] += 1
            per_class[label][1] += any(related(class_id, c, pairs) and iou(box, b) >= 0.5 for c, _, _, b in found)
        total += len(found)
        extra += sum(not any(related(c, rc, pairs) and iou(b, rb) >= 0.5 for rc, _, rs, rb in reference.get(frame, ())
                             if rs >= ref_score) for c, _, _, b in found)
    return {'classes': dict(per_class), 'candidate_boxes': total, 'extra': extra}


def pct(found: int, total: int) -> str:
    return f'{found / total:.0%}' if total else '-'


def report(videos: list[str], results: dict[str, dict], ref_score: float, cand_scores: dict[str, float]) -> str:
    """Markdown table: reference classes down, candidates across."""
    names = list(results)
    totals = {n: [sum(v[0] for v in results[n]['classes'].values()), sum(v[1] for v in results[n]['classes'].values())]
              for n in names}
    labels = sorted({l for r in results.values() for l in r['classes']},
                    key=lambda l: -max(results[n]['classes'].get(l, [0])[0] for n in names))
    lines = [f'Reference: YOLOX-S boxes with score >= {ref_score} on {len(videos)} video(s): {", ".join(videos)}.', '',
             'Share of the reference boxes each model also finds (same or parent/child class, IoU >= 0.5):', '',
             '| object | reference boxes | ' + ' | '.join(f'{n} (>= {cand_scores[n]})' for n in names) + ' |',
             '| --- | ---: | ' + ' | '.join('---:' for _ in names) + ' |',
             f'| **all** | {totals[names[0]][0]} | ' + ' | '.join(f'**{pct(*reversed(totals[n]))}**' for n in names) + ' |']
    for label in labels[:30]:
        count = results[names[0]]['classes'].get(label, [0])[0]
        lines.append(f'| {label} | {count} | ' + ' | '.join(
            pct(results[n]['classes'].get(label, [0, 0])[1], count) for n in names) + ' |')
    lines += ['', 'Boxes the model has that match no reference box (mostly classes YOLOX-S cannot name): ' +
              ', '.join(f'{n} {results[n]["extra"]} of {results[n]["candidate_boxes"]}' for n in names) + '.']
    return '\n'.join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--reference', type=Path, nargs='+', required=True,
                        help='YOLOX-S detections CSV, one per video (same order as every --candidate)')
    parser.add_argument('--candidate', action='append', required=True,
                        help='NAME=file[,file...] detections of one model on the same videos; NAME@0.45=... sets its score')
    parser.add_argument('--ref-score', type=float, default=0.5)
    parser.add_argument('--cand-score', type=float, default=0.35, help='default score a candidate box must reach')
    parser.add_argument('--out', type=Path)
    args = parser.parse_args(argv)

    pairs = read_hierarchy()
    results, scores = {}, {}
    for spec in args.candidate:
        name, _, files = spec.partition('=')
        name, _, score = name.partition('@')
        paths = [Path(f) for f in files.split(',')]
        if len(paths) != len(args.reference):
            parser.error(f'{name}: {len(paths)} files for {len(args.reference)} reference files')
        scores[name] = float(score) if score else args.cand_score
        merged: dict = {'classes': defaultdict(lambda: [0, 0]), 'candidate_boxes': 0, 'extra': 0}
        for reference, candidate in zip(args.reference, paths):
            one = compare(read_detections(reference), read_detections(candidate), args.ref_score, scores[name], pairs)
            for label, (count, found) in one['classes'].items():
                merged['classes'][label][0] += count
                merged['classes'][label][1] += found
            merged['candidate_boxes'] += one['candidate_boxes']
            merged['extra'] += one['extra']
        results[name] = {**merged, 'classes': dict(merged['classes'])}
    text = report([p.stem for p in args.reference], results, args.ref_score, scores)
    print(text)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text + '\n', encoding='utf-8')
        args.out.with_suffix('.json').write_text(json.dumps(results, indent=1), encoding='utf-8')
    return 0


if __name__ == '__main__':
    sys.exit(main())
