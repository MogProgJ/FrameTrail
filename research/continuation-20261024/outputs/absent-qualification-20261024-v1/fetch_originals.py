"""Fetch each queued original from the public Open Images bucket and prove byte identity.

Images are written outside the repository (argument 1). Only the receipt is written here.
A file is usable for review only when its SHA-256 equals the inventory's recorded value.
"""
import hashlib, json, pathlib, sys, urllib.request
from PIL import Image

HERE = pathlib.Path(__file__).resolve().parent


def dhash(path):
    # Same 9x8 grayscale difference hash as data-tools-v1/photo_transport.py.
    with Image.open(path) as image:
        image.load()
        size = image.size
        gray = image.convert('L').resize((9, 8))
        pixels = [gray.getpixel((x, y)) for y in range(8) for x in range(9)]
    bits = 0
    for y in range(8):
        for x in range(8):
            bits = (bits << 1) | (pixels[y * 9 + x] > pixels[y * 9 + x + 1])
    return f'{bits:016x}', size


def main():
    cache = pathlib.Path(sys.argv[1])
    cache.mkdir(parents=True, exist_ok=True)
    queue = json.loads((HERE / 'QUEUE.json').read_text())
    results = []
    for entry in queue['entries']:
        target = cache / f"{entry['image_id']}.jpg"
        if not target.exists():
            with urllib.request.urlopen(entry['public_original_url'], timeout=60) as response:
                target.write_bytes(response.read())
        digest = hashlib.sha256(target.read_bytes()).hexdigest()
        observed_dhash, (width, height) = dhash(target)
        results.append({'image_id': entry['image_id'], 'url': entry['public_original_url'],
                        'bytes': target.stat().st_size, 'width': width, 'height': height,
                        'sha256_matches_inventory': digest == entry['sha256'],
                        'dhash_matches_inventory': observed_dhash == entry['recorded_dhash']})
    receipt = {
        'schema': 1, 'queue_sha256': hashlib.sha256((HERE / 'QUEUE.json').read_bytes()).hexdigest(),
        'source': 'Public Open Images train bucket, the same URL pattern used by intake jobs 7824179/7840599.',
        'images_committed_to_git': False,
        'all_sha256_match': all(r['sha256_matches_inventory'] for r in results),
        'all_dhash_match': all(r['dhash_matches_inventory'] for r in results),
        'count': len(results), 'records': results,
    }
    with (HERE / 'ORIGINALS_RECEIPT.json').open('x', encoding='utf-8') as handle:
        json.dump(receipt, handle, indent=1)
        handle.write('\n')
    print(receipt['count'], receipt['all_sha256_match'], receipt['all_dhash_match'])


if __name__ == '__main__':
    main()
