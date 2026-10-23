"""SQLite-only sampler regression tests; no Pillow, network or GPU required."""
import argparse
from collections import Counter
import contextlib
import importlib.util
import io
import json
from pathlib import Path
import shutil
import sqlite3
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('balanced_pilot', ROOT / 'scripts/select-balanced-pilot.py')
sampler = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sampler)


def database(path=':memory:'):
    db = sqlite3.connect(path)
    db.executescript('''CREATE TABLE images(id TEXT PRIMARY KEY, rotation TEXT, license TEXT);
        CREATE TABLE classes(raw_id INTEGER PRIMARY KEY, canonical_id INTEGER);
        CREATE TABLE boxes(image_id TEXT, raw_id INTEGER, group_of INTEGER, depiction INTEGER);
        CREATE TABLE meta(key TEXT PRIMARY KEY, value TEXT);''')
    return db


def add(db, image_id, raw_id, rotation='0', license='https://creativecommons.org/licenses/by/2.0/', group=0, depiction=0):
    db.execute('INSERT OR IGNORE INTO images VALUES(?,?,?)', (image_id, rotation, license))
    db.execute('INSERT OR IGNORE INTO classes VALUES(?,?)', (raw_id, raw_id))
    db.execute('INSERT INTO boxes VALUES(?,?,?,?)', (image_id, raw_id, group, depiction))


def policy(domains, cap, quota):
    return dict(schema=1, id='test', seed=17, domains=domains, max_images=cap,
                images_per_category=quota, max_download_bytes=1000000000)


class BalancedPilotTests(unittest.TestCase):
    def test_all_52_anchors_before_repeat_and_600_cap(self):
        p = sampler.read(ROOT / 'training/general-intake-pilot.json')
        names = {name: index for index, name in enumerate(name for values in p['domains'].values() for name in values)}
        with contextlib.closing(database()) as db:
            for name, index in names.items():
                for j in range(15):
                    add(db, f'{index:08x}{j:08x}', index)
            selected, eligible = sampler.select_balanced(db, p, names)
        counts = Counter(item['selected_category'] for item in selected)
        self.assertEqual(len(selected), 600)
        self.assertEqual(len({item['id'] for item in selected}), 600)
        self.assertEqual(len(counts), 52)
        self.assertEqual(len({item['selected_category'] for item in selected[:52]}), 52)
        self.assertEqual(set(counts.values()), {11, 12})
        self.assertEqual(counts['lantern'], 11)
        self.assertEqual(counts['balloon'], 11)
        self.assertEqual(set(eligible.values()), {15})

    def test_deterministic_overlap_exclusions_and_repeat(self):
        p = policy({'domain': ['a', 'b']}, 4, 2)
        with contextlib.closing(database()) as db:
            for raw in range(2):
                for image_id in ('excluded', 'shared', f'own-{raw}', f'extra-{raw}'):
                    add(db, image_id, raw)
            first, available = sampler.select_balanced(db, p, {'a': 0, 'b': 1}, ['excluded'])
            second, _ = sampler.select_balanced(db, p, {'a': 0, 'b': 1}, ['excluded'])
        self.assertEqual(first, second)
        self.assertEqual(len(first), len({item['id'] for item in first}))
        self.assertNotIn('excluded', {item['id'] for item in first})
        self.assertEqual(available, {'a': 3, 'b': 3})

    def test_eligibility_and_empty_anchor_are_explicit(self):
        p = policy({'domain': ['a', 'b']}, 4, 2)
        with contextlib.closing(database()) as db:
            add(db, 'valid', 0)
            add(db, 'rotated', 0, rotation='90')
            add(db, 'wrong-license', 0, license='unknown')
            add(db, 'group', 0, group=1)
            add(db, 'depiction', 0, depiction=1)
            add(db, 'another-box-invalid', 0)
            add(db, 'another-box-invalid', 99, group=1)
            selected, eligible = sampler.select_balanced(db, p, {'a': 0, 'b': 1})
        self.assertEqual([item['id'] for item in selected], ['valid'])
        self.assertEqual(eligible, {'a': 1, 'b': 0})

    def test_reject_invalid_policy(self):
        p = policy({'domain': ['a', 'b']}, 1, 1)
        with self.assertRaises(ValueError):
            sampler.anchors(p, {'a': 0, 'b': 1})
        for field, value in [('max_images', 601), ('max_images', True), ('seed', '17'),
                             ('images_per_category', 13), ('max_download_bytes', 1000000001)]:
            broken = policy({'domain': ['a']}, 1, 1)
            broken[field] = value
            with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                sampler.anchors(broken, {'a': 0})
        with self.assertRaises(ValueError):
            sampler.anchors(policy({'x': ['a'], 'y': ['a']}, 2, 1), {'a': 0})


class RunnerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.base = self.root / 'output/training-general-v1'
        self.source = self.base / 'catalogue-1'
        self.prior = self.base / 'pilot-selection-2'
        self.scope = self.base / 'metadata-tools-v1/general-intake-pilot.json'
        for folder in (self.source, self.prior, self.scope.parent, self.root / 'scripts', self.root / 'dependencies'):
            folder.mkdir(parents=True)
        shutil.copyfile(ROOT / 'scripts/training_data.py', self.root / 'scripts/training_data.py')
        shutil.copyfile(ROOT / 'dependencies/recognition-vocabulary.json', self.root / 'dependencies/recognition-vocabulary.json')
        registry = sampler.read(self.root / 'dependencies/recognition-vocabulary.json')
        names = {name: index for index, name in enumerate(registry['classes'])}
        self.p = policy({'first': ['person'], 'second': ['dog'], 'third': ['balloon']}, 6, 2)
        self.write(self.scope, self.p)
        self.dbpath = self.source / 'openimages-train.sqlite'
        self.source_meta = {'publisher_split': 'train', 'vocabulary_sha256': sampler.sha(self.root / 'dependencies/recognition-vocabulary.json')}
        with contextlib.closing(database(self.dbpath)) as db:
            for name in ('person', 'dog', 'balloon'):
                for j in range(3):
                    add(db, f'{names[name]:08x}{j:08x}', names[name])
            db.execute('INSERT INTO meta VALUES(?,?)', ('source', json.dumps(self.source_meta)))
            db.commit()
        self.write(self.source / 'inventory.json', {'raw_labels': 601, 'canonical_categories': 597, 'domains': self.p['domains']})
        self.write(self.source / 'preparation.json', {'status': 'completed', 'publisher_split': 'train',
                   'scope_sha256': sampler.sha(self.scope), 'catalogue_sha256': sampler.sha(self.dbpath)})
        self.write(self.prior / 'selection.json', {'scope': self.p, 'source': self.source_meta, 'images': []})
        prior_hash = sampler.sha(self.prior / 'selection.json')
        self.write(self.prior / 'selection-summary.json', {'status': 'completed', 'source_catalogue_job': '1', 'selection_sha256': prior_hash})
        exclusion = self.root / 'output/training-0.13/general-smoke-bundle/manifest.json'
        exclusion.parent.mkdir(parents=True)
        self.write(exclusion, {'images': [{'id': 'old-smoke'}]})
        self.args = argparse.Namespace(root=self.root, catalogue_job='1', prior_selection_job='2',
                                       job_id='3', expected_prior_sha256=prior_hash, run=False)
        self.output = self.base / 'pilot-selection-v2-3'

    @staticmethod
    def write(path, obj):
        path.write_text(json.dumps(obj), encoding='utf-8')

    def invoke(self):
        with contextlib.redirect_stdout(io.StringIO()):
            sampler.run(self.args)

    def test_preflight_no_output_and_run_with_receipts(self):
        self.invoke()
        self.assertFalse(self.output.exists())
        self.args.run = True
        self.invoke()
        result = sampler.read(self.output / 'selection-summary.json')
        self.assertTrue(result['coverage_gate_passed'])
        self.assertEqual(result['selected_candidates'], 6)
        self.assertEqual(result['selected_anchor_categories'], 3)
        self.assertEqual(result['selection_sha256'], sampler.sha(self.output / 'selection.json'))
        self.assertEqual(result['photographs_downloaded'], 0)
        self.assertFalse(result['approved_for_training'])
        self.assertEqual(set(path.name for path in self.output.iterdir()), {'selection.json', 'selection-summary.json', 'inventory.json'})
        prior_hash = sampler.sha(self.prior / 'selection.json')
        with self.assertRaises(FileExistsError):
            self.invoke()
        self.assertEqual(sampler.sha(self.prior / 'selection.json'), prior_hash)

    def test_changed_catalogue_or_prior_rejected(self):
        self.args.expected_prior_sha256 = '0' * 64
        with self.assertRaises(ValueError):
            self.invoke()
        self.assertFalse(self.output.exists())
        self.args.expected_prior_sha256 = sampler.sha(self.prior / 'selection.json')
        self.write(self.scope, dict(self.p, seed=18))
        with self.assertRaises(ValueError):
            self.invoke()
        self.assertFalse(self.output.exists())

        self.write(self.scope, self.p)
        with contextlib.closing(sqlite3.connect(self.dbpath)) as db:
            db.execute("INSERT INTO meta VALUES('changed','true')")
            db.commit()
        with self.assertRaises(ValueError):
            self.invoke()
        self.assertFalse(self.output.exists())

    def test_empty_anchor_writes_failed_gate_and_raises(self):
        with contextlib.closing(sqlite3.connect(self.dbpath)) as db:
            db.execute('DELETE FROM boxes WHERE raw_id=(SELECT MAX(raw_id) FROM classes)')
            db.commit()
        report = sampler.read(self.source / 'preparation.json')
        report['catalogue_sha256'] = sampler.sha(self.dbpath)
        self.write(self.source / 'preparation.json', report)
        self.args.run = True
        with self.assertRaises(ValueError):
            self.invoke()
        result = sampler.read(self.output / 'selection-summary.json')
        self.assertEqual(result['status'], 'coverage_failed')
        self.assertFalse(result['coverage_gate_passed'])
        self.assertEqual(len(result['missing_anchors']), 1)


if __name__ == '__main__':
    unittest.main()
