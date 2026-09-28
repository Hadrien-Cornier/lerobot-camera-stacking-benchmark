#!/usr/bin/env bash
# Round 3: stage the job files into job/_bundle_r3/ with SHA256SUMS (upload target: bundle-r3/). Uploads nothing.
set -euo pipefail
JOB="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SRC="$(cd "$JOB/.." && pwd)"
STAGE="$JOB/_bundle_r3"
rm -rf "$STAGE"
mkdir -p "$STAGE/job"
for f in common.py selection.json readers.py s10_prep.py s11_access.py r3_prep.py r3_size.py r3_access.py r3_pr3917.py r3_summary.py r1_upload.json; do
  cp "$SRC/$f" "$STAGE/$f"
done
cp "$JOB/entrypoint_r3.sh" "$JOB/watch_job.py" "$STAGE/job/"
chmod +x "$STAGE"/job/*.sh
(cd "$STAGE" && find . -type f ! -name SHA256SUMS | sed 's|^\./||' | LC_ALL=C sort | xargs shasum -a 256 > SHA256SUMS)
echo "staged $(wc -l < "$STAGE/SHA256SUMS" | tr -d ' ') files in $STAGE"
echo "Upload: hf upload \"\$RESULTS_REPO\" \"$STAGE\" bundle-r3 --repo-type dataset --private"
