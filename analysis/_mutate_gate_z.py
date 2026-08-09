#!/usr/bin/env python3.11
"""Mutation test for GATE Z (`thd_locus_gate.py`).  Session 128.

Same mechanics as `_mutate_gate_w.py` (read its header): the patched copy LIVES in `analysis/` so
its sibling imports resolve and RUNS from the repo root so repo-relative data paths resolve, every
needle is asserted to appear exactly once, the unmutated control runs first, and a refusal is only
credited when it carries the tag of the guard the mutation was aimed at (session 117 -- exit code
alone cannot tell a firing guard from a crash).

⭐ ONE ADDITION OVER THE EARLIER RUNNERS, AND IT IS THE POINT OF HALF THIS FILE.  GATE Z deliberately
does NOT `sys.exit` on how the physics comes out -- session 108's rule: exit only on things that make
the numbers below meaningless, and give everything that is an OUTCOME a computed verdict.  So its two
most important statements (Z3's "the surface changes sign" and Z4's cross-instrument corroboration)
cannot be mutation-tested by exit code at all.  Those arms carry `expect_rc = 0` plus a line the
output MUST contain, so a verdict that has quietly become hard-coded narration fails here
(`computed-verdicts-not-narrated`, four prior occurrences in this project).
"""
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "analysis", "thd_locus_gate.py")
TMP = os.path.join(ROOT, "analysis", "_mutant_gate_z.py")

