#!/usr/bin/env python3.11
"""a3_extra_tf_probe -- Phase 9 / A3 step 2, first cut.

Session 31 established WHAT is missing (an extra phase lead in the OD path,
>= 168 deg total at 40 Hz vs the model's 57.6) and that no existing stage can
supply it. This asks the next question, and it is the one that decides what
KIND of element to go looking for:

    Is the missing thing MINIMUM-PHASE?

`a3_phase_solve.py` part 3 returns, per band, BOTH halves of the requirement:

    s(f)      how much the pedal's OD magnitude differs from the model's
    theta(f)  the pedal's OD-vs-bleed phase

so the extra transfer the model needs is fully specified as a complex number:

    G(f) = s(f) . e^( i . (theta_ped(f) - theta_mdl(f)) )

A passive (minimum-phase) network cannot choose its magnitude and its phase
independently -- the phase is fixed by the magnitude slope. So fitting a
candidate family to |G| ALONE and then reading off how much phase it delivers
is a falsification test:

  * if the magnitude-optimal fit also lands the phase, a passive LF network
    exists and this prints its corner frequencies;
  * if it falls short in phase, no network OF THAT FAMILY does both -- which is
    a statement about the family, not about minimum-phase in general.

⚠ ANSWERED, AND THE ANSWER IS NEGATIVE -- see the VERDICT this prints.  The
tempting next step is to promote a shortfall into "therefore the mechanism is
NON-minimum-phase" via the Bode gain-phase ceiling.  That inference does not
survive: the ceiling at 40 Hz is set mostly by the magnitude slope BELOW 20 Hz,
which no capture in the matrix measures, and extrapolating it flat understates
a real highpass by 36-91 deg over 20-40 Hz -- the entire size of the apparent
shortfall.  `selftest()` demonstrates this on networks whose phase is known in
closed form, and stays in the file for the same reason session 31 item 8 kept
its own: it is the only thing that catches this class of error.

Reliability: part 3's per-band `rms_dB` says how well the 5-point drive sweep
was actually fitted. 40-101 Hz fit badly (the model's mu_d is wrong on the
drive axis there, session 31 item 6), so every fit here is WEIGHTED by
1/(1+rms) and the unweighted per-band residuals are printed too. The 40 Hz
phase is separately pinned by the assumption-free depth bound from part 2,
which does not depend on the least-squares at all -- that bound is printed
alongside so a candidate can be judged against it directly.

Usage:  python3.11 analysis/a3_extra_tf_probe.py
No renders, no build -- it consumes a3_phase_solve.py's printed table.
"""
import itertools
import math

import numpy as np

# ---------------------------------------------------------------------------
# Session 31 measurements (analysis/a3_phase_solve.py, sweep_drv_-18,
# grunt cut / BLEND max / ATTACK flat).  Part 3 unless noted.
# ---------------------------------------------------------------------------
F = np.array([20.0, 25.0, 32.0, 40.0, 50.0, 64.0, 80.0, 101.0, 127.0, 160.0, 202.0, 254.0])
S = np.array([0.36, 0.32, 0.20, 0.21, 0.22, 0.54, 0.68, 0.82, 0.94, 1.05, 1.10, 1.10])
TH_PED = np.array([147.9, 151.6, 180.0, 180.0, 131.0, 139.4, 134.2, 127.1, 117.1, 104.2, 87.8, 85.5])
TH_MDL = np.array([104.2, 90.0, 73.3, 57.6, 41.5, 23.7, 8.0, 7.3, 20.7, 31.5, 37.9, 37.6])
RMS = np.array([0.88, 0.92, 0.81, 4.00, 4.37, 3.79, 3.07, 2.19, 1.26, 0.47, 0.13, 0.30])
# part 2, assumption-free lower bound at beta = -16.9 dB (blank -> nan)
BOUND = np.array([144.6, 148.4, 157.9, 169.6, 142.1, 129.6, 110.9,
                  np.nan, np.nan, np.nan, np.nan, np.nan])

