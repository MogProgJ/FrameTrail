"""Acquire or run the isolated CPU RF-DETR Small inference/export probe. Never trains."""
import argparse
import json
from pathlib import Path

from rfdetr_probe import ASSETS, ASSET_NAME, acquire_asset, contract, run_probe


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    commands.add_parser('contract')
    commands.add_parser('acquire', help='Explicit bounded download from the pinned publisher URL')
    run = commands.add_parser('run')
    run.add_argument('--manifest', type=Path, required=True)
    run.add_argument('--checkpoint', type=Path, default=ASSETS / ASSET_NAME)
    run.add_argument('--output', type=Path, required=True)
    run.add_argument('--count', type=int, default=6, help='First 1..12 intake images, default 6')
    run.add_argument('--baseline-cli', type=Path, help='Optional existing native executable for separate CPU baseline outputs')
    args = parser.parse_args()
    try:
        if args.command == 'contract':
            result = contract()
        elif args.command == 'acquire':
            result = acquire_asset()
        else:
            result = run_probe(args.manifest, args.checkpoint, args.output, args.count, args.baseline_cli)
        print(json.dumps(result, indent=2, allow_nan=False))
    except (OSError, ValueError, RuntimeError, ImportError) as error:
        parser.exit(1, f'RF-DETR probe error: {error}\n')


if __name__ == '__main__':
    main()
