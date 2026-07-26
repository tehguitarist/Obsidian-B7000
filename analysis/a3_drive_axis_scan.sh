#!/bin/bash
# a3_drive_axis_scan -- Phase 9 / A3 step 3a (session 34).
#
# Sweep one FitParams candidate across the whole DRIVE axis and grade it with
# analysis/a3_drive_axis.py. The gate is a drive SWEEP (the defect is that the
# model's |OD| turns over at drive 2:30 instead of growing), so a candidate needs
# all five decompose CSVs before it can be judged at all -- a single-drive probe
# cannot see this class of error, which is why it survived four sessions.
#
# Usage:   analysis/a3_drive_axis_scan.sh <tag> [key=value ...]
# Example: analysis/a3_drive_axis_scan.sh c7_1n trebleC7=1e-9
#
# Runs the five drives in parallel (each is ~6 s single-threaded).
set -euo pipefail
tag="$1"; shift
out="build/s34/${tag}"
mkdir -p build/s34
for d in 0.0 0.25 0.5 0.75 1.0; do
    ./build/a3_blend_decompose 1 "$d" -18 "$@" > "${out}_drv${d}.csv" &
done
wait
echo "### ${tag}  ${*:-<nominal>}"
/opt/homebrew/bin/python3.11 analysis/a3_drive_axis.py \
    --csv-prefix "${out}_drv" --betas="-15.5,-16.93,-18.0"
