#!/usr/bin/env python3.11
"""Mutation test for GATE AH (analysis/vertex_curvature_gate.py).

Every arm carries an expected EXIT CODE **and** a string the output must contain (s128):

  * `expect_rc != 0` arms test the REFUSALS -- guards whose job is to stop the gate.  GATE AH
    refuses with rc = 2 (its `_die`), so a mutant that exits 1 is a crash, not a fired guard.
  * `expect_rc == 0` arms test the COMPUTED VERDICTS.  s108's rule means a well-built gate's
    headline findings deliberately never change the exit code, so a conclusion that has quietly
    become hard-coded narration would survive an exit-code-only runner.  Those arms break the
    data behind a verdict and require the gate to print the OPPOSITE verdict.

GATE AH's deliverables are AH4's ratio, AH5's comparison against AG6's stored implication, AH6's
cross-instrument corroboration and AH7's budget.  Three of the eleven arms below are verdict arms.

Mechanics, each paid for by an earlier session:
  * the patched copy LIVES in analysis/ (so sibling imports resolve) and RUNS from the repo root
    (so data paths resolve) -- two different requirements, and satisfying one is the natural way
    to break the other (s110).
  * an unmutated CONTROL runs first; if it does not pass, no failure below is attributable (s107).
  * failures are scored on the guard's own tag, not merely on a non-zero exit (s117).
  * verdict arms assert on the VERDICT SENTENCE, never on a count -- two classes can be the same
    size and a count-based assertion then passes vacuously (s130's `_mutate_gate_ab.py` arm 6).
  * perturbations are applied at the DATA level wherever a threshold would be nowhere near the
    data (s110's vacuity trap, and s133's own repeat of it).
  * ⚠ the model-side renders are CACHED with an argv+binary stamp, so these arms re-read rather
    than re-render.  A mutation that changed a render argument would silently re-render 16
    captures; none below does, and any future arm that does must say so.

Run:  python3.11 analysis/_mutate_gate_ah.py
"""
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
SRC = os.path.join(HERE, "vertex_curvature_gate.py")
TMP = os.path.join(HERE, "_mutated_gate_ah.py")

