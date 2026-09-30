# How to run the benchmark

This folder is the code that made the numbers in `../results/`. It runs on Hugging Face Jobs (HF Jobs). HF Jobs are containers that Hugging Face runs for you and bills per minute. Every job uses the `cpu-upgrade` machine (8 CPUs, 32 GB RAM) and the image `python:3.12-slim-trixie`.

## What it compares

The source is `lerobot/abc_130k_v3_train@68651e49`: 3 cameras, 224x224, 30 fps, AV1. All layouts hold the same decoded pixels and use the same encoder (libsvtav1, crf 30, GOP 2, yuv420p, preset 12, the LeRobot default).

- SEP: one video file per camera.
- STACK: one video file per group. The 3 cameras sit on top of each other (224x672), in the order `top, left_wrist, right_wrist`.
- BIG: like SEP, but 3 groups joined into one file (3x the frames per file).
- MULTI (round 2): one MP4 file with 3 video tracks, a stream copy of the 3 SEP files.

`selection.json` lists the episodes in each group. `select_slice.py` made it from the pinned dataset metadata. You do not need to run it again.

## Before you start

1. A Hugging Face account that can run HF Jobs (a Pro account, or an organization with billing).
2. A token with write access in `HF_TOKEN`.
3. The `hf` CLI: `pip install "huggingface_hub>=1.0"`.
4. A dataset repo that you own, for results. Make it private:

```bash
export RESULTS_REPO=<your-user>/camera-stacking-results
hf repos create "$RESULTS_REPO" --repo-type dataset --private
```

## Environment variables

| name | default | what it does |
|---|---|---|
| `RESULTS_REPO` | none, required | Where the job writes results, its bundle, and any new videos. The job stops with a clear message if it is not set. |
| `VARIANTS_REPO` | `hadriencornier/lerobot-camera-stacking-benchmark` | Where rounds 2 and 3 read the test videos (`variants/...`). The default is the public copy. |
| `VARIANTS_REVISION` | `b4a3426ab4b1105ecd2caf2e747019af898a6e5d` (pinned) | Branch or commit of `VARIANTS_REPO`. |
| `R1_RUN` | `20260925T025221Z` | The round-1 run whose videos rounds 2 and 3 use. |
| `PREP_SEP_REPO`, `PREP_STACK_REPO` | `hadriencornier/lerobot-data11-stream-sep`, `-stream-stack` | Small LeRobot v3 datasets that round 2 builds and uploads. Set them to repos in your own namespace. |
| `R3_SEP_REPO`, `R3_STACK_REPO` | `hadriencornier/lerobot-data11-r3-sep`, `-r3-stack` | The same for round 3. Set them to your own repos. |
| `SMOKE=1` | off | A short test run. |
| `NO_UPLOAD=1` | off | Run with nothing uploaded (for local tests). |
| `STAGES` | every stage of that round | Run only some stages, for example `STAGES="prep2 access"`. |

Each stage script also reads its own knobs (`DL_*`, `RM_*`, `ACC_*`, `STREAM_*`, `P_*`, `SZ_*`). They are listed at the top of each script.

When `VARIANTS_REPO` is not `RESULTS_REPO`, the prep stage of rounds 2 and 3 first copies the input videos it needs into `RESULTS_REPO`, at the same paths. Then every later stage reads all files from one repo at one revision, as in the original runs. This copy is about 1.5 GB (round 2) or 2.5 GB (round 3).

The public dataset holds the `ckpt_full` videos of round 1 and the round-3 cuts. The smaller `ckpt_1k` and `ckpt_5k` families are not there. To test with them, run round 1 yourself.

## Round 1: encode, then read locally and over hf://

Script: `job/entrypoint.sh`. It encodes every layout, uploads the `ckpt_*` families to `RESULTS_REPO` under `variants/<run>/`, and then measures.

