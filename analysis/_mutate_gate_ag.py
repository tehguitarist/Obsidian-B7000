#!/usr/bin/env python3.11
"""Mutation test for GATE AG (analysis/drive_tilt_shape_gate.py).

Every arm carries an expected EXIT CODE **and** a string the output must contain (s128):

  * `expect_rc != 0` arms test the REFUSALS -- guards whose job is to stop the gate.
  * `expect_rc == 0` arms test the COMPUTED VERDICTS. s108's rule means a well-built gate's
    headline findings deliberately never change the exit code, so a conclusion that has quietly
    become hard-coded narration would survive an exit-code-only runner. Those arms break the data
    behind a verdict and require the gate to print the OPPOSITE verdict.

GATE AG's deliverable is three verdicts (AG3's dose-response, AG4's shape, AG5's sign-and-size),
all of them `expect_rc == 0`, so four of the eleven arms below are verdict arms -- one per verdict
plus one for the reference's own direction.

Mechanics, each paid for by an earlier session:
  * the patched copy LIVES in analysis/ (so sibling imports resolve) and RUNS from the repo root
    (so data paths resolve) -- two different requirements, and satisfying one is the natural way
    to break the other (s110).
  * an unmutated CONTROL runs first; if it does not pass, no failure below is attributable (s107).
  * failures are scored on the guard's own tag, not merely on rc != 0 (s117).
  * verdict arms assert on the VERDICT SENTENCE, never on a count -- two classes can be the same
    size, and a count-based assertion then passes vacuously (s130's `_mutate_gate_ab.py` arm 6).
  * arms that perturb a value do so at the DATA level wherever possible rather than by loosening
    a threshold: a mutation on a bar that is nowhere near the data does nothing and reads as
    GUARD DEAD (s110's vacuity trap, and s133's own repeat of it).

Run:  python3.11 analysis/_mutate_gate_ag.py
"""
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
SRC = os.path.join(HERE, "drive_tilt_shape_gate.py")
TMP = os.path.join(HERE, "_mutated_gate_ag.py")
REPORT = "analysis/reports/s124_ship.json"

