"""Checks for the RF-DETR training pipeline's pure logic (no network, models or images)."""
import sys
import tempfile
import unittest
from pathlib import Path

TRAINING = Path(__file__).resolve().parents[1] / 'training'
sys.path.insert(0, str(TRAINING))
import evaluate  # noqa: E402
import oi_metric  # noqa: E402
import openimages  # noqa: E402


def truth(boxes, positive=(1,), negative=()):
    return oi_metric.ImageTruth(set(positive), set(negative), list(boxes))


class AveragePrecisionTests(unittest.TestCase):
    def test_perfect_and_empty(self):
        self.assertAlmostEqual(oi_metric.average_precision([0.9, 0.8], [True, True], 2), 1.0)
        self.assertAlmostEqual(oi_metric.average_precision([], [], 3), 0.0)

    def test_precision_envelope(self):
        # TP, FP, TP over 2 objects: recall 0.5 at precision 1, recall 1 at precision 2/3.
        self.assertAlmostEqual(oi_metric.average_precision([0.9, 0.8, 0.7], [True, False, True], 2),
                               0.5 * 1 + 0.5 * (2 / 3))

    def test_undefined_without_ground_truth(self):
        with self.assertRaises(ValueError):
            oi_metric.average_precision([0.5], [False], 0)


class OpenImagesRuleTests(unittest.TestCase):
    cats = {1: 'Dog', 2: 'Cat'}

    def test_duplicate_detection_is_false_positive(self):
        t = {'a': truth([(1, 0, 0, 10, 10, False)])}
        d = {'a': [(1, 0.9, (0, 0, 10, 10)), (1, 0.8, (0, 0, 10, 9))]}
        result = oi_metric.evaluate(t, d, self.cats)['per_class']['Dog']
        self.assertEqual((result['true_positives'], result['detections_scored']), (1, 2))
        self.assertAlmostEqual(result['ap'], 1.0)

    def test_unverified_class_is_ignored(self):
        # Cat is neither verified present nor absent on image a: cat detections there do not count.
        t = {'a': truth([(1, 0, 0, 10, 10, False)], positive=(1,))}
        d = {'a': [(2, 0.99, (50, 50, 60, 60))]}
        result = oi_metric.evaluate(t, d, self.cats)
        self.assertEqual(result['per_class']['Cat']['detections_scored'], 0)
        self.assertIsNone(result['per_class']['Cat']['ap'])

    def test_verified_absent_class_counts_false_positives(self):
        t = {'a': truth([(1, 0, 0, 10, 10, False)], positive=(1,), negative=(2,)),
             'b': truth([(2, 0, 0, 10, 10, False)], positive=(2,))}
        d = {'a': [(2, 0.99, (50, 50, 60, 60))], 'b': [(2, 0.5, (0, 0, 10, 10))]}
        cat = oi_metric.evaluate(t, d, self.cats)['per_class']['Cat']
        self.assertEqual(cat['detections_scored'], 2)
        self.assertAlmostEqual(cat['ap'], 0.5)  # The higher-scored detection is the false alarm.

    def test_group_of_box_counts_once(self):
        t = {'a': truth([(1, 0, 0, 100, 100, True)])}
        d = {'a': [(1, 0.9, (0, 0, 20, 20)), (1, 0.8, (30, 30, 50, 50)), (1, 0.7, (60, 60, 80, 80))]}
        dog = oi_metric.evaluate(t, d, self.cats)['per_class']['Dog']
        self.assertEqual((dog['ground_truth'], dog['detections_scored'], dog['true_positives']), (1, 1, 1))
        self.assertAlmostEqual(dog['ap'], 1.0)

    def test_detection_outside_group_is_false_positive(self):
        t = {'a': truth([(1, 0, 0, 10, 10, True)])}
        d = {'a': [(1, 0.9, (20, 20, 40, 40))]}
        self.assertAlmostEqual(oi_metric.evaluate(t, d, self.cats)['per_class']['Dog']['ap'], 0.0)

    def test_merged_duplicates_suppressed(self):
        items = [(1, 0.9, (0, 0, 10, 10)), (1, 0.8, (0, 0, 10, 10.5)), (2, 0.7, (0, 0, 10, 10))]
        self.assertEqual(evaluate.suppress_duplicates(items), [items[0], items[2]])

    def test_truth_from_coco_adds_box_evidence(self):
        coco = {'images': [{'id': 1, 'file_name': 'x.jpg', 'oi_verified_positive': [], 'oi_verified_negative': [2]}],
                'annotations': [{'image_id': 1, 'category_id': 1, 'bbox': [1, 2, 3, 4], 'oi_group_of': 1}],
                'categories': [{'id': 1, 'name': 'Dog'}, {'id': 2, 'name': 'Cat'}]}
        t, names = oi_metric.truth_from_coco(coco)
        self.assertEqual(t['x.jpg'].positive, {1})
        self.assertEqual(t['x.jpg'].boxes, [(1, 1, 2, 4, 6, True)])
        self.assertEqual(names, {1: 'Dog', 2: 'Cat'})