| stage | script | what it does |
|---|---|---|
| fetch | `s1_fetch.py` | Downloads only the selected source MP4s (4.34 GB, 0.82 GB for smoke). Checks sizes. |
| encode | `s2_encode.py` | Decodes the sources once. Writes SEP (3 files) and STACK per group. |
| big | `s3_big.py` | Builds BIG with `ffmpeg -f concat -c copy`. Checks packets and timestamps. |
| verify | `s4_verify.py` | Checks exact timestamps, camera order, and that BIG decodes the same as SEP. |
| upload | `s8_upload.py` | Uploads SEP, STACK and BIG to `RESULTS_REPO` (must be private). Reads them back at that commit. |
| remote | `s9_remote.py` | Main result. Reads the files over `hf://` the way LeRobot does. Counts requests, bytes and 429 errors. |
| opencost | `s5_opencost.py` | Cost to open a file, first frame, steady decode, warm and cold. |
| loader | `s6_loader.py` | PyTorch DataLoader arms with a per-worker file cache (PR #4556 behavior). |
| model | `s7_model.py` | Fits the numbers and predicts ABC v3 and DROID v3. These are extrapolations. |

## Round 2: streaming and random access

Script: `job/entrypoint.sh` with `STAGES="prep2 stream access summary2"`. It reuses the round-1 videos and does not encode.

| stage | script | what it does |
|---|---|---|
| prep2 | `s10_prep.py` | Builds MULTI from SEP (stream copy) and checks it decodes bit-exact. Builds 2 small v3 datasets (SEP, STACK). |
| stream | `s12_stream.py` | The real `StreamingLeRobotDataset` (lerobot PR #4702 branch) over `hf://`. |
| access | `s11_access.py` | Random access over `hf://` with cheaper reader fixes (smaller blocks, reused signed link, exact byte ranges). |
| summary2 | `s13_summary.py` | Writes `summary.md`. |

`readers.py` holds the round-2 readers.

## Round 3: equal-size files and PR #3917

Script: `job/entrypoint_r3.sh`.

| stage | script | what it does |
|---|---|---|
| prep | `r3_prep.py` | Cuts STACK and MULTI into files of about the same bytes as one SEP file (stream copy, checked bit-exact). Builds 2 v3 datasets for PR #3917. |
| size | `r3_size.py` | Does request time grow with file size inside HF? 256 KiB range reads on files of different sizes. |
| access | `r3_access.py` | The round-2 random access arms on the equal-size files, plus a control on the round-2 files. |
| pr3917 | `r3_pr3917.py` | PR #3917 (episode-pool streaming) on SEP vs STACK, 1 and 8 processes, plus a multi-track check. |
| size2 | `r3_size.py` | The size check again, at the end. |
| summary | `r3_summary.py` | Writes `summary.md`. |

## Round 4: 4 more datasets, and GPU step time

Script: `job/entrypoint_r4.sh`, one job per dataset (`R4_DATASET` = `droid`, `molmo`, `libero` or `hqf`).

| stage | script | what it does |
|---|---|---|
| slice | `r4_slice.py` | Reads the real file stats and takes whole consecutive episodes (up to `R4_MAX_FRAMES`, default 60,000) from the first video file of every camera. |
| encode | `r4_encode.py` | Decodes once, then writes SEP and STACK with LeRobot's default encoder. Pads cameras of different sizes. |
| build | `r4_build.py` | Builds 3 small LeRobot v3 datasets (SEP, STACK, SEP1 with 1 camera), 8 copies of the slice each, and uploads them as private repos named `R4_REPO_PREFIX-<ds>-{sep,stack,sep1}`. Set `R4_REPO_PREFIX` to your own namespace. |
| check | `r4_check.py` | PSNR, camera order, `hf://` == local, and a read back through `LeRobotDataset`. |
| stream | `r4_stream.py` | `StreamingLeRobotDataset` over `hf://`, plus a DataLoader shard audit. |
| map | `r4_map.py` | Map-style `LeRobotDataset` on the local copies, with `lerobot-train` DataLoader settings. |
| summary | `r4_summary.py` | Writes `summary.md`. |

`LEROBOT_SHA` pins LeRobot. Round 4 used `32b671d437f8c50014f74a322ad3df09c6fab944`, the head of [#4702](https://github.com/huggingface/lerobot/pull/4702), because streaming on `main` breaks after the first file of a multi-file dataset.

`r4train_bench.py` (script `job/entrypoint_r4train.sh`) times training steps of ACT and SmolVLA on a GPU with synthetic batches of each dataset's shapes.

## Launch

Run these from this folder. First build the bundle (the scripts plus `SHA256SUMS`) and upload it to your results repo. The job downloads it and checks the checksums.

```bash
bash job/make_bundle.sh
hf upload "$RESULTS_REPO" job/_bundle bundle --repo-type dataset --private
bash job/make_bundle_r3.sh
hf upload "$RESULTS_REPO" job/_bundle_r3 bundle-r3 --repo-type dataset --private
```

Round 1 smoke test (about 11 minutes):

```bash
hf jobs run --detach --flavor cpu-upgrade --timeout 45m \
  --secrets HF_TOKEN --env RESULTS_REPO="$RESULTS_REPO" --env SMOKE=1 \
  python:3.12-slim-trixie \
  bash -c 'set -e; pip install -q --root-user-action=ignore "huggingface_hub>=1.0"; hf download "$RESULTS_REPO" --repo-type dataset --include "bundle/*" --local-dir /work/dl >/dev/null; exec bash /work/dl/bundle/job/entrypoint.sh'
```

Round 1 main run (the settings used for `results/round1`):

```bash
hf jobs run --detach --name camera-stacking-r1 --flavor cpu-upgrade --timeout 8h \
  --secrets HF_TOKEN --env RESULTS_REPO="$RESULTS_REPO" \
  --env DL_BUDGET_S=21600 --env DL_ARM_CAP_S=180 --env DL_REPEATS=2 \
  python:3.12-slim-trixie \
  bash -c 'set -e; pip install -q --root-user-action=ignore "huggingface_hub>=1.0"; hf download "$RESULTS_REPO" --repo-type dataset --include "bundle/*" --local-dir /work/dl >/dev/null; exec bash /work/dl/bundle/job/entrypoint.sh'
```

Round 2 (the settings used for `results/round2`):

```bash
hf jobs run --detach --name camera-stacking-r2 --flavor cpu-upgrade --timeout 3h \
  --secrets HF_TOKEN --env RESULTS_REPO="$RESULTS_REPO" \
  --env STAGES="prep2 stream access summary2" --env STREAM_REPEATS=3 \
  --env PREP_SEP_REPO=<your-user>/camera-stacking-stream-sep --env PREP_STACK_REPO=<your-user>/camera-stacking-stream-stack \
  python:3.12-slim-trixie \
  bash -c 'set -e; pip install -q --root-user-action=ignore "huggingface_hub>=1.0"; hf download "$RESULTS_REPO" --repo-type dataset --include "bundle/*" --local-dir /work/dl >/dev/null; exec bash /work/dl/bundle/job/entrypoint.sh'
```

Round 3 (the settings used for `results/round3`):

```bash
hf jobs run --detach --name camera-stacking-r3 --flavor cpu-upgrade --timeout 2h \
  --secrets HF_TOKEN --env RESULTS_REPO="$RESULTS_REPO" \
  --env P_N1=8000 --env P_N8=2000 --env P_CAP_S=300 --env SZ_N=60 \
  --env R3_SEP_REPO=<your-user>/camera-stacking-r3-sep --env R3_STACK_REPO=<your-user>/camera-stacking-r3-stack \
  python:3.12-slim-trixie \
  bash -c 'set -e; pip install -q --root-user-action=ignore "huggingface_hub>=1.0"; hf download "$RESULTS_REPO" --repo-type dataset --include "bundle-r3/*" --local-dir /work/dl_bundle >/dev/null; exec bash /work/dl_bundle/bundle-r3/job/entrypoint_r3.sh'
```

Round 4, one job per dataset (the settings used for `results/round4`):

```bash
bash job/make_bundle_r4.sh
hf upload "$RESULTS_REPO" job/_bundle_r4 bundle-r4 --repo-type dataset --private
hf jobs run --detach --name camera-stacking-r4-droid --flavor cpu-upgrade --timeout 3h \
  --secrets HF_TOKEN --env RESULTS_REPO="$RESULTS_REPO" --env R4_DATASET=droid \
  --env LEROBOT_SHA=32b671d437f8c50014f74a322ad3df09c6fab944 --env R4_STREAM_REPEATS=5 --env R4_MAP_REPEATS=4 \
  --env R4_REPO_PREFIX=<your-user>/camera-stacking-r4 \
  python:3.12-slim-trixie \
  bash -c 'set -e; pip install -q --root-user-action=ignore "huggingface_hub>=1.0,<2"; hf download "$RESULTS_REPO" --repo-type dataset --include "bundle-r4/*" --local-dir /work/dl >/dev/null; exec bash /work/dl/bundle-r4/job/entrypoint_r4.sh'
```

Round 4 GPU step time (A100; use `--flavor l4x1 --env FLAVOR_TAG=l4 --env R4T_BUDGET_S=720 --env R4T_RUN_TIMEOUT_S=360` for the L4):

```bash
bash job/make_bundle_r4train.sh
hf upload "$RESULTS_REPO" job/_bundle_r4train bundle-r4train --repo-type dataset --private
hf jobs run --detach --name camera-stacking-r4train-a100 --flavor a100-large --timeout 45m \
  --secrets HF_TOKEN --env RESULTS_REPO="$RESULTS_REPO" --env FLAVOR_TAG=a100 \
  --env PIP_BREAK_SYSTEM_PACKAGES=1 --env R4T_BUDGET_S=420 --env R4T_RUN_TIMEOUT_S=300 \
  pytorch/pytorch:2.11.0-cuda12.8-cudnn9-runtime \
  bash -c 'set -e; python3 -m pip install -q --root-user-action=ignore "huggingface_hub>=1.0,<2"; hf download "$RESULTS_REPO" --repo-type dataset --include "bundle-r4train/*" --local-dir /work/dl >/dev/null; exec bash /work/dl/bundle-r4train/job/entrypoint_r4train.sh'
```

## Watch a job

```bash
hf jobs logs <job id>
hf jobs inspect <job id>
python job/watch_job.py <job id> --max-running-min 120   # cancels the job if it runs too long
```

Results appear in `RESULTS_REPO` under `results/<run name>/` after every stage. `STATUS.tsv` lists each stage, its time and its peak memory. `README.md` or `summary.md` in that folder holds the tables.

The job refuses to run twice with the same job id. HF Jobs restarts a container from scratch after an out-of-memory kill, and the restart does not respect `--timeout`. The guard stops that second run. Never add `set -x` to the entrypoints: `HF_TOKEN` is in the environment.

## Time and cost

`cpu-upgrade` costs about $0.03 per hour, `a100-large` $2.50 and `l4x1` $0.80. The original runs took:

| run | wall time | cost |
|---|---|---|
| round 1 smoke | 11 min | under $0.01 |
| round 1 main | 1 h 46 min | about $0.05 |
| round 2 | 1 h 1 min | about $0.03 |
| round 3 | 37 min | about $0.02 |
| round 4, per dataset | 40 to 52 min | about $0.03 |
| round 4 GPU, A100 | 9 min | about $0.38 |
| round 4 GPU, L4 | 16 min | about $0.22 |

With the default `VARIANTS_REPO`, rounds 2 and 3 take a few minutes longer, for the copy into `RESULTS_REPO`.

## Local test

Docker, no upload, smoke settings:

```bash
bash job/make_bundle.sh
docker run --rm -v "$PWD/job/_bundle:/bundle:ro" -e NO_UPLOAD=1 -e SMOKE=1 -e BUNDLE_DIR=/bundle \
  python:3.12-slim-trixie bash /bundle/job/entrypoint.sh
```

## Notes

- Every stage that decodes limits its thread pools with `pin_threads()`. HF containers report 64 CPUs, but the quota is 8.
- `huggingface_hub` is pinned to 1.30.0 in the job, because the HTTP counter patches its internals.
- Each `hf://` block read costs one resolve call plus one CDN call. The resolve calls share a per-token limit (12000 per 300 s when checked on 2026-09-24).
- Identical files can differ about 2x in speed between runs. Compare layouts only inside one run.
