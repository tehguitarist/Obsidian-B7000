#!/usr/bin/env python3.11
"""a5_fit_eval — score ONE parameter point on `fit_nonlinear`'s own objective, no fitting.

WHY THIS EXISTS (session 42, Phase 9 / A5)
------------------------------------------
Before re-fitting the clipper family under the clean path's supply bound, two numbers are
needed that `fit_nonlinear.py` does not print on its own:

  (1) the cost of the SHIPPED point, on today's model. The session-17 family was fitted
      BEFORE `trebleC7` (100n -> 680p, s34), before `clipC15` existed as a stage at all
      (s36/37), and before the clean-path fixes (s25 trebleWiperR, s26/27 mid caps, s28
      c21R). Every one of those is frequency-dependent and sits in or after the OD path, so
      each one moves H3 (660 Hz) and H2 (440 Hz) by DIFFERENT amounts -- i.e. it moves the
      harmonic-TO-harmonic ratios this objective is built from. The capture targets have not
      moved; the model under them has. So "is the shipped clipper family still the optimum of
      its own objective?" is an open question, and it is the same staleness class as the A5b
      makeup finding (a constant left behind by later fixes to the path it was fitted against).

  (2) a like-for-like cost for candidate points, so a constrained fit can be compared against
      the shipped point on ONE scale rather than against session 17's logged number, which was
      produced by a different model.

`--gm-scan` almost does this, but it sets PHASE_TARGET = None (dropping the psi3 term), so its
cost is NOT comparable with a fit's. This scores the full objective, phase term included.

Run:
  /opt/homebrew/bin/python3.11 analysis/a5_fit_eval.py                 # shipped + nominal
  /opt/homebrew/bin/python3.11 analysis/a5_fit_eval.py --point a,b,... # one explicit vector
"""
import sys, os

sys.path.insert(0, os.path.dirname(__file__))
import fit_nonlinear as F

# The SHIPPED defaults, read off src/dsp/FitParams.h + GainStaging.h, in FIT_KEYS order.
# ⚠ clipC11 is carried in NANOFARADS in the fit vector (F.EMIT_SCALE), so 5.7207e-9 F -> 5.7207.
# ⚠ kInputRef comes from GainStaging.h::kInputRefNominal, NOT FitParams -- it is processor-domain
#    (F.CLI_FLAG_KEYS routes it to --input-ref). Keeping the two sources straight matters: this is
#    exactly the pair whose degeneracy A5 is trying to break.
SHIPPED = {
    "jfetSatPos": 0.20072, "jfetSatNeg": 3.1769, "jfetCeilPos": 2.3428,
    "jfetCeilNeg": 0.27408, "jfetExpandBeta": 2.1354,
    "clipA0": 26.142, "clipSatLo": 2.0067, "clipSatHi": 2.9321, "clipK": 2.8462,
    "kInputRef": 3.377, "clipC11": 5.7207,
}


def vec(d):
    return [d[k] for k in F.FIT_KEYS]


def report(label, params, targets):
    c, prof = F.cost(params, targets, verbose=True)
    if prof is None:
        print(f"\n{label}: INFEASIBLE (non-monotone waveshaper) — cost {c:.1f}")
        return c
    print(f"\n{label}: cost = {c:.2f}")
    print(f"  {'drive':5s}  {'H3-H2':>16} {'H4-H2':>16} {'H5-H2':>16}")
    for lbl in targets:
        cells = []
        for hi, lo in (("H3", "H2"), ("H4", "H2"), ("H5", "H2")):
            m = prof[lbl][hi] - prof[lbl][lo]
            t = targets[lbl][hi] - targets[lbl][lo]
            cells.append(f"{m:+6.1f}/{t:+6.1f}{'':1s}({m-t:+5.1f})")
        print(f"  {lbl:5s}  " + " ".join(f"{c_:>16s}" for c_ in cells))
    print("         (model/capture, and (model-capture) in parentheses)")
    return c


def main():
    F.make_short_input()
    targets = F.capture_targets()
    F.PHASE_TARGET = F.capture_phase_target()
    print("=" * 92)
    print("A5 — scoring points on fit_nonlinear's objective (harmonic ratios + psi3), TODAY's model")
    print("=" * 92)
    print(f"  held: " + ", ".join(f"{k}={v:g}" for k, v in F.HELD.items()))
    print(f"  phase target: drive-min psi3 @ {F.PHASE_TONE:g} Hz = {F.PHASE_TARGET:+.1f} deg")

    pts = [("SHIPPED (session-17 family)", vec(SHIPPED))]
    for arg in sys.argv[1:]:
        if arg.startswith("--point="):
            pts.append(("--point", [float(v) for v in arg.split("=", 1)[1].split(",")]))
    if "--no-nominal" not in sys.argv:
        pts.append(("NOMINAL (pre-fit)", F.NOMINAL))

    for label, p in pts:
        report(label, p, targets)
    print()


if __name__ == "__main__":
    main()
