"""Checks for the RF-DETR training pipeline's pure logic (no network, models or images)."""
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

TRAINING = Path(__file__).resolve().parents[1] / 'training'
sys.path.insert(0, str(TRAINING))
import checkpoints  # noqa: E402
import evaluate  # noqa: E402
import hierarchy  # noqa: E402
import missing_labels  # noqa: E402
import export  # noqa: E402
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

    def test_images_of_earlier_datasets_are_reused(self):
        with tempfile.TemporaryDirectory() as folder:
            earlier, target = Path(folder) / 'pilot', Path(folder) / 'full' / 'a.jpg'
            (earlier / 'test').mkdir(parents=True)
            (earlier / 'test' / 'a.jpg').write_bytes(b'jpeg')
            target.parent.mkdir()
            self.assertTrue(openimages.reuse_image('a', target, [earlier]))
            self.assertEqual(target.read_bytes(), b'jpeg')
            self.assertFalse(openimages.reuse_image('b', target.with_name('b.jpg'), [earlier]))


class HierarchyTests(unittest.TestCase):
    tree = {'LabelName': '/m/root', 'Subcategory': [
        {'LabelName': '/m/animal', 'Subcategory': [{'LabelName': '/m/dog'}, {'LabelName': '/m/cat'}]}]}
    mids = {'Animal': '/m/animal', 'Dog': '/m/dog', 'Cat': '/m/cat'}
    classes = [{'id': 1, 'name': 'Animal', 'open_images': ['Animal']}, {'id': 2, 'name': 'Dog', 'open_images': ['Dog']},
               {'id': 3, 'name': 'Cat', 'open_images': ['Cat']}]

    def ancestors(self):
        return hierarchy.ancestors_by_category(self.tree, self.mids, self.classes)

    def test_ancestors_follow_the_tree(self):
        self.assertEqual(self.ancestors(), {1: set(), 2: {1}, 3: {1}})

    def test_truth_expands_up_and_negatives_down(self):
        truth = {'a': oi_metric.ImageTruth({2}, set(), [(2, 0, 0, 10, 10, False)]),
                 'b': oi_metric.ImageTruth(set(), {1}, []),
                 'c': oi_metric.ImageTruth({1, 2}, set(), [(1, 0, 0, 10, 10, False), (2, 0, 0, 10, 10, False)])}
        expanded = hierarchy.expand_truth(truth, self.ancestors())
        self.assertEqual(expanded['a'].positive, {1, 2})
        self.assertIn((1, 0, 0, 10, 10, False), expanded['a'].boxes)
        self.assertEqual(expanded['b'].negative, {1, 2, 3})
        self.assertEqual(len(expanded['c'].boxes), 2, 'an Animal box and a Dog box on one animal stay one Animal')

    def test_child_detection_scores_for_the_parent(self):
        truth = {'a': oi_metric.ImageTruth({2}, set(), [(2, 0, 0, 10, 10, False)])}
        detections = {'a': [(2, 0.9, (0, 0, 10, 10))]}
        categories = {1: 'Animal', 2: 'Dog', 3: 'Cat'}
        flat = oi_metric.evaluate(truth, detections, categories)
        self.assertIsNone(flat['per_class']['Animal']['ap'])
        ancestors = self.ancestors()
        expanded = oi_metric.evaluate(hierarchy.expand_truth(truth, ancestors),
                                      hierarchy.expand_detections(detections, ancestors), categories)
        self.assertEqual((expanded['per_class']['Animal']['ap'], expanded['per_class']['Dog']['ap']), (1.0, 1.0))


class MissingLabelTests(unittest.TestCase):
    coco = {'categories': [{'id': 2, 'name': 'Dog'}, {'id': 1, 'name': 'Animal'}, {'id': 3, 'name': 'Cup'}],
            'images': [{'id': 7, 'oi_verified_positive': [2], 'oi_verified_negative': [3]},
                       {'id': 8, 'oi_verified_positive': [], 'oi_verified_negative': []}]}

    def test_labels_follow_category_id_order(self):
        self.assertEqual(missing_labels.label_index(self.coco['categories']), {1: 0, 2: 1, 3: 2})

    def test_table_marks_verified_labels_and_unboxed_parents(self):
        table = missing_labels.image_table(self.coco, {2: {1}, 1: set(), 3: set()})
        self.assertEqual(table[7], ([1, 2], [0]))
        self.assertEqual(table[8], ([], []))

    def test_unknown_classes_are_not_pushed_even_with_boxes(self):
        coco = {'categories': self.coco['categories'],
                'images': [{'id': 7, 'oi_verified_positive': [2], 'oi_verified_negative': [], 'oi_unknown': [2, 3]}]}
        self.assertEqual(missing_labels.image_table(coco)[7], ([1], [1, 2]))

    def test_image_ids_must_be_the_annotation_files(self):
        table = missing_labels.image_table(self.coco)
        missing_labels.check_targets(table, [7, 8], [[1], []])            # Dog boxes on image 7: consistent.
        with self.assertRaises(RuntimeError):
            missing_labels.check_targets(table, [8], [[1]])               # Image 8 lists no Dog: the ids are off.
        with self.assertRaises(RuntimeError):
            missing_labels.check_targets(table, [99], [[]])

    @unittest.skipUnless(importlib.util.find_spec('torch'), 'needs torch')
    def test_weights(self):
        table = missing_labels.image_table(self.coco, {2: {1}, 1: set(), 3: set()})
        weights = missing_labels.class_weights(table, [7, 8, 99], classes=3, columns=4, unverified_weight=0.25)
        self.assertEqual(weights.shape, (3, 1, 4))
        self.assertEqual(weights[0, 0].tolist(), [0.0, 1.0, 1.0, 1.0])  # Animal is true via Dog; no-object keeps 1.
        self.assertEqual(weights[1, 0].tolist(), [0.25, 0.25, 0.25, 1.0])
        self.assertEqual(weights[2, 0].tolist(), [1.0, 1.0, 1.0, 1.0])  # Unknown image: plain loss.


