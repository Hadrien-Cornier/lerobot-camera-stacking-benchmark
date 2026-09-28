# Stacking camera views: a LeRobot benchmark

This repo tests one idea from the LeRobot roadmap ([#3832](https://github.com/huggingface/lerobot/issues/3832), items DATA-11 and DATA-03):

> Put the 3 camera views of a robot in **one** video file (stacked into one tall image) instead of **3** files. Does training read data faster?

## Answer

Yes, in most cases. Stacking wins for two reasons:

1. **Less CPU.** The reader decodes 1 video instead of 3. This makes it 1.4x to 1.9x faster.
2. **Fewer things to keep open.** You need 3x fewer files, decoders and network requests. This matters when many workers read at once.

Stacking does **not** make a single network read faster. With one reader and files of the same size, stacked and separate files are equally fast.

## Results

Dataset: [`lerobot/abc_130k_v3_train`](https://huggingface.co/datasets/lerobot/abc_130k_v3_train). It has 3 cameras (top, left wrist, right wrist) and is stored in LeRobot's default format (AV1, a keyframe every 2 frames). All reads go over `hf://` from a Hugging Face Jobs machine (`cpu-upgrade`, 8 CPUs). Each number is the mean of 3 runs, ± a 95% confidence interval.

| How training reads data | Separate files | Stacked | Stacked is |
|---|---|---|---|
| Streaming (`StreamingLeRobotDataset`), 1 process, frames/s | 182 ± 30 | 342 ± 17 | **1.9x faster** |
| Streaming, too many workers for the decoder cache, frames/s | 4.6 ± 1.5 | 308 ± 81 | **67x faster** |
| Whole-episode reads ([#3917](https://github.com/huggingface/lerobot/pull/3917)), 1 process, samples/s | 138 ± 80 | 212 ± 38 | **1.5x faster** |
| Whole-episode reads (#3917), 8 processes, samples/s | 1320 ± 240 | 1900 ± 521 | **1.4x faster** |
| Random access, 1 reader, same file size, samples/s | 7.7 ± 5.1 | 7.3 ± 3.4 | the same |
| Random access, 8 readers, samples/s (1 run) | 73 | 108 | **1.5x faster** |

### Why each row comes out this way

- **Streaming reads each file forward.** One 5 MB download serves about 1,700 frames, so the network costs almost nothing. What is left is decoding, and stacked needs 1 decode call instead of 3.
- **The decoder cache holds 100 open files per worker.** With `lerobot-train`, each worker keeps about `3 × num_workers` files open for separate cameras. Past about 34 workers the cache overflows. Separate files then reopen a file for almost every frame, and speed falls to 4.6 frames/s. Stacked needs 3x fewer open files, so it overflows only past about 100 workers.
- **#3917 downloads one episode per camera in one request.** Both layouts download the same bytes (24 vs 25 MB per episode). Stacked wins on CPU.
- **Random access with 1 reader waits on one request at a time.** Stacked sends 1 request per sample and separate files send 3, but the 3 go out at the same time, so the wait is the same.
- **With 8 readers, the number of requests counts.** Separate files sent 219 requests/s, stacked sent 107.

## What stacking costs

- **Every camera must have the same width and frame rate.** Cameras of different sizes need padding, or cannot be stacked.
- **The videos must be re-encoded.** Each stacked view is close to the separate encode (PSNR 40 dB or more), but not identical.
- **Reading one camera means decoding all of them.** A policy that uses 1 of 3 cameras pays for 3.
- **It is a format change.** Old LeRobot versions cannot read it. The reader must crop the views back into `observation.images.*`.

## Limits

- **Runs vary about 2x on the Hub.** The same files gave 6.8 samples/s in one run and 13.6 in another. So we only compare layouts inside the same run.
- All jobs ran inside Hugging Face's network. From a laptop, each request waited about 170 ms instead of about 65 ms. Fewer requests help more there.
- The "too many workers" row uses a small cache (12) with 8 shards. That gives the same hit rate as 64 workers with the default cache of 100.
- The #3917 pool held every episode, so it never had to swap episodes.
- One dataset: small frames (224 px) and 3 cameras.
- The 8-reader row is a single run.

## Follow-up questions

1. **For the DATA-03 owners:** is stacking planned? If yes, what happens to cameras of different sizes: pad, or refuse to stack?
2. Can a reader get the CPU gain without a format change, by decoding 3 separate files in one batched call?
3. Does the gain hold for bigger frames (480p, 720p) and for more cameras (ALOHA has 4)?
4. How many workers do large LeRobot training runs use? That decides how often the cache overflows.
5. Should stacking be an option when recording, a conversion tool for existing datasets, or both?
6. With a #3917 pool that swaps episodes, does 1 request per episode instead of 3 matter?

## Not in this report

We also tested faster readers (exact byte ranges, opening files outside the decoder cache lock) and multi-track MP4 files (one file, 3 video tracks). Those results will go in separate issues. One of them needs attention now: on a multi-track file, #3917 returns the first camera for every camera, with no error.

## Files

- [`METHOD.md`](METHOD.md): how we measured, the job ids and the cost.
- [`bench/`](bench/): the code. It runs on Hugging Face Jobs, and one round costs under $0.10. See [`bench/README.md`](bench/README.md).
- [`results/`](results/): summaries and raw numbers for each round.
- Test videos: [`hadriencornier/lerobot-camera-stacking-benchmark`](https://huggingface.co/datasets/hadriencornier/lerobot-camera-stacking-benchmark) on the Hub.

Source data: `lerobot/abc_130k_v3_train` (Apache-2.0), from the ABC project ([paper](https://arxiv.org/abs/2606.27375), [code](https://github.com/amazon-far/abc)). This repo is Apache-2.0.

I used AI (Claude) to help write the code and this text. The numbers come from the jobs listed in `METHOD.md`.