# A patch is (name, why, [(pattern, replacement)], expect_rc, must_contain).
ARMS = [
    # ---------------- REFUSAL ARMS (rc = 2) -------------------------------
    ("AH1a  the curvature estimator must recover an injected parabola EXACTLY",
     "scale the estimator's curvature by 1.05.  Injecting ZERO still recovers zero (the arm's "
     "own control is a difference), so only the non-zero rungs catch it -- which is precisely "
     "why the sweep has non-zero rungs.  Without this guard every number in AH2/AH4/AH7 would "
     "carry a silent 5 % bias and nothing else in the gate would notice.",
     [(r'^    return \{"curv_db_oct2": float\(2\.0 \* a\),',
       '    return {"curv_db_oct2": float(2.0 * a) * 1.05,')],
     2, "AH1a"),

    ("AH1b  the estimator must reproduce AF1c's stored closed-form curvature",
     "bend the closed-form cascade by adding a parabola to it.  AH1b is what makes AH4's MODEL "
     "column comparable to the C_model AG6 actually used; without it the gate could measure a "
     "different quantity from AG6 and report the difference as a device property.\n"
     "    ⚠ Note this arm does NOT disturb AH1a: that check is a DIFFERENCE of two curvatures on "
     "the same curve, so a common parabola cancels.  The two guards are independent by "
     "construction, which is why both are needed.",
     [(r'^    closed_db = 20\.0 \* np\.log10\(np\.abs\(AB\.cascade\(W\.GRID\)\) \+ 1e-300\)$',
       '    closed_db = (20.0 * np.log10(np.abs(AB.cascade(W.GRID)) + 1e-300)\n'
       '                 + 1.5 * np.log2(W.GRID / 2934.0) ** 2)')],
     2, "AH1b"),

    ("AH3  a cell located ON its window bound is a VALIDITY failure, not an exclusion",
     "narrow the locator's window so the pedal's peaks (2435-2700 Hz) land on the lower bound.  "
     "AH3's whole design is that a partial ladder is split by REASON: a cell lost to PROMINENCE "
     "is physics and is excluded + named, a cell lost to the EDGE means the window no longer "
     "contains a migrating feature and must refuse.  Collapsing the two either refuses on "
     "ordinary physics or swallows a broken window (s122's W1b).",
     [(r'^            loc = W\.locate\(d, W\.FEAT_BY_NAME\[FEATURE\]\[2\], W\.FEAT_BY_NAME\[FEATURE\]\[1\]\)$',
       '            loc = W.locate(d, (2600.0, 4200.0), W.FEAT_BY_NAME[FEATURE][1])')],
     2, "AH3"),

    ("AH3  the prominence bar sweep must actually TURN THE KNOB",
     "make every setting of the bar sweep the same value.  s106's N5: a robustness sweep whose "
     "parameter never changes the surviving count is a constant printed N times, and it reads as "
     "an unusually strong result.  The gate must refuse rather than print four identical rows.",
     [(r'^    counts = \[\(b, int\(\(proms >= b\)\.sum\(\)\)\) for b in W\.PROM_SWEEP\]$',
       '    counts = [(b, int((proms >= b).sum())) for b in (1.0, 1.0, 1.0, 1.0)]')],
     2, "AH3"),

    ("AH3b  a fit window that reaches a neighbouring feature must refuse",
     "add a 0.60-octave half-width to the sweep.  Around the located vertices that reaches "
     "4586 Hz, i.e. into GATE W's `treble_notch` window -- and GATE AE has measured ND's notch "
     "there MOVING with drive, so a curvature read across it would be two features, not one.  "
     "This is AG1c's rule; the containment must be asserted BEFORE any curvature is read.",
     [(r'^HALFWIDTHS = \(1\.0 / 24, 1\.0 / 16, 1\.0 / 12, 1\.0 / 8, 1\.0 / 6\)$',
       'HALFWIDTHS = (1.0 / 24, 1.0 / 16, 1.0 / 12, 1.0 / 8, 1.0 / 6, 0.60)')],
     2, "AH3b"),

    ("AH2  the PRIMARY half-width must be USABLE, or AH4's number describes a shoulder",
     "tighten the vertex-offset bar to a quarter of the half-width.  The primary's worst offset "
     "is 0.027 oct against a 0.042 bar, so this genuinely binds (it is not a threshold moved "
     "somewhere the data is not).  If the window AH4 quotes cannot hold its own fitted vertex, "
     "the quoted curvature is not the feature's.",
     [(r'^VERTEX_OFFSET_FRAC = 0\.5$', 'VERTEX_OFFSET_FRAC = 0.25')],
     2, "AH2"),

    ("AH4  AH2's primary row and AH4's table are ONE statistic, computed twice",
     "make AH2 compute a mean instead of the median AH4 uses.  The two code paths exist for "
     "different reasons (a sweep and a per-rung table) and must agree exactly at the primary "
     "half-width -- without that assertion the sweep is a decorative table beside the quoted "
     "number rather than a description of it.",
     [(r'^            cell\[side\] = float\(np\.median\(vals\)\) if vals else float\("nan"\)$',
       '            cell[side] = float(np.mean(vals)) + 0.01 if vals else float("nan")')],
     2, "AH4"),

    ("VACUITY  AG's operands must be READ, never invented",
     "point the stored GATE AG report at a file that is not there.  This gate exists to test "
     "AG6's implied curvature and AG5's tilt; falling back to transcribed constants would make "
     "it test itself (`rebuild-targets-dont-transcribe`).",
     [(r'^AG_REPORT = .*$', 'AG_REPORT = "analysis/reports/_absent.json"')],
     2, "not found"),

    # ---------------- COMPUTED-VERDICT ARMS (rc = 0) ----------------------
    ("AH5  COMPUTED VERDICT — 'the pedal is sharper' is a COMPARISON, not a restatement",
     "SHARPEN THE MODEL by -6.0 dB/oct^2, taking C_model from -10.9 to about -16.9, i.e. sharper "
     "than the pedal's -14.7.  The pedal side is untouched, so `sharper_always` must go False and "
     "the verdict must invert to REFUTED.  A verdict that describes only the pedal, or that "
     "hard-codes AG6's expected direction, survives this -- AB5's own s130 defect.\n"
     "    ⚠⚠ THE FIRST VERSION OF THIS ARM FLATTENED THE PEDAL INSTEAD, and AH3 refused it: "
     "adding a positive parabola lifts the curve at the window edges, which pushed one pedal "
     "peak onto its lower bound.  That is the gate being better than this test's model of it "
     "(s119 -- when a mutation is caught by an EARLIER guard than you aimed at, fix the "
     "EXPECTATION or the ARM, never the guard), and the repair is structural rather than a "
     "tuned constant: SUBTRACTING a parabola can only make a maximum more prominent and more "
     "central, so it cannot manufacture an edge hit at all.\n"
     "    ⚠ This arm deliberately moves AH4's ratio and AH7's budget as well; it asserts on "
     "AH5's sentence only.  (s133: when a mutation changes something outside its stated scope, "
     "suspect the arm -- so the scope is stated.)",
     [(r'^            d = W\.smooth\(f, m\)$',
       '            d = W.smooth(f, m)\n'
       '            if side == "model":\n'
       '                d = d - 3.0 * np.log2(W.GRID / 2980.0) ** 2')],
     0, "REFUTED"),

    ("AH6  COMPUTED VERDICT — the cross-instrument check compares against AG5's STORED value",
     "flip the sign of AG5's stored primary_diff.  This gate's own measured tilt is untouched, "
     "so the two instruments must now disagree in SIGN and the verdict must become NOT "
     "CORROBORATED.  A predicate that does not contain the target reads identically whatever "
     "the target is (s130, AB5).",
     [(r'^    ag_diff = ag5\["primary_diff"\]$', '    ag_diff = -ag5["primary_diff"]')],
     0, "NOT CORROBORATED"),

    ("AH5  COMPUTED VERDICT — the decomposition closure is CHECKED, not announced",
     "inflate AG6's stored over-prediction factor by 1.5x.  AH5 claims AG6's 1.55x factorises "
     "into (curvature ratio) x (the vertex law's own residual) and closes it from both ends to "
     "1.5 %.  If that closure were narrated rather than computed, a 50 % change in one operand "
     "would still print PASS.",
     [(r'^    over_ag6 = ag6\.get\("over_predict"\)$',
       '    over_ag6 = ag6.get("over_predict")\n'
       '    over_ag6 = None if over_ag6 is None else over_ag6 * 1.5')],
     0, "CHECK"),
]


