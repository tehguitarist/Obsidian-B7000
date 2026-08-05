#!/usr/bin/env python3.11
"""Mutation test for GATE AZ (analysis/level_taper_fit.py).

GATE AZ is the gate that CHOSE the shipped LEVEL taper, so every statement it makes has already
become a constant in `src/dsp/FitParams.h`. That is the strongest possible reason for its verdicts
to be computed rather than narrated, and the reason four of these arms carry `expect_rc == 0`:

  * `expect_rc != 0` arms test the REFUSALS -- the known answer against GATE AY3's stored numbers,
    the epoch of the report the requirement was solved on, monotonicity, the exact endpoints, and
    the bleed-free anchor.
  * `expect_rc == 0` arms test the COMPUTED VERDICTS, i.e. the four sentences the shipped comment
    block in `LevelBlend.h` quotes:
      - "the family SATURATES at 5 segments, so 4 is the LIMIT"     -> az2-saturate
      - "SHIP the 4-SEGMENT curve" (vs a smaller/larger one)        -> az2-choice
      - "INSIDE the requirement's own spread at EVERY detent"       -> az3-contain
      - "moves the pot TOWARD the A-taper band"                     -> az4-band

⚠⚠ THE MOST IMPORTANT ARM IS `az1-known-answer`. AZ rebuilds GATE AY3's scorer (AY3's is a
closure), and every family comparison, the segment count, and therefore the shipped constants rest
on those five lines being AY3's. If the reproduction can be broken without the gate noticing, the
whole tool is scoring an objective nobody has validated.

⚠ THE SECOND IS `az1-epoch`. AZ maps detent -> L with the taper the REPORT WAS RENDERED WITH, read
out of GATE AY's stored report -- not with whatever is shipped now. The moment AZ's own output
shipped, those two stopped being the same curve, so an AZ that silently used the current taper
would mislabel every point on its horizontal axis and would do so ONLY after its constants landed,
which is the worst possible time to find out.

⚠ WHAT IS NOT COVERED, stated rather than left to be discovered:
  * **That the requirement itself is right** is GATE AY's claim, not this gate's; AZ imports it and
    its known answer only shows the two agree about the OBJECTIVE.
  * **The optimiser's global-ness is not armed.** It is multi-start (60 random + seeded), and the
    saturation control is what makes a landed optimum credible; a mutation cannot distinguish "a
    better optimum exists" from "this family is worse".

Mechanics, each paid for by an earlier session:
  * the patched copy LIVES in analysis/ (sibling imports) and RUNS from the repo root (data
    paths) -- two different requirements (s110).
  * the mutant path is PID-UNIQUE (s139).
  * `--json` has NO default, so a mutant invoked without it writes nothing and cannot leave a
    deliberately falsified report on disk wearing the real gate's name (s153). ASSERTED below.
  * an unmutated CONTROL runs first; if it does not pass, nothing below is attributable (s107).
  * failures are scored on the guard's own tag, not merely a non-zero exit (s117).

Run:  python3.11 analysis/_mutate_gate_az.py
"""
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SRC = os.path.join(HERE, "level_taper_fit.py")
MUT = os.path.join(HERE, f"_mutated_gate_az_{os.getpid()}.py")

REPORT = "analysis/reports/s162_shipped.json"
AY = "analysis/reports/s162_level_taper.json"