DPHI = TH_PED - TH_MDL          # phase the model is missing, deg
W = 1.0 / (1.0 + RMS)           # trust weight
W = W / W.sum()


def response(params, kind, f):
    """Complex response of a candidate extra transfer function at f (Hz)."""
    s = 1j * f
    if kind == "hp1":                       # k . s/(s+w)
        k, w = params
        return k * s / (s + w)
    if kind == "hp2":                       # k . s/(s+w1) . s/(s+w2)
        k, w1, w2 = params
        return k * (s / (s + w1)) * (s / (s + w2))
    if kind == "shelf1":                    # k . (s+wz)/(s+wp)
        k, wz, wp = params
        return k * (s + wz) / (s + wp)
    if kind == "shelf2":                    # two identical shelves
        k, wz, wp = params
        return k * ((s + wz) / (s + wp)) ** 2
    if kind == "hp1_ap1":                   # hp1 cascaded with an ALL-PASS
        k, w, wa = params
        return k * (s / (s + w)) * ((wa - s) / (wa + s))
    if kind == "hp2_res":                   # 2nd-order HP with Q (complex poles)
        k, w0, q = params
        return k * (s * s) / (s * s + (w0 / q) * s + w0 * w0)
    raise ValueError(kind)


def err_mag(params, kind):
    g = response(params, kind, F)
    d = 20.0 * np.log10(np.abs(g) / S)
    return float(np.sqrt(np.sum(W * d * d)))


def err_phase(params, kind):
    g = response(params, kind, F)
    d = np.degrees(np.angle(g)) - DPHI
    return float(np.sqrt(np.sum(W * d * d)))


def err_joint(params, kind):
    # 1 dB of magnitude error ~ 10 deg of phase error (both ~ "one notch wrong")
    return math.hypot(err_mag(params, kind), err_phase(params, kind) / 10.0)


GRIDS = {
    "hp1":     (np.logspace(-0.7, 0.7, 29), np.logspace(1.0, 3.2, 45)),
    "hp2":     (np.logspace(-0.7, 0.7, 21), np.logspace(0.7, 2.9, 31), np.logspace(0.7, 2.9, 31)),
    "shelf1":  (np.logspace(-0.7, 0.7, 21), np.logspace(1.0, 3.2, 31), np.logspace(0.3, 2.6, 31)),
    "shelf2":  (np.logspace(-0.7, 0.7, 21), np.logspace(1.0, 3.2, 31), np.logspace(0.3, 2.6, 31)),
    "hp1_ap1": (np.logspace(-0.7, 0.7, 17), np.logspace(1.0, 3.2, 25), np.logspace(1.0, 3.4, 25)),
    "hp2_res": (np.logspace(-0.7, 0.7, 21), np.logspace(1.0, 2.8, 31), np.logspace(-0.5, 0.9, 21)),
}
LABEL = {
    "hp1":     "1st-order highpass            k.s/(s+w)",
    "hp2":     "2nd-order highpass, real poles",
    "hp2_res": "2nd-order highpass, Q (complex poles)",
    "shelf1":  "1st-order shelf               k.(s+wz)/(s+wp)",
    "shelf2":  "2nd-order shelf (two identical)",
    "hp1_ap1": "1st-order HP + ALL-PASS   (NON-minimum-phase)",
}


def search(kind, objective):
    grid = GRIDS[kind]
    best, bestp = float("inf"), None
    for p in itertools.product(*grid):
        e = objective(p, kind)
        if e < best:
            best, bestp = e, p
    return bestp, best


