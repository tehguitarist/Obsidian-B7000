#!/bin/zsh
# a3_level_axis_scan -- sweep one FitParams value across the LEVEL axis and gate it.
#
# The level-axis gate needs 15 decompose passes per candidate (5 drives x 3
# stimulus levels), because the defect it is built to see only exists in how the
# OD/bleed ratio moves with input LEVEL. ~6.4 s per pass, so ~15 s per candidate
# with the parallelism below.
#
# ⚠ Always pass the parameter EXPLICITLY, including the "off" condition -- never
# rely on omitting the flag to mean disabled. Session 36 lost a scan to exactly
# that: a FitParams default had already been moved mid-session, so "no override"
# silently meant "at the new default", and an A/B came back bit-identical.
#
# Usage: analysis/a3_level_axis_scan.sh <tag> <key=value> [key=value ...]
#   e.g. analysis/a3_level_axis_scan.sh c15_5p2 clipC15=5.2e-9
set -e
TAG="$1"; shift
[ -z "$TAG" ] && { echo "usage: $0 <tag> <key=value>..." >&2; exit 1; }
# GUARD: refuse to run with no override at all. Called with zero key=value pairs
# this would silently re-render the SHIPPED defaults under a candidate's tag and
# print a gate that looks like "the candidate changed nothing" -- which is exactly
# how session 36 lost a scan, and how a caller-side quoting slip lost one here
# (zsh does not word-split unquoted parameters, so `set -- $spec` passed the whole
# string as the tag and no arguments at all). A bit-identical A/B must be a
# measurement, never a wiring accident.
if [ $# -eq 0 ]; then
  echo "$0: refusing to scan with no key=value override -- that would just re-render" >&2
  echo "  the shipped defaults. Pass the parameter explicitly, including its OFF value." >&2
  exit 2
fi
for a in "$@"; do
  case "$a" in *=*) ;; *) echo "$0: '$a' is not key=value" >&2; exit 2 ;; esac
done
PREFIX="build/a3ls_${TAG}_"
for L in -18 -12 -6; do
  for d in 0.0 0.25 0.5 0.75 1.0; do
    ./build/a3_blend_decompose 1 $d $L "$@" > "${PREFIX}${L}_drv${d}.csv" &
  done
done
wait
# fail loudly if the superposition self-check ever degrades -- every number the
# gate prints is meaningless if full != od + clean.
awk -F, '!/^#/ && $10 > -200 { print "SUPERPOSITION FAILED", FILENAME, $1, $10; bad=1 }
         END { if (bad) exit 1 }' ${PREFIX}*.csv
/opt/homebrew/bin/python3.11 analysis/a3_level_axis.py --gate-only \
    --prefix "$PREFIX" --label "[$TAG: $*]"
