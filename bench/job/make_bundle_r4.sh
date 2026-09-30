#!/usr/bin/env bash
# Round 4: stage the job files into job/_bundle_r4/ with SHA256SUMS (upload target: bundle-r4/). Uploads nothing.
set -euo pipefail
JOB="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SRC="$(cd "$JOB/.." && pwd)"
STAGE="$JOB/_bundle_r4"
rm -rf "$STAGE"
mkdir -p "$STAGE/job"
for f in common.py r4_common.py r4_slice.py r4_encode.py r4_build.py r4_check.py r4_stream.py r4_map.py r4_summary.py; do
  cp "$SRC/$f" "$STAGE/$f"
done
cp "$JOB/entrypoint_r4.sh" "$JOB/watch_job.py" "$STAGE/job/"
chmod +x "$STAGE"/job/*.sh
(cd "$STAGE" && find . -type f ! -name SHA256SUMS | sed 's|^\./||' | LC_ALL=C sort | xargs shasum -a 256 > SHA256SUMS)
echo "staged $(wc -l < "$STAGE/SHA256SUMS" | tr -d ' ') files in $STAGE"
echo "Upload: hf upload $RESULTS_REPO \"$STAGE\" bundle-r4 --repo-type dataset --private"
