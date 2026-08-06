#!/usr/bin/env python3.11
"""Mutation test for GATE BE (analysis/clipsat_headroom_gate.py).

GATE BE's whole output is verdicts — it ships no constant — so almost every arm here carries
`expect_rc == 0` and is scored on a STRING the gate must print.  That is the only way to test a
computed verdict at all: s108's rule (exit only on validity, never on an outcome) guarantees the
findings never move the exit code, so a runner scoring `rc != 0` alone could not test one of them.

⚠⚠ THE ARM THAT MATTERS MOST, and the defect it is named after.  `be5-signed` exists because this
gate's own FIRST DRAFT published a false negative: it scored the locus on `mean|absolute error|`,
found a V at L = 1.5, and reported "INTERIOR OPTIMUM FOUND — the stop does NOT fire".  The signed
error is MONOTONE at all eight rungs, so that V is the zero crossing of a monotone gain and is
there BY CONSTRUCTION for any level lever whatsoever.  The repaired gate reads the signed column;
this arm makes the signed column genuinely turn over and requires the stop to stand down.

⚠ `be5-align` is its partner.  The stop's second escape hatch is BAR-FREE on purpose — a SHARE
(cos^2), not a dB threshold — because the gain-matched column moves 0.084 dB and judging that
against any number I chose would be `a-threshold-you-guessed-is-not-a-guard` (s154's "a verdict
that flips on 1 % of its own bar is not a verdict").  This arm points the lever's delivered shape
straight at the defect and requires the gate to notice.

⚠ WHAT IS NOT COVERED, stated rather than left to be discovered:
  * **The release gate.**  BE deliberately never runs the 162-capture matrix — W1's own stop says
    the matrix is owed only if an interior optimum is found, and none is.  No arm substitutes.
  * **s142's supply arithmetic** is IMPORTED as the top rung (VDD/satsum); nothing here re-derives
    it, and BE explicitly does not re-litigate it.
  * **Whether a DIFFERENT lever closes A3.**  BE screens `clipSat` only.

Mechanics (s110/s139/s153/s107/s117): the mutant lives in analysis/ and runs from the repo root,
its path and its private render dir are PID-unique, the render redirect REFUSES if its pattern
stops applying, an unmutated control runs first, and failures are scored on the guard's own tag.

Run:  python3.11 analysis/_mutate_gate_be.py
"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SRC = os.path.join(HERE, "clipsat_headroom_gate.py")
MUT = os.path.join(HERE, f"_mutated_gate_be_{os.getpid()}.py")

ARMS = [
    # ---- refusals (validity) -------------------------------------------------------------------
    ("be0-bleedfree", 1, "BE0 REFUSES",
     'COND[(_g, _d)] = f"{_dtok}level-1700{_tok}_base-od.wav"',
     'COND[(_g, _d)] = f"{_dtok}ref-od.wav" if (_g, _d) == ("cut", "noon") '
     'else f"{_dtok}level-1700{_tok}_base-od.wav"',
     "swap one condition for a LEVEL-noon capture.  s151 measured that set ~44 % clean, and GATE "
     "K2 says bleed vanishes only where BOTH LEVEL and BLEND are max — the gate must refuse "
     "rather than quietly average a diluted row into an absolute-level statistic"),

    ("be0-gruntidx", 1, "BE0 REFUSES",
     'for _g, _tok in (("cut", ""), ("flat", "_grunt-flat"), ("boost", "_grunt-boost")):',
     'for _g, _tok in (("cut", ""), ("flat", "_grunt-boost"), ("boost", "_grunt-flat")):',
     "swap the flat and boost tokens.  The grid must be resolved from SETTINGS, not filenames "
     "(s114) — with the labels transposed every GRUNT verdict in BE1/BE2 would be backwards and "
     "nothing else in the gate would notice"),

    ("be0-toprung", 1, "BE0 REFUSES",
     "L_RUNGS = (1.0, 1.25, 1.5, 2.0, 2.5, 3.0, 4.0, 5.442)",
     "L_RUNGS = (1.0, 1.25, 1.5, 2.0, 2.5, 3.0, 4.0, 4.0)",
     "stop the sweep short of the physical ceiling.  The top rung must BE VDD/satsum, or the "
     "gate's headline ('monotone all the way to the physical ceiling') is about a range it "
     "never reached"),

    ("be2-addcap", 1, "BE2 REFUSES",
     'caps_g = {"cut": c11, "flat": c11 + c12, "boost": c11 + c13}',
     'caps_g = {"cut": c11, "flat": c11 + c13, "boost": c11 + c12}',
     "mis-compose the GRUNT caps.  s139 caught exactly this class (FitParams stores clipC12/13 as "
     "ADD-caps and Clipper::gruntCapNow composes them); the ordering assertion must catch a "
     "composition that no longer runs cut < flat < boost"),

    ("be4-vacuous", 1, "BE4 REFUSES",
     '    if L != 1.0:\n        args += ["--fit", f"clipSatLo={ship[\'clipSatLo\'] * L:.10g}",\n'
     '                 "--fit", f"clipSatHi={ship[\'clipSatHi\'] * L:.10g}"]',
     "    if False:\n        args += []",
     "drop the --fit override so every rung renders the shipped point.  The non-vacuity known "
     "answer must fire — without it a sweep that never reached the stage would report a perfectly "
     "flat locus and the stop would fire for the WRONG reason"),

    ("be4-baseline", 1, "BE4 FAIL",
     '        want = base_rows[(g, "sweep_drv_-12")]["abs_mid"]',
     '        want = base_rows[(g, "sweep_drv_-12")]["abs_mid"] + 0.5',
     "move the stored baseline out from under the re-render.  KA(a) must notice — a baseline that "
     "has silently moved makes every comparison in BE1-BE3 a fiction (s77's SHIP_RECORD)"),

    # ---- computed verdicts (rc == 0; the STRING is what proves the verdict is computed) --------
    # ⚠ `expect_rc = 1`, and that is s119's rule rather than a concession: injecting a GRUNT-
    # dependent deficit into the baseline ALSO moves the baseline out from under BE4's KA(a), so
    # a SECOND guard fires after the one this arm aims at.  That is the gate being better than
    # the test's model of it — fix the expectation, not the guard.  The STRING is what proves
    # BE1's verdict inverted; the exit code proves KA(a) noticed the manipulated baseline.
    ("be1-grunt", 1, "GRUNT-DEPENDENT — the framing's",
     "    caps = {c[\"file\"]: c for c in base[\"captures\"]}",
     "    caps = {c[\"file\"]: c for c in base[\"captures\"]}\n"
     "    for _f, _c in caps.items():\n"
     "        _k = 6.0 if 'grunt-flat' in _f else (3.0 if 'grunt-boost' in _f else 0.0)\n"
     "        for _sw in _c['fr']:\n"
     "            _c['fr'][_sw]['plugin_db'] = [v - _k for v in _c['fr'][_sw]['plugin_db']]",
     "inject a genuinely GRUNT-dependent absolute deficit.  BE1's verdict must invert — it is the "
     "premise the whole of W1 rests on, so it must be able to come back the other way"),

    ("be2-dose", 0, "the deficit DOES grow with clipper drive",
     "            sl[g] = (rows[(g, sw)][\"abs_mid\"] - base) / dose[g]",
     "            sl[g] = -((rows[(g, sw)][\"abs_mid\"] - base) / dose[g]) - 0.5",
     "flip the dose-response so the deficit grows where the clipper is driven harder.  BE2 must "
     "then say the headroom mechanism is consistent — the refutation cannot be a fixed string"),

    ("be3-stimulus", 0, "stimulus-DEPENDENT and monotone in 3/3",
     "        v = [rows[(g, sw)][\"abs_mid\"] for sw in DRIVEN]",
     "        v = [rows[(g, sw)][\"abs_mid\"] - 3.0 * i for i, sw in enumerate(DRIVEN)]",
     "inject a monotone 3 dB-per-rung stimulus dependence.  BE3 must report a compression "
     "signature — 'not a compression signature' has to be a measurement, not narration"),

    # ⚠⚠ the arm named after this gate's own first-draft defect.
    ("be5-signed", 0, "STOP DOES NOT FIRE",
     "        curve_signed.append(float(np.mean(list(per.values()))))",
     "        curve_signed.append(float(np.mean(list(per.values()))) + 15.0 * (L - 3.0) ** 2)",
     "make the SIGNED locus genuinely turn over.  The stop must stand down — this is the exact "
     "shape the first draft of this gate hallucinated out of mean|abs|, so the repaired gate has "
     "to be able to find a real one when there IS one.  ⚠ The first version of this arm added "
     "`4*(L-1.5)^2`, which is VACUOUS: the real curve climbs ~9 dB across the sweep, so a "
     "perturbation that small leaves it monotone and the arm read GUARD DEAD against a working "
     "guard (s110 — suspect the mutation before the guard).  Centred at L=3 and scaled to "
     "dominate, it turns over for real"),

    ("be5-align", 0, "ALIGNED with the defect",
     "                    dv = np.array(scored[(COND[(g, d)], L)][sw][\"abs_grade_bands\"]) - e",
     "                    dv = -0.3 * e",
     "point the lever's delivered shape straight AT the defect.  The bar-free alignment share must "
     "swing the verdict — cos^2 is the stop's only escape hatch that carries no invented threshold, "
     "so it must be a live test rather than a number that is always small"),
]


def run(path, extra=()):
    return subprocess.run([sys.executable, path, *extra],
                          cwd=ROOT, capture_output=True, text=True, timeout=7200)


def main():
    with open(SRC, encoding="utf-8") as fh:
        src = fh.read()

    priv = 'PRIV_DIR = "build/s170_clipsat_headroom"'
    if src.count(priv) != 1:
        sys.exit("MUTATION HARNESS FAIL: cannot redirect the mutant's private render dir — the "
                 "PRIV_DIR line has moved, and without the redirect every arm would render into "
                 "the real gate's cache (s153)")
    out = 'OUT_JSON = "analysis/reports/s170_clipsat_headroom.json"'
    if src.count(out) != 1:
        sys.exit("MUTATION HARNESS FAIL: cannot redirect the mutant's report — a faithful copy "
                 "writes the real gate's artefact, and the last arm's FALSIFIED output would be "
                 "left on disk wearing the real filename (s153)")
    src_m = (src
             .replace(priv, f'PRIV_DIR = "build/s170_clipsat_headroom_mut_{os.getpid()}"')
             .replace(out, f'OUT_JSON = "analysis/reports/_s170_mut_{os.getpid()}.json"'))

    print("=== CONTROL (unmutated, rendering into the mutant's private dir) ===")
    with open(MUT, "w", encoding="utf-8") as fh:
        fh.write(src_m)
    c = run(MUT, ["--jobs", "10"])
    if c.returncode != 0:
        print(c.stdout[-3000:], c.stderr[-2000:])
        sys.exit("MUTATION HARNESS FAIL: the UNMUTATED gate does not pass (s107)")
    print(f"  control OK (rc=0), {len(c.stdout.splitlines())} lines\n")

    passed = 0
    try:
        for name, rc_want, want, find, repl, why in ARMS:
            if src_m.count(find) != 1:
                print(f"  {name:<16} PATCH DID NOT APPLY ({src_m.count(find)} matches)")
                continue
            with open(MUT, "w", encoding="utf-8") as fh:
                fh.write(src_m.replace(find, repl))
            # The refusal arms are cheap (BE0/BE2 exit before any render); the verdict arms need
            # the sweep, which is cached by then.
            r = run(MUT, ["--jobs", "10"])
            ok_rc = (r.returncode != 0) if rc_want else (r.returncode == 0)
            body = r.stdout + r.stderr
            ok_txt = want in body
            verdict = ("PASS" if (ok_rc and ok_txt)
                       else ("NARRATED" if (ok_rc and not ok_txt and rc_want == 0)
                             else ("WRONG GUARD" if ok_rc else "GUARD DEAD")))
            passed += verdict == "PASS"
            print(f"  {name:<16} {verdict:<12} rc={r.returncode} "
                  f"want={'!=0' if rc_want else '==0'} | {want!r} "
                  f"{'found' if ok_txt else 'MISSING'}")
            if verdict != "PASS":
                print(f"      why the arm exists: {why}")
                print("      last output:", (body.strip().splitlines() or ["<empty>"])[-1][:170])
    finally:
        if os.path.exists(MUT):
            os.remove(MUT)
        stray = os.path.join(ROOT, "analysis", "reports", f"_s170_mut_{os.getpid()}.json")
        if os.path.exists(stray):
            os.remove(stray)

    print(f"\n{passed}/{len(ARMS)} arms PASS")
    sys.exit(0 if passed == len(ARMS) else 1)


if __name__ == "__main__":
    main()