@unittest.skipUnless(importlib.util.find_spec('rfdetr'), 'needs rfdetr')
class MissingLabelLossTests(unittest.TestCase):
    """The patched loss is rfdetr's own when every weight is 1, and only lowers the "absent" part otherwise."""

    def losses(self, weight, table_images):
        import torch
        from rfdetr.models import criterion
        torch.manual_seed(3)
        outputs = {'pred_logits': torch.randn(2, 5, 4), 'pred_boxes': torch.rand(2, 5, 4) * 0.5 + 0.25}
        targets = [{'labels': torch.tensor([1]), 'boxes': torch.tensor([[0.5, 0.5, 0.2, 0.2]]), 'image_id': torch.tensor(1)},
                   {'labels': torch.tensor([0, 2]), 'boxes': torch.tensor([[0.4, 0.4, 0.2, 0.2], [0.6, 0.6, 0.1, 0.1]]),
                    'image_id': torch.tensor(2)}]
        indices = [(torch.tensor([3]), torch.tensor([0])), (torch.tensor([0, 4]), torch.tensor([0, 1]))]
        owner = criterion.SetCriterion.__new__(criterion.SetCriterion)
        torch.nn.Module.__init__(owner)
        owner.ia_bce_loss, owner.focal_alpha = True, 0.25
        original = criterion.SetCriterion.loss_labels
        with tempfile.TemporaryDirectory() as folder:
            annotations = Path(folder) / 'train.json'
            annotations.write_text(json.dumps({'categories': [{'id': i + 1, 'name': str(i)} for i in range(3)],
                                               'images': table_images}), encoding='utf-8')
            try:
                missing_labels.install(annotations, 3, weight)
                patched = criterion.SetCriterion.loss_labels(owner, outputs, targets, indices, torch.tensor(3.0))
            finally:
                criterion.SetCriterion.loss_labels = original
        plain = original(owner, outputs, targets, indices, torch.tensor(3.0))
        return float(plain['loss_ce']), float(patched['loss_ce'])

    def test_weight_one_is_rfdetrs_loss(self):
        plain, patched = self.losses(1.0, [])
        self.assertAlmostEqual(plain, patched, places=6)

    def test_unverified_classes_count_less(self):
        images = [{'id': 1, 'oi_verified_positive': [2], 'oi_verified_negative': []},
                  {'id': 2, 'oi_verified_positive': [1, 3], 'oi_verified_negative': []}]
        plain, patched = self.losses(0.0, images)
        self.assertLess(patched, plain)
        self.assertGreater(patched, 0)


@unittest.skipUnless(importlib.util.find_spec('torch'), 'needs torch')
class CheckpointTests(unittest.TestCase):
    def test_head_classes_reads_model_and_lightning_layouts(self):
        import torch
        with tempfile.TemporaryDirectory() as folder:
            weights, archive = Path(folder) / 'best.pth', Path(folder) / 'last.ckpt'
            torch.save({'model': {'class_embed.bias': torch.zeros(111)}}, weights)
            torch.save({'state_dict': {'model.class_embed.bias': torch.zeros(596)}}, archive)
            self.assertEqual(checkpoints.head_classes(weights), 110)
            self.assertEqual(checkpoints.head_classes(archive), 595)


class AppExportTests(unittest.TestCase):
    vocabulary = json.loads((TRAINING.parent / 'dependencies' / 'recognition-vocabulary.json').read_text(encoding='utf-8'))

    def test_every_class_list_maps_to_distinct_app_categories(self):
        for path in sorted((TRAINING / 'classes').glob('*.txt')):
            lines = (raw.split('#', 1)[0].strip() for raw in path.read_text(encoding='utf-8').splitlines())
            names = [line.partition('=')[0].strip() for line in lines if line]
            with self.subTest(path.name):
                self.assertEqual(len(set(export.app_columns(names, self.vocabulary))), len(names))

    def test_open_images_names_use_the_app_mapping(self):
        self.assertEqual(export.app_columns(['Person', 'Mobile phone', 'Table'], self.vocabulary), [0, 67, 544])

    def test_unknown_or_clashing_classes_are_refused(self):
        with self.assertRaises(SystemExit):
            export.app_columns(['Person', 'Flux capacitor'], self.vocabulary)
        with self.assertRaises(SystemExit):
            export.app_columns(['Person', 'Man'], self.vocabulary)


if __name__ == '__main__':
    unittest.main()
