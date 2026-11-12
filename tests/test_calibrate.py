"""Checks for the score calibration tool's pure logic (no model, no images)."""
import csv
import json
import math
import random
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np

TRAINING = Path(__file__).resolve().parents[1] / 'training'
sys.path.insert(0, str(TRAINING))
import calibrate  # noqa: E402


def draw(curve, count, seed):
    """Boxes whose chance of being right follows `curve` exactly."""
    rng = random.Random(seed)
    rows = []
    for _ in range(count):
        raw = rng.uniform(0.02, 0.95)
        rows.append((raw, rng.random() < calibrate.apply(curve, raw)))
    return rows


class CurveTests(unittest.TestCase):
    def test_fit_recovers_a_known_curve(self):
        truth = (1.5, 2.0)
        slope, offset = calibrate.fit_curve(draw(truth, 6000, 1), None, 0.0)
        self.assertAlmostEqual(slope, truth[0], delta=0.15)
        self.assertAlmostEqual(offset, truth[1], delta=0.2)

    def test_little_evidence_stays_near_the_prior(self):
        prior = (1.0, 0.5)
        few = calibrate.fit_curve([(0.1, True), (0.12, True), (0.2, True)], prior, calibrate.PRIOR_WEIGHT)
        self.assertAlmostEqual(few[0], prior[0], delta=0.3)
        self.assertLess(abs(few[1] - prior[1]), 1.0)
        many = calibrate.fit_curve(draw((1.0, 3.0), 4000, 2), prior, calibrate.PRIOR_WEIGHT)
        self.assertGreater(many[1], 2.5)    # Plenty of evidence overrides the prior.

    def test_curve_is_monotone_and_invertible(self):
        curve = (0.8, 1.2)
        values = [calibrate.apply(curve, raw / 100) for raw in range(2, 99)]
        self.assertEqual(values, sorted(values))
        self.assertAlmostEqual(calibrate.apply(curve, calibrate.raw_for(0.35, curve)), 0.35, places=6)

    def test_bounds_hold_on_one_sided_evidence(self):
        slope, offset = calibrate.fit_curve([(0.3, True)] * 500, None, 0.0)    # Always right: the fit would run away.
        self.assertTrue(calibrate.SLOPE_RANGE[0] <= slope <= calibrate.SLOPE_RANGE[1])
        self.assertTrue(calibrate.OFFSET_RANGE[0] <= offset <= calibrate.OFFSET_RANGE[1])


class DecodeTests(unittest.TestCase):
    def test_decode_matches_the_app(self):
        output = np.full((calibrate.QUERIES, 4 + 615), -20.0, dtype=np.float32)
        output[:, :4] = (0.5, 0.5, 0.2, 0.2)
        output[0, 4 + 600] = 3.0
        output[0, 4] = 2.0
        output[1, 4 + 600] = 4.0      # Same class on the same box: class-wise NMS keeps the stronger one.
        output[2, 4 + 45] = -3.0      # 0.047: kept at the 0.02 floor, far below what the app shows.
        found = calibrate.decode(output, 1000, 500)
        self.assertEqual([c for c, _, _ in found], [600, 0, 45])
        self.assertAlmostEqual(found[0][1], 1 / (1 + math.exp(-4)), places=5)
        self.assertEqual([round(v) for v in found[0][2]], [400, 200, 600, 300])


class FitTests(unittest.TestCase):
    def test_fit_uses_verified_images_only_and_writes_the_app_table(self):
        vocabulary = calibrate.load_vocabulary()
        person = vocabulary['classes'].index('person')
        bowl = vocabulary['classes'].index('bowl')
        rng = random.Random(3)
        images, annotations, predictions = [], [], []
        for number in range(400):
            verified = number % 2 == 0      # Odd images say nothing about either class: their boxes must be ignored.
            images.append({'id': number, 'file_name': f'{number}.jpg', 'width': 1000, 'height': 1000,
                           'oi_verified_positive': [1, 2] if verified else [], 'oi_verified_negative': []})
            detections = []
            for cat, app, right_at in ((1, person, 0.5), (2, bowl, 0.1)):
                raw = rng.uniform(0.03, 0.9)
                x = 100 if cat == 1 else 600
                if verified and raw >= right_at:      # A person box is right from 0.5 up, a bowl box from 0.1 up.
                    annotations.append({'id': len(annotations) + 1, 'image_id': number, 'category_id': cat,
                                        'bbox': [x, 100, 200, 200], 'oi_group_of': 0})
                detections.append([app, raw, [x, 100, x + 200, 300]])
            if not verified:
                detections.append([bowl, 0.95, [0, 0, 50, 50]])    # Would look wrong if unverified images counted.
            predictions.append({'image': f'{number}.jpg', 'detections': detections})
        coco = {'images': images, 'annotations': annotations,
                'categories': [{'id': 1, 'name': 'Person'}, {'id': 2, 'name': 'Bowl'}]}
        with tempfile.TemporaryDirectory() as folder:
            folder = Path(folder)
            (folder / 'coco.json').write_text(json.dumps(coco), encoding='utf-8')
            (folder / 'predictions.jsonl').write_text('\n'.join(json.dumps(p) for p in predictions), encoding='utf-8')
            out = folder / 'model.calibration.csv'
            self.assertEqual(calibrate.main(['fit', '--predictions', str(folder / 'predictions.jsonl'), '--annotations',
                                             str(folder / 'coco.json'), '--others', 'keep', '--out', str(out)]), 0)
            with out.open(encoding='utf-8', newline='') as handle:
                rows = list(csv.reader(handle))
            self.assertEqual(rows[0][:3], ['class_id', 'slope', 'offset'])      # The three columns the app reads.
            table = {int(r[0]): (float(r[1]), float(r[2])) for r in rows[1:]}
            self.assertEqual(set(table), {person, bowl})                        # --others keep: nothing else is written.
            self.assertEqual([int(r[3]) for r in rows[1:]], [200, 200])         # Verified images only.
            # The same raw score means different things: a 0.3 bowl is right, a 0.3 person is not.
            self.assertGreater(calibrate.apply(table[bowl], 0.3), 0.8)
            self.assertLess(calibrate.apply(table[person], 0.3), 0.4)
            self.assertLess(calibrate.raw_for(0.5, table[bowl]), calibrate.raw_for(0.5, table[person]))
            self.assertTrue(out.with_suffix('.md').exists() and out.with_suffix('.json').exists())


if __name__ == '__main__':
    unittest.main()
