"""Index Open Images, select a bounded general sample, review, then export training data."""
import argparse
import json
from pathlib import Path

from training_data import catalogue, export_bundle, prepare


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    index = commands.add_parser('index')
    for name in ('boxes', 'classes', 'metadata', 'output'):
        index.add_argument('--' + name, type=Path, required=True)
    index.add_argument('--publisher-split', choices=('train', 'validation', 'test'), required=True)
    sample = commands.add_parser('sample')
    sample.add_argument('--catalogue', type=Path, required=True)
    sample.add_argument('--scope', type=Path, default=Path(__file__).resolve().parents[1] / 'training/scope.json')
    sample.add_argument('--output', type=Path, required=True)
    sample.add_argument('--fetch-images', action='store_true', help='Explicit bounded network acquisition; metadata-only by default')
    sample.add_argument('--exclude-manifest', type=Path)
    export = commands.add_parser('export')
    export.add_argument('--manifest', type=Path, required=True)
    export.add_argument('--output', type=Path, required=True)
    export.add_argument('--smoke', action='store_true', help='Allow unreviewed labels ONLY for a mechanical pipeline test')
    args = parser.parse_args()
    if args.command == 'index':
        result = catalogue(args.boxes, args.classes, args.metadata, args.output, args.publisher_split)
    elif args.command == 'sample':
        exclude = ()
        if args.exclude_manifest:
            prior = json.loads(args.exclude_manifest.read_text(encoding='utf-8-sig'))
            exclude = [item.get('id', Path(item['path']).stem) for item in prior['images']]
        result = prepare(args.catalogue, args.scope, args.output, args.fetch_images, exclude)
    else:
        result = export_bundle(args.manifest, args.output, args.smoke)
        result = {'purpose': result['purpose'], 'images': result['images'], 'labels': len(result['classes']),
                  'lock': str(args.output / 'dataset-lock.json')}
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
