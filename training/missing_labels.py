"""Train with incomplete Open Images labels: a switch for Phase 3 (`train.py --unverified-weight`), off by default.

Open Images does not label every object on every image. rfdetr's classification loss (IoU-aware BCE) pushes every
class towards "absent" on every query that is not matched to a box, so an unlabelled cup teaches the model that
cups are background, and a box labelled Dog teaches it that the dog is not an Animal. This module re-weights the
"absent" part of that loss per image and class:

- classes human-verified on the image (present or absent) and classes with boxes: weight 1, as before;
- parents of a class that is present (Dog present: Animal, Carnivore, Mammal): weight 0, because they are true
  but have no box of their own to be matched to;
- classes an image lists as unknown (`oi_unknown`, written by mix_coco.py: Van on a COCO photo with a car, a type
  that COCO only marks as a crowd): weight 0 as well, even when the class also has boxes on the image;
- every other class: `unverified_weight`. 0 ignores them entirely, which removes nearly all "absent" signal on a
  595-class image and invites false detections; 1 is rfdetr's plain loss. A value in between keeps some.

Only the training loss changes; validation losses, scoring and the exported model are untouched. The loss code
below is rfdetr 1.11.2's (`SetCriterion.loss_labels`, IoU-aware BCE branch) with the weights applied, so `install`
refuses other rfdetr versions.
"""
from __future__ import annotations

import json
from pathlib import Path

RFDETR_VERSION = '1.11.2'
CHECK_IMAGES = 2000


def label_index(categories: list[dict]) -> dict[int, int]:
    """COCO category id -> rfdetr label: position in id order (rfdetr's own mapping for our datasets)."""
    return {int(c['id']): label for label, c in enumerate(sorted(categories, key=lambda c: int(c['id'])))}


def image_table(coco: dict, ancestors: dict[int, set[int]] | None = None) -> dict[int, tuple[list[int], list[int]]]:
    """Image id -> (labels verified on it, labels not to push towards "absent": parents of present classes that
    have no box of their own, and the classes the image lists as unknown)."""
    labels = label_index(coco['categories'])
    table = {}
    for image in coco['images']:
        positive = set(image.get('oi_verified_positive', ()))
        verified = positive | set(image.get('oi_verified_negative', ()))
        parents = set()
        for cat in positive:
            parents |= (ancestors or {}).get(cat, set())
        parents = (parents - verified) | set(image.get('oi_unknown', ()))
        table[int(image['id'])] = (sorted(labels[c] for c in verified if c in labels),
                                   sorted(labels[c] for c in parents if c in labels))
    return table


def class_weights(table: dict, image_ids: list[int], classes: int, columns: int, unverified_weight: float):
    """[images, 1, columns] weights for the classification loss; columns past `classes` (no-object) keep 1."""
    import torch
    weights = torch.full((len(image_ids), columns), float(unverified_weight))
    for row, image_id in enumerate(image_ids):
        entry = table.get(image_id)
        if entry is None:  # Not a training image we know: plain loss.
            weights[row] = 1.0
            continue
        verified, parents = entry
        weights[row, verified] = 1.0
        weights[row, parents] = 0.0
    weights[:, classes:] = 1.0
    return weights[:, None, :]


def check_targets(table: dict, image_ids: list[int], labels: list[list[int]]) -> None:
    """Stop if the trainer's image ids are not the annotation file's: every box label of an image is verified on
    that image by construction, so a label outside its entry means the weights would go to the wrong images."""
    for image_id, image_labels in zip(image_ids, labels):
        entry = table.get(image_id)
        if entry is None:
            raise RuntimeError(f'--unverified-weight: the trainer reports image id {image_id}, which the training '
                               f'annotations do not contain')
        stray = set(image_labels) - set(entry[0])
        if stray:
            raise RuntimeError(f'--unverified-weight: image id {image_id} has boxes of labels {sorted(stray)} that its '
                               f'annotation entry does not list; the image ids do not match the annotation file')


