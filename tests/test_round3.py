"""Checks for round 3's pure logic: the teacher's decoding, pseudo-labelling and the footage check (no models, no images)."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np

TRAINING = Path(__file__).resolve().parents[1] / 'training'
sys.path.insert(0, str(TRAINING))
import footage_check  # noqa: E402
import oi_metric  # noqa: E402
import pseudo_labels  # noqa: E402
import teacher  # noqa: E402


def image(number, width=1000, height=800, positive=(), negative=()):
    return {'id': number, 'file_name': f'{number}.jpg', 'width': width, 'height': height,
            'oi_verified_positive': list(positive), 'oi_verified_negative': list(negative)}


CATEGORIES = [{'id': 1, 'name': 'Person'}, {'id': 2, 'name': 'Handbag'}, {'id': 3, 'name': 'Car'},
              {'id': 4, 'name': 'Houseplant'}]
TARGETS = {'person': 1, 'handbag': 2, 'car': 3}


class TeacherDecodeTests(unittest.TestCase):
    def output(self):
        return np.zeros((teacher.candidate_count(), teacher.ATTRIBUTES), dtype=np.float32)

    def test_geometry_and_names(self):
        self.assertEqual(teacher.candidate_count(), 8400)
        self.assertEqual(teacher.coco_names()[:3], ['person', 'bicycle', 'car'])
        self.assertEqual(len(teacher.coco_names()), 80)
        columns, rows, strides = teacher.grid()
        self.assertEqual((columns[0], rows[0], strides[0]), (0, 0, 8))
        self.assertEqual((columns[1], rows[1]), (1, 0))                  # Row by row.
        self.assertEqual((columns[6400], rows[6400], strides[6400]), (0, 0, 16))   # 80 x 80 cells of stride 8 first.

    def test_decode_one_box(self):
        out = self.output()
        # Stride-8 cell (x=10, y=20): centre (10 + 0.5, 20 + 0.5) cells, 4 cells wide, 2 high; class 26 (handbag).
        row = 20 * 80 + 10
        out[row, :4] = [0.5, 0.5, np.log(4), np.log(2)]
        out[row, 4] = 0.9
        out[row, 5 + 26] = 0.8
        found = teacher.decode(out, ratio=0.5, width=1280, height=720, confidence=0.3)
        self.assertEqual(len(found), 1)
        class_id, score, box = found[0]
        self.assertEqual(class_id, 26)
        self.assertAlmostEqual(score, 0.72, places=5)
        # Centre (10.5 * 8 / 0.5, 20.5 * 8 / 0.5) = (168, 328); size (4 * 8 / 0.5, 2 * 8 / 0.5) = (64, 32).
        for got, want in zip(box, (136, 312, 200, 344)):
            self.assertAlmostEqual(got, want, places=3)

    def test_nms_is_per_class_and_threshold_applies(self):
        out = self.output()
        for row, cls, objectness in ((100, 0, 0.9), (101, 0, 0.8), (102, 1, 0.7), (103, 0, 0.1)):
            out[row, :4] = [0.5, 0.5, np.log(3), np.log(3)]   # Neighbouring cells: heavily overlapping boxes.
            out[row, 4], out[row, 5 + cls] = objectness, 1.0
        found = teacher.decode(out, 1.0, 640, 640, 0.3)
        self.assertEqual([(c, round(s, 2)) for c, s, _ in found], [(0, 0.9), (1, 0.7)])  # 2nd person suppressed; 0.1 below 0.3

    def test_preprocess_letterboxes_bgr(self):
        rgb = np.zeros((20, 40, 3), dtype=np.uint8)
        rgb[..., 0] = 200                                   # Red image, 2:1.
        tensor, ratio = teacher.preprocess(rgb, size=64)
        self.assertEqual(tensor.shape, (1, 3, 64, 64))
        self.assertAlmostEqual(ratio, 64 / 40)
        self.assertEqual(tensor[0, 2, 10, 10], 200)         # Red lands in the last (BGR) plane.
        self.assertEqual(tensor[0, 0, 10, 10], 0)
        self.assertEqual(tensor[0, 0, 60, 10], 114)         # Below the resized 64 x 32 image: padding.

    def test_bad_output_shape_is_refused(self):
        with self.assertRaises(ValueError):
            teacher.decode(np.zeros((10, 85), dtype=np.float32), 1.0, 640, 640, 0.3)


class ClassMapTests(unittest.TestCase):
    def test_exact_names_aliases_and_merged_sources(self):
        coco = {'categories': CATEGORIES}
        mapped = pseudo_labels.class_map(coco, None, ['person', 'handbag', 'potted plant', 'tv'])
        self.assertEqual(mapped, {'person': 1, 'handbag': 2, 'potted plant': 4})   # tv: no Television in this dataset
        summary = {'classes': [{'id': 1, 'name': 'Person', 'open_images': ['Person', 'Man']}]}
        self.assertEqual(pseudo_labels.class_map(coco, summary, ['man'])['man'], 1)

    def test_real_vocabulary_maps_the_street_classes(self):
        coco = {'categories': [{'id': i, 'name': n} for i, n in enumerate(['Person', 'Handbag', 'Backpack', 'Umbrella'], 1)]}
        self.assertEqual(sorted(pseudo_labels.class_map(coco)), ['backpack', 'handbag', 'person', 'umbrella'])


class FillTests(unittest.TestCase):
    thresholds = {1: 0.5, 2: 0.5, 3: 0.7}

    def add(self, info, boxes, detections):
        return pseudo_labels.new_boxes(info, boxes, detections, TARGETS, self.thresholds)

    def test_adds_only_unverified_classes(self):
        info = image(1, positive=[1], negative=[3])        # Person present, Car verified absent, Handbag unverified.
        detections = [('person', 0.9, (500, 500, 600, 700)), ('car', 0.95, (10, 10, 200, 100)),
                      ('handbag', 0.8, (100, 100, 160, 180))]
        self.assertEqual([c for c, _, _ in self.add(info, [], detections)], [2])

    def test_threshold_per_class_and_unknown_classes(self):
        info = image(1)
        detections = [('car', 0.6, (10, 10, 200, 100)),        # Below Car's 0.7.
                      ('handbag', 0.55, (300, 300, 360, 380)),
                      ('dog', 0.99, (500, 500, 600, 600))]     # Not mapped.
        self.assertEqual([c for c, _, _ in self.add(info, [], detections)], [2])

    def test_skips_boxes_on_top_of_existing_or_better_boxes(self):
        info = image(1)
        existing = [(100, 100, 300, 400)]
        detections = [('handbag', 0.9, (105, 100, 300, 395)),           # Same object as the human box.
                      ('person', 0.8, (600, 100, 700, 300)),
                      ('handbag', 0.6, (602, 102, 698, 298))]           # Same object as the better person box.
        self.assertEqual([c for c, _, _ in self.add(info, existing, detections)], [1])

    def test_tiny_boxes_are_dropped(self):
        info = image(1)
        self.assertEqual(self.add(info, [], [('handbag', 0.9, (10, 10, 15, 15))]), [])   # 5 px on a 1000 px image

    def test_fill_adds_annotations_and_marks_presence(self):
        coco = {'categories': CATEGORIES, 'images': [image(1, positive=[3]), image(2)],
                'annotations': [{'id': 7, 'image_id': 1, 'category_id': 3, 'bbox': [0, 0, 100, 50], 'area': 5000,
                                 'iscrowd': 0, 'oi_group_of': 0, 'oi_depiction': 0}]}
        cache = {'1.jpg': [('handbag', 0.8, (500, 500, 580, 600))], '2.jpg': []}
        filled, report = pseudo_labels.fill(coco, cache, TARGETS, self.thresholds)
        self.assertEqual(len(coco['annotations']), 1)                   # The input is not changed.
        added = [a for a in filled['annotations'] if a.get('oi_pseudo')]
        self.assertEqual(len(added), 1)
        self.assertEqual((added[0]['id'], added[0]['image_id'], added[0]['category_id']), (8, 1, 2))
        self.assertEqual(added[0]['bbox'], [500, 500, 80, 100])
        self.assertEqual(filled['images'][0]['oi_verified_positive'], [2, 3])
        self.assertEqual(filled['images'][1]['oi_verified_positive'], [])
        self.assertEqual((report['boxes_added'], report['per_class']['Handbag']['boxes']), (1, 1))

    def test_images_without_teacher_output_are_left_alone(self):
        coco = {'categories': CATEGORIES, 'images': [image(1)], 'annotations': []}
        filled, report = pseudo_labels.fill(coco, {}, TARGETS, self.thresholds)
        self.assertEqual((filled['annotations'], report['images_without_teacher_output']), ([], 1))


class MeasureTests(unittest.TestCase):
    def truth(self):
        return {'a.jpg': oi_metric.ImageTruth({1, 2}, set(), [(2, 100, 100, 200, 200, False)]),
                'b.jpg': oi_metric.ImageTruth(set(), {2}, []),
                'c.jpg': oi_metric.ImageTruth(set(), set(), [])}       # Handbag unverified on c.

    def test_right_wrong_and_unverified(self):
        detections = {'a.jpg': [('handbag', 0.9, (100, 100, 200, 200)), ('handbag', 0.45, (400, 400, 450, 450))],
                      'b.jpg': [('handbag', 0.8, (50, 50, 90, 90))],      # Verified absent: wrong.
                      'c.jpg': [('handbag', 0.9, (50, 50, 90, 90))]}      # Unverified: not counted.
        measured = pseudo_labels.measure_precision(self.truth(), detections, {'handbag': 2}, thresholds=(0.4, 0.5))
        self.assertEqual(measured['handbag']['0.4'], {'right': 1, 'wrong': 2})
        self.assertEqual(measured['handbag']['0.5'], {'right': 1, 'wrong': 1})

    def test_threshold_choice(self):
        measured = {'handbag': {'0.4': {'right': 6, 'wrong': 4}, '0.5': {'right': 18, 'wrong': 2}, '0.6': {'right': 9, 'wrong': 0}},
                    'bench': {'0.4': {'right': 1, 'wrong': 9}, '0.5': {'right': 1, 'wrong': 5}},
                    'tiny': {'0.4': {'right': 3, 'wrong': 0}}}
        chosen = pseudo_labels.choose_thresholds(measured, 0.8, 15)
        self.assertEqual(chosen['handbag']['threshold'], 0.5)       # 0.4 is too imprecise, 0.5 the lowest that qualifies
        self.assertNotIn('bench', chosen)                           # Never precise enough
        self.assertNotIn('tiny', chosen)                            # Too few checked boxes

    def test_cache_round_trip(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'cache.jsonl'
            path.write_text(json.dumps({'image': 'a.jpg', 'detections': [['person', 0.9, [1, 2, 3, 4]]]}) + '\n', encoding='utf-8')
            self.assertEqual(pseudo_labels.read_cache(path), {'a.jpg': [('person', 0.9, (1, 2, 3, 4))]})
            self.assertEqual(pseudo_labels.read_cache(Path(folder) / 'missing.jsonl'), {})


class FootageCheckTests(unittest.TestCase):
    pairs = {(540, 2)}   # taxi < car, as in the app's hierarchy header

    def test_hierarchy_is_read_from_the_apps_header(self):
        pairs = footage_check.read_hierarchy()
        self.assertGreater(len(pairs), 500)
        self.assertTrue(footage_check.related(2, 2, pairs))
        self.assertTrue(footage_check.related(552, 2, pairs) and footage_check.related(2, 552, pairs))   # Taxi and car
        self.assertTrue(footage_check.related(7, 552, pairs))                                            # Truck and taxi
        self.assertFalse(footage_check.related(0, 2, pairs))                                             # Person and car
        self.assertFalse(footage_check.related(26, 269, pairs))                                          # Handbag and footwear

    def test_recall_against_confident_reference_boxes(self):
        reference = {0: [(26, 'handbag', 0.9, (100, 100, 150, 150)), (2, 'car', 0.8, (300, 300, 500, 400)),
                         (26, 'handbag', 0.3, (600, 600, 650, 650))]}      # Below the reference score: not counted
        candidate = {0: [(540, 'taxi', 0.5, (305, 300, 500, 395)),         # Taxi covers the reference car
                         (269, 'footwear', 0.7, (10, 10, 40, 40))]}        # Nothing in the reference: extra
        result = footage_check.compare(reference, candidate, 0.5, 0.35, self.pairs)
        self.assertEqual(result['classes'], {'handbag': [1, 0], 'car': [1, 1]})
        self.assertEqual((result['candidate_boxes'], result['extra']), (2, 1))

    def test_candidate_score_filters(self):
        reference = {0: [(0, 'person', 0.9, (0, 0, 10, 20))]}
        candidate = {0: [(0, 'person', 0.3, (0, 0, 10, 20))]}
        self.assertEqual(footage_check.compare(reference, candidate, 0.5, 0.35, set())['classes'], {'person': [1, 0]})
        self.assertEqual(footage_check.compare(reference, candidate, 0.5, 0.25, set())['classes'], {'person': [1, 1]})

    def test_detections_csv(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'd.csv'
            path.write_text('﻿sequence,timestamp_us,class_id,label,confidence,left,top,right,bottom,detection_ms\n'
                            '3,0,26,handbag,0.5,1,2,3,4,10\n', encoding='utf-8')
            self.assertEqual(footage_check.read_detections(path), {3: [(26, 'handbag', 0.5, (1.0, 2.0, 3.0, 4.0))]})


if __name__ == '__main__':
    unittest.main()