class DatasetBuildTests(unittest.TestCase):
    mids = {'Person': '/m/p', 'Man': '/m/man', 'Dog': '/m/d', 'Cat': '/m/c'}

    def spec(self, text):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'classes.txt'
            path.write_text(text, encoding='utf-8')
            return openimages.parse_class_spec(path, self.mids)

    def test_class_spec_merges_and_numbers(self):
        cats = self.spec('# comment\nPerson = Person, Man\nDog\n')
        self.assertEqual([(c.id, c.name, c.sources) for c in cats],
                         [(1, 'Person', ('Person', 'Man')), (2, 'Dog', ('Dog',))])

    def test_class_spec_rejects_unknown_and_duplicate(self):
        with self.assertRaises(ValueError):
            self.spec('Unicorn\n')
        with self.assertRaises(ValueError):
            self.spec('Person = Person, Man\nMan\n')

    def test_duplicate_merged_boxes_removed(self):
        boxes = {'a': [(1, 0, .5, 0, .5, 0, 0), (1, .01, .5, 0, .5, 0, 0), (2, 0, .5, 0, .5, 0, 0)]}
        self.assertEqual(openimages.deduplicate(boxes, merged={1}), 1)
        self.assertEqual(len(boxes['a']), 2)

    def test_selection_is_balanced_and_deterministic(self):
        cats = [openimages.Category(1, 'Dog', ('Dog',)), openimages.Category(2, 'Cat', ('Cat',))]
        boxes = {f'd{i}': [(1, 0, 1, 0, 1, 0, 0)] for i in range(10)}
        boxes.update({f'c{i}': [(2, 0, 1, 0, 1, 0, 0)] for i in range(3)})
        first = openimages.select_images(boxes, cats, cap=2, seed=5, exclude={'d0'})
        self.assertEqual(first, openimages.select_images(boxes, cats, cap=2, seed=5, exclude={'d0'}))
        self.assertEqual(sum(i.startswith('c') for i in first), 2)
        self.assertEqual(sum(i.startswith('d') for i in first), 2)
        self.assertNotIn('d0', first)

    def test_build_coco_converts_boxes_and_verdicts(self):
        cats = [openimages.Category(1, 'Dog', ('Dog',)), openimages.Category(2, 'Cat', ('Cat',))]
        boxes = {'a': [(1, .1, .5, .2, .6, 1, 0)]}
        coco = openimages.build_coco(['a', 'missing'], {'a': (200, 100)}, boxes, {'a': (set(), {2})}, cats)
        self.assertEqual(len(coco['images']), 1)
        image, annotation = coco['images'][0], coco['annotations'][0]
        self.assertEqual((image['oi_verified_positive'], image['oi_verified_negative']), ([1], [2]))
        self.assertEqual(annotation['bbox'], [20.0, 20.0, 80.0, 40.0])
        self.assertEqual((annotation['oi_group_of'], annotation['iscrowd']), (1, 0))


if __name__ == '__main__':
    unittest.main()