# (name, expect_rc, tag the output must carry, needle, replacement, why)
#   expect_rc = None -> must refuse (rc != 0) and the refusal must carry `tag`
#   expect_rc = 0    -> must still PASS, and `tag` must appear (a computed-verdict arm)
MUTATIONS = [
    # ---- Z1: the known answer, four guards, four distinct tags -------------------------------
    ("Z1 sign convention reverted",
     None, "GATE Z1 FAIL [sign]",
     '    for j in range(Q.shape[1]):',
     '    for j in range(0):',
     "undo session 128's column-sign canonicalisation INSIDE shape_gate's importer -- see the "
     "note below; this is the arm that proves Z1 pins the sign fix where it is CONSUMED"),

    # ⚠ THE FIRST VERSION OF THIS ARM WAS VACUOUS AND READ AS "GUARD DEAD" (`suspect the mutation
    # before the guard`, s110).  It raised this tool's own MIN_BANDS by 6 -- and every graded row
    # uses ALL 26 bands in the range (Z3 prints that), so the bar never bound and n never moved.
    # A band-count mutation cannot drift membership in a population that is nowhere near the bar.
    # The honest mutation is at the DATA level: re-admit the reference dropouts (s114's rule that a
    # predicate flip is the weaker choice), which is also `defective-rows-must-not-vote` inverted.
    ("Z1 membership drifts from release_gate",
     None, "GATE Z1 FAIL [membership]",
     "            if (f, sw) in drops:\n                continue",
     "            if False:\n                continue",
     "stop excluding the reference ladder dropouts, so this tool grades 2 rows release_gate does "
     "not -- the n comparison must refuse rather than compare two different populations"),

    # ⚠ AND THE FIRST VERSION OF *THIS* ARM WAS CAUGHT BY AN EARLIER GUARD THAN IT AIMED AT (s119:
    # "fix the expectation, not the guard").  Dropping the gain-n12 rows at COLLECT time empties the
    # control group but also shrinks "OD (gated)" from 322 to 289, so [membership] fired first --
    # defence in depth, i.e. the gate being better than the test's model of it.  Emptying only the
    # control group's own predicate isolates the guard under test.
    ("Z1 sub-population empty",
     None, "GATE Z1 FAIL [empty]",
     '            "  gain-n12 only [control]": [r for r in rows.values() if r["n12"]]}',
     '            "  gain-n12 only [control]": [r for r in rows.values() if r["n12"] and False]}',
     "empty ONLY the control group, leaving the other two intact -- `empty-gate-must-fail`, and an "
     "empty control is exactly what makes a proposed split look free"),

    # ---- Z3 / Z5: population guards ------------------------------------------------------------
    # ⚠⚠ RE-POINTED AT s191, AND THE EXPECTATION IS DELIBERATELY INVERTED. Until s191 this arm
    # required `rc != 0`: an empty anchor class was a `sys.exit` in Z3. That exit is what suppressed
    # Z4-Z6 for eight sessions once s181's end stop emptied the class for real, which is s108's rule
    # broken ("exit only on things that make the numbers below meaningless"). The gate now REPORTS
    # the emptiness as a computed NOT-AVAILABLE and continues — so the arm tests that it says so,
    # loudly, rather than that it dies. `fix the EXPECTATION, not the guard` (s119) applied to a
    # guard that was deliberately changed.
    ("Z3 anchor population empty",
     0, "Z3 CANNOT RUN ON THIS REPORT",
     'def is_anchor(cf):',
     'def is_anchor(cf):\n    return False  # MUTANT',
     "make the anchor class unsatisfiable -- the convention-free table is the load-bearing "
     "measurement of the session, so the gate must SAY it cannot run rather than print an empty "
     "surface or silently skip to Z4"),

    ("Z5 too few bleed classes to fit",
     None, "GATE Z5 FAIL",
     '    CF_EDGES = ',
     '    CF_EDGES = ',
     "PLACEHOLDER -- replaced below"),

    # ---- the anchor derivation's own known answer (s191) ---------------------------------------
    ("anchor cf diverges from the shipped end stop",
     None, "GATE Z FAIL [anchor]",
     '    a, c = LLG.coef_closed(1.0, LLG.level_taper(1.0))',
     '    a, c = (0.5, 0.5)  # MUTANT: a fourth stale mirror of LevelBlend',
     "model the corner with a DIFFERENT LevelBlend than the one FitParams.h ships. The anchor "
     "class is derived from that corner, so a stale mirror would silently re-classify every "
     "anchor row -- s182 found two stale mirrors and s189 a third, and none of them was caught "
     "by the tool that used the value"),

    # ---- the computed verdicts, which no exit code can test ------------------------------------
    ("Z3 sign-change verdict is COMPUTED",
     0, "THE SURFACE NO LONGER CHANGES SIGN",
     '    changes_sign = bool(vals.max() > 0.0 and vals.min() < 0.0)',
     '    changes_sign = bool(vals.max() > 99.0 and vals.min() < 0.0)',
     "force the surface to read as single-signed; the gate must print the OPPOSITE verdict and "
     "tell the reader a pooled direction is quotable again, not keep narrating session 128's"),

    ("Z4 corroboration verdict is COMPUTED",
     0, "THE TWO INSTRUMENTS DISAGREE",
     '    falls = all(b < a for a, b in zip(seq_mean, seq_mean[1:]))',
     '    falls = all(b > a for a, b in zip(seq_mean, seq_mean[1:]))',
     "invert the ordering test so the harmonics arm reads as DISAGREEING with Z3 -- the gate "
     "must say so instead of printing 'corroborated'"),

    ("Z5 A3 agreement verdict is COMPUTED",
     0, "does NOT match A3",
     "    elif agree <= 1.5:",
     "    elif agree <= 0.01:",
     "make the agreement bar unreachable; the gate must report NO match and refuse to attribute, "
     "rather than printing the 'needs no second mechanism' conclusion regardless"),

    ("Z5 dilution fit unidentified",
     0, "on its bound, so DF is UNIDENTIFIED",
     "    grid = np.arange(-12.0, 0.0001, 0.01)",
     "    grid = np.arange(-0.30, -0.2999, 0.01)",
     "collapse the search range so the optimum can only rest on a bound -- "
     "`bound-resting-means-unidentified` must be reported instead of a fitted DF"),

    # ---- the imported shipped constant --------------------------------------------------------
    ("shipped LEVEL taper not checked",
     None, "GATE K2 FAIL",
     "    LLG.check_shipped_constant()",
     "    LLG.SHIPPED_LEVEL_TAPER = (0.9, 0.91, 0.92, 0.93, 0.94, 0.95); LLG.check_shipped_constant()",
     "move the transcribed taper off what FitParams.h ships -- `cf` is computed through "
     "it, so an unchecked taper silently mis-bins every row (session 113's own defect)"),
]

