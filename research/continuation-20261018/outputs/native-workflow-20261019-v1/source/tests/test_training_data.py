import copy
import csv
from contextlib import closing
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest

SCRIPTS = Path(__file__).resolve().parents[1] / 'scripts'
sys.path.insert(0, str(SCRIPTS))
import training_data as data


class DatasetContracts(unittest.TestCase):
    def setUp(self):
        from PIL import Image
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.images = []
        # Distinct patterns exercise actual image bytes/fingerprints and the bundle round trip.
        for number, split in enumerate(data.SPLITS):
            image = Image.new('RGB', (32, 24))
            image.putdata([((x * 17 + number * 33) % 256, (y * 23 + number * 71) % 256,
                            ((x ^ y) * 19 + number * 53) % 256) for y in range(24) for x in range(32)])
            path = self.root / f'{number}.jpg'
            image.save(path)
            width, height, dhash, _ = data.image_info(path)
            self.images.append({'id': str(number), 'path': path.name, 'width': width, 'height': height,
                'sha256': data.digest(path), 'dhash': dhash, 'group_id': f'camera-{number}', 'split': split,
                'publisher_split': 'train', 'review': {'complete_target_classes': False, 'rights_verified': False},
                'objects': [{'raw_id': 0, 'box': [0, 0, 16, 12]}]})
        self.manifest = {'schema': 1, 'classes': data.vocabulary(), 'images': self.images}
        self.path = self.root / 'manifest.json'
        self.save()

    def tearDown(self):
        self.temp.cleanup()

    def save(self):
        data.write_json(self.path, self.manifest)

    def test_smoke_bundle_roundtrip_and_both_formats(self):
        output = self.root / 'bundle'
        lock = data.export_bundle(self.path, output, smoke=True)
        self.assertEqual(lock['purpose'], 'mechanical-smoke-only')
        self.assertEqual(data.verify_bundle(output, smoke=True)['images'], {'train': 1, 'val': 1, 'test': 1})
        self.assertEqual(len(data.read_json(output / 'data.yaml')['names']), 601)
        coco = data.read_json(output / 'coco/train/_annotations.coco.json')
        self.assertEqual(coco['annotations'][0]['bbox'], [0, 0, 16, 12])
        self.assertEqual((output / 'train/labels/0.txt').read_text(encoding='utf-8').split(),
                         ['0', '0.250000000', '0.250000000', '0.500000000', '0.500000000'])
        with self.assertRaisesRegex(ValueError, 'smoke'):
            data.verify_bundle(output)

    def test_review_gate_and_publisher_eval_leakage(self):
        with self.assertRaisesRegex(ValueError, 'reviewed'):
            data.validate_manifest(self.path)
        for image in self.images:
            image['review'] = {'complete_target_classes': True, 'rights_verified': True}
        self.save()
        data.validate_manifest(self.path)
        self.images[0]['publisher_split'] = 'validation'
        self.save()
        with self.assertRaisesRegex(ValueError, 'Publisher evaluation'):
            data.validate_manifest(self.path)

    def test_source_groups_and_exact_duplicates_do_not_cross_splits(self):
        self.images[1]['group_id'] = self.images[0]['group_id']
        self.save()
        with self.assertRaisesRegex(ValueError, 'Source group'):
            data.validate_manifest(self.path, True)
        self.images[1]['group_id'] = 'other'
        for field in ('path', 'sha256', 'dhash'):
            self.images[1][field] = self.images[0][field]
        self.save()
        with self.assertRaisesRegex(ValueError, 'Duplicate image content'):
            data.validate_manifest(self.path, True)

    def test_image_mutation_and_invalid_boxes_fail(self):
        self.images[0]['objects'][0]['box'][2] = 33
        self.save()
        with self.assertRaisesRegex(ValueError, 'box'):
            data.validate_manifest(self.path, True)
        self.images[0]['objects'][0]['box'][2] = 16
        self.save()
        (self.root / '0.jpg').write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError, 'changed'):
            data.validate_manifest(self.path, True)

    def test_label_order_path_escape_and_missing_partition_fail(self):
        swapped = copy.deepcopy(self.manifest['classes'])
        swapped[0], swapped[1] = swapped[1], swapped[0]
        self.manifest['classes'] = swapped
        self.save()
        with self.assertRaisesRegex(ValueError, 'class map'):
            data.validate_manifest(self.path, True)
        self.manifest['classes'] = data.vocabulary()
        self.images[0]['path'] = '../outside.jpg'
        self.save()
        with self.assertRaisesRegex(ValueError, 'escapes'):
            data.validate_manifest(self.path, True)
        self.images[0]['path'] = '0.jpg'
        self.images[2]['split'] = 'val'
        self.save()
        with self.assertRaisesRegex(ValueError, 'partitions'):
            data.validate_manifest(self.path, True)

    def test_bundle_tampering_and_existing_destination_fail(self):
        output = self.root / 'bundle'
        data.export_bundle(self.path, output, True)
        with self.assertRaises(FileExistsError):
            data.export_bundle(self.path, output, True)
        (output / 'train/labels/0.txt').write_text('16 .5 .5 1 1\n', encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'bundle changed'):
            data.verify_bundle(output, True)

    def test_split_is_stable_by_source_group(self):
        self.assertEqual(data.split_for('camera-1', 17), data.split_for('camera-1', 17))
        self.assertIn(data.split_for('camera-1', 17), data.SPLITS)

    def test_repository_scope_covers_six_domains_with_supported_categories(self):
        policy = data.read_json(data.ROOT / 'training/scope.json')
        names = {item['canonical_name'] for item in data.vocabulary()}
        self.assertEqual(len(policy['domains']), 6)
        self.assertTrue(all(name in names for domain in policy['domains'].values() for name in domain))
        self.assertIn('fox_dog_confusion', policy['hard_slices'])
        self.assertTrue(any(item['family'] == 'RF-DETR Small' for item in policy['shortlist']))

    def test_training_preflight_preserves_full_head_and_bounds_smoke(self):
        spec = importlib.util.spec_from_file_location('train_detector', SCRIPTS / 'train-detector.py')
        training = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(training)
        output = self.root / 'bundle'
        data.export_bundle(self.path, output, True)
        config = data.read_json(data.ROOT / 'training/general-smoke.json')
        weights = data.ROOT / '.deps/world-export/weights/yolov8s-oiv7.pt'
        if weights.exists():
            report = training.preflight(output, config, 'smoke', weights)
            self.assertEqual((report['raw_labels'], report['canonical_categories']), (601, 597))
        config['epochs'] = 2
        with self.assertRaisesRegex(ValueError, 'one epoch'):
            training.preflight(output, config, 'smoke', self.root / 'unused.pt')

    def test_unregistered_images_and_download_instructions_are_rejected(self):
        output = self.root / 'bundle'
        data.export_bundle(self.path, output, True)
        extra = output / 'train/images/unreviewed.jpg'
        extra.write_bytes((output / 'train/images/0.jpg').read_bytes())
        with self.assertRaisesRegex(ValueError, 'Unregistered'):
            data.verify_bundle(output, True)
        extra.unlink()
        config = data.read_json(output / 'data.yaml')
        config['download'] = 'unexpected download instruction'
        data.write_json(output / 'data.yaml', config)
        lock = data.read_json(output / 'dataset-lock.json')
        lock['files']['data.yaml'] = data.digest(output / 'data.yaml')
        data.write_json(output / 'dataset-lock.json', lock)
        with self.assertRaisesRegex(ValueError, 'download instructions'):
            data.verify_bundle(output, True)

    def test_catalogue_is_atomic_and_records_full_vocabulary(self):
        classes = self.root / 'classes.csv'
        with classes.open('w', newline='', encoding='utf-8') as stream:
            csv.writer(stream).writerows((f'/class/{item["raw_id"]}', item['name']) for item in data.vocabulary())
        metadata = self.root / 'metadata.csv'
        with metadata.open('w', newline='', encoding='utf-8') as stream:
            writer = csv.DictWriter(stream, fieldnames=['ImageID', 'Subset', 'OriginalLandingURL', 'OriginalURL',
                'License', 'Author', 'AuthorProfileURL', 'Title', 'Rotation'])
            writer.writeheader()
            writer.writerow(dict(ImageID='0000000000000001', Subset='train', OriginalLandingURL='source',
                OriginalURL='image', License='CC BY', Author='author', AuthorProfileURL='profile', Title='title', Rotation='0'))
        boxes = self.root / 'boxes.csv'
        fields = ['ImageID','LabelName','XMin','YMin','XMax','YMax','IsOccluded','IsTruncated','IsGroupOf','IsDepiction','Source']
        row = dict(zip(fields, ['0000000000000001','/class/0',0,0,1,1,0,0,0,0,'xclick']))
        def write_boxes():
            with boxes.open('w', newline='', encoding='utf-8') as stream:
                writer = csv.DictWriter(stream, fieldnames=fields)
                writer.writeheader(); writer.writerow(row)
        write_boxes()
        target = self.root / 'catalogue.sqlite'
        data.catalogue(boxes, classes, metadata, target, 'train')
        with closing(data.sqlite3.connect(target)) as connection:
            self.assertEqual(connection.execute('SELECT COUNT(*) FROM classes').fetchone()[0],601)
            self.assertEqual(connection.execute('SELECT COUNT(*) FROM boxes').fetchone()[0],1)
        with self.assertRaises(FileExistsError):
            data.catalogue(boxes, classes, metadata, target, 'train')
        row['XMax'] = 2
        write_boxes()
        failed = self.root / 'failed.sqlite'
        with self.assertRaisesRegex(ValueError, 'box'):
            data.catalogue(boxes, classes, metadata, failed, 'train')
        self.assertFalse(failed.exists())
        self.assertFalse(list(self.root.glob('*.partial')))


if __name__ == '__main__':
    unittest.main()