# A patch is (name, why, [(pattern, replacement)], expect_rc, must_contain).
ARMS = [
    # ---------------- REFUSAL ARMS ----------------------------------------
    ("AG1a  D(f) must reproduce GATE Q's own Q4 elementwise",
     "offset this tool's rebuilt D(f) by 0.1 dB. The surface is supposed to be IMPORTED from "
     "GATE Q rather than re-derived, so any divergence means one of the two has drifted and "
     "every number below is unattributable -- the gate must refuse, not proceed.",
     [(r"^    D = \(Ehi - Elo\)\.mean\(axis=0\)$",
       "    D = (Ehi - Elo).mean(axis=0) + 0.1")],
     1, "AG1a"),

    ("AG1b  the tilt estimator must recover an injected tilt EXACTLY",
     "scale the estimator's output by 1.05. Injecting zero still recovers zero (the arm's own "
     "control is a difference), so only the non-zero rungs catch it -- which is exactly why the "
     "sweep has non-zero rungs. Without this guard AG3/AG5 would report a 5 %-biased slope.",
     [(r"^    return float\(np\.linalg\.lstsq\(A, y\[m\], rcond=None\)\[0\]\[1\]\), n$",
       "    return float(np.linalg.lstsq(A, y[m], rcond=None)[0][1]) * 1.05, n")],
     1, "AG1b"),

    ("AG1c  the primary window must clear both migrating features",
     "widen the primary window to +-1.0 oct, which reaches 1467-5870 Hz and so crosses both the "
     "bridged-T below and the treble notch above. The slope read there would be a feature "
     "sliding through the window rather than a tilt, and the gate must refuse BEFORE AG3 reads "
     "anything -- this is why the check sits in AG1 and not beside AG5 where it is used.",
     [(r"^HALF_PRIMARY = 0\.5$", "HALF_PRIMARY = 1.0")],
     1, "AG1c"),

    ("AG2  a partial row GATE Q has NOT flagged is a MALFORMED read",
     "hide one rung of one capture without GATE Q having flagged that cell as a dropout. s129's "
     "three outcomes: complete / partial / absent are not two branches. A row that LOST data "
     "must refuse, where a row that never had it is a named exclusion -- collapsing the two is "
     "how the guard passes the exact thing it exists to catch.",
     [(r'^        have = \[r for r in RUNGS if \(f, r\) not in drops\]$',
       '        have = [r for r in RUNGS if (f, r) not in drops\n'
       '                and not (f.startswith("level-1700_base") and r == "sweep_drv_-18")]')],
     1, "AG2"),

    ("AG2  the control-spread keys are ASSERTED, not defaulted",
     "rename one settings key the spread is printed over. A `.get` with a default would print "
     "`{None: 14}` -- a spread that says nothing while reading as diligence -- so the gate must "
     "refuse instead. (This arm exists because the first draft of AG2 did exactly that.)",
     [(r'^    for k in \("drive", "attackIdx", "gruntIdx"\):$',
       '    for k in ("drive", "attackIdxXXX", "gruntIdx"):')],
     1, "AG2"),

    ("AG4  too few uncontaminated centres must FAIL, not average whatever is left",
     "raise the feature-free band's FLOOR so no centre's whole window fits inside it. "
     "`empty-gate-must-fail`: a shape verdict computed over nothing is not a shape.\n"
     "    ⚠ The first version of this arm lowered SMOOTH_HI to 2500 instead, and was caught by "
     "AG1c -- which also reads those bounds and fires first. That is the gate being better than "
     "this test's model of it (s119: when a mutation is caught by an EARLIER guard than you "
     "aimed at, fix the EXPECTATION, not the guard). SMOOTH_LO = 2000 keeps the vertex window "
     "2075-4150 contained, so AG1c passes and the mutation reaches the guard it is aimed at.",
     [(r"^SMOOTH_LO = W\.FEAT_BY_NAME\[\"bt_notch\"\]\[2\]\[1\].*$",
       "SMOOTH_LO = 2000.0")],
     1, "AG4"),

    ("VACUITY  AF6's requirement must be READ, never invented",
     "point the stored GATE AF report at a file that is not there. This gate exists to test "
     "AF6's number; falling back to a transcribed constant would make it test itself "
     "(`rebuild-targets-dont-transcribe`).",
     [(r'^AF_REPORT = .*$', 'AF_REPORT = "analysis/reports/_absent.json"')],
     1, "will not invent one"),

    # ---------------- COMPUTED-VERDICT ARMS -------------------------------
    ("AG3  COMPUTED VERDICT — the dose-response is TESTED, not asserted",
     "spike the pedal's slope at one interior rung so the ladder stops being monotone. s129: a "
     "dose-response that reverses is not a mechanism's signature. If AG3 hard-codes 'pedal "
     "falls monotonically' this arm passes with the wrong answer.",
     [(r"^            P\[r\]\.append\(tilt_at\(p_abs\[nonhf\], lg, half\)\[0\]\)$",
       '            P[r].append(tilt_at(p_abs[nonhf], lg, half)[0]\n'
       '                        + (5.0 if r == "sweep_drv_-18" else 0.0))')],
     0, "not a drive mechanism"),

    ("AG3  COMPUTED VERDICT — 'MODEL PINNED' is a comparison against the pedal",
     "give the MODEL a large drive-dependent slope of its own. The pedal is untouched and still "
     "falls monotonically, so the verdict must degrade to 'the model is NOT pinned beside it'. "
     "A verdict that names only the pedal would survive this.",
     [(r"^            M\[r\]\.append\(tilt_at\(m_abs\[nonhf\], lg, half\)\[0\]\)$",
       "            M[r].append(tilt_at(m_abs[nonhf], lg, half)[0]\n"
       "                        - 3.0 * RUNGS.index(r))")],
     0, "NOT pinned beside it"),

    ("AG4  COMPUTED VERDICT — 'steepens' is measured, not restated",
     "make the pedal's drive-tilt GAIN with frequency instead of steepening. AF6's broadband "
     "assumption is exactly what AG4 exists to test, so the shape verdict must follow the data.",
     [(r"^        pl, ph = mean_slope\(RUNGS\[0\], 1\), mean_slope\(RUNGS\[-1\], 1\)$",
       "        pl, ph = mean_slope(RUNGS[0], 1), mean_slope(RUNGS[-1], 1)\n"
       "        ph = ph + 6.0 * float(np.log2(f0 / 2000.0))")],
     0, "not monotone across the interpretable band"),

    ("AG5  COMPUTED VERDICT — sign is compared against AF6's target, not hard-coded",
     "flip the SIGN of AF6's required tilt. The measured surface is untouched, so the verdict "
     "MUST invert to REFUTED. This is AB5's own s130 defect -- a classifier whose predicate does "
     "not contain the target reads identically whatever the target is.",
     [(r'^        return \(float\(d\["af6"\]\["tilt_required_db_oct"\]\),',
       '        return (-float(d["af6"]["tilt_required_db_oct"]),')],
     0, "REFUTED"),
]


def run(path, argv=()):
    p = subprocess.run([sys.executable, path, *argv], cwd=REPO,
                       capture_output=True, text=True)
    return p.returncode, p.stdout + p.stderr


def main():
    src = open(SRC).read()

    # ---- CONTROL: the unmutated copy, in the mutant's own location --------
    open(TMP, "w").write(src)
    rc, out = run(TMP, (REPORT,))
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
        rc, out = run(TMP, (REPORT,))
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
            print("    " + "\n    ".join(out.strip().splitlines()[-6:]))

    os.remove(TMP)
    print(f"\n{passed}/{len(ARMS)} arms behaved as required.")
    sys.exit(0 if passed == len(ARMS) else 1)


if __name__ == "__main__":
    main()
