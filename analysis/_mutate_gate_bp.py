#!/usr/bin/env python3.11
"""Mutation test for GATE BP (analysis/od_tilt_mix_gate.py).

GATE BP re-reads a SHIPPED stage's acceptance at settings its acceptance never covered, so its
headline is a claim about `OdDriveTilt` that a later session will quote.  Every one of those
headlines is a COMPUTED verdict and five arms below carry `expect_rc == 0` to prove it — a gate
whose conclusions are hard-coded strings passes its refusal arms perfectly and is still narration
(s108/s128, `computed-verdicts-not-narrated`, six prior occurrences).

⚠⚠ THE THREE ARMS THAT MATTER MOST, and why:
  * `bp1b-scope` — the whole gate reads `ON - OFF` as "the stage's own OD-branch change, seen
    through different amounts of dilution".  That reading is only licensed because the stage cannot
    reach the clean tap, which BP1b proves by BIT-IDENTITY at two settings.  Bit-identity is true
    by construction here, which is exactly the kind of check that quietly becomes a tautology.
  * `bp2b-sign` — the gate's largest claim is that `required` CHANGES SIGN between the corner and
    every mixed cell.  The arm flips the difference and requires the per-centre verdict to invert.
  * `bp3b-confound` — the A3 confound's DIRECTION is what makes the sign claim survivable, and its
    first draft got that direction BACKWARDS while printing a correct number beside it.  The arm
    negates the measured locus slope and requires the verdict to flip with it.

⚠ WHAT IS NOT COVERED, stated rather than left to be discovered:
  * **The matrix.**  GATE BP prices nothing; `comprehensive_report.py` does.
  * **Whether the stage should CHANGE.**  Nothing here is a fit, a candidate or a proposal.
  * **The pedal's own locus.**  BP3b reasons about where the pedal sits on the MODEL's cf -> tilt
    curve; that premise is printed every run and no arm can test it.
  * **The faintness of `treble_peak` at the hot rungs** is REPORTED (BP4's bar axis), not fixed —
    no arm makes the feature resolve, because nothing can.

Mechanics (s110/s139/s153/s107/s117): the mutant lives in analysis/ and runs from the repo root,
its path and its private render dir are PID-unique, the redirect REFUSES if its pattern stops
applying, an unmutated control runs first, and failures are scored on the guard's own tag.

Run:  python3.11 analysis/_mutate_gate_bp.py
"""
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SRC = os.path.join(HERE, "od_tilt_mix_gate.py")
MUT = os.path.join(HERE, f"_mutated_gate_bp_{os.getpid()}.py")

