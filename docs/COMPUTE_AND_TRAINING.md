# Compute, training, and bwUniCluster plan

Updated: 4 October 2026.

## Decision

FrameTrail will keep a native C++ application and a local CPU path as its dependable baseline. GPU inference, Python training, bwUniCluster jobs, a Python inference worker, and a hosted service are optional capability gates. They enter the implementation only when measurements show a concrete need.

The gates are intentionally independent. Training does not require a Python service in the shipped application. A GPU backend does not require cloud infrastructure. Access to a cluster does not make it suitable as a live application server.

## What bwUniCluster 3.0 offers

KIT's current system is **bwUniCluster 3.0+KIT-GFA-HPC 3**, placed into operation on 7 April 2025. KIT reports 393 nodes, 27,632 CPU cores, 127.15 TiB aggregate main memory, 188 accelerators, and 8.8 PFLOP/s theoretical peak performance. Those are whole-system figures, not a personal allocation or a promise of immediate availability. See the [KIT service page](https://www.scc.kit.edu/en/services/bwUniCluster_3.0.php) and [bwHPC hardware documentation](https://wiki.bwhpc.de/e/BwUniCluster3.0/Hardware_and_Architecture).

The documented compute types are strong enough for FrameTrail's future training work:

| Resource type | Documented hardware | Relevant use |
| --- | --- | --- |
| Standard CPU node | 2x AMD EPYC 9454, 96 physical cores, 384 GiB RAM | Dataset indexing, conversion, evaluation, CPU benchmarks |
| Ice Lake CPU node | 2x Intel Xeon Platinum 8358, 64 physical cores, 256 GiB RAM | Parallel preprocessing and comparison with x86 deployments |
| High-memory node | 96 physical cores, about 2.25 TiB RAM | Only if a measured dataset operation cannot fit ordinary nodes |
| NVIDIA GPU node | Four H100 GPUs, 94 GiB per GPU | Single-GPU training first; multi-GPU only after profiling |
| Older NVIDIA GPU nodes | Four A100/H100 accelerators, 40 or 80 GiB per GPU depending on partition | Training, batch inference, and reproducible GPU benchmarks |
| AMD accelerator node | Four MI300A accelerators with 128 GiB shared HBM each | A later portability experiment, not the initial training target |

