#!/usr/bin/env python3.11
"""Mutation test for GATE AI (analysis/at_clipper_tilt_gate.py).

Every arm carries an expected EXIT CODE **and** a string the output must contain (s128):

  * `expect_rc != 0` arms test the REFUSALS.  GATE AI refuses with rc = 2 (its `_die`), so a
    mutant that exits 1 is a crash, not a fired guard.
  * `expect_rc == 0` arms test the COMPUTED VERDICTS.  s108's rule means a well-built gate's
    headline findings deliberately never change the exit code, so a conclusion that has quietly
    become narration would survive an exit-code-only runner.  Those arms break the data behind a
    verdict and require the gate to print a DIFFERENT verdict.

GATE AI's deliverable is a REFUTATION, which raises the bar on the verdict arms: a refutation that
cannot become a non-refutation is narration.  Three of the ten arms below therefore drive AI5 to
each of its other three outcomes (`REACHES`, `REFUTED ON SIGN`, `RIGHT SIGN EVERYWHERE`).

Mechanics, each paid for by an earlier session:
  * the patched copy LIVES in analysis/ (sibling imports) and RUNS from the repo root (data
    paths) -- two different requirements, and satisfying one is the natural way to break the
    other (s110).
  * an unmutated CONTROL runs first; if it does not pass, no failure below is attributable (s107).
  * failures are scored on the guard's own tag, not merely a non-zero exit (s117).
  * perturbations are applied at the DATA level wherever a predicate mutation would produce a
    message that contradicts itself (s122's W1b) or would be nowhere near the data (s110).
  * ⚠ this gate reads only stored reports and closed-form arithmetic -- there is no render and no
    cache, so no arm here can trigger one.  Any future arm that changes a render argument must
    say so.

Run:  python3.11 analysis/_mutate_gate_ai.py
"""
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
SRC = os.path.join(HERE, "at_clipper_tilt_gate.py")
TMP = os.path.join(HERE, "_mutated_gate_ai.py")

