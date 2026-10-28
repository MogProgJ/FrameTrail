"""Open Images class hierarchy, for a score in which a child also counts as its parents.

Open Images nests its classes (Dog < Carnivore < Mammal < Animal, Taxi < Car < Land vehicle < Vehicle), and its
challenge scores with the hierarchy: a box labelled Dog is also ground truth for Animal. The flat score treats
the two as unrelated, so a model that says Dog where an annotator wrote Animal gets no credit. This module
expands both sides before scoring:

- ground-truth boxes and verified-present labels go up to every ancestor class;
- verified-absent labels go down to every descendant (no Animal on the image means no Dog either);
- each detection is copied to every ancestor with the same box and score.

After expansion, near-identical boxes of one class (an annotated Animal box and the Animal copy of a Dog box on
the same animal) are merged, so one object stays one ground truth; evaluate.py's class-wise NMS does the same
for detections. The challenge's own tool expands ground truth only and leaves expanding detections to each
entrant; expanding both models' detections the same way keeps the comparison fair.
"""
from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

import oi_metric

URL = 'https://storage.googleapis.com/openimages/2018_04/bbox_labels_600_hierarchy.json'
SAME_OBJECT_IOU = 0.7


def ancestors_by_category(hierarchy: dict, mid_by_name: dict[str, str], classes: list[dict]) -> dict[int, set[int]]:
    """Category id -> ids of the categories above it. `classes` are dataset.json entries (id, open_images names)."""
    cat_by_mid = {mid_by_name[name]: entry['id'] for entry in classes for name in entry['open_images']
                  if name in mid_by_name}
    parents: dict[str, set[str]] = defaultdict(set)

    def walk(node: dict) -> None:
        for child in node.get('Subcategory', ()):
            parents[child['LabelName']].add(node['LabelName'])
            walk(child)
    walk(hierarchy)

    def above(mid: str) -> set[str]:
        found, stack = set(), [mid]
        while stack:
            for parent in parents.get(stack.pop(), ()):
                if parent not in found:
                    found.add(parent)
                    stack.append(parent)
        return found

    result: dict[int, set[int]] = defaultdict(set)
    for mid, cat in cat_by_mid.items():
        result[cat] |= {cat_by_mid[m] for m in above(mid) if m in cat_by_mid} - {cat}
    return dict(result)


def for_dataset(dataset: Path, cache: Path) -> dict[int, set[int]] | None:
    """Ancestors of each category of a dataset built by openimages.py, or None (no dataset.json, no network)."""
    summary = dataset / 'dataset.json'
    if not summary.exists():
        return None
    try:
        import openimages
        tree = json.loads(openimages.fetch(URL, cache).read_text(encoding='utf-8'))
        mid_by_name = openimages.read_class_descriptions(openimages.fetch(openimages.META['classes'], cache))
    except Exception as error:  # No network or pandas: callers carry on without the hierarchy.
        print(f'Open Images class hierarchy unavailable: {error}', flush=True)
        return None
    ancestors = ancestors_by_category(tree, mid_by_name, json.loads(summary.read_text(encoding='utf-8'))['classes'])
    return ancestors if any(ancestors.values()) else None


def expand_truth(truth: dict[str, oi_metric.ImageTruth], ancestors: dict[int, set[int]]) -> dict[str, oi_metric.ImageTruth]:
    descendants: dict[int, set[int]] = defaultdict(set)
    for cat, above in ancestors.items():
        for parent in above:
            descendants[parent].add(cat)
    expanded = {}
    for image_id, image in truth.items():
        positive = set(image.positive)
        for cat in image.positive:
            positive |= ancestors.get(cat, set())
        negative = set(image.negative)
        for cat in image.negative:
            negative |= descendants.get(cat, set())
        boxes = list(image.boxes)
        for cat, x0, y0, x1, y1, group_of in image.boxes:
            for parent in ancestors.get(cat, ()):
                if not any(b[0] == parent and oi_metric._iou(b[1:5], (x0, y0, x1, y1)) > SAME_OBJECT_IOU for b in boxes):
                    boxes.append((parent, x0, y0, x1, y1, group_of))
                positive.add(parent)
        expanded[image_id] = oi_metric.ImageTruth(positive, negative - positive, boxes)
    return expanded


def expand_detections(detections: dict[str, list[tuple[int, float, tuple]]],
                      ancestors: dict[int, set[int]]) -> dict[str, list[tuple[int, float, tuple]]]:
    return {image: items + [(parent, score, box) for cat, score, box in items for parent in ancestors.get(cat, ())]
            for image, items in detections.items()}
