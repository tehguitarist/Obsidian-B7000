#!/usr/bin/env python3.11
"""Mutation test for GATE AC (analysis/sk_gate_i_reconcile.py).

Every arm carries an expected EXIT CODE **and** a string the output must contain (s128):

  * `expect_rc != 0` arms test the REFUSALS -- guards whose job is to stop the gate.
  * `expect_rc == 0` arms test the COMPUTED VERDICTS. s108's rule means a well-built gate's
    headline findings deliberately never change the exit code, so a conclusion that has quietly
    become hard-coded narration would survive an exit-code-only runner. Those arms break the data
    behind a verdict and require the gate to print the OPPOSITE verdict.

Mechanics, each paid for by an earlier session:
  * the patched copy LIVES in analysis/ (so sibling imports resolve) and RUNS from the repo root
    (so data paths resolve) -- two different requirements, and satisfying one is the natural way
    to break the other (s110).
  * an unmutated CONTROL runs first; if it does not pass, no failure below is attributable (s107).
  * four arms (AC1a, AC1b, AC0, AC4) patch an IMPORTED module (`bt_pair_shape_gate`,
    `hf_artefact_gate`) rather than the gate under test, because that is where the quantity lives.
    Said at each arm rather than pretended to be local.
  * failures are scored on the guard's own tag, not merely on rc != 0 (s117).

Run:  python3.11 analysis/_mutate_gate_ac.py
"""
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
SRC = os.path.join(HERE, "sk_gate_i_reconcile.py")
TMP = os.path.join(HERE, "_mutated_gate_ac.py")
REPORT = "analysis/reports/s124_ship.json"

# A patch is (name, why, [(pattern, replacement)], expect_rc, must_contain, extra_argv).
ARMS = [
    ("AC1a  cross-implementation known answer",
     "perturb ONE of the two SK transcriptions; two independent readings of one network must "
     "then disagree and the gate must refuse before using either.",
     [(r"^import hf_artefact_gate as HI.*$",
       "import hf_artefact_gate as HI  # noqa: E402\n"
       "HI.SK_STAGES = (dict(name='x', R1=10e3, R2=22e3, Cfb=1.3e-9, Cgnd=1.0e-9),\n"
       "               dict(name='y', R1=22e3, R2=47e3, Cfb=2.2e-9, Cgnd=1.0e-9))")],
     2, "AC1a", []),

    ("AC1b  cascade baseline vs s125",
     "move the closed-form answer the cascade must reproduce; AC1b must refuse rather than "
     "carry a cascade that no longer agrees with the derivation it inherits.",
     [(r"^import bt_pair_shape_gate as AB.*$",
       "import bt_pair_shape_gate as AB  # noqa: E402\nAB.S125_PEAK_HZ = 1500.0")],
     2, "AC1b", []),

    ("AC2  separability",
     "make the sk_scale perturbation ALSO move the clipper pole, so the full-cascade delta stops "
     "equalling the SK-only delta. AC3's whole assumption-light claim rests on this.",
     [(r"^def cascade_db\(f, \*\*kw\):",
       "def cascade_db(f, **kw):\n"
       "    if 'sk_scale' in kw:\n"
       "        kw = dict(kw, c14=AB.C14 * 1.4)")],
     2, "AC2", []),

    ("AC5  bound-convergence guard",
     "sweep the multiplier over too small a range, so the SK pair has NOT converged to "
     "transparent and `bound` is not a bound. A ceiling read off an unconverged sweep is a "
     "sentinel, not a measurement.",
     [], 2, "AC5", ["--sk-bound-decades", "0.2"]),

    ("AC0  membership / vacuity",
     "make every capture unclassifiable, so no OD class survives. A gate that produces no data "
     "must refuse, not fall through (`empty-gate-must-fail`). Patches the IMPORTED "
     "hf_artefact_gate, which owns classification.",
     [(r"^import hf_artefact_gate as HI.*$",
       "import hf_artefact_gate as HI  # noqa: E402\nHI.classify = lambda c: None")],
     1, "EMPTY", []),

    ("AC4  COMPUTED VERDICT — direction is a comparison, not a property",
     "flip the SIGN of the peak target. The candidate is unchanged, so its direction verdict "
     "MUST invert; if AC4 hard-codes the reference's own signature (AB5's s130 defect) it will "
     "keep saying TOWARD. Patches bt_pair_shape_gate, which owns the target.",
     [(r"^import bt_pair_shape_gate as AB.*$",
       "import bt_pair_shape_gate as AB  # noqa: E402\nAB.PEDAL_DPEAK = -AB.PEDAL_DPEAK")],
     0, "0 of 2 axes move toward", []),

    ("AC5  COMPUTED VERDICT — reachability is measured, not asserted",
     "collapse the PEDAL's top-octave level in the loaded report so its rate stops exceeding the "
     "model's. The bound is unchanged, so the gate must now report the gap as REACHABLE. A "
     "data-level mutation (s114): the honest way to test a guard whose threshold is derived.",
     [(r"^    d, bands, lo_i, hi_i = HI\.band_octave\(args\.report\)",
       "    d, bands, lo_i, hi_i = HI.band_octave(args.report)\n"
       "    for _c in d['captures']:\n"
       "        for _sw in _c.get('fr', {}).values():\n"
       "            _sw['pedal_db'][hi_i] -= 40.0")],
     0, "3 of 3 classes are reachable", []),
]


def run(path, extra):
    p = subprocess.run([sys.executable, path, REPORT] + extra,
                       cwd=REPO, capture_output=True, text=True)
    return p.returncode, p.stdout + p.stderr


def main():
    src = open(SRC).read()
    open(TMP, "w").write(src)
    rc, out = run(TMP, [])
    if rc != 0:
        print("CONTROL FAILED — the unmutated copy does not pass, so nothing below is "
              f"attributable to a mutation (rc={rc}).")
        print(out[-3000:])
        os.remove(TMP)
        return 1
    print(f"CONTROL  unmutated copy passes (rc=0) ... OK\n")

    npass = 0
    for name, why, patches, exp_rc, must, extra in ARMS:
        mutated = src
        for pat, rep in patches:
            new, n = re.subn(pat, rep, mutated, count=1, flags=re.M)
            if n != 1:
                print(f"[{name}] MUTATION DID NOT APPLY (pattern {pat!r}) — this is a defect in "
                      f"the TEST, not the gate (s110: suspect the mutation first).")
                mutated = None
                break
            mutated = new
        if mutated is None:
            continue
        open(TMP, "w").write(mutated)
        rc, out = run(TMP, extra)
        hit = must in out
        good = (rc == exp_rc) and hit
        npass += 1 if good else 0
        if good:
            verdict = "OK"
        elif rc != exp_rc and not hit:
            verdict = f"**GUARD DEAD** (rc={rc}, expected {exp_rc}; and no {must!r})"
        elif rc != exp_rc:
            verdict = f"**WRONG RC** (rc={rc}, expected {exp_rc})"
        else:
            verdict = f"**NARRATED** (rc as expected but never printed {must!r})"
        print(f"[{name}]\n    {why}\n    -> {verdict}")
        if not good:
            print("    --- tail ---")
            print("    " + "\n    ".join(out.strip().splitlines()[-14:]))
        print()

    os.remove(TMP)
    print(f"{npass}/{len(ARMS)} arms behaved as specified.")
    return 0 if npass == len(ARMS) else 1


if __name__ == "__main__":
    sys.exit(main())