# A patch is (name, why, [(pattern, replacement)], expect_rc, must_contain, extra_argv).
ARMS = [
    # ---------------- REFUSAL ARMS (rc = 2) -------------------------------
    ("AI1a  the at-clipper block must REDUCE to GATE AB's validated closed loop",
     "scale R16 by 1.05 inside h_at only.  AI1a is the single check tying this gate's own "
     "expression to the one s125/AB already validated against the render; without it the gate "
     "could screen a mechanism that is not the shipped stage and report the difference as physics.",
     [(r'^    return -a0 \* zf / \(zf \+ \(1\.0 \+ a0\) \* \(AB\.R16 \+ 1\.0 / \(s \* cg\)\)\)$',
       '    return -a0 * zf / (zf + (1.0 + a0) * (AB.R16 * 1.05 + 1.0 / (s * cg)))')],
     2, "AI1a", []),

    ("AI1b  the tilt estimator must recover an injected tilt EXACTLY",
     "return the quadratic coefficient instead of the linear one.  Every number in AI2 and AI4 is "
     "a tilt, so an estimator reporting the wrong coefficient would still print a plausible, "
     "monotone, entirely wrong table.",
     [(r'^    return float\(np\.linalg\.lstsq\(A, y, rcond=None\)\[0\]\[1\]\)$',
       '    return float(np.linalg.lstsq(A, y, rcond=None)[0][0])')],
     2, "AI1b", []),

    ("AI1c  THE LICENCE — an a0-independent block must cancel from the tilt CHANGE",
     "make the estimator a NONLINEAR functional of the curve, by adding a term in the SQUARE of "
     "the fitted curvature.\n"
     "    ⚠⚠ THIS ARM'S FIRST VERSION WAS WRONG AND READ AS `GUARD DEAD` (s110 — suspect the "
     "mutation before the guard).  It returned `c1 + 0.05*c0`, i.e. a different LINEAR functional "
     "of y, and the cancellation AI1c tests depends only on LINEARITY -- not on which coefficient "
     "is returned -- so an a0-independent block still cancelled exactly and the guard was right to "
     "stay silent.  The property being guarded is `tilt(a + b) = tilt(a) + tilt(b)`, so only a "
     "genuinely nonlinear functional can break it.\n"
     "    Squaring the curvature is the one that also PASSES AI1b, which is what makes the two "
     "guards independently tested: AI1b differences two curves with the SAME curvature (a pure "
     "added tilt does not change c0), so the squared term cancels there exactly, while AI1c's "
     "wild fixed block does change c0 and therefore leaks into the difference.  Without AI1c the "
     "gate's entire simplification -- skipping the whole fixed chain unrendered -- would be an "
     "unexamined argument rather than a measured fact.",
     [(r'^    return float\(np\.linalg\.lstsq\(A, y, rcond=None\)\[0\]\[1\]\)$',
       '    _c = np.linalg.lstsq(A, y, rcond=None)[0]\n'
       '    return float(_c[1] + 1e-3 * _c[0] ** 2)')],
     2, "AI1c", []),

    ("AI3  the endpoint membership must be asserted, not inherited",
     "drop one capture from GATE Q's selection AFTER it is loaded (a DATA mutation, so the "
     "refusal message prints two genuinely different counts -- s122's W1b, where a predicate "
     "mutation produced a refusal claiming a change while printing two identical numbers).",
     [(r'^    bands, caps_, absfr, nonhf, fb, files, drops = Q\.load_surface\(REPORT\)$',
       '    bands, caps_, absfr, nonhf, fb, files, drops = Q.load_surface(REPORT)\n'
       '    files = sorted(files)[:-1]')],
     2, "AI3", []),

    ("AI3  a non-finite drive-tilt must REFUSE, not vote",
     "poison one capture's model rung with nan.  s106's N3: `nan <= FLOOR` is False, so a "
     "non-finite sails through any comparison-based guard and then poisons the mean -- the gate "
     "would print a nan group mean and a verdict computed from it.",
     [(r'^    lg = np\.log2\(fb / f0\)$',
       '    absfr[(sorted(files)[0], AG.RUNGS[0])][0][:] = np.nan\n'
       '    lg = np.log2(fb / f0)')],
     2, "AI3", []),

    ("AI3  the GRUNT split must actually SPLIT — the discriminator needs all three positions",
     "classify every capture as `cut`.  The whole refutation rests on comparing the mechanism's "
     "sign ACROSS GRUNT positions against the defect's; if the membership silently collapsed to "
     "one position the gate would still print a verdict, computed from a comparison it could not "
     "make.",
     [(r'^        nm = \("boost" if "grunt-boost" in f else "flat" if "grunt-flat" in f else "cut"\)$',
       '        nm = "cut"')],
     2, "AI3", []),

    ("VACUITY  the operands must be READ from the stored reports, never invented",
     "point --ag at a file that does not exist.  The vertex, the window, the budget and the "
     "available tilt all come from AG/AH; a gate that silently fell back to defaults would be "
     "screening against transcribed numbers (`rebuild-targets-dont-transcribe`).",
     [],
     2, "not found", ["--ag", "analysis/reports/_no_such_report.json"]),

    # ---------------- COMPUTED-VERDICT ARMS (rc = 0) ----------------------
    ("AI5  COMPUTED VERDICT — a refutation that cannot become REACHES is narration",
     "replace the measured defect with one the mechanism DOES reach: sign-matched at all three "
     "positions and smaller than the a0 -> 1 limit.  The gate must then say the mechanism "
     "REACHES.  This is the arm that proves AI5 is a comparison against the target rather than a "
     "restatement of the mechanism (AB5: the target must appear as a VARIABLE).",
     [(r'^        need\[nm\] = float\(v\.mean\(\)\)$',
       '        need[nm] = {"cut": -0.4, "flat": 0.9, "boost": 1.0}[nm]')],
     0, "REACHES", []),

    ("AI5  COMPUTED VERDICT — `REFUTED ON SIGN` must be reachable from the data",
     "make the mechanism positive at every GRUNT position while the measured defect stays "
     "negative at all three.  The gate must then refute on sign alone, with no size argument -- a "
     "different verdict from the shipped one, which refutes on sign at 2 of 3 AND on size at the "
     "third.",
     [(r'^    lim = tab\[f"\{A0_LIMIT:g\}"\]$',
       '    lim = {k: abs(v) for k, v in tab[f"{A0_LIMIT:g}"].items()}')],
     0, "REFUTED ON SIGN", []),

    ("AI2/AI5  COMPUTED VERDICT — the GRUNT sign-dependence must be DATA-DRIVEN",
     "give all three GRUNT positions the SAME coupling cap.  The mechanism's sign flip is the "
     "load-bearing half of the refutation, and it is a claim about the caps: with one cap it must "
     "vanish, the printed sign line must read the same sign three times, and the verdict must "
     "become RIGHT SIGN EVERYWHERE, TOO SMALL.  Without this arm, `the switch changes the sign` "
     "could be a sentence the gate always prints.",
     [(r'^    caps = \{nm: AB\._read_fitparam\(key\) for nm, key in GRUNT_CAP\.items\(\)\}$',
       '    caps = {nm: AB._read_fitparam("clipC11") for nm in GRUNT_CAP}')],
     0, "RIGHT SIGN EVERYWHERE", []),
]


