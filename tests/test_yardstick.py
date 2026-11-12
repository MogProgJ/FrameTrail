"""Checks for yardstick A's pure logic (no model, no images)."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

TRAINING = Path(__file__).resolve().parents[1] / 'training'
sys.path.insert(0, str(TRAINING))
import coco_yardstick as yardstick  # noqa: E402


class MappingTests(unittest.TestCase):
    def test_equivalents_and_narrower_classes_count(self):
        vocabulary = json.loads(yardstick.VOCABULARY.read_text(encoding='utf-8'))
        names = [n.lower() for n in vocabulary['classes']]
        mapping = yardstick.coco_classes()
        self.assertEqual([mapping[i] for i in range(80)], names[:80])            # Every COCO type counts as itself.
        for app, coco in (('cattle', 'cow'), ('mug', 'cup'), ('coffee cup', 'cup'), ('table', 'dining table'),
                          ('taxi', 'car'), ('houseplant', 'potted plant'), ('mixing bowl', 'bowl')):
            self.assertEqual(mapping[names.index(app)], coco, app)
        for app in ('footwear', 'tree', 'clothing', 'animal', 'vehicle', 'food'):   # Not one of the 80, or a parent.
            self.assertNotIn(names.index(app), mapping, app)
        self.assertEqual(mapping[names.index('raven')], 'bird')                  # Narrower Open Images class.

    def test_missing_equivalent_names_are_skipped(self):
        mapping = yardstick.coco_classes({'classes': [f'c{i}' for i in range(80)] + ['other']}, '')
        self.assertEqual(len(mapping), 80)


class MatchTests(unittest.TestCase):
    def test_duplicates_crowds_and_misses(self):
        boxes = [((0, 0, 100, 100), False, 10000), ((200, 0, 300, 100), False, 10000), ((400, 0, 600, 200), True, 40000)]
        detections = [(0.9, (0, 0, 100, 100)), (0.8, (2, 2, 100, 100)),      # Right, then a second box on the same object.
                      (0.7, (410, 10, 500, 100)),                              # Inside the crowd region: not counted.
                      (0.6, (700, 700, 800, 800))]                             # Nothing there.
        results, found = yardstick.match(detections, boxes)
        self.assertEqual(results, [(0.9, True), (0.8, False), (0.6, False)])
        self.assertEqual(found, [0.9, 0.0])                                    # The second object was missed.

    def test_low_overlap_is_wrong(self):
        results, found = yardstick.match([(0.9, (0, 0, 100, 40))], [((0, 0, 100, 100), False, 10000)])
        self.assertEqual((results, found), ([(0.9, False)], [0.0]))


class ScoreTests(unittest.TestCase):
    def test_report_numbers(self):
        coco = {'categories': [{'id': 1, 'name': 'person'}, {'id': 47, 'name': 'cup'}],
                'images': [{'id': 1, 'file_name': 'a.jpg', 'width': 640, 'height': 480},
                           {'id': 2, 'file_name': 'b.jpg', 'width': 640, 'height': 480}],
                'annotations': [{'image_id': 1, 'category_id': 1, 'bbox': [0, 0, 200, 400], 'area': 80000, 'iscrowd': 0},
                                {'image_id': 1, 'category_id': 47, 'bbox': [300, 300, 20, 20], 'area': 400, 'iscrowd': 0},
                                {'image_id': 2, 'category_id': 1, 'bbox': [100, 100, 50, 100], 'area': 5000, 'iscrowd': 0}]}
        names = [n.lower() for n in json.loads(yardstick.VOCABULARY.read_text(encoding='utf-8'))['classes']]
        mug, person, tree = names.index('mug'), names.index('person'), names.index('tree')
        rows = [{'image': 'a.jpg', 'detections': [[person, 0.9, [0, 0, 200, 400]], [mug, 0.2, [300, 300, 320, 320]],
                                                  [tree, 0.99, [0, 0, 640, 480]]]},       # A tree cannot be judged: left out.
                {'image': 'b.jpg', 'detections': [[person, 0.5, [300, 300, 400, 400]]]}]  # Wrong place: the person is missed.
        with tempfile.TemporaryDirectory() as folder:
            folder = Path(folder)
            (folder / 'coco.json').write_text(json.dumps(coco), encoding='utf-8')
            (folder / 'model.jsonl').write_text('\n'.join(json.dumps(r) for r in rows), encoding='utf-8')
            out = folder / 'report.md'
            self.assertEqual(yardstick.main(['score', '--annotations', str(folder / 'coco.json'),
                                             '--model', f"m={folder / 'model.jsonl'}", '--out', str(out)]), 0)
            summary = json.loads(out.with_suffix('.json').read_text(encoding='utf-8'))
        model = summary['models']['m']
        self.assertEqual((model['objects'], model['boxes']), (3, 2))                 # At 0.35: two person boxes shown.
        self.assertAlmostEqual(model['found'], 1 / 3)
        self.assertAlmostEqual(model['right'], 1 / 2)
        self.assertEqual(model['by_size']['small'], [0.0, 1])                        # The mug scored 0.2: found only below the setting.
        self.assertEqual(model['by_size']['large'], [1.0, 1])
        self.assertAlmostEqual(summary['types']['cup']['m']['ap'], 1.0)              # AP ignores the setting: the mug box is right.
        self.assertAlmostEqual(summary['types']['person']['m']['ap'], 0.5)


if __name__ == '__main__':
    unittest.main()