def show(kind, params, tag):
    g = response(params, kind, F)
    mag = 20.0 * np.log10(np.abs(g) / S)
    ph = np.degrees(np.angle(g)) - DPHI
    names = {"hp1": ("k", "fc"), "hp2": ("k", "fc1", "fc2"), "shelf1": ("k", "fz", "fp"),
             "shelf2": ("k", "fz", "fp"), "hp1_ap1": ("k", "fc", "fap"),
             "hp2_res": ("k", "f0", "Q")}[kind]
    pstr = "  ".join(f"{n}={v:.4g}" for n, v in zip(names, params))
    print(f"    {tag:<22s} {pstr}")
    print(f"      mag err dB : " + " ".join(f"{v:+6.1f}" for v in mag)
          + f"   | wRMS {err_mag(params, kind):5.2f}")
    print(f"      phase err  : " + " ".join(f"{v:+6.1f}" for v in ph)
          + f"   | wRMS {err_phase(params, kind):5.1f}")
    # phase delivered vs the assumption-free bound (part 2), where it exists
    tot = TH_MDL + np.degrees(np.angle(g))
    slack = tot - BOUND
    txt = " ".join("     -" if np.isnan(v) else f"{v:+6.1f}" for v in slack)
    print(f"      vs BOUND   : {txt}   (negative = fails the depth bound)")


def min_phase(mag_on_F, lf_slope_db_oct, hf_slope_db_oct=0.0, npts=40001, mag_fn=None):
    """Bode minimum-phase reconstruction from a log-magnitude curve.

        phi(w0) = (1/pi) . INTEGRAL  d(ln|G|)/du . ln|coth(|u|/2)| du,
                                                          u = ln(w/w0)

    For ANY given magnitude the minimum-phase realisation delivers the MAXIMUM
    lead of any causal LTI network (the only other option, right-half-plane
    zeros, keeps |G| and subtracts phase). So with the magnitude fixed this is
    a ceiling, not a fit.

    ⚠ THE TAILS ARE NOT OPTIONAL, AND THEY DOMINATE.  The measured band is
    20-254 Hz, but the phase AT 40 Hz is bought mostly by the magnitude slope
    BELOW 20 Hz, which the captures do not constrain at all.  Extrapolating
    flat understates a real highpass by 36-90 deg over 20-40 Hz -- see
    `selftest()`, which is why this function takes the tail slopes explicitly
    instead of hiding a default.  Integrate wide (0.02 Hz - 400 kHz): a 2-4 kHz
    window alone costs another 2-7 deg at the bottom.
    """
    lo, hi = np.log(2 * math.pi * 0.02), np.log(2 * math.pi * 400000.0)
    u = np.linspace(lo, hi, npts)
    w = np.exp(u)
    f = w / (2 * math.pi)
    if mag_fn is not None:
        lg = np.log(mag_fn(f))          # exact curve everywhere: numerics-only test
    else:
        lg = np.interp(f, F, np.log(mag_on_F))
        # replace np.interp's flat clamping with the declared tail slopes
        lo_m = f < F[0]
        hi_m = f > F[-1]
        lg[lo_m] = np.log(mag_on_F[0]) + (lf_slope_db_oct / 20.0) * math.log(10.0) * np.log2(f[lo_m] / F[0])
        lg[hi_m] = np.log(mag_on_F[-1]) + (hf_slope_db_oct / 20.0) * math.log(10.0) * np.log2(f[hi_m] / F[-1])
    dl = np.gradient(lg, u)
    out = []
    for f0 in F:
        ker = np.log(np.abs(1.0 / np.tanh(np.abs(u - math.log(2 * math.pi * f0)) / 2.0) + 1e-300))
        out.append(math.degrees(np.trapz(dl * ker, u) / math.pi))
    return np.array(out)