def install(train_annotations: Path, classes: int, unverified_weight: float,
            ancestors: dict[int, set[int]] | None = None) -> dict:
    """Patch rfdetr's classification loss for this process. Returns a summary for the run record."""
    from importlib.metadata import version
    if version('rfdetr') != RFDETR_VERSION:
        raise SystemExit(f'--unverified-weight is written against rfdetr {RFDETR_VERSION}, found {version("rfdetr")}')
    import torch
    import torch.nn.functional as F
    from rfdetr.models import criterion

    coco = json.loads(train_annotations.read_text(encoding='utf-8'))
    table = image_table(coco, ancestors)
    original = criterion.SetCriterion.loss_labels
    checked = [0]

    def loss_labels(self, outputs, targets, indices, num_boxes, log=True, matched_targets=None):
        src_logits = outputs['pred_logits']
        if not (self.ia_bce_loss and torch.is_grad_enabled() and src_logits.shape[-1] >= classes):
            return original(self, outputs, targets, indices, num_boxes, log=log, matched_targets=matched_targets)
        valid_mask = self._matched_valid_mask(targets, indices)
        if matched_targets is None:
            idx = self._get_src_permutation_idx(indices)
            target_classes_o = torch.cat([t['labels'][J] for t, (_, J) in zip(targets, indices)])
            target_boxes = torch.cat([t['boxes'][i] for t, (_, i) in zip(targets, indices)], dim=0)
        else:
            idx, target_classes_o, target_boxes = (matched_targets.source_indices, matched_targets.labels,
                                                   matched_targets.boxes)
        alpha, gamma = self.focal_alpha, 2
        src_boxes = outputs['pred_boxes'][idx]
        iou_targets, _ = criterion.box_ops.elementwise_box_iou(
            criterion.box_ops.box_cxcywh_to_xyxy(src_boxes.detach()),
            criterion.box_ops.box_cxcywh_to_xyxy(target_boxes))
        pos_ious = iou_targets.clone().detach()
        prob = src_logits.sigmoid()
        pos_weights = torch.zeros_like(src_logits)
        neg_weights = prob ** gamma
        pos_ind = list(idx)
        pos_ind.append(target_classes_o)
        t = torch.clamp(prob[tuple(pos_ind)].pow(alpha) * pos_ious.pow(1 - alpha), 0.01).detach()
        if valid_mask is None:
            pos_weights[tuple(pos_ind)] = t.to(pos_weights.dtype)
            neg_weights[tuple(pos_ind)] = 1 - t.to(neg_weights.dtype)
        else:
            keep = valid_mask.to(torch.bool)
            pos_weights[tuple(pos_ind)] = (t * valid_mask).to(pos_weights.dtype)
            neg_weights[tuple(pos_ind)] = torch.where(keep, (1 - t).to(neg_weights.dtype), neg_weights[tuple(pos_ind)])
        image_ids = [int(target['image_id']) for target in targets]
        if checked[0] < CHECK_IMAGES:      # The first images of a run: are these ids the annotation file's?
            check_targets(table, image_ids, [target['labels'].tolist() for target in targets])
            checked[0] += len(image_ids)
        weights = class_weights(table, image_ids, classes, src_logits.shape[-1], unverified_weight)
        neg_weights = neg_weights * weights.to(device=src_logits.device, dtype=neg_weights.dtype)
        loss_ce = neg_weights * src_logits - F.logsigmoid(src_logits) * (pos_weights + neg_weights)
        losses = {'loss_ce': loss_ce.sum() / num_boxes}
        if log:
            if valid_mask is None:
                losses['class_error'] = 100 - criterion.accuracy(src_logits[idx], target_classes_o)[0]
            else:
                correct = (src_logits[idx].argmax(dim=-1) == target_classes_o).to(valid_mask.dtype)
                losses['class_error'] = 100 - 100 * (correct * valid_mask).sum() / valid_mask.sum().clamp(min=1)
        return losses

    criterion.SetCriterion.loss_labels = loss_labels
    verified = sum(len(v) for v, _ in table.values())
    parents = sum(len(p) for _, p in table.values())
    return {'unverified_weight': unverified_weight, 'images': len(table),
            'verified_labels_per_image': round(verified / max(1, len(table)), 2),
            'parent_labels_ignored_per_image': round(parents / max(1, len(table)), 2),   # Parents and unknown classes.
            'images_listing_unknown_classes': sum(1 for i in coco['images'] if i.get('oi_unknown'))}
