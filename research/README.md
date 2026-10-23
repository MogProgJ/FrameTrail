# FrameTrail research and evidence archive

Snapshot recorded 24 October 2026. Start with [current project progress](../PROJECT_PROGRESS.md) and the [latest handoff](../CURRENT_HANDOFF.md).

- [Continuation](continuation-20261018/): scripts, plans, authorization receipts, results, audits, versioned source snapshots and handoffs from the canonical continuation workspace. `outputs/` preserves the original names and directory structure.
- [Earlier local output](local-output/): inspectable text records from the application checkout, including earlier evaluations, annotation work and cluster receipts.
- `local-packages/`, `model-metadata/` and `local-media-results/`: package manifests/checksums, export receipts and the local demonstration analysis CSV; binary assets remain local.
- [Source manifest](SOURCE_MANIFEST.json): original SHA-256 and byte count for each copied source file. Publication procedure and verification records live separately in `sync-20261024/`. Git attributes disable newline conversion in this archive.
- [Local artifact inventory](LOCAL_ARTIFACT_INVENTORY.json): source path, size and reason for each excluded local file. Existing scientific manifests retain model/image artifact hashes. This inventory is not a backup of excluded contents.

All original reports and receipts remain historical snapshots, including failed attempts and superseded scope decisions. Absolute paths in those records describe the original Windows/cluster environment; a fresh clone will need explicit path configuration. Archived scripts may create exclusive snapshots or submit jobs: reading or publishing them does not authorize rerunning them. The latest task definition and handoff supersede older pending questions without changing old results.

The archive intentionally excludes raw photos/video, screenshots or embedded photo payloads, model weights/checkpoints, feature/cache binaries, generated packages/builds, third-party runtimes and authentication/session artifacts. These stay preserved locally. No dataset, trained-model or production release is claimed. Annotation drafts are assistant-reviewed and have unresolved qualification holds.

Current research entry points:

- [Training strategy](continuation-20261018/outputs/training-strategy-20261019-v1/STRATEGY.md)
- [Four-trial experiment](continuation-20261018/outputs/fresh-selector-batch-20261022-v1/POSTRUN_REPORT.md)
- [64-query discrimination](continuation-20261018/outputs/train-discrimination-7870268-20261022-v1/STUDY_REPORT.md)
- [Full-query control](continuation-20261018/outputs/train-discrimination-full-query-7870268-20261022-v1/CONTROL_REPORT.md)
- [Photo-level loss](continuation-20261018/outputs/train-photo-max-loss-7870268-20261022-v1/STUDY_REPORT.md)
- [Expanded definition and first review](continuation-20261018/outputs/broad-billboard-definition-20261022-v1/REVISION_REPORT.md)
- [Focused next-chat handoff](continuation-20261018/NEXT_CHAT_BROAD_BILLBOARD_20261022.md)

Next step: qualify the unused local candidates against the expanded definition, because the missing truly absent examples block a trustworthy new baseline.
