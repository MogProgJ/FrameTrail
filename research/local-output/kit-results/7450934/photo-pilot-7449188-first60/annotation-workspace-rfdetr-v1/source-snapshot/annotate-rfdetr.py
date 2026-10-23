"""Create a NEW offline annotation workspace with RF-DETR suggestions for up to 60 existing images."""
import argparse
import json
from pathlib import Path
from rfdetr_annotations import prepare_rf

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('workspace','annotations','experiment','output'):
        parser.add_argument('--'+name,required=True,type=Path)
    args = parser.parse_args()
    try:
        result = prepare_rf(args.workspace,args.annotations,args.experiment,args.output)
        print(json.dumps(result,indent=2))
    except (OSError,ValueError,RuntimeError,KeyError,ImportError) as error:
        parser.exit(1,f'RF annotation preparation error: {error}\n')