def selftest():
    """Recover a KNOWN minimum-phase network's phase from its own magnitude.

    Session 31 item 8's lesson, applied to this tool: a two-phasor solve that
    was wrong by 7 deg on data synthesised from the model itself was caught
    only because a self-test existed.  Keep this one for the same reason -- it
    is what showed that a flat-tail ceiling manufactures a 36-90 deg shortfall
    at exactly the bands A3 cares about.
    """
    print("  SELF-TEST -- recover an order-n highpass's own phase from its |G|.")
    print("  Three error sources, separated (max |err| in deg over the 12 bands):")
    print("    exact  = analytic |G| on the fine grid   -> the INTEGRAL itself")
    print("    12-pt  = |G| sampled at our 12 bands     -> band-grid resolution")
    print("    flat   = 12-pt with a FLAT sub-20 Hz tail-> the trap")
    ok = True
    for order, fc in ((1, 150.0), (2, 52.0), (2, 150.0)):
        def mag_fn(x, order=order, fc=fc):
            return (x / np.sqrt(x * x + fc * fc)) ** order
        truth = order * np.degrees(np.arctan2(fc, F))
        exact = min_phase(None, 0.0, mag_fn=mag_fn)
        pts = min_phase(mag_fn(F), lf_slope_db_oct=6.0 * order)
        flat = min_phase(mag_fn(F), lf_slope_db_oct=0.0)
        e_ex = np.max(np.abs(exact - truth))
        ok &= e_ex < 0.5
        print(f"    order-{order} HP fc={fc:6.1f}   exact {e_ex:5.2f}   12-pt {np.max(np.abs(pts-truth)):5.2f}"
              f"   flat {np.max(np.abs(flat-truth)):5.1f}"
              f"   (flat err at 20/40 Hz {flat[0]-truth[0]:+6.1f} /{flat[3]-truth[3]:+6.1f})")
    print(f"    -> integral {'OK' if ok else 'FAILED'}. The band grid costs a few deg;")
    print("       the flat tail costs 36-91 deg at 20-40 Hz -- it is not conservative.\n")
    return ok


def bode_ceiling():
    need_b = BOUND - TH_MDL
    print("  Bode gain-phase CEILING -- the most lead a given |G| can buy for ANY")
    print("  causal LTI element, vs what the null-depth bound demands:")
    print("       f " + " ".join(f"{v:6.0f}" for v in F))
    print("   needed " + " ".join(f"{v:+5.0f}" for v in DPHI))
    print("   bound  " + " ".join("    -" if np.isnan(v) else f"{v:+5.0f}" for v in need_b))

    # Two axes of sensitivity, because BOTH are unconstrained by the captures:
    #  (1) the sub-20 Hz tail slope -- unmeasured, and it is what buys lead at
    #      40 Hz.  0 dB/oct is not "conservative", it is a strong and wrong
    #      assumption for any highpass-shaped element.
    #  (2) the two least trustworthy measured points: 20/25 Hz, where |G| turns
    #      back UP as f falls (no highpass does that; it is the bottom band edge
    #      where session 24 measured ref-clean itself -1.3 dB and A2d found a
    #      real clean-path deficit), and the 50->64 Hz step of 8 dB in a third
    #      of an octave, inside the bands whose least-squares residual is 3-4 dB.
    repaired = S.copy()
    repaired[0], repaired[1] = 0.11, 0.15        # continue the 32->64 slope down
    repaired[3], repaired[4] = 0.27, 0.35        # smooth the 50->64 step
    for tag, mag in (("measured", S), ("monotone-repaired", repaired)):
        print(f"   -- |G| = {tag}")
        for slope in (0.0, 6.0, 12.0):
            ceil = min_phase(mag, lf_slope_db_oct=slope)
            short = ceil - need_b
            print(f"      LF tail {slope:4.0f} dB/oct  ceiling "
                  + " ".join(f"{v:+5.0f}" for v in ceil))
            print("                            SHORT   "
                  + " ".join("    -" if np.isnan(v) else f"{v:+5.0f}" for v in short))
    print("   (SHORT < 0 => that magnitude curve CANNOT supply the lead the null")
    print("    depth requires.  Note how completely the UNMEASURED tail decides it.)\n")


