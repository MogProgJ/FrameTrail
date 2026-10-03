import json
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).parents[1]


class Registry(unittest.TestCase):
    def test_generated_native_registry_matches_reviewed_json(self):
        data = json.loads((ROOT/'dependencies/recognition-vocabulary.json').read_text(encoding='utf-8'))
        header = (ROOT/'src/recognition_vocabulary.hpp').read_text(encoding='utf-8')
        labels = re.findall(r'"([^"\\]*)"', header)
        self.assertEqual(labels, data['classes'])
        self.assertEqual(len(set(labels)), 615)
        ids = [int(v) for v in header.split('openimages_ids={')[1].split('}')[0].replace('\n','').split(',') if v.strip()]
        self.assertEqual(ids, data['openimages_ids'])
        self.assertEqual(len(ids), 601)
        self.assertEqual(len(set(ids)), 597)
        world = json.loads((ROOT/'dependencies/world-vocabulary.json').read_text(encoding='utf-8'))
        self.assertEqual(data['classes'][:100], world['classes'])

    def test_aliases_and_added_animal_labels(self):
        data = json.loads((ROOT/'dependencies/recognition-vocabulary.json').read_text(encoding='utf-8'))
        by_name = dict(zip(data['openimages_labels'], data['openimages_ids']))
        for name in ['Man', 'Woman', 'Boy', 'Girl', 'Person']:
            self.assertEqual(by_name[name], 0)
        self.assertEqual(by_name['Fox'], 80)
        self.assertNotEqual(by_name['Dog'], by_name['Fox'])
        self.assertNotEqual(by_name['Bat (Animal)'], by_name['Baseball bat'])


if __name__ == '__main__':
    unittest.main()