# The Z5 arm needs a two-line replacement that the tuple form above cannot express cleanly.
MUTATIONS[4] = (
    "Z5 too few bleed classes to fit",
    0, "Z5 CANNOT RUN",
    'CF_EDGES = ((0.35, "cf<0.35"), (0.60, "0.35-0.60"), (0.80, "0.60-0.80"), (1.01, "cf>=0.80"))',
    'CF_EDGES = ((1.01, "cf-all"),)',
    "collapse the bleed classes to one so a one-parameter law would be fitted to a single point -- "
    "the gate must REPORT that it cannot run rather than return a perfectly-fitting meaningless DF. "
    "⚠ s191: expectation changed from rc!=0 to a computed refusal, for the same reason as the Z3 "
    "arm above -- a thin membership is an epoch fact, and exiting on it takes Z6 down with it",
)

#: ⚠ The Z1-sign arm mutates `shape_gate.py`, not the gate under test, because that is where the
#: defect lived.  Patching an IMPORTED module means the mutant copy of GATE Z is unchanged, so the
#: needle/replacement pair below is applied to shape_gate's source and written to a patched copy
#: that the mutant imports first.  Handled as a special case rather than pretended away.
SHAPE_GATE = os.path.join(ROOT, "analysis", "shape_gate.py")
SIGN_ARM = "Z1 sign convention reverted"


def run(path):
    p = subprocess.run(["/opt/homebrew/bin/python3.11", "-u", path],
                       cwd=ROOT, capture_output=True, text=True)
    return p.returncode, (p.stdout + p.stderr)


def main():
    src = open(SRC).read()
    sg_src = open(SHAPE_GATE).read()

    print("=" * 92)
    print("CONTROL -- the UNMUTATED gate must PASS, or no failure below is attributable")
    print("=" * 92)
    open(TMP, "w").write(src)
    rc, out = run(TMP)
    tail = [ln for ln in out.strip().splitlines() if ln.strip()][-1]
    print(f"  rc={rc}   {tail}")
    if rc != 0:
        os.remove(TMP)
        sys.exit("CONTROL FAILED -- fix the gate before reading any mutation result")
    print("  CONTROL OK\n")

    bad = 0
    for name, expect_rc, tag, needle, repl, why in MUTATIONS:
        target_src, target_path = (sg_src, SHAPE_GATE) if name == SIGN_ARM else (src, SRC)
        n = target_src.count(needle)
        if n != 1:
            print(f"  VACUOUS  {name}: needle appears {n} times in "
                  f"{os.path.basename(target_path)}, expected exactly 1")
            bad += 1
            continue

        if name == SIGN_ARM:
            # patch shape_gate in place, run the UNMUTATED gate, restore
            open(SHAPE_GATE, "w").write(target_src.replace(needle, repl))
            open(TMP, "w").write(src)
            try:
                rc, out = run(TMP)
            finally:
                open(SHAPE_GATE, "w").write(sg_src)
        else:
            open(TMP, "w").write(src.replace(needle, repl))
            rc, out = run(TMP)

        lines = [ln for ln in out.strip().splitlines() if ln.strip()]
        hit = next((ln for ln in reversed(lines) if tag in ln), None)
        if expect_rc is None:
            if rc == 0:
                print(f"  GUARD DEAD  {name}: the gate PASSED with this broken\n"
                      f"              ({why})")
                bad += 1
            elif hit is None:
                print(f"  WRONG GUARD {name}: refused (rc={rc}) but not by {tag!r}\n"
                      f"              last line: {lines[-1][:150]}")
                bad += 1
            else:
                print(f"  OK  {name}\n      -> {hit.strip()[:150]}")
        else:
            if rc != expect_rc:
                print(f"  UNEXPECTED  {name}: rc={rc}, wanted {expect_rc} (this arm tests a "
                      f"COMPUTED VERDICT, so the gate must still pass)\n"
                      f"              last line: {lines[-1][:150]}")
                bad += 1
            elif hit is None:
                print(f"  NARRATED    {name}: the gate passed but never printed {tag!r} --\n"
                      f"              the verdict is hard-coded, not computed ({why})")
                bad += 1
            else:
                print(f"  OK  {name}\n      -> {hit.strip()[:150]}")

    os.remove(TMP)
    print("\n" + "=" * 92)
    if bad:
        print(f"{bad} of {len(MUTATIONS)} mutations did not behave as their guard requires")
    else:
        print(f"all {len(MUTATIONS)} mutations fired their own guard; the control passes")
    print("=" * 92)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
