# First FrameTrail training test on bwUniCluster 3.0

Prepared 4 October 2026 for the Python modules reported by the user. The user's GPU diagnostic completed successfully on an NVIDIA A100 80 GB. This guide prepares a one-epoch GPU training check with the existing 96-image sample. Larger accuracy training still needs reviewed data; RF-DETR is not trained by this job.

Current progress: upload checksum and extraction passed; environment installation completed with PyTorch 2.8.0+cu128 and Ultralytics 8.3.228. After the first attempt failed before setup was complete, replacement job **7446193 completed with Slurm exit code 0** on the A100. It saved both checkpoints after one epoch on 70 training images and validation on 11 images. Training-wrapper time was 106.91 seconds; complete job time was 3 minutes 44 seconds. The locked test was untouched and the artifact is not approved for the app. Continue with result retrieval; see [HANDOFF.md](../HANDOFF.md). The preparation/submission steps below remain a reproduction guide, not instructions to repeat the successful run.

The assistant has not logged into KIT or submitted a remote job. Run each stage in the terminal named below, and stop if a command reports an error. Enter passwords and OTPs only in your own terminal.

## 1. Cluster terminal: create storage and select Python

An empty `ws_list` means no active workspaces were listed. Create a 30-day workspace, then find its actual path:

```bash
ws_allocate frametrail 30
ws_find frametrail
module load devel/miniforge/25.3.1-python-3.12
python --version
```

The Python version should begin with `3.12`. If loading the module fails, inspect `module spider devel/miniforge/25.3.1-python-3.12` and share its prerequisite instructions. Workspaces expire and have no backup; keep a local copy of important results. [Official workspace instructions](https://wiki.bwhpc.de/e/Workspace), [Miniforge instructions](https://wiki.bwhpc.de/e/Development/Conda).

## 2. Windows PowerShell: upload the prepared package

Open a separate PowerShell window on your laptop; keep your cluster terminal open. The prepared archive and checksum are in the usual FrameTrail folder under `output/training-0.13/`. They contain training scripts, vocabulary/configuration, the complete immutable 96-image bundle, and the verified pretrained checkpoint. No Windows Python environment, camera/video recordings, or unrelated local analysis files are included.

```powershell
$taskLocalRoot = Read-Host "Full path of your local FrameTrail folder"
$taskClusterUser = Read-Host "Your cluster SSH username"
scp "$taskLocalRoot\output\training-0.13\frametrail-cluster-smoke.tar.gz" "$taskLocalRoot\output\training-0.13\frametrail-cluster-smoke.tar.gz.sha256" "${taskClusterUser}@uc3.scc.kit.edu:~/"
```

Use the same campus network/VPN that allowed your SSH login. The transfer may ask for OTP/password again. Keep the archive in your cluster home directory as a staging copy; the extracted training files go into the workspace.

## 3. Cluster terminal: verify and extract the package

```bash
export FT_WORKSPACE="$(ws_find frametrail)"
cd "$HOME"
sha256sum -c frametrail-cluster-smoke.tar.gz.sha256
tar --keep-old-files -xzf frametrail-cluster-smoke.tar.gz -C "$FT_WORKSPACE"
cd "$FT_WORKSPACE/FrameTrail"
```

The checksum command must print `OK`. Extract once: `--keep-old-files` refuses to overwrite existing files if this step is repeated. The archive contains a minimal training checkout, not the Windows app. Its `transfer-manifest.json` records the source revision, file hashes and mechanical-test purpose. Dataset fingerprints and vocabulary are checked again before training. Derived Windows label caches are omitted.

## 4. Cluster terminal: install the isolated environment

```bash
bash -l training/setup-cluster-env.sh
```

This loads the reported Miniforge module and installs binary wheels in this project's `.venv`. It does not modify the module's shared Python installation or start training. Dependencies include the existing pinned PyTorch 2.8.0/torchvision 0.23.0 CUDA 12.8 wheels and the project's training requirements. [Official PyTorch wheel commands](https://pytorch.org/get-started/previous-versions/#v280).

The log's `CUDA Version: 13.2` describes the driver's supported CUDA level; it does not require PyTorch to use a CUDA 13.2 build. Newer NVIDIA drivers support older CUDA runtimes through [backward compatibility](https://docs.nvidia.com/deploy/cuda-compatibility/why-cuda-compatibility.html). CUDA operation is tested on the allocated GPU before training. Package installation downloads several GB and may take time. Core package versions are pinned; the final installed dependency snapshot is saved in `.venv/installed-packages.txt` and each experiment's environment report. The user's job 7446193 has now verified this Linux/CUDA smoke path.

## 5. Cluster terminal: submit one training test

Submit from the extracted FrameTrail folder:

```bash
sbatch training/run-cluster-smoke.sbatch
```

The script requests one NVIDIA GPU for at most 15 minutes in `dev_gpu_a100_il`. It uses the partition's CPU/memory defaults, loads the same Python module, checks CUDA with a real GPU tensor operation, validates the dataset/checkpoint, and runs one epoch on the 70-image training partition with the 11-image validation partition. The 15-image test partition remains untouched. Checkpoints and experiment reports go into `output/cluster-smoke-JOBID/`. The sample remains unreviewed and cannot be submitted as a substantial training dataset.

The queue succeeded for the user's diagnostic, but availability and account permissions are runtime facts. If Slurm rejects the request, share its error. GPU training belongs on compute nodes. [Official Slurm instructions and queue limits](https://wiki.bwhpc.de/e/BwUniCluster3.0/Running_Jobs).

## 6. Check the result

```bash
squeue
```

`PD` means waiting and `R` means running. Check manually, no more frequently than every 30 seconds. After completion, replace `JOBID` in the following commands with the number printed by `sbatch`:

```bash
cat frametrail-smoke-JOBID.log
cat output/cluster-smoke-JOBID/experiment.json
```

Success requires Slurm exit code 0 and experiment status `completed`; a vanished queue entry alone does not establish success. Send the log/error for the first run. The app continues using its current models until an independently evaluated candidate is adopted.

To return to the folder in a later SSH session, run `cd "$(ws_find frametrail)/FrameTrail"`. Retrieve important results to your laptop before the workspace expires. A larger dataset is a separate preparation step and does not block this infrastructure check.