The cluster runs RHEL 9.x. Jobs use Slurm and start according to resource availability and fair-share priority. Compute-heavy work on login nodes is prohibited and may be terminated. The regular documented GPU queues accept requests beginning at one GPU and have maximum wall times of roughly 48–72 hours, depending on the partition. Development queues are intended for short setup/debugging work. See [running jobs and queue policy](https://wiki.bwhpc.de/e/BwUniCluster3.0/Running_Jobs).

The hardware is therefore more than sufficient for training a compact detector. The practical constraints are queue wait time, the user's active entitlement and permitted partitions, fair-share priority, job wall time, dataset rights, and a reproducible Linux environment. We will verify those from the account before writing cluster-specific automation.

## Appropriate role in FrameTrail

bwUniCluster is a **batch training and evaluation target**:

1. Prepare a versioned, permissioned dataset locally.
2. Transfer the dataset and immutable experiment configuration to a temporary cluster workspace.
3. Submit a single-GPU Slurm job.
4. Save checkpoints, logs, metrics, environment metadata, and the final ONNX export.
5. Download the selected ONNX model and its report.
6. Validate that artifact with the existing C++ detector contract and representative local footage.

It is not planned as the desktop application's live inference backend. A queued Slurm job can wait before it starts, has a wall-time limit, and can be pre-empted by ordinary operational failures. That does not fit interactive video playback or a continuously available API.

The cluster supports Enroot and Apptainer/Singularity; bwHPC recommends Enroot and provides Slurm integration through Pyxis. Native Docker is not supported on the shared system. A pinned container or locked Python environment will hold PyTorch, CUDA, the training repository, and export tools. See the [bwUniCluster container guide](https://wiki.bwhpc.de/e/BwUniCluster3.0/Containers).

## Storage and data handling

The documented Lustre-backed HOME quota is 500 GiB per user and is backed up. A workspace can hold up to 40 TiB per user but has a maximum lifetime of 240 days and no backup. Job-local `$TMPDIR` uses fast local SSD storage and disappears when the job ends. See [filesystem details](https://wiki.bwhpc.de/e/BwUniCluster3.0/Hardware_and_Architecture/Filesystem_Details).

Use HOME for small scripts, environment locks, and experiment manifests. Use a workspace for datasets and checkpoints. Copy hot training shards to job-local storage when measurement shows that it helps. Treat workspaces and `$TMPDIR` as disposable: final models, reports, and essential metadata must be copied back before expiry or job completion.

Only footage whose collection and processing permit cluster use may be transferred. Secrets, account names, access tokens, and private SSH keys never enter this repository. Raw footage and model weights remain outside Git.

KIT student access can depend on a lecture-period entitlement; the official migration guide says those accounts may be deprovisioned and their data deleted after the semester. Other student projects may require an appropriate guest/partner account. We will confirm the user's actual entitlement and retention rules instead of treating current access as permanent. See the [bwUniCluster migration/access guide](https://wiki.bwhpc.de/e/BwUniCluster3.0/Data_Migration_Guide).

## Conditional capability gates

### Gate 1: local GPU inference

Trigger: representative footage shows that CPU inference cannot meet the chosen throughput, latency, temperature, or CPU-headroom target.

Action: add a selectable ONNX Runtime GPU execution provider with automatic CPU fallback. Benchmark end-to-end performance, including frame upload and result synchronization. Keep it only if it improves the measured application rather than just the isolated model call.

Stop condition: CPU already meets the target, deployment burden outweighs the gain, or the selected GPU/runtime combination is unreliable. The current GTX 1650 Ti is a useful test device but does not justify making CUDA mandatory.

### Gate 2: custom model training

Trigger: a labelled evaluation set shows that detector errors materially limit recognition, appearance review, tracking or crossing-event accuracy. Examples include systematic misses of small people, unusual vehicle angles, night footage, or domain-specific classes.

Action: create a separate Python training toolchain, fine-tune a documented model, evaluate it against the unchanged baseline, export ONNX, and load it through a model-specific C++ adapter. Use one bwUniCluster NVIDIA GPU initially. Distributed training is out of scope until a single-GPU run is measured and demonstrably too slow.

Stop condition: the pretrained detector meets the product target, labels are too sparse or unreliable, validation does not improve, or the new model cannot be exported and reproduced.

### Gate 3: Python inference worker

Trigger: a valuable model cannot reasonably run through the stable native ONNX boundary, or rapid model experimentation becomes more important than a single-process deployment.

Action: define a versioned request/result protocol carrying source, generation, frame, model, boxes, masks, and errors. Run the worker locally first. Treat it as an optional adapter and preserve native detection as the fallback.

Stop condition: the same capability exports cleanly to ONNX, inter-process copies or latency are excessive, deployment becomes fragile, or the model does not improve the agreed metric.

### Gate 4: commercial cloud service

Trigger: the product needs an always-available remote API, shared team access, multiple concurrent sources, or compute beyond scheduled cluster jobs.

Action: design authentication, storage lifetime, encryption, observability, cost limits, failure behavior, and data-location rules before choosing a provider. Upload selected frames or batch artifacts where possible rather than streaming every raw video by default.

Stop condition: one local installation remains the real use case, network latency harms the workflow, footage cannot leave its environment, or recurring cost is not justified.

bwUniCluster substantially reduces the reason to pay for commercial training compute. It does not replace a managed online endpoint because the scheduler is designed for scientific batch jobs rather than service uptime.

## Experiment acceptance rules

Every optional path needs a written baseline and the same held-out evaluation inputs. Record model checksum, code revision, environment/container identifier, dataset version, random seed, hardware/partition, training duration, peak accelerator memory, inference latency, event accuracy, and known failures.

Adopt a change only when it improves an agreed product metric enough to justify its operational cost. A larger model, faster isolated benchmark, newer framework, or successful training loss is not sufficient evidence by itself.

The first cluster exercise will be a short, reproducible smoke job on a development GPU queue: inspect the allocation, run a small training or inference command, export an artifact, and retrieve its logs. It will not begin until representative footage, labels, and a local evaluation command exist.

## 0.8 gate update — 3 October 2026

A stronger pretrained CPU model (YOLOX-S) and local comparison tooling are implemented. Selected-target recovery improved on the supplied generated clip, but CPU throughput fell to about 5 FPS. Evaluate optional GPU inference next, retaining the CPU baseline, before undertaking custom training. Full real-footage annotations and event accuracy remain required. No cluster job, Python inference worker or cloud service has been provisioned. See [evidence and limits](MODEL_EVALUATION.md).

## 0.10 gate update — 3 October 2026

The local GPU gate now has a measured implementation: isolated DirectML inference with CPU fallback, strict benchmarking and unchanged saved-analysis workflow. YOLOX-S's warm pipeline improved roughly 4.2× on the GTX 1650 Ti; Nano's short run was slower after loading. CPU stays the default. The frozen partially annotated targets kept the CPU recovery counts. See [GPU evidence and limits](GPU_INFERENCE.md).

This justifies keeping acceleration optional for the stronger model. It does not justify cluster training, a Python inference service or cloud hosting. Broader labelled accuracy, tracking/event evaluation and sustained resource behaviour remain the next gates; no cluster job or cloud resource was created.

## 0.12 readiness audit — 3 October 2026

Broader native recognition and GPU execution are implemented. The user selected a narrow **low-light fox/dog and related-animal** training pilot. Preparation is now the next Phase 8 module; a full run remains conditional on reviewed real-world labels and a measured domain gap. The small partial-label comparisons cannot establish precision or general accuracy.

Follow the [training-readiness audit](TRAINING_READINESS.md): inventory and evaluate scoped data, prove custom-model registration/export and saved-analysis compatibility, establish a pinned Linux single-GPU setup test, then assess one limited fine-tuning run. Fixed native profiles and the publisher-checkpoint exporter currently require extension for a small custom class head. The optional Windows CPU export environment is not a CUDA training environment.

A trained wildlife profile will remain optional while YOLOX-S and broad recognition remain available. The accepted saved-analysis layout/flow is preserved. Unrelated live-camera, audio, multi-camera and public-release work need not block preparation. No dataset, cluster login, job, Python inference worker or cloud service was added by this audit.

## General-recognition tooling update — 4 October 2026

The user clarified broad everyday-object recognition as the goal; fox/dog and low light are evaluation slices. RF-DETR Small is shortlisted. A general catalogue, bounded six-domain sample, reviewed-data gate, YOLO/COCO bundles, training runner, full-vocabulary export and single-GPU Slurm template are now implemented. A local one-epoch CPU smoke produced a checkpoint and ONNX artifact that passed native CPU/DirectML reference and vocabulary checks. It is mechanics evidence, not an adopted accuracy upgrade. See [dataset/training tooling](TRAINING.md).

The target hostname is `uc3.scc.kit.edu`. Login requires the user's interactive password/OTP; no credentials or account names are stored, and no remote job was submitted. The prepared Slurm script still needs account-permitted partition, pinned Linux CUDA environment, reviewed data and storage verification. The app keeps its current models and accepted saved-analysis interface.
