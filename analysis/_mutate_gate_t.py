#!/usr/bin/env python3
"""Mutation-test GATE T's guards.

Each mutation must make the gate exit non-zero.  An UNMUTATED CONTROL runs first: if the control
does not PASS, no failure below is attributable to a mutation (s107 -- five "passes" that were all
ModuleNotFoundError).  The patched copy LIVES in analysis/ so its sibling imports resolve, and RUNS
from the repo root so its repo-relative data paths resolve -- getting only one of those right is
s110's trap.  Every needle is asserted present EXACTLY ONCE, so a vacuous mutation reports as
vacuous rather than as a dead guard (s110/s113).
"""
import os, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SRC = os.path.join(HERE, "master_anchor_gate.py")

MUTATIONS = [
    ("T2 pad value",
     "NOMINAL_N12_TO_N18_PAD = 6.000", "NOMINAL_N12_TO_N18_PAD = 7.000"),
    ("T2/T3 pure-gain flatness",
     "PURE_GAIN_SPAN_TOL   = 0.010", "PURE_GAIN_SPAN_TOL   = 0.000000001"),
    ("T3 duplicate identity",
     "DUP_IDENTITY_DBFS    = -60.0", "DUP_IDENTITY_DBFS    = -200.0"),
    ("T3 data: point at genuinely DIFFERENT detents",
     'DUP_DETENTS = ("1545", "1700")', 'DUP_DETENTS = ("1430", "1700")'),
    ("T4 flat-spot control",
     "DETENT_STEP_MIN_DB   = 0.50", "DETENT_STEP_MIN_DB   = 0.0001"),
    ("T5 anchor-error magnitude",
     "if err < 1.0:", "if err < 10.0:"),
    ("T6 power-law spread",
     "if hi / lo < 1.25:", "if hi / lo < 5.0:"),
    ("T7 tool-staleness list",
     '    needed = ["master-0700_base-clean.wav", "master-0930_base-clean.wav", "ref-clean.wav",',
     '    needed = ["ref-clean.wav",'),
]


def run(path):
    r = subprocess.run([sys.executable, path, "--json", os.path.join(tempfile.gettempdir(), "mt.json")],
                       cwd=ROOT, capture_output=True, text=True)
    last = [l for l in r.stdout.splitlines() if l.strip()]
    return r.returncode, (last[-2] if len(last) > 1 else "") + " | " + (last[-1] if last else "")


def main():
    src = open(SRC).read()
    tmp = os.path.join(HERE, "_gate_t_mutant.py")

    print("=" * 90)
    open(tmp, "w").write(src)
    rc, tail = run(tmp)
    print(f"CONTROL (unmutated): rc={rc}  {'PASS' if rc == 0 else '** BROKEN -- results below mean nothing'}")
    print(f"   {tail}")
    if rc != 0:
        os.remove(tmp)
        return 1

    print("=" * 90)
    bad = 0
    for name, needle, repl in MUTATIONS:
        n = src.count(needle)
        if n != 1:
            print(f"{name:44s} ** VACUOUS -- needle appears {n} times (expected exactly 1)")
            bad += 1
            continue
        open(tmp, "w").write(src.replace(needle, repl))
        rc, tail = run(tmp)
        ok = rc != 0
        print(f"{name:44s} rc={rc}  {'FIRES' if ok else '** GUARD DEAD'}")
        if not ok:
            bad += 1
        else:
            print(f"   {tail.strip()[:140]}")
    os.remove(tmp)
    print("=" * 90)
    print(f"{len(MUTATIONS)-bad}/{len(MUTATIONS)} guards fire; control passes."
          if not bad else f"** {bad} problem(s)")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
