#!/usr/bin/env python3
"""Mutation-test GATE U's guards.

Each mutation must make the gate exit non-zero.  An UNMUTATED CONTROL runs first: if the control
does not PASS, no failure below is attributable to a mutation (s107 -- five "passes" that were all
ModuleNotFoundError).  The patched copy LIVES in analysis/ so its sibling imports resolve, and RUNS
from the repo root so its repo-relative data paths resolve -- getting only one of those right is
s110's trap.  Every needle is asserted present EXACTLY ONCE, so a vacuous mutation reports as
vacuous rather than as a dead guard (s110/s113).

⚠ Mutate a guard's PREMISE or its DATA, never write `if False:` over its predicate -- that DISABLES
a guard rather than making it fire, and reports a healthy guard as dead (s114's two backwards
mutations).
"""
import os, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SRC = os.path.join(HERE, "level_bleed_gate.py")
REPORT = "analysis/reports/s114_baseline.json"

MUTATIONS = [
    # U1a -- the recorded GATE K2 table.  Move one entry: the clean-fraction algebra must stop
    # reproducing the record.
    ("U1a K2 recorded table",
     "0.5: -2.05,", "0.5: -2.55,"),
    # U1a -- the taper itself.  Dropping it is the s113 defect; U1a must catch it.
    ("U1a taper actually applied",
     "        L = L ** K.SHIPPED_LEVEL_TAPER_EXP\n    od, cl = K.coef_closed(float(settings[\"blend\"]), L)\n    if od <= 0.0:",
     "        L = L\n    od, cl = K.coef_closed(float(settings[\"blend\"]), L)\n    if od <= 0.0:"),
    # U1b -- the mutation control itself.  If `taper=False` is made a no-op, U1b must report that
    # U1a has become vacuous.
    ("U1b non-vacuity control",
     "def clean_re_od_db(settings, taper=True):", "def clean_re_od_db(settings, taper=True):\n    taper = True"),
    # U1c -- the statistic must be release_gate's own.
    ("U1c statistic agreement",
     "    mine = J.band_rms_headline(d_all)", "    mine = J.band_rms_headline(d_all) + 0.01"),
    # U2 -- asserted duplicate count.
    ("U2a duplicate-count assertion",
     "EXPECT_DUP_PAIRS = 3", "EXPECT_DUP_PAIRS = 4"),
    # U2b -- the model-side known answer.  Tighten past the storage floor so a real render
    # difference would be needed to pass; the guard must fire on ordinary float noise.
    ("U2b model-identity bar",
     "DUP_MODEL_TOL_DB = 1e-9", "DUP_MODEL_TOL_DB = 1e-20"),
    # U2b -- and the defect it was written for: checking the GAIN-MATCHED column instead of the raw
    # render is the first draft's bug, and it must be caught rather than silently passing.
    ("U2b raw-vs-gain-matched column",
     "    g = fr.get(\"gain_db_applied\") or 0.0", "    g = 0.0"),
    # U2c -- the s112 grid completeness assertion.
    ("U2c grid completeness",
     "want_grid = {(L, B) for L in (0.25, 0.5, 0.75, 1.0) for B in (0.25, 0.5, 0.75)}",
     "want_grid = {(L, B) for L in (0.25, 0.5, 0.75, 1.0) for B in (0.125, 0.25, 0.5, 0.75)}"),
    # U2 -- the settings-match itself.  Drop a key from OTHER_KEYS and captures that differ in it
    # join the family, which must break the duplicate model-identity known answer.
    ("U2 settings-match completeness",
     'FREE_KEYS = ("level", "blend")', 'FREE_KEYS = ("level", "blend", "drive", "attackIdx")'),
    # U4 -- empty-population guard.
    ("U4 empty-population guard",
     "MIN_DLEVEL = 0.20", "MIN_DLEVEL = 9.00"),
    # U6 -- the path-identity check.  Perturb one leg so the two stop summing to the total.
    ("U6 path identity",
     "    leg2 = C_rms - B_r[\"band_rms\"]          # bleed, LEVEL fixed",
     "    leg2 = C_rms - B_r[\"band_rms\"] + 0.05    # bleed, LEVEL fixed"),
    # U8 -- the tolerance must actually bind.
    ("U8 tolerance-binds assertion",
     "    for tol in (0.005, 0.01, 0.02, 0.03, 0.05, 0.08):",
     "    for tol in (0.03, 0.03, 0.03, 0.03, 0.03, 0.03):"),
]


def run(path):
    r = subprocess.run([sys.executable, path, REPORT,
                        "--json", os.path.join(tempfile.gettempdir(), "mu.json")],
                       cwd=ROOT, capture_output=True, text=True)
    out = [l for l in (r.stdout + r.stderr).splitlines() if l.strip()]
    return r.returncode, (out[-1][:110] if out else "")


def main():
    src = open(SRC).read()
    tmp = os.path.join(HERE, "_gate_u_mutant.py")

    print("=" * 100)
    open(tmp, "w").write(src)
    rc, tail = run(tmp)
    print(f"CONTROL (unmutated): rc={rc}  "
          f"{'PASS' if rc == 0 else '** BROKEN -- results below mean nothing'}")
    print(f"   {tail}")
    if rc != 0:
        os.remove(tmp)
        return 1

    print("=" * 100)
    bad = 0
    for name, needle, repl in MUTATIONS:
        n = src.count(needle)
        if n != 1:
            print(f"{name:38s} ** VACUOUS -- needle appears {n} times (expected exactly 1)")
            bad += 1
            continue
        open(tmp, "w").write(src.replace(needle, repl))
        rc, tail = run(tmp)
        ok = rc != 0
        print(f"{name:38s} rc={rc}  {'FIRES' if ok else '** GUARD DEAD'}")
        print(f"   {tail}")
        if not ok:
            bad += 1

    os.remove(tmp)
    print("=" * 100)
    print(f"{len(MUTATIONS) - bad}/{len(MUTATIONS)} mutations fire; control passes."
          if not bad else f"** {bad} PROBLEM(S) -- see above")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
