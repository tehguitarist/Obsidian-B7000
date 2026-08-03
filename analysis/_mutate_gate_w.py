#!/usr/bin/env python3.11
"""Mutation test for GATE W (`feature_locus_gate.py`).  Session 122.

Every guard is broken on purpose and the gate must REFUSE, with the refusal coming from the guard
the mutation was aimed at -- not merely with a non-zero exit code.  Session 117's lesson: a runner
that scores `rc != 0` alone cannot tell a firing guard from a crash, and the vacuity mutation in
that session did crash.

Two mechanics that are easy to get wrong and have both cost real sessions:
  * the patched copy must LIVE in `analysis/` (so its sibling imports resolve) and RUN from the
    repo root (so repo-relative data paths resolve).  Getting only the first half right is what
    session 107 recorded; getting only the second gives ModuleNotFoundError on every arm and reads
    as 100 % PASS.
  * each needle is asserted to appear EXACTLY ONCE in the source, so a mutation that silently
    matches nothing reports as VACUOUS instead of as a dead guard.
"""
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "analysis", "feature_locus_gate.py")
TMP = os.path.join(ROOT, "analysis", "_mutant_gate_w.py")

# (name, tag the refusal must carry, needle, replacement, why)
MUTATIONS = [
    # ⚠⚠ TWO SUCCESSIVE VERSIONS OF THIS MUTATION WERE VACUOUS AND BOTH READ AS "GUARD DEAD".
    # `suspect the mutation before the guard` (s110), twice over -- and the second one is worth
    # recording because it measured a real property rather than just wasting a run:
    #   (1) a 12 dB tilt across the grid (0.026 dB per cell).  A vertex slides by the tilt divided
    #       by the CURVATURE, so on a 15-20 dB-deep notch with steep flanks it moved essentially
    #       nothing.  Amplitude bias is not frequency bias.
    #   (2) a 5 % multiplicative bias on the frequency GRID.  Also inert -- and necessarily so:
    #       the grid is LOG-UNIFORM, so scaling it merely re-indexes the same set of cell centres,
    #       and each cell still averages the real curve around its own reported centre.  The
    #       locator is INVARIANT to the grid's absolute offset, which is a property worth having
    #       and which this mutation accidentally proved.
    # The honest mutation is to bias the REPORTED vertex.  It is also a clean demonstration of the
    # division of labour between the two known answers: it breaks W1a (an ABSOLUTE comparison) and
    # leaves W1b untouched (a RATIO, in which any multiplicative bias cancels exactly).
    ("W1a locator biased",
     "GATE W1a",
     "    f0 = float(np.exp(LOG_GRID[i] + dl * step))",
     "    f0 = 1.05 * float(np.exp(LOG_GRID[i] + dl * step))",
     "put a 5 % bias on the REPORTED vertex -- the cross-instrument known answer against GATE R "
     "must catch it"),

    ("W1b perturbation inert",
     "GATE W1b",
     '        ap += ["--fit", f"{k}={v * 2.0:.6e}"]',
     '        ap += ["--fit", f"{k}={v * 1.0:.6e}"]',
     "make the ladder x2 arm render the SHIPPED value -- the notch does not move, so the R-C "
     "scaling law must refuse (this is also the `a bit-identical A/B must be a measurement, "
     "never an accident` check)"),

    ("W1b moved-window wrong",
     "GATE W1b",
     "MID_WIN_MOVED = (100.0, 260.0)",
     "MID_WIN_MOVED = (285.0, 358.0)",
     "point the moved-notch window where the notch is NOT -- the arm's own validity guards must "
     "refuse before the ratio is read (this reproduces a real defect from this session)"),

    ("W2 reference condition typed instead of read",
     "GATE W2",
     "    ref = dict(caps[REF_OD]['settings'])".replace("'", '"'),
     '    ref = {"master": 0.5, "blend": 1.0, "drive": 0.5, "attackIdx": 1, "gruntIdx": 1}',
     "hardcode the matrix default (with the WRONG attackIdx, exactly as the first draft did) -- "
     "the ladder collapses and the detent-count assertion must refuse"),

    ("W2 endpoint count moved",
     "GATE W2",
     "    eps = Q.endpoints_od(caps)",
     "    eps = Q.endpoints_od(caps)[:-1]",
     "drop an endpoint so GATE Q's selection really HAS changed under us -- the asserted count "
     "must refuse rather than grading whatever arrived.  NOTE this is a DATA-level mutation on "
     "purpose (s114): flipping the PREDICATE instead fires the same exit but prints the two real, "
     "EQUAL counts, i.e. a refusal whose own message contradicts itself"),

    ("W2 dropout token matches nothing",
     "GATE W2",
     '    if Q.DEFECT_TOKEN not in "".join(caps):',
     '    if "no-such-capture-token" not in "".join(caps):',
     "an exclusion that excludes nothing is `empty-gate-must-fail` in a costume"),

    ("W3 prominence sweep does not turn",
     "GATE W3",
     "PROM_SWEEP = (0.5, 1.0, 2.0, 4.0)",
     "PROM_SWEEP = (1.0, 1.0, 1.0, 1.0)",
     "a robustness sweep whose knob never moves is a constant printed four times (s106 N5)"),

    ("W1 known-answer source absent",
     "GATE W1",
     'GATE_R_REPORT = "analysis/reports/s110_null_locus.json"',
     'GATE_R_REPORT = "analysis/reports/__absent__.json"',
     "with no GATE R report there is nothing to validate the locator against, and the gate must "
     "say so rather than proceeding unvalidated"),
]


def run(path):
    p = subprocess.run(["/opt/homebrew/bin/python3.11", "-u", path],
                       cwd=ROOT, capture_output=True, text=True)
    return p.returncode, (p.stdout + p.stderr)


def main():
    src = open(SRC).read()

    print("=" * 88)
    print("CONTROL -- the UNMUTATED gate must PASS, or no failure below is attributable")
    print("=" * 88)
    open(TMP, "w").write(src)
    rc, out = run(TMP)
    tail = [l for l in out.strip().splitlines() if l.strip()][-1]
    print(f"  rc={rc}   {tail}")
    if rc != 0:
        os.remove(TMP)
        sys.exit("CONTROL FAILED -- fix the gate before reading any mutation result")
    print("  CONTROL OK\n")

    bad = 0
    for name, tag, needle, repl, why in MUTATIONS:
        n = src.count(needle)
        if n != 1:
            print(f"  VACUOUS  {name}: needle appears {n} times, expected exactly 1")
            bad += 1
            continue
        open(TMP, "w").write(src.replace(needle, repl))
        rc, out = run(TMP)
        lines = [l for l in out.strip().splitlines() if l.strip()]
        fail = next((l for l in reversed(lines) if tag in l), None)
        if rc == 0:
            print(f"  GUARD DEAD  {name}: the gate PASSED with this broken\n"
                  f"              ({why})")
            bad += 1
        elif fail is None:
            print(f"  WRONG GUARD {name}: refused (rc={rc}) but not by {tag}\n"
                  f"              last line: {lines[-1][:150]}")
            bad += 1
        else:
            print(f"  OK  {name}\n      -> {fail.strip()[:150]}")

    os.remove(TMP)
    print("\n" + "=" * 88)
    if bad:
        print(f"{bad} of {len(MUTATIONS)} mutations did not fire the guard they were aimed at")
    else:
        print(f"all {len(MUTATIONS)} mutations fired their own guard; the control passes")
    print("=" * 88)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