# (name, expect_rc, must_contain, find, replace, why)  -- `must_contain` may be a (NOT, text) pair
ARMS = [
    # ---- refusals -------------------------------------------------------------------------
    ("az1-known-answer", 1, "GATE AZ1 FAIL",
     "        return (float(np.sqrt(np.mean(np.square(errs))))",
     "        errs = [e + 0.05 for e in errs]\n        return (float(np.sqrt(np.mean(np.square(errs))))",
     "perturb the rebuilt objective by 0.05 dB. It must stop reproducing GATE AY3's stored "
     "numbers -- if it does not, the known answer is not comparing anything and every family "
     "number below it is unvalidated"),

    ("az1-epoch", 1, "GATE AZ1 FAIL",
     '    a1 = ay.get("ay1", {})',
     '    a1 = {}',
     "hide the render-epoch taper from the gate. It must REFUSE rather than fall back to the "
     "currently-shipped curve, which after s163 is a different curve and would mislabel the "
     "detent -> L axis of a stored report"),

    ("az4-monotone", 1, "GATE AZ4 FAIL",
     "    mono = bool(np.all(np.diff(Ls) >= -1e-15))",
     "    mono = False",
     "a non-monotone curve is not a pot law at all, whatever its residual -- the gate must exit "
     "rather than print it as a property"),

    ("az4-endpoint", 1, "GATE AZ4 FAIL",
     "    ends = (abs(pwl(0.0, bs, fs)) , abs(pwl(1.0, bs, fs) - 1.0))",
     "    ends = (0.0, 1e-6)",
     "break L(1) = 1. That endpoint is the bleed-free anchor every absolute instrument in the "
     "project reads at, so an inexact one must be fatal, not reported"),

    ("az6-anchor", 1, "GATE AZ6 FAIL",
     "    a_new, b_new = K.coef_closed(1.0, pwl(1.0, fit[\"breaks\"], fit[\"fracs\"]))",
     "    a_new, b_new = K.coef_closed(1.0, 0.999)",
     "move the bleed-free corner by 0.001 in L. GATE K7's ratio, GATE O's A3 ledger, GATE L's "
     "|rho| and OdToneRestore's base row all anchor there -- the gate must refuse"),

    # ---- computed verdicts ----------------------------------------------------------------
    ("az2-saturate", 0, "NO SATURATION",
     "    sat = [b for b, g in gains.items() if abs(g) < 1e-6]",
     "    sat = []",
     "with no saturating family the gate must SAY the segment count is a judgement rather than a "
     "measured limit -- the shipped comment block quotes the saturation, so it must not be "
     "narrated"),

    # ⚠ `SEG_RANGE` counts BREAKPOINTS; the family printed is `n + 1` SEGMENTS. The first version
    # of this arm restricted it to (2, 3) meaning to leave 3 segments as the richest family, and
    # that range still CONTAINS the 4-segment family — so the gate correctly shipped four and the
    # runner scored it NARRATED against a gate that was working. `suspect the mutation before the
    # guard` (s110/s114), and the off-by-one is exactly the kind a segment-count parameter invites.
    # Verified at (1, 2): the gate ships THREE and prints the "JUDGEMENT, not a measured limit"
    # caveat, i.e. the choice tracks the measurement.
    ("az2-choice", 0, "SHIP the 3-SEGMENT",
     "SEG_RANGE = (2, 3, 4, 5)",
     "SEG_RANGE = (1, 2)",
     "restrict the sweep so 3 SEGMENTS (n = 2 breakpoints) is the richest family available. The "
     "gate must ship THREE, i.e. the choice tracks the measurement rather than being hard-coded"),

    ("az3-contain", 0, "OUTSIDE at one or more detents",
     '    spreads = {float(k): v["spread"] for k, v in ay["ay3"]["required_taper"].items()}',
     '    spreads = {float(k): v["spread"] * 1e-4 for k, v in ay["ay3"]["required_taper"].items()}',
     "shrink the requirement's own spread by 1e4. The containment verdict must FLIP to OUTSIDE -- "
     "it is the overfitting test the shipped constants rest on, so it cannot be a fixed string"),

    ("az4-band", 0, "AWAY FROM the band",
     "    moved = abs(half - 0.5 * (A_TAPER_LO + A_TAPER_HI)) < abs(half_ship - 0.5 * (A_TAPER_LO + A_TAPER_HI))",
     "    moved = abs(half - 0.5 * (A_TAPER_LO + A_TAPER_HI)) < 0.0",
     "the A-taper corroboration is the one outside check on this fit, so 'moves TOWARD the band' "
     "must be able to come back as its opposite"),
]


def run(path, extra=()):
    return subprocess.run([sys.executable, path, REPORT, "--ay", AY, *extra],
                          cwd=ROOT, capture_output=True, text=True, timeout=1800)


def main():
    with open(SRC, encoding="utf-8") as fh:
        src = fh.read()

    # The s153 hazard, asserted rather than assumed: a mutant must not be able to write the real
    # gate's report. This gate's --json has no default, so an invocation without it writes nothing.
    if re.search(r'add_argument\("--json"[^)]*default=(?!None)', src):
        sys.exit("MUTATION HARNESS FAIL: --json has a non-None default, so a mutant would write a "
                 "deliberately falsified report over the real one (s153)")

    print("=== CONTROL (unmutated) ===")
    c = run(SRC)
    if c.returncode != 0:
        print(c.stdout[-3000:], c.stderr[-2000:])
        sys.exit("MUTATION HARNESS FAIL: the UNMUTATED gate does not pass, so no failure below is "
                 "attributable to a mutation (s107)")
    print(f"  control OK (rc=0), {len(c.stdout.splitlines())} lines\n")

    passed = 0
    try:
        for name, rc_want, want, find, repl, why in ARMS:
            if src.count(find) != 1:
                print(f"  {name:<18} PATCH DID NOT APPLY ({src.count(find)} matches) -- the arm "
                      f"targets a line that has moved")
                continue
            with open(MUT, "w", encoding="utf-8") as fh:
                fh.write(src.replace(find, repl))
            r = run(MUT)
            ok_rc = (r.returncode != 0) if rc_want else (r.returncode == 0)
            body = r.stdout + r.stderr
            ok_txt = want in body
            verdict = ("PASS" if (ok_rc and ok_txt)
                       else ("NARRATED" if (ok_rc and not ok_txt and rc_want == 0)
                             else ("WRONG GUARD" if ok_rc else "GUARD DEAD")))
            passed += verdict == "PASS"
            print(f"  {name:<18} {verdict:<12} rc={r.returncode} want={'!=0' if rc_want else '==0'} "
                  f"| {want!r} {'found' if ok_txt else 'MISSING'}")
            if verdict != "PASS":
                print(f"      why the arm exists: {why}")
                print("      last output:", (body.strip().splitlines() or ["<empty>"])[-1][:160])
    finally:
        if os.path.exists(MUT):
            os.remove(MUT)

    print(f"\n{passed}/{len(ARMS)} arms passed")
    sys.exit(0 if passed == len(ARMS) else 1)


if __name__ == "__main__":
    main()
