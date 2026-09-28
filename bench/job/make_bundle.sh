#!/usr/bin/env bash
# Stage the scripts the job needs into job/_bundle/ with SHA256SUMS. Does NOT upload anything;
# it prints the upload command for the operator to run.
set -euo pipefail
JOB="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SRC="$(cd "$JOB/.." && pwd)"
STAGE="$JOB/_bundle"
rm -rf "$STAGE"
mkdir -p "$STAGE/job"
for f in common.py selection.json select_slice.py s1_fetch.py s2_encode.py s3_big.py s4_verify.py s5_opencost.py s6_loader.py s7_model.py s8_upload.py s9_remote.py readers.py s10_prep.py s11_access.py s12_stream.py s13_summary.py r1_upload.json; do
  cp "$SRC/$f" "$STAGE/$f"
done
cp "$JOB/entrypoint.sh" "$JOB/watch_job.py" "$SRC/README.md" "$STAGE/job/"
chmod +x "$STAGE"/job/*.sh
(cd "$STAGE" && find . -type f ! -name SHA256SUMS | sed 's|^\./||' | LC_ALL=C sort | xargs shasum -a 256 > SHA256SUMS)
echo "staged $(wc -l < "$STAGE/SHA256SUMS" | tr -d ' ') files in $STAGE"
echo
echo "Upload:"
echo "  hf upload \"\$RESULTS_REPO\" \"$STAGE\" bundle --repo-type dataset --private --commit-message \"DATA-11 job bundle\""