def run(path, argv=()):
    p = subprocess.run([sys.executable, path, *argv], cwd=REPO, capture_output=True, text=True)
    return p.returncode, p.stdout + p.stderr


def main():
    src = open(SRC).read()

    # ---- CONTROL: the unmutated copy, in the mutant's own location --------
    open(TMP, "w").write(src)
    rc, out = run(TMP, ("--json", ""))
    if rc != 0:
        os.remove(TMP)
        print("CONTROL FAILED — the unmutated copy does not pass where the mutants run.")
        print(f"  rc={rc}\n{out[-2500:]}")
        sys.exit(1)
    print(f"CONTROL   rc=0, gate passes from {os.path.relpath(TMP, REPO)}  ✓\n")

    passed = 0
    for name, why, patches, want_rc, want_str in ARMS:
        mutated = src
        for pat, rep in patches:
            new, n = re.subn(pat, rep, mutated, count=1, flags=re.M)
            if n != 1:
                print(f"✗ {name}\n    PATCH DID NOT APPLY ({n} matches for {pat!r}) — the arm is "
                      f"vacuous, which is a defect in the TEST (s110).")
                mutated = None
                break
            mutated = new
        if mutated is None:
            continue

        open(TMP, "w").write(mutated)
        rc, out = run(TMP, ("--json", ""))
        ok_rc = rc == want_rc
        ok_str = want_str in out
        if ok_rc and ok_str:
            passed += 1
            kind = "REFUSED" if want_rc else "VERDICT INVERTED"
            print(f"✓ {name}\n    {kind} as required (rc={rc}, saw {want_str!r})")
        else:
            print(f"✗ {name}\n    {why}")
            if not ok_rc:
                print(f"    WRONG EXIT: got rc={rc}, wanted {want_rc}"
                      + ("  — GUARD DEAD" if want_rc and rc == 0 else ""))
            if not ok_str:
                tag = "NARRATED" if want_rc == 0 else "WRONG GUARD"
                print(f"    {tag}: output never contained {want_str!r}")
            print("    " + "\n    ".join(out.strip().splitlines()[-8:]))

    os.remove(TMP)
    print(f"\n{passed}/{len(ARMS)} arms behaved as required.")
    sys.exit(0 if passed == len(ARMS) else 1)


if __name__ == "__main__":
    main()
