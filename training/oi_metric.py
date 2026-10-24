"""Open Images-style average precision at IoU 0.5.

Follows the Open Images Challenge rules (TF Object Detection API, `OpenImagesDetectionChallengeEvaluator`):

- A class is only scored on images where it was human-verified present or absent.
  Detections of that class on other images are ignored, because the labels are not exhaustive.
- Detections match ordinary boxes greedily by score at IoU >= 0.5; a second detection of the same
  object is a false positive.
- A detection that matches no ordinary box but lies mostly inside a group-of box
  (intersection over detection area >= 0.5) is a true positive for that group once;
  further detections inside the same group are ignored, not penalised.
- Each group-of box counts as one ground-truth object.
- AP is the area under the precision envelope over all recall points (VOC 2010+ style).

Boxes are (x0, y0, x1, y1) in pixels.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ImageTruth:
    positive: set[int]
    negative: set[int]
    boxes: list[tuple[int, float, float, float, float, bool]]  # (cat, x0, y0, x1, y1, group_of)


def _area(b) -> float:
    return max(0.0, b[2] - b[0]) * max(0.0, b[3] - b[1])


def _intersection(a, b) -> float:
    return max(0.0, min(a[2], b[2]) - max(a[0], b[0])) * max(0.0, min(a[3], b[3]) - max(a[1], b[1]))


def _iou(a, b) -> float:
    inter = _intersection(a, b)
    union = _area(a) + _area(b) - inter
    return inter / union if union > 0 else 0.0


def _ioa(detection, group) -> float:
    area = _area(detection)
    return _intersection(detection, group) / area if area > 0 else 0.0


def average_precision(scores: list[float], labels: list[bool], ground_truth: int) -> float:
    """All-point interpolated AP from per-detection (score, is_true_positive)."""
    if ground_truth == 0:
        raise ValueError('AP is undefined without ground truth')
    order = sorted(range(len(scores)), key=lambda i: -scores[i])
    precision, recall, true_positives = [], [], 0
    for rank, index in enumerate(order, 1):
        true_positives += labels[index]
        precision.append(true_positives / rank)
        recall.append(true_positives / ground_truth)
    for i in range(len(precision) - 2, -1, -1):  # Precision envelope: best precision at any higher recall.
        precision[i] = max(precision[i], precision[i + 1])
    ap, previous_recall = 0.0, 0.0
    for p, r in zip(precision, recall):
        ap += p * (r - previous_recall)
        previous_recall = r
    return ap


def _score_image(detections, boxes, threshold):
    """Return [(score, is_tp)] for one image and class, ignoring detections absorbed by group-of boxes."""
    ordinary = [b for b in boxes if not b[4]]
    groups = [b for b in boxes if b[4]]
    matched = [False] * len(ordinary)
    results, group_best = [], {}
    for score, box in sorted(detections, key=lambda d: -d[0]):
        best, best_iou = -1, threshold
        for i, truth in enumerate(ordinary):
            overlap = _iou(box, truth)
            if overlap >= best_iou:
                best, best_iou = i, overlap
        if best >= 0:
            # Greedy by score: the best-overlapping box is taken; if already taken, this is a duplicate.
            results.append((score, not matched[best]))
            matched[best] = True
            continue
        group = max(range(len(groups)), key=lambda g: _ioa(box, groups[g]), default=None)
        if group is not None and _ioa(box, groups[group]) >= threshold:
            group_best[group] = max(group_best.get(group, score), score)
            continue
        results.append((score, False))
    results.extend((score, True) for score in group_best.values())
    return results


def evaluate(truth: dict[str, ImageTruth], detections: dict[str, list[tuple[int, float, tuple]]],
             categories: dict[int, str], threshold: float = 0.5) -> dict:
    """Per-class AP and mean AP.

    truth: image id -> ImageTruth. detections: image id -> [(cat, score, (x0, y0, x1, y1))].
    Detections on images missing from `truth` are ignored.
    """
    per_class = {}
    for cat, name in categories.items():
        scores, labels, ground_truth, images = [], [], 0, 0
        for image_id, image in truth.items():
            if cat not in image.positive and cat not in image.negative:
                continue
            images += 1
            boxes = [(b[1], b[2], b[3], b[4], b[5]) for b in image.boxes if b[0] == cat]
            ground_truth += len(boxes)
            found = [(score, box) for c, score, box in detections.get(image_id, ()) if c == cat]
            for score, is_tp in _score_image(found, boxes, threshold):
                scores.append(score)
                labels.append(is_tp)
        per_class[name] = {
            'ap': average_precision(scores, labels, ground_truth) if ground_truth else None,
            'ground_truth': ground_truth, 'verified_images': images,
            'detections_scored': len(scores), 'true_positives': sum(labels)}
    scored = [v['ap'] for v in per_class.values() if v['ap'] is not None]
    return {'map50': sum(scored) / len(scored) if scored else None, 'classes_scored': len(scored),
            'per_class': per_class}


def subset_map(result: dict, names: list[str]) -> float | None:
    values = [result['per_class'][n]['ap'] for n in names
              if n in result['per_class'] and result['per_class'][n]['ap'] is not None]
    return sum(values) / len(values) if values else None


def truth_from_coco(coco: dict) -> tuple[dict[str, ImageTruth], dict[int, str]]:
    """Read our COCO export (with oi_verified_* and oi_group_of fields), keyed by file name."""
    by_id = {}
    truth = {}
    for image in coco['images']:
        record = ImageTruth(set(image.get('oi_verified_positive', ())), set(image.get('oi_verified_negative', ())), [])
        truth[image['file_name']] = record
        by_id[image['id']] = record
    for annotation in coco['annotations']:
        x, y, w, h = annotation['bbox']
        by_id[annotation['image_id']].boxes.append(
            (annotation['category_id'], x, y, x + w, y + h, bool(annotation.get('oi_group_of', 0))))
    for record in truth.values():  # A box is presence evidence even without an image-level verdict.
        record.positive.update(b[0] for b in record.boxes)
    return truth, {c['id']: c['name'] for c in coco['categories']}

