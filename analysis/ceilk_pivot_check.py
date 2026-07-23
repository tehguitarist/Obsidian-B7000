#!/usr/bin/env python3.11
"""Session-13 RESHAPE §3j discriminating check (handover §3s(2)) — the gate BEFORE fitting the
ceiling-hardness reshape. Mirror of `clipk_pivot_check.py`, but for the JFET ceiling's own
hardness `jfetCeilK` (algebraic sigmoid `T(w)=w/(1+|w/L|^k)^(1/k)` replacing `L*tanh(w/L)`).

THE RESHAPE IS NOT IMPLEMENTED YET. `jfetCeilK` is not a FitParams field, so OfflineRender will
reject `--fit jfetCeilK=...` until `JfetStage.h`/`FitParams.h`/`PedalChain`/`offline_render.cpp`
are changed (with dsp-validator sign-off — handover §3s(1),(5)). This script is the ready-to-run
gate for the moment AFTER that lands: it detects the unimplemented case and tells you so, rather
than silently doing nothing.

THE PRE-REGISTERED SIGNATURE (must hold, or STOP and do NOT fit — §3s(2)):
    as k RISES (harder knee), drive-min H3-H2 FALLS toward the capture's -23.2 dB,
    AND drive-noon H3-H2 RISES toward -10.6 dB, SIMULTANEOUSLY.
This is sharper than the clipK pivot (which only needed noon to move, and moved it the WRONG way):
the ceiling reshape must reduce the drive-min ceiling-H3 EXCESS *and* unmask the clipper's
mid-drive ramp at noon in one lever. If min and noon do not move the right way together, the
hardness lever is wrong — try the asymmetry (cPos/cNeg) or the odd-term sign, per §3s(2).

Run: /opt/homebrew/bin/python3.11 analysis/ceilk_pivot_check.py [--point=s,a,cp,cn,A0,satLo,satHi]
     --point defaults to the session-11 fitted point (the operating point where noon fails).
Log: analysis/fit_logs/step5_ceilk_pivot.log
"""
import sys, os, subprocess
sys.path.insert(0, os.path.dirname(__file__))
import fit_nonlinear as F

# k values to sweep. 2.0 is the ADAA anchor; the OLD tanh ceiling behaves like k ~ 1.5-2, so
# HIGHER k (harder knee) is the direction expected to cut the drive-min ceiling-H3 excess.
K_SWEEP = [1.0, 1.5, 2.0, 3.0, 4.0, 6.0, 8.0]

# Session-11 fitted point (FIT_KEYS order: s, a, cp, cn, clipA0, clipSatLo, clipSatHi).
FITTED_POINT = [0.24601, 2.6099, 0.48727, 0.27357, 29.937, 1.2328, 1.5779]


def _reshape_implemented():
    """True iff OfflineRender accepts --fit jfetCeilK (i.e. the reshape has landed)."""
    try:
        r = subprocess.run([F.RENDER_BIN, "--print-fit", "--fit", "jfetCeilK=2"],
                           capture_output=True, text=True)
        return r.returncode == 0
    except Exception:
        return False


def main():
    if not _reshape_implemented():
        print("=" * 78)
        print("jfetCeilK is NOT implemented yet — the ceiling reshape (§3s(1)) has not landed.")
        print("OfflineRender rejects `--fit jfetCeilK=`. Implement the algebraic-sigmoid ceiling")
        print("in JfetStage.h (+ FitParams/PedalChain/offline_render plumbing), get the")
        print("dsp-validator sign-off (§3s(5)), THEN re-run this gate before any fit.")
        print("=" * 78)
        return 2

    point = list(FITTED_POINT)
    for arg in sys.argv[1:]:
        if arg.startswith("--point="):
            point = [float(v) for v in arg.split("=", 1)[1].split(",")]
    F.make_short_input()
    targets = F.capture_targets()

    os.makedirs("analysis/fit_logs", exist_ok=True)
    log = open("analysis/fit_logs/step5_ceilk_pivot.log", "w")

    def emit(s):
        print(s); log.write(s + "\n")

    emit("Capture targets (tone_220, H3-H2 dB):")
    for lbl, p in targets.items():
        emit(f"  {lbl:5s}  {p['H3'] - p['H2']:>7.1f}")
    emit("\nFull-chain H3-H2 (dB) vs jfetCeilK — HELD as in the fit; point:")
    emit("  " + ", ".join(f"{k}={v:g}" for k, v in zip(F.FIT_KEYS, point)))
    labels = list(targets.keys())
    emit(f"  {'k':>5} | " + " | ".join(f"{l:>6s}" for l in labels))

    rows = {}
    try:
        for k in K_SWEEP:
            F.HELD["jfetCeilK"] = k
            prof = F.render_profiles(point)
            rows[k] = [prof[l]["H3"] - prof[l]["H2"] for l in labels]
            emit(f"  {k:>5.2f} | " + " | ".join(f"{v:>6.1f}" for v in rows[k]))
    finally:
        F.HELD.pop("jfetCeilK", None)

    ks = sorted(rows.keys())
    mn = [rows[k][labels.index("min")] for k in ks]
    noon = [rows[k][labels.index("noon")] for k in ks]
    # signature: min FALLS and noon RISES as k increases (ks ascending)
    min_fall = mn[0] - mn[-1]     # low-k minus high-k; >0 means min fell as k rose
    noon_rise = noon[-1] - noon[0]
    cap_min = targets["min"]["H3"] - targets["min"]["H2"]
    cap_noon = targets["noon"]["H3"] - targets["noon"]["H2"]
    emit(f"\nPre-registered signature (capture: min {cap_min:+.1f}, noon {cap_noon:+.1f}):")
    emit(f"  min  falls as k rises : {min_fall:+.1f} dB  (want > 0, toward {cap_min:+.1f})")
    emit(f"  noon rises as k rises : {noon_rise:+.1f} dB  (want > 0, toward {cap_noon:+.1f})")
    ok = min_fall > 1.0 and noon_rise > 1.0
    emit(f"  SIGNATURE {'CONFIRMED — proceed to the complex fit' if ok else '** NOT CONFIRMED — STOP, wrong lever **'}")
    log.close()
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
