# Absent-photo qualification: first pass over the unused inventory

24 October 2026. Cloud-session continuation of the broader billboard definition (task definition v2, `03bb6d7d…`). This is an assistant review, not independent human annotation. Nothing here is admitted to a release or approved for training. No model predictions, fitting, cluster jobs or app changes were involved.

## What was done

1. **Queue frozen first.** `QUEUE.json` fixed the order of all 223 unused candidates before any image was fetched or viewed. Pinned inputs (inventory, task definition, v4 draft, experiment design) were hash-checked. Roles are unchanged.
2. **Originals verified.** All 223 originals were re-downloaded from the public Open Images bucket, the same source the intake jobs used. Every SHA-256 and dHash matches the inventory (`ORIGINALS_RECEIPT.json`). Images stay out of Git.
3. **Whole-photo review.** Each photo was judged absent, hold, not-absent (contains an in-scope board) or reject. Zoomed crops were made for small or distant detail. One recorded dHash-6 near match (`65e34de96ff0f728` vs prior `aa002b206c310671`) was viewed and is a false match (railway warning sign vs a light switch).

| Block | Photos | Coverage |
| --- | ---: | --- |
| A: contrast anchors, all roles | 48 | All viewed at full resolution |
| B: TRAIN billboard anchors | 52 | All viewed at full resolution |
| C: held-out billboard anchors, TEST | 66 | 34 at full resolution; 32 that prior triage called clear advertising were confirmed on contact sheets (enough to rule out absence, not a box review) |
| C: held-out billboard anchors, validation | 57 | Not reviewed: the frozen order only opens block C for gaps left after block A, and block A closed the validation gap |

## Result against the gaps

| Role | Gap before | Absent candidates found | Remaining gap |
| --- | ---: | ---: | ---: |
| TRAIN | 11 | 30 | 0 |
| Validation | 6 | 8 | 0 |
| TEST | 4 | 0 | **4** |

TRAIN confuser families, counting the current draft plus the new candidates (minimum 5 each):

| Family | Draft now | After candidates | Remaining gap |
| --- | ---: | ---: | ---: |
| Shop/business lettering | 0 | 0 | **5** |
| Traffic/information signs | 4 | 7 | 0 |
| Indoor frames/screens/boards | 8 | 30 | 0 |
| Household/laundry | 7 | 10 | 0 |

Two TRAIN absent candidates fit no family. `83345074adb9538f` is a hand-held printed card. `3db2cf22867fc76a` is graffiti lettering painted on brick: a good lettering confuser, but not shop lettering, so it was not counted toward that family.

## The two shortfalls, in plain terms

**Shop/business lettering (TRAIN).** The broader definition made almost every shopfront positive, because shops normally have an identity board. Every street scene in the unused TRAIN inventory contains at least one in-scope board. A genuine "shop lettering but no board" negative needs bare letters applied directly to a facade, with no panel anywhere in the photo. The inventory has none. This is a structural effect of the definition change, not a reviewing gap.

**TEST.** The unused TEST pool is 66 billboard-anchor photos plus four contrast photos. Every contrast photo is held, positive or rejected:

- `3c49b6fe8d3f1115` stays rejected under its existing prior-venue overlap record.
- `29cd97b5de31d220` is a pasted composite.
- `679f52e059e4622f` has an event poster on a noticeboard.
- `c7e6392996d34449` is a trade-show booth with promotion panels.

None of the 66 billboard-anchor TEST photos is absent.

## Holds that a human decision could resolve

These are deliberate holds, not guesses. Each turns on a boundary that task definition v2 does not settle:

- **Noticeboards and event posters:** `910041a96e70e3b7` (TRAIN), `679f52e059e4622f` (TEST). Is a flyer or event poster on a noticeboard an in-scope promotional display?
- **Painted wall advertising and murals:** `c0ba504f51ead771`, `766ff9c58948dc8e` (TRAIN), `14739a4907bd6163` (TEST).
- **Blank billboard structures:** `45b675d7a987eb2d`, `bd7fae17003521c6` (TRAIN). Positive unit, or neither?
- **Information boards carrying institution or brand identity:** `3547d8e7ed6d8111` (TRAIN), `1868a6fcfbfac188` (TEST), `d9e8beecc85c8c4a` (validation road-safety campaign).
- **Decorative message plaque:** `a05ca9ca50d00afb` (TEST). Proverb plaque on a door.
- **Composites, watermarks and source questions:** `bb2c1ddff018b1d2` (TRAIN), `31389522f357909e` (validation), `29cd97b5de31d220` (TEST).
- **Small unresolvable details:** `a8df81ce61f8a569`, `b33447da6ab4cbe6`, `117cc5e10b16b05b`, `7d3c9512d8ad8e26`, `dcfb7be73a1b8376`, `356986d84c8bdc28` (TRAIN), `17f1bc32271053f6`, `13738fd6baee7352` (TEST).

The TEST holds most likely to become absent after a ruling are `679f52e059e4622f`, `a05ca9ca50d00afb`, `1868a6fcfbfac188` and `17f1bc32271053f6`. Even then the TEST gap only closes if all four go that way.

## Other observations

- Block B surfaced about 40 new positive candidates in TRAIN and about 60 in TEST under v2. That is useful if more positives are wanted, but none has boxes yet.
- `3db2cf22867fc76a` and `bd7fae17003521c6` share the same graffiti tag. Both are TRAIN, so there is no cross-role leak, but they are a possible scene link.
- The existing exclusions for the mockup `9b5635760011caeb`, the collage `eec5343864ac439f` and the laundrette `3c49b6fe8d3f1115` were confirmed and kept.

## Still required before any of this becomes release data

- Visual scene/session comparison of the 38 absent candidates against prior releases and regression scenes.
- Formal rights clearance. All 223 carry photo-specific licence corroboration only.
- Independent human confirmation of the assistant absence decisions.
- A decision on the shop-family shortfall and the TEST shortfall: rule on the holds, redefine the family, or run a bounded new collection.

## Files

`QUEUE.json`, `ORIGINALS_RECEIPT.json`, `REVIEW_A_DECISIONS.json`, `REVIEW_B_DECISIONS.json`, `REVIEW_C_DECISIONS.json`, `SUMMARY.json`, and the scripts that produced them (`prepare_queue.py`, `fetch_originals.py`, `record_block.py`, `summarize.py`). All outputs are created with exclusive-create mode and never overwrite.
