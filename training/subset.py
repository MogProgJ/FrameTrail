"""Make a small dataset from a built one (first N images per split, images symlinked).

Used by the GPU smoke job to measure training speed on real data within a short job.

Example:
    python training/subset.py --source data/pilot --out data/pilot-smoke --train 1500 --valid 300 --test 500
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from pathlib import Path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--train', type=int, default=1500)
    parser.add_argument('--valid', type=int, default=300)
    parser.add_argument('--test', type=int, default=500)
    args = parser.parse_args(argv)

    if args.out.exists():
        shutil.rmtree(args.out)
    for split, count in (('train', args.train), ('valid', args.valid), ('test', args.test)):
        coco = json.loads((args.source / split / '_annotations.coco.json').read_text(encoding='utf-8'))
        images = coco['images'][:count]
        keep = {image['id'] for image in images}
        coco['images'] = images
        coco['annotations'] = [a for a in coco['annotations'] if a['image_id'] in keep]
        folder = args.out / split
        folder.mkdir(parents=True)
        for image in images:
            os.symlink((args.source / split / image['file_name']).resolve(), folder / image['file_name'])
        (folder / '_annotations.coco.json').write_text(json.dumps(coco), encoding='utf-8')
        print(f'{split}: {len(images)} images, {len(coco["annotations"])} boxes')
    shutil.copy(args.source / 'dataset.json', args.out / 'dataset.json')
    return 0


if __name__ == '__main__':
    sys.exit(main())