def main():
    print("A3 extra-transfer probe -- is the missing OD-path response MINIMUM-PHASE?\n")
    print("  Requirement per band (from a3_phase_solve part 3; * = weak fit, rms>2 dB):")
    print("       f " + " ".join(f"{v:6.0f}" for v in F))
    print("      |G|" + " ".join(f"{v:6.2f}" for v in S))
    print("    dB|G|" + " ".join(f"{20*math.log10(v):+6.1f}" for v in S))
    print("   argG  " + " ".join(f"{v:+6.0f}" for v in DPHI))
    print("   weak? " + " ".join(("     *" if r > 2 else "      ") for r in RMS))
    print()
    print("  Local Bode check (a minimum-phase network's phase is ~15 deg per dB/octave):")
    lo = np.log2(F[1:] / F[:-1])
    slope = (20 * np.log10(S[1:]) - 20 * np.log10(S[:-1])) / lo
    mid = np.sqrt(F[1:] * F[:-1])
    implied = 15.0 * slope
    actual = 0.5 * (DPHI[1:] + DPHI[:-1])
    print("       f " + " ".join(f"{v:6.0f}" for v in mid))
    print("   dB/oct" + " ".join(f"{v:+6.1f}" for v in slope))
    print("   implied" + " ".join(f"{v:+5.0f}" for v in implied))
    print("   needed " + " ".join(f"{v:+5.0f}" for v in actual))
    print("   EXCESS " + " ".join(f"{v:+5.0f}" for v in (actual - implied)))
    print()

    selftest()
    bode_ceiling()

    for kind in ("hp1", "hp2", "hp2_res", "shelf1", "shelf2", "hp1_ap1"):
        print(f"  === {LABEL[kind]}")
        for tag, obj in (("fit MAGNITUDE only", err_mag),
                         ("fit PHASE only", err_phase),
                         ("fit JOINT", err_joint)):
            p, _ = search(kind, obj)
            show(kind, p, tag)
        print()

    # ------------------------------------------------------------------
    # Named candidates.  The weighted searches above are pulled off this
    # family by the 20/25 Hz bands, which are the two least trustworthy in
    # the whole set for a reason the `rms` column cannot see: they sit at
    # the bottom edge of the capture (session 24 measured ref-clean itself
    # -1.3 dB at 25 Hz) and they are the bands A2d's c21R fix was about.
    # So evaluate this family explicitly rather than letting them veto it.
    # ------------------------------------------------------------------
    print("  === NAMED CANDIDATE: coincident 2nd-order highpass, k.(s/(s+w))^2")
    print("      (the one family that can meet the 40 Hz depth bound at all)")
    for fc in (45.0, 52.0, 59.0, 70.0, 85.0):
        show("hp2", (1.10, fc, fc), f"fc={fc:g} Hz, k=1.10")
    print()

    print("  === VERDICT")
    print("  MINIMUM-PHASE IS NOT RULED OUT, and this probe cannot rule it out.")
    print("  The ceiling above is decided almost entirely by the sub-20 Hz magnitude")
    print("  slope, which NO capture in the matrix measures -- flat tails understate a")
    print("  real highpass by 36-91 deg at 20-40 Hz (see SELF-TEST), which is the whole")
    print("  size of the apparent shortfall.  Declare a 12 dB/oct tail on the repaired")
    print("  curve and the 40 Hz shortfall goes -37 -> +1 deg.  Corroboration from the")
    print("  other direction: the explicit coincident-HP candidates at fc = 70-85 Hz")
    print("  CLEAR the 40 Hz depth bound (+8.5 / +17.6), which a genuine ceiling could")
    print("  never permit.  So do NOT conclude 'no passive network can do this'.")
    print()
    print("  What survives, and it is session 31 item 5 restated with numbers: the")
    print("  binding constraint is SHAPE, not attainable lead.  Every family above")
    print("  fits magnitude OR phase and misses the other, and the coincident HP that")
    print("  clears 40 Hz is 20-45 deg short at 64-80 Hz while running 8-16 dB hot at")
    print("  20-25 Hz.  The requirement is a HUMP; one corner frequency cannot place")
    print("  it.  Next lever is a pole+zero (lead network) shape, gated on the null.")
    print()


if __name__ == "__main__":
    main()