ARMS = [
    # ---- refusals -------------------------------------------------------------------------------
    ("bp0-mislabel", 1, "GATE BP BP0 FAIL",
     '    ("L0.500/B1.00 *PLAY*",    "ref-od.wav",                         0.500, 1.00),   # the reference',
     '    ("L0.500/B1.00 *PLAY*",    "ref-od.wav",                         0.875, 1.00),',
     "mislabel a cell's LEVEL.  Every axis in this gate is the mix, so a cell that is not the "
     "(LEVEL, BLEND) its label claims silently re-orders the dose-response — the membership must "
     "be resolved from SETTINGS and asserted (s114), never taken from the label"),

    ("bp0-cache", 1, "GATE BP BP0 FAIL",
     "    before = BA.fingerprint(W.REN_DIR)",
     '    before = {"phantom-entry-that-is-not-in-the-cache": (0, 0)}',
     "record a bogus 'before' fingerprint for GATE W's READ-ONLY cache.  The end-of-run integrity "
     "check must fire — it is the only thing standing between this gate and the s122 epoch that "
     "GATEs AV / AW / AF / AG / BC all read, and whose stamps are ALL already stale"),

    ("bp1a-estimator", 1, "GATE BP BP1a FAIL",
     "import task_e_placement_gate as BA         # noqa: E402  slope(), drive_tilt(), fingerprint(), HALF",
     "import task_e_placement_gate as BA         # noqa: E402\n"
     "_orig_slope = BA.slope\nBA.slope = lambda d, f0, half=BA.HALF: _orig_slope(d, f0, half) * 0.97",
     "scale the tilt estimator by 3 %.  It must stop recovering an injected tilt — otherwise BP1a "
     "is comparing nothing and every slope in the gate is unvalidated"),

    ("bp1b-untested", 1, "GATE BP BP1b FAIL",
     'SCOPE = (("BLEND min (OD out of circuit)", "blend-0700_base-od.wav"),\n'
     '         ("CLEAN path", "ref-clean.wav"))',
     "SCOPE = ()",
     "empty the scope set entirely.  ⚠ THIS ARM FOUND A REAL HOLE: the original guard was "
     "`n_s != len(SCOPE)`, which 0 == 0 satisfies, so an untested scope control passed the check "
     "written to catch one.  The guard now also refuses on n_s == 0"),

    ("bp1d-vacuous", 1, "GATE BP BP1d FAIL",
     "MIN_DELIVERY_DB_OCT = 0.05   # BP1d non-vacuity: the corner must move by at least this",
     "MIN_DELIVERY_DB_OCT = 100.0  #",
     "raise the non-vacuity floor above what the stage actually delivers.  The refusal must fire — "
     "proving the floor is a live check and not a threshold nothing ever reaches (s110: the FIRST "
     "draft of a floor arm usually mutates it to a value that still never binds)"),

    ("bp1e-empty", 1, "GATE BP BP1e FAIL",
     '    calls = re.findall(r"odDriveTilt\\.(\\w+)\\s*\\(([^;]*)\\)\\s*;", src)',
     '    calls = re.findall(r"odDriveTiltZZZ\\.(\\w+)\\s*\\(([^;]*)\\)\\s*;", src)',
     "make the source scan match nothing.  A source assertion that matches no call sites must "
     "REFUSE — it would otherwise report 'no LEVEL/BLEND term reaches the stage' about a file it "
     "never read, which is the licence for the whole gate's reading of `ON - OFF`"),

    ("bp1e-banned", 1, "GATE BP BP1e FAIL",
     '    banned = ("level", "blend", "cleanFrac", "cleanfrac", "mix")',
     '    banned = ("level", "blend", "cleanFrac", "cleanfrac", "mix", "osRate")',
     "add a term that IS present in a real call site (`prepare(osRate)`).  The banned-term check "
     "must fire, proving it reads the ACTUAL argument text rather than passing because the tuple "
     "happens to miss"),

    # ---- computed verdicts ----------------------------------------------------------------------
    ("bp2-shape", 0, "FALLS MONOTONICALLY",
     '    seq = [rows[l]["delivered"] for l in ladder]',
     "    seq = [-1.0 / (1.0 + i) for i in range(len(ladder))]",
     "feed the shape test a monotone sequence.  The verdict must switch to simple dilution — the "
     "measured answer is an INTERIOR peak, and a gate that cannot also say 'monotone' is narrating "
     "the interesting one"),

    ("bp2b-sign", 0, "unanimously NEGATIVE at 2714",
     '        r = [BA.drive_tilt(ped[lab], f) - BA.drive_tilt(mod_off[lab], f) for f in fs]',
     '        r = [BA.drive_tilt(mod_off[lab], f) - BA.drive_tilt(ped[lab], f) for f in fs]',
     "flip the sign of `required`.  The per-centre verdict must invert with it — this is the "
     "gate's largest claim (the model is ALREADY over-tilted at every mixed cell above the vertex) "
     "and it must be read off the data, not printed"),

    ("bp3b-confound", 0, "INFLATES `required`",
     "    slope = (off[hi] - off[lo]) / (cf[hi] - cf[lo]) if cf[hi] != cf[lo] else float(\"nan\")",
     "    slope = -(off[hi] - off[lo]) / (cf[hi] - cf[lo]) if cf[hi] != cf[lo] else float(\"nan\")",
     "negate the measured locus slope.  The confound's DIRECTION verdict must flip — the first "
     "draft of this sub-gate printed the wrong direction word beside a correct number, which is "
     "the exact defect `computed-verdicts-not-narrated` describes"),

    ("bp4-bar", 0, "bar 1.0 dB : 12 of 12",
     '        return (fs, 100.0 * (fs[-1] / fs[0] - 1.0),\n'
     '                min(r["prom"] for r in rs), any(r["edge"] for r in rs))',
     '        return (fs, 100.0 * (fs[-1] / fs[0] - 1.0),\n'
     '                min(r["prom"] for r in rs) + 5.0, any(r["edge"] for r in rs))',
     "lift every prominence above GATE W's bar.  The survivor counts must follow the data — the "
     "measured answer is that NOTHING resolves at that bar, and a gate that cannot report the "
     "opposite is not measuring it"),

    ("bp4-overshoot", 0, "0 of 12 cells OVERSHOOT",
     '                     (("off", mod_off[lab]), ("on", mod_on[lab]), ("ped", ped[lab]))}',
     '                     (("off", mod_off[lab]), ("on", mod_on[lab]), ("ped", mod_on[lab]))}',
     "feed the pedal arm the model's own ON curve, so the walks coincide.  The overshoot count "
     "must fall to zero — proving 11-of-12 is a comparison against the reference and not a "
     "constant"),
]


def run(path, extra=()):
    return subprocess.run([sys.executable, path, *extra],
                          cwd=ROOT, capture_output=True, text=True, timeout=5400)


def main():
    with open(SRC, encoding="utf-8") as fh:
        src = fh.read()

    if re.search(r'add_argument\("--json"[^)]*default=(?!None)', src):
        sys.exit("MUTATION HARNESS FAIL: --json has a non-None default (s153) — an arm would "
                 "overwrite the real gate's report with a deliberately falsified one")

    priv = 'PRIV_DIR = os.path.join(os.path.dirname(HERE), "build", "s188_od_tilt_mix")'
    if src.count(priv) != 1:
        sys.exit("MUTATION HARNESS FAIL: cannot redirect the mutant's private render dir — the "
                 "PRIV_DIR line has moved, and without the redirect every arm would render into "
                 "the real gate's cache")
    src_m = src.replace(priv, f'PRIV_DIR = os.path.join(os.path.dirname(HERE), "build", '
                              f'"s188_od_tilt_mix_mut_{os.getpid()}")')

    print("=== CONTROL (unmutated, rendering into the mutant's private dir) ===")
    with open(MUT, "w", encoding="utf-8") as fh:
        fh.write(src_m)
    c = run(MUT)
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
            r = run(MUT)
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
        for n in os.listdir(HERE):
            if n.startswith(f"_mutated_gate_bp_{os.getpid()}"):
                os.remove(os.path.join(HERE, n))

    print(f"\n{passed}/{len(ARMS)} arms PASS")
    sys.exit(0 if passed == len(ARMS) else 1)


if __name__ == "__main__":
    main()
