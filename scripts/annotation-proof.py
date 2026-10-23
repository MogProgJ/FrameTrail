"""Render private local draft contact sheets; originals remain unchanged."""
import argparse
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from annotation_review import load_checked
from training_data import contained, read_json


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace', type=Path, required=True)
    parser.add_argument('--annotations', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    source, state = load_checked(args.workspace, args.annotations)
    if args.output.exists():
        raise FileExistsError('Choose a new proof directory; previous proofs are preserved')
    args.output.mkdir(parents=True)
    root = Path(read_json(args.workspace / 'workspace.json')['source_manifest']).parent
    try:
        font = ImageFont.truetype('arial.ttf', 16)
        small = ImageFont.truetype('arial.ttf', 12)
    except OSError:
        font, small = ImageFont.load_default(size=16), ImageFont.load_default(size=12)
    for start in range(0, len(source['images']), 6):
        sheet = Image.new('RGB', (1800, 2250), 'white')
        draw = ImageDraw.Draw(sheet)
        for offset, image in enumerate(state['images'][start:start+6]):
            x, y = (offset % 2)*900, (offset // 2)*750
            original = source['images'][start+offset]
            with Image.open(contained(root, original['path'])) as photo:
                thumb = photo.convert('RGB')
                thumb.thumbnail((890, 690))
                sheet.paste(thumb, (x, y+35))
                sx, sy = thumb.width / image['width'], thumb.height / image['height']
            draw.text((x+5, y+5), f'{image["number"]}. {image["id"]} / {image["anchor"]}', font=font, fill='#18242b')
            for obj in image['objects']:
                if obj['status'] == 'rejected':
                    continue
                box = [x+obj['box'][0]*sx, y+35+obj['box'][1]*sy, x+obj['box'][2]*sx, y+35+obj['box'][3]*sy]
                color = '#159951' if obj['status'] == 'confirmed' else '#216ec4' if obj['origin']['kind'] == 'publisher' else '#f49400'
                draw.rectangle(box, outline=color, width=2)
                label = obj['id'][0] + obj['id'].split('-')[-1] + ' ' + state['classes'][obj['raw_id']]['name']
                draw.text((box[0]+1, box[1]+1), label, font=small, fill=color, stroke_width=1, stroke_fill='white')
        sheet.save(args.output / f'photos-{start+1:02d}-{min(start+6,len(source["images"])):02d}.jpg', quality=94)
    print('Draft proof contact sheets: ' + str(args.output))


if __name__ == '__main__':
    main()
