#!/usr/bin/env bash
# Round 4 train side: stage the job files into job/_bundle_r4train/ with SHA256SUMS (upload target: bundle-r4train/).
# Uploads nothing.
set -euo pipefail
JOB="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SRC="$(cd "$JOB/.." && pwd)"
STAGE="$JOB/_bundle_r4train"
rm -rf "$STAGE"
mkdir -p "$STAGE/job"
for f in r4train_bench.py; do
  cp "$SRC/$f" "$STAGE/$f"
done
cp "$JOB/entrypoint_r4train.sh" "$JOB/watch_job.py" "$STAGE/job/"
chmod +x "$STAGE"/job/*.sh
(cd "$STAGE" && find . -type f ! -name SHA256SUMS | sed 's|^\./||' | LC_ALL=C sort | xargs shasum -a 256 > SHA256SUMS)
echo "staged $(wc -l < "$STAGE/SHA256SUMS" | tr -d ' ') files in $STAGE"
echo "Upload: hf upload $RESULTS_REPO \"$STAGE\" bundle-r4train --repo-type dataset --private"