def run(path, extra):
    p = subprocess.run([sys.executable, path, "--json", os.devnull] + extra,
                       cwd=REPO, capture_output=True, text=True, timeout=1800)
    return p.returncode, (p.stdout + p.stderr)


def main():
    src = open(SRC).read()

    open(TMP, "w").write(src)
    try:
        rc, out = run(TMP, [])
        tail = [l for l in out.strip().splitlines() if l.strip()][-1:]
        print(f"CONTROL   rc={rc}, gate passes from {os.path.relpath(TMP, REPO)}  "
              f"{'✓' if rc == 0 else '✗ ' + str(tail)}")
        if rc != 0:
            print("\n⛔ the UNMUTATED control does not pass — no failure below is attributable "
                  "to any mutation (s107).  Fix this first.")
            return 1
    finally:
        pass

    bad = 0
    for name, why, patches, exp_rc, must, extra in ARMS:
        mutated = src
        for pat, rep in patches:
            new, n = re.subn(pat, rep, mutated, count=1, flags=re.M)
            if n != 1:
                print(f"✗ {name}\n    PATCH DID NOT APPLY ({n} matches) — the arm is testing "
                      f"nothing.  Pattern: {pat[:70]}")
                bad += 1
                mutated = None
                break
            mutated = new
        if mutated is None:
            continue
        open(TMP, "w").write(mutated)
        rc, out = run(TMP, extra)
        hit = must in out
        ok = (rc == exp_rc) and hit
        if ok:
            if exp_rc == 0:
                print(f"✓ {name}\n    VERDICT CHANGED as required (rc=0, saw '{must}')")
            else:
                print(f"✓ {name}\n    REFUSED as required (rc={rc}, saw '{must}')")
        else:
            bad += 1
            if exp_rc != 0 and rc == 0:
                kind = "GUARD DEAD — the mutant ran clean"
            elif exp_rc == 0 and not hit:
                kind = "NARRATED — the gate passed but never printed the opposite verdict"
            elif rc != exp_rc:
                kind = f"WRONG EXIT (rc={rc}, wanted {exp_rc})"
            else:
                kind = f"WRONG GUARD — refused without '{must}'"
            print(f"✗ {name}\n    {kind}")
            for l in [l for l in out.strip().splitlines() if l.strip()][-3:]:
                print(f"      | {l[:110]}")

    if os.path.exists(TMP):
        os.remove(TMP)
    n = len(ARMS)
    print(f"\n{n - bad}/{n} arms behaved as required.")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
