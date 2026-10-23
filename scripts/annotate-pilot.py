"""Prepare/validate/export a local correction workspace, with no cluster or network access."""
import argparse
import json
from pathlib import Path
from annotation_review import apply_corrections, export_draft, load_checked, load_proposals, prepare, render_editor, summary, validate_state
from training_data import read_json, write_json


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    create = commands.add_parser('prepare')
    create.add_argument('--manifest', type=Path, required=True)
    create.add_argument('--output', type=Path, required=True)
    create.add_argument('--detector', type=Path)
    create.add_argument('--model', type=Path)
    create.add_argument('--corrections', type=Path)
    for name in ('validate', 'export-draft', 'correct', 'editor'):
        sub = commands.add_parser(name)
        sub.add_argument('--workspace', type=Path, required=True)
        sub.add_argument('--annotations', type=Path, required=True)
        if name in ('export-draft', 'correct', 'editor'):
            sub.add_argument('--output', type=Path, required=True)
        if name == 'correct':
            sub.add_argument('--corrections', type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.command == 'prepare':
            result = summary(prepare(args.manifest, args.output, args.detector, args.model, args.corrections))
        elif args.command == 'validate':
            _, state = load_checked(args.workspace, args.annotations)
            result = summary(state)
        elif args.command == 'export-draft':
            result = export_draft(args.workspace, args.annotations, args.output)
        else:
            _, state = load_checked(args.workspace, args.annotations)
            if args.output.exists():
                raise FileExistsError('Existing output is preserved; choose a new file')
            seed = read_json(args.workspace / 'seed.json')
            proposals = load_proposals(args.workspace, seed)
            if args.command == 'correct':
                apply_corrections(state, args.corrections, state['source_manifest_sha256'])
                validate_state(seed, state, proposals)
                write_json(args.output, state)
            else:
                if args.output.resolve().parent != args.workspace.resolve():
                    raise ValueError('Editor must stay in its workspace for relative photograph links')
                render_editor(seed, state, args.output, proposals)
            result = summary(state)
        print(json.dumps(result, indent=2))
    except (ValueError, OSError, KeyError, StopIteration) as error:
        parser.exit(1, f'Annotation draft error: {error}\n')


if __name__ == '__main__':
    main()
