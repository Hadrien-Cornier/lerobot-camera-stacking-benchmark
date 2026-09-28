# Method

## Source data

- Dataset: `lerobot/abc_130k_v3_train` at revision `68651e4929d9fb00f798937b2d62617cab5c771d`. It has 38,164 video files, 3.43 TB, and 3 cameras (`top`, `left_wrist`, `right_wrist`).
- We took a slice of episodes (listed in `bench/selection.json`). We decoded it once, then re-encoded it with LeRobot's default settings into these layouts:

| Layout | What it is |
|---|---|
| SEP | One MP4 per camera, the same as LeRobot v3 today |
| STACK | The 3 views stacked vertically into one video |
| BIG | 3 SEP groups joined into one file, 3x longer (tests "fewer files" without stacking) |
| MULTI | One MP4 with 3 video tracks, copied from SEP with no re-encode |
| r3 cuts | STACK and MULTI files cut at keyframes to the same size in bytes as the SEP files |

The test videos are public: [`hadriencornier/lerobot-camera-stacking-benchmark`](https://huggingface.co/datasets/hadriencornier/lerobot-camera-stacking-benchmark).

## Machines

- Every job ran on Hugging Face Jobs, flavor `cpu-upgrade`: 8 CPUs, 32 GB of RAM.
- The container reports 64 CPUs, but its quota is 8. The code reads the quota from `cpu.max` and pins every thread pool to it.
- One extra run went from a laptop, over the internet, and downloaded 369 MB.

## Rounds

| Round | What it measured | Job | Time | Cost |
|---|---|---|---|---|
| 1 | Local decode model. Random access over `hf://` with the default 5 MB blocks. STACK files held the same frames as SEP, so they were 3x bigger. | `6ab5e1dc52d0dbd7f1d8df2a` | 1 h 45 min | about $0.05 |
| 2 | Real `StreamingLeRobotDataset` (with the fix from [#4702](https://github.com/huggingface/lerobot/pull/4702)). Random access with block sizes from 64 KB to 5 MB, reused file lookups, exact byte ranges, and 8 readers. | `6ab69b4b6b030d633f691998` | 61 min | about $0.035 |
| 3 | Equal-size files, file size vs request time inside Hugging Face, and [#3917](https://github.com/huggingface/lerobot/pull/3917) on SEP vs STACK. | `6ab6bd546b030d633f691efe` | 37 min | about $0.03 |

The README takes each number from the round that measured it best:
- streaming: round 2;
- random access with equal-size files, and #3917: round 3.

Round 1 and round 2 random-access numbers used 3x bigger STACK and MULTI files, and they come from different runs. The README does not use them.

## How each number is measured

- **Streaming:** frames/s from `StreamingLeRobotDataset`, with the default shuffle buffer of 1,000.
  - The shard count is the same for both layouts in each pair.
  - To test "too many workers", we set the decoder cache to 12 with 8 shards. That gives a hit rate of about 0.5, the same as 64 shards with the default cache of 100. A simulation agreed: 0.498 vs 0.516.
- **Random access:** samples/s, drawing random frame numbers with a fixed seed, the same for every layout.
  - Separate files read their 3 cameras in parallel threads.
  - "Warm" means the file is already open. "Cold" means a new decoder for every sample.
- **#3917:** samples/s over the second half of each 300 s run, once the episode pool is full.
  - #3917 allows 1 DataLoader worker per process, so "8 processes" means 8 separate processes.
- **Requests and bytes:** we count every HTTP request `huggingface_hub` sends, by type (lookup, download), and every byte.
- **Repeats:** 3 per arm. The ± values are 95% confidence intervals (Student t). 8-reader arms ran once.

## One rule we learned

The same files can run 2x faster or slower from one job to the next: 6.8 samples/s in round 2, 13.6 in round 3. So we compare layouts **only inside the same job**. Numbers from different jobs are never compared.

## Checks

- Every remote decode matched a local decode, bit for bit: 112 of 112 in round 2, 52 of 52 in round 3.
- The r3 cuts have the same frames, timestamps and packet bytes as the originals: 18 of 18 files.
- Stacked views compared with the separate encodes: PSNR at least 40.2 dB.
- Multi-track: each track matched its own camera when chosen by track number (360 of 360 frames).
