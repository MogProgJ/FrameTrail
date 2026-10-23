"""Adapt the previously audited offline source reviewer to the pinned new intake."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OLD = Path(r'C:\Users\nazee\.codex\visualizations\2026\10\15\01a141ae-c7a6-7303-a280-403af88736f3')
BASE = ROOT.parent / 'billboard-data-refresh-7818553-20261018-v1/retrieval-7824179/verified-7824179/output/billboard-data-refresh-7824179'
code = (OLD / 'review_nextdata_sources_7769109.py').read_text(encoding='utf-8-sig')
old_setup = "R=Path(r'C:\\Users\\nazee\\.codex\\visualizations\\2026\\10\\15\\01a141ae-c7a6-7303-a280-403af88736f3')\nA=R/'nextdata-acquisition-7768932-v1';BASE=A/'results-7769109/retrieved/output/training-general-v1/next-photo-7768932-v1';OUT=R/'nextdata-source-review-7769109-v1'"
new_setup = f"R=Path({str(ROOT)!r})\nBASE=Path({str(BASE)!r});OUT=R/'source-review'"
assert old_setup in code
code = code.replace(old_setup, new_setup)
code = code.replace("'7836e65a5cbe2d49d126948dba3edd8787ddc614027265fc1b27fdb284b66af4'", "'be48baf7c20e5ead0e211c27cf5e0e12c5ce247a6553fe1d349d30630dc370bd'")
code = code.replace("==980", "==240").replace("/980", "/240").replace("'7769109'", "'7824179'")
code = code.replace("selected_domain=original['selected_domain'],source_url", "selected_domain=original['selected_domain'],prospective_split=original['prospective_split'],source_url")
code = code.replace("  page=BASE/source['page_file']", "  page=(BASE/source['page_file']).resolve()\n  assert page.is_relative_to(BASE.resolve()) and not page.is_symlink()")
destination = ROOT / 'review_sources.py'
with destination.open('x', encoding='utf-8') as stream:
    stream.write(code)
print(destination)
