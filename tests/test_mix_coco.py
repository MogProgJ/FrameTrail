"""Checks for adding COCO photos to an Open Images dataset (no network, no model)."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

TRAINING = Path(__file__).resolve().parents[1] / 'training'
sys.path.insert(0, str(TRAINING))
import missing_labels  # noqa: E402
import mix_coco  # noqa: E402

CLASSES = ['Person', 'Car', 'Taxi', 'Van', 'Cattle', 'Bull', 'Coffee cup', 'Mug', 'Television', 'Computer monitor',
           'Mouse', 'Computer mouse', 'Table', 'Footwear', 'Tree']


def categories(names=CLASSES):
    return [{'id': i, 'name': name, 'supercategory': 'object'} for i, name in enumerate(names, 1)]


def cat(name, cats):
    return next(c['id'] for c in cats if c['name'] == name)


def coco_file(annotations, images=(1, 2, 3)):
    types = ['person', 'car', 'cow', 'cup', 'tv', 'mouse', 'dining table', 'zebra']
    return {'categories': [{'id': 10 + i, 'name': t} for i, t in enumerate(types)],
            'images': [{'id': i, 'file_name': f'{i:012d}.jpg', 'width': 640, 'height': 480} for i in images],
            'annotations': [{'image_id': image, 'category_id': 10 + types.index(t), 'bbox': list(box),
                             'area': box[2] * box[3], 'iscrowd': crowd} for image, t, box, crowd in annotations]}


class ClassMapTests(unittest.TestCase):
    def test_types_go_to_the_class_that_means_the_same(self):
        cats, _ = mix_coco.with_new_classes(categories(), {'cup', 'person'})
        mapping = mix_coco.class_map(cats)
        name = {c['id']: c['name'] for c in cats}
        shown = {t: (name[p], [name[n] for n in narrower]) for t, (p, narrower) in mapping.items()}
        self.assertEqual(shown['car'], ('Car', ['Taxi', 'Van']))
        self.assertEqual(shown['cow'], ('Cattle', ['Bull']))
        self.assertEqual(shown['cup'], ('Cup', ['Coffee cup', 'Mug']))          # The added class, not Mug.
        self.assertEqual(shown['tv'], ('Television', ['Computer monitor']))
        self.assertEqual(shown['mouse'], ('Computer mouse', []))                # The class named Mouse is the animal.
        self.assertEqual(shown['dining table'], ('Table', []))
        self.assertNotIn('zebra', shown)                                        # No such class in this list.
        self.assertEqual(len(shown), 7)

    def test_cup_is_added_once_and_only_when_coco_has_it(self):
        cats, added = mix_coco.with_new_classes(categories(), {'cup'})
        self.assertEqual((added, cats[-1]), (['Cup'], {'id': 16, 'name': 'Cup', 'supercategory': 'object'}))
        self.assertEqual(mix_coco.with_new_classes(cats, {'cup'})[1], [])
        self.assertEqual(mix_coco.with_new_classes(categories(), {'person'})[1], [])

    def test_the_real_class_list_covers_all_80_types(self):
        targets = [line.split('#')[0].split('=')[0].strip()
                   for line in (TRAINING / 'classes' / 'full.txt').read_text(encoding='utf-8').splitlines()]
        cats, added = mix_coco.with_new_classes(categories([t for t in targets if t]), {'cup'})
        mapping = mix_coco.class_map(cats)
        self.assertEqual((len(cats), added, len(mapping)), (596, ['Cup'], 80))
        self.assertEqual(len({p for p, _ in mapping.values()}), 80)


class ConvertTests(unittest.TestCase):
    def setUp(self):
        self.cats, _ = mix_coco.with_new_classes(categories(), {'cup'})
        self.mapping = mix_coco.class_map(self.cats)

    def ids(self, *names):
        return {cat(n, self.cats) for n in names}

    def test_what_a_coco_photo_vouches_for(self):
        coco = coco_file([(1, 'car', (10, 10, 100, 50), 0), (1, 'person', (0, 0, 50, 100), 0),
                          (1, 'person', (300, 0, 300, 200), 1),          # A crowd of people besides the boxed one.
                          (1, 'cow', (0, 300, 200, 100), 1),             # Cows only as a crowd.
                          (1, 'zebra', (5, 5, 50, 50), 0),               # No class: dropped, nothing vouched.
                          (2, 'cup', (5, 5, 0.5, 20), 0),                # Too thin to train on, and photo 2 has nothing else.
                          (3, 'cup', (5, 5, 30, 30), 0)])
        records, dropped = mix_coco.convert(coco, self.mapping)
        self.assertEqual([r['coco_id'] for r in records], [1, 3])
        first = records[0]
        self.assertEqual(first['positive'], self.ids('Car', 'Person'))
        self.assertEqual(first['unknown'], self.ids('Taxi', 'Van', 'Person', 'Cattle', 'Bull', 'Table'))
        self.assertEqual(first['negative'], self.ids('Cup', 'Coffee cup', 'Mug', 'Television', 'Computer monitor',
                                                     'Computer mouse'))       # Never "no Table": ours is wider.
        self.assertEqual(sorted(b[0] for b in first['boxes']), sorted(self.ids('Car', 'Person')))
        self.assertEqual(records[1]['positive'], self.ids('Cup'))
        self.assertEqual(records[1]['unknown'], self.ids('Coffee cup', 'Mug', 'Table'))
        self.assertEqual(dropped, {'boxes of types without a class': 1, 'boxes under 1 px': 1,
                                   'photos without a usable box': 1})
        for record in records:                                           # Footwear, Tree, Mouse: never vouched for.
            self.assertFalse((record['positive'] | record['negative'] | record['unknown'])
                             & self.ids('Footwear', 'Tree', 'Mouse'))

    def test_tv_gives_no_boxes_and_table_no_absence(self):
        coco = coco_file([(1, 'tv', (10, 10, 100, 50), 0), (1, 'dining table', (0, 200, 400, 200), 0),
                          (2, 'tv', (10, 10, 100, 50), 0)])              # Photo 2 has only a tv: nothing to train on.
        records, dropped = mix_coco.convert(coco, self.mapping)
        self.assertEqual([r['coco_id'] for r in records], [1])
        record = records[0]
        self.assertEqual(record['positive'], self.ids('Table'))
        self.assertEqual([b[0] for b in record['boxes']], [cat('Table', self.cats)])
        self.assertEqual(record['unknown'], self.ids('Table', 'Television', 'Computer monitor'))
        self.assertEqual(dropped['boxes of types that lump several classes'], 2)

    def test_cap_keeps_rare_classes(self):
        coco = coco_file([(i, 'person', (0, 0, 50, 50), 0) for i in range(1, 9)] + [(8, 'cup', (0, 0, 20, 20), 0)],
                         images=range(1, 9))
        records, _ = mix_coco.convert(coco, self.mapping)
        chosen = mix_coco.select(records, 3)
        self.assertEqual([r['coco_id'] for r in chosen], [1, 2, 8])       # The one cup photo first, then people up to 3.
        self.assertEqual(len(mix_coco.select(records, None)), 8)

    def test_open_images_photos_with_a_narrower_class(self):
        images = [{'id': 1, 'oi_verified_positive': list(self.ids('Mug')), 'oi_verified_negative': []},
                  {'id': 2, 'oi_verified_positive': list(self.ids('Taxi', 'Car')), 'oi_verified_negative': []},
                  {'id': 3, 'oi_verified_positive': list(self.ids('Computer monitor')),
                   'oi_verified_negative': list(self.ids('Television'))},
                  {'id': 4, 'oi_verified_positive': list(self.ids('Tree')), 'oi_verified_negative': []}]
        self.assertEqual(mix_coco.mark_open_images(images, self.mapping), 1)
        self.assertEqual(images[0]['oi_unknown'], sorted(self.ids('Cup')))
        self.assertTrue(all('oi_unknown' not in i for i in images[1:]))   # Verified classes keep their verdict.


class DatasetTests(unittest.TestCase):
    def build(self, folder):
        from PIL import Image
        data, photos = folder / 'data', folder / 'photos'
        cats = categories()
        for role in mix_coco.ROLES:
            (data / role).mkdir(parents=True)
            images = [{'id': 1, 'file_name': 'oi1.jpg', 'width': 1000, 'height': 500,
                       'oi_verified_positive': [cat('Mug', cats)], 'oi_verified_negative': [cat('Tree', cats)]}]
            boxes = [{'id': 1, 'image_id': 1, 'category_id': cat('Mug', cats), 'bbox': [100, 50, 200, 100], 'area': 20000,
                      'iscrowd': 0, 'oi_group_of': 0, 'oi_depiction': 0}]
            Image.new('RGB', (1000, 500), 'gray').save(data / role / 'oi1.jpg')
            (data / role / '_annotations.coco.json').write_text(json.dumps(
                {'info': {}, 'images': images, 'annotations': boxes, 'categories': cats}), encoding='utf-8')
        (data / 'dataset.json').write_text(json.dumps(
            {'classes': [{'id': c['id'], 'name': c['name'], 'open_images': [c['name']]} for c in cats]}), encoding='utf-8')
        photos.mkdir()
        Image.new('RGB', (640, 480), 'white').save(photos / f'{1:012d}.jpg')
        Image.new('RGB', (320, 240), 'white').save(photos / f'{3:012d}.jpg')     # Not the size the annotations state.
        coco = coco_file([(1, 'car', (10, 10, 100, 50), 0), (2, 'person', (0, 0, 50, 100), 0), (3, 'cup', (5, 5, 30, 30), 0)])
        (folder / 'coco.json').write_text(json.dumps(coco), encoding='utf-8')
        return data, photos

    def test_shrink_then_add_and_add_again(self):
        with tempfile.TemporaryDirectory() as folder:
            folder = Path(folder)
            data, photos = self.build(folder)
            self.assertEqual(mix_coco.main(['shrink', '--dataset', str(data), '--max-side', '640']), 0)
            train = json.loads((data / 'train' / '_annotations.coco.json').read_text(encoding='utf-8'))
            self.assertEqual((train['images'][0]['width'], train['images'][0]['height']), (640, 320))
            self.assertEqual(train['annotations'][0]['bbox'], [64.0, 32.0, 128.0, 64.0])
            self.assertEqual(mix_coco.main(['shrink', '--dataset', str(data), '--max-side', '640']), 0)   # Nothing to do.
            self.assertEqual(mix_coco.main(['status', '--dataset', str(data)]), 1)
            command = ['add', '--dataset', str(data), '--annotations', str(folder / 'coco.json'), '--images-dir', str(photos)]
            for _ in range(2):                                           # The second run starts from the original again.
                self.assertEqual(mix_coco.main(command), 0)
                train = json.loads((data / 'train' / '_annotations.coco.json').read_text(encoding='utf-8'))
                cats = train['categories']
                self.assertEqual([i['file_name'] for i in train['images']], ['oi1.jpg', 'coco_000000000001.jpg'])
                self.assertEqual(train['images'][0]['oi_unknown'], [cat('Cup', cats)])      # A mug is a cup.
                added = train['images'][1]
                self.assertEqual((added['id'], added['oi_verified_positive']), (2, [cat('Car', cats)]))
                self.assertEqual(added['oi_unknown'], sorted([cat('Taxi', cats), cat('Van', cats), cat('Table', cats)]))
                self.assertEqual([(a['id'], a['image_id'], a['category_id'], a['bbox']) for a in train['annotations'][1:]],
                                 [(2, 2, cat('Car', cats), [10.0, 10.0, 100.0, 50.0])])
                self.assertTrue((data / 'train' / 'coco_000000000001.jpg').is_file())
                self.assertFalse((data / 'train' / 'coco_000000000003.jpg').exists())      # Wrong size: removed.
            self.assertEqual(mix_coco.main(['status', '--dataset', str(data)]), 0)
            report = json.loads((data / 'mix_coco.json').read_text(encoding='utf-8'))
            self.assertEqual((report['photos_added'], report['photos_skipped'], report['classes_added']), (1, 2, ['Cup']))
            for role in ('valid', 'test'):                               # The same class list in every split.
                other = json.loads((data / role / '_annotations.coco.json').read_text(encoding='utf-8'))
                self.assertEqual([c['name'] for c in other['categories']], [c['name'] for c in cats])
                self.assertEqual(len(other['images']), 1)
            described = json.loads((data / 'dataset.json').read_text(encoding='utf-8'))
            self.assertEqual(described['classes'][-1], {'id': 16, 'name': 'Cup', 'open_images': [], 'coco': True})
            # The loss reads it: on the COCO photo Car is verified and Taxi and Van are left alone.
            table = missing_labels.image_table(train)
            labels = missing_labels.label_index(cats)
            verified, ignored = table[2]
            self.assertIn(labels[cat('Car', cats)], verified)
            self.assertIn(labels[cat('Mug', cats)], verified)            # No cup on the photo, so no mug either.
            self.assertEqual(ignored, sorted(labels[cat(n, cats)] for n in ('Taxi', 'Van', 'Table')))
            self.assertNotIn(labels[cat('Tree', cats)], verified + ignored)


if __name__ == '__main__':
    unittest.main()
