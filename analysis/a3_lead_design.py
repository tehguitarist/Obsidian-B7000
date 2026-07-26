#!/usr/bin/env python3.11
"""a3_lead_design -- Phase 9 / A3 step 2 (session 33): design the missing OD-path
element against a CORRECTED target, and test whether one can exist at all.

⚠ READ THIS FIRST (session 34). The narrative below is session 33's and describes
the model AS IT WAS THEN. Since then `trebleC7` (C7 100n -> 680p) fixed the
drive-axis magnitude defect, and that changes two of the conclusions stated below:

  * "the requirement is a broad PLATEAU of +115..+136 deg out to 254 Hz, so a
    lead network's shape no longer follows" was an artefact OF THE BROKEN DRIVE
    AXIS, not of the sign fix. Re-measured on the fixed model the residual
    requirement is +30..+36 deg at 40-127 Hz falling to ~0 by 160-254 and going
    NEGATIVE at 20-25 -- a bump that returns to zero at both ends, i.e. a
    lead-network shape after all. The SIGN CORRECTION ITSELF STILL STANDS.
  * "the target is not designable at all (40-101 Hz drive-fit residual 2-5 dB at
    every beta)" is fixed: it is now 0.1-0.5 dB, and beta is sharply identified
    at ~ -16.5..-17.0 instead of being flat across the scan.

Every VERDICT this tool prints is now computed from the live scan rather than
asserted in a string -- because these two paragraphs are exactly the failure mode
(a conclusion narrated in prose outlives the condition it described). Run it with
--csv-prefix pointing at the candidate's CSVs and believe the printed numbers,
not the prose. See docs/phase9-validation.md §4 "A3 step 3a".

WHY THIS FILE EXISTS: THE TARGET WAS WRONG ABOVE ~90 Hz.
-------------------------------------------------------
`a3_phase_solve.py` part 3 printed `abs(theta_mdl)` (its solved `theta_ped` is a
magnitude, so the model column was made to match it) and differenced that. But
the MODEL's OD-vs-bleed phase is signed and CROSSES ZERO near 90 Hz:

    f      20    25    32    40    50    64    80   101   127   160   202   254
    mdl +104.2 +90.0 +73.3 +57.6 +41.5 +23.7  +8.0  -7.3 -20.7 -31.5 -37.9 -37.6

so |mdl| understates the extra phase an added element must supply by 2|mdl| --
15 deg at 101 Hz, rising to 76 deg at 202-254. Sessions 31 and 32 both read the
requirement off that column. The consequences are not cosmetic:

  * "the deficit is a HUMP falling to ~50 deg at 202-254" is an ARTEFACT. The
    corrected requirement is a broad PLATEAU: ~+44 deg at 20 Hz, +107 at 32,
    and +115..+136 continuously from 64 Hz to 254 Hz.
  * so "a pole+zero / lead network has the right shape" no longer follows -- a
    lead network's phase returns to zero, and this requirement does not.

Both sessions' NEGATIVE results survive unharmed (no existing stage can supply
the lead; the Bode ceiling was decided by its unmeasured tails). Only the shape
of what to build changes.

WHAT THIS TOOL DOES
-------------------
1. Rebuilds the target LIVE from a3_phase_solve (no transcribed constants -- the
   transcription is what went wrong), out to 806 Hz. The upper bands matter: the
   requirement is still +120 deg at 254 Hz, and whether that is realisable is
   decided by what |G| does ABOVE the band. Session 32's lesson was that an
   unmeasured tail decides the band edge, so this measures it.

2. Resolves the SIGN BRANCH rigorously instead of by assertion. The solve returns
   |theta_ped|, so +theta and -theta fit identically; continuity allows exactly
   two branches (the sign can only flip where |theta| touches 180, at 32-40 Hz):
       P: theta_ped stays POSITIVE          extra = theta_ped - theta_mdl
       M: theta_ped is its mirror image     extra = -theta_ped - theta_mdl
   Any causal H = (minimum-phase) x (all-pass), and an all-pass's phase is
   MONOTONICALLY NON-INCREASING in frequency. So excess = arg(H) - phi_minphase
   must be non-increasing. That is a decisive test, and it kills M outright.

3. Applies the SAME test to branch P, constructively: fit minimum-phase rational
   H(s) to |G| alone (min phase => the phase is then not ours to choose) and
   report how far the delivered phase falls short. Because non-minimum-phase can
   only SUBTRACT phase, a shortfall here cannot be recovered by any causal
   element -- which is the one direction the session-32 tail problem cannot
   reverse (tails move the ceiling; they do not change its sign convention).

Self-test: recover a known min-phase network from its own magnitude, and confirm
the all-pass monotonicity test flags a network built with a real RHP zero.

Usage:  python3.11 analysis/a3_lead_design.py [--sweep sweep_drv_-18]
Needs the same build/a3_dec_drv*.csv as a3_phase_solve (regenerate them after
changing a3_blend_decompose.cpp's band list).
"""
import argparse
import math
import os
import sys

import numpy as np
from scipy.optimize import minimize

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import a3_phase_solve as ps                                    # noqa: E402

# Bands where the OD actually competes with the bleed (mu >= ~1), so the drive
# sweep genuinely determines (s, theta). Above 254 Hz mu falls to 0.4-0.8 and the
# total is bleed-dominated: s and theta trade off and the fit stops being sharp.
# 320 Hz is excluded outright -- it is the TrebleAttack notch band, a KNOWN
# separate gap (GAP #2, session 20: the dip is real in the captures and the
# plugin does not reproduce it), and it shows up here as a lone outlier.
CORE_HI = 254
EXCLUDE = {320}


# ---------------------------------------------------------------------------
# candidate transfer functions -- all strictly minimum phase (LHP zeros+poles)
# ---------------------------------------------------------------------------
def _sec(s, spec):
    """One section. spec frequencies are in Hz; s is in rad/s."""
    if spec[0] == "r":
        return s + 2 * math.pi * spec[1]
    w, q = 2 * math.pi * spec[1], spec[2]
    return s * s + (w / q) * s + w * w


def response(f, k, zeros, poles):
    s = 2j * math.pi * np.asarray(f, dtype=float)
    h = np.full(s.shape, complex(k))
    for z in zeros:
        h = h * _sec(s, z)
    for p in poles:
        h = h / _sec(s, p)
    return h


def _pack(zeros, poles):
    v = []
    for spec in list(zeros) + list(poles):
        v.append(math.log(spec[1]))
        if spec[0] == "c":
            v.append(math.log(spec[2]))
    return np.array(v)


def _unpack(v, kinds):
    """Clamped so the optimiser cannot walk a corner frequency to 0 or overflow.
    The bounds are wide (0.1 Hz - 100 kHz, Q 0.05-20) but they are real: an
    unclamped search parks a pole at DC, which fits the band and means nothing.
    """
    out, i = [], 0
    for kind in kinds:
        f = math.exp(min(max(v[i], math.log(0.1)), math.log(1e5))); i += 1
        if kind == "r":
            out.append(("r", f))
        else:
            q = math.exp(min(max(v[i], math.log(0.05)), math.log(20.0))); i += 1
            out.append(("c", f, q))
    return out, i


# ---------------------------------------------------------------------------
# minimum-phase reference phase, by the Bode integral (used only for the
# all-pass monotonicity test, where a shared bias cancels along the curve)
# ---------------------------------------------------------------------------
def min_phase(f_at, F, mag, lf_slope_db_oct, hf_slope_db_oct, npts=40001):
    """Bode gain-phase reconstruction. Tail slopes are REQUIRED (session 32)."""
    lo, hi = math.log(2 * math.pi * 0.002), math.log(2 * math.pi * 4.0e6)
    u = np.linspace(lo, hi, npts)
    w = np.exp(u)
    fr = w / (2 * math.pi)
    lg = np.interp(fr, F, np.log(mag))
    c = math.log(10.0) / 20.0
    lo_m, hi_m = fr < F[0], fr > F[-1]
    lg[lo_m] = math.log(mag[0]) + lf_slope_db_oct * c * np.log2(fr[lo_m] / F[0])
    lg[hi_m] = math.log(mag[-1]) + hf_slope_db_oct * c * np.log2(fr[hi_m] / F[-1])
    dl = np.gradient(lg, u)
    out = []
    for f0 in np.atleast_1d(f_at):
        ker = np.log(np.abs(1.0 / np.tanh(np.abs(u - math.log(2 * math.pi * f0)) / 2.0)) + 1e-300)
        out.append(math.degrees(np.trapz(dl * ker, u) / math.pi))
    return np.array(out)


# ---------------------------------------------------------------------------
def fit(F, target_db, target_ph, w, kinds_z, kinds_p, mode, ntry=24, seed=7):
    """Fit a minimum-phase rational to the target.

    mode 'mag'   : magnitude only -- the phase is then DETERMINED, which is the
                   whole point (a passive network does not get to pick both).
    mode 'joint' : 1 dB of magnitude ~ 10 deg of phase.
    """
    rng = np.random.default_rng(seed)

    def cost(v):
        zn, i = _unpack(v[:], kinds_z)
        pn, _ = _unpack(v[i:], kinds_p)
        try:
            h = response(F, 1.0, zn, pn)
        except FloatingPointError:
            return 1e9
        a = np.abs(h)
        if not np.all(np.isfinite(a)) or np.any(a <= 0):
            return 1e9
        # optimal scalar gain in dB, in closed form
        d = target_db - 20 * np.log10(a)
        kdb = float(np.sum(w * d) / np.sum(w))
        em = d - kdb
        ep = np.degrees(np.angle(h)) - target_ph
        if mode == "mag":
            return float(np.sum(w * em * em))
        return float(np.sum(w * (em * em + (ep / 10.0) ** 2)))

    best = (float("inf"), None)
    nz, npar = len(kinds_z), len(kinds_p)
    for _ in range(ntry):
        v0 = []
        for kind in list(kinds_z) + list(kinds_p):
            v0.append(math.log(10 ** rng.uniform(1.0, 3.0)))
            if kind == "c":
                v0.append(math.log(10 ** rng.uniform(-0.4, 0.5)))
        r = minimize(cost, np.array(v0), method="Nelder-Mead",
                     options=dict(maxiter=20000, maxfev=20000, xatol=1e-6, fatol=1e-9))
        if r.fun < best[0]:
            best = (r.fun, r.x)
    zn, i = _unpack(best[1], kinds_z)
    pn, _ = _unpack(best[1][i:], kinds_p)
    h = response(F, 1.0, zn, pn)
    d = target_db - 20 * np.log10(np.abs(h))
    kdb = float(np.sum(w * d) / np.sum(w))
    return zn, pn, 10 ** (kdb / 20.0), (nz, npar)


def describe(zeros, poles, k):
    def one(spec):
        return ("f=%.1f" % spec[1] if spec[0] == "r"
                else "f=%.1f Q=%.2f" % (spec[1], spec[2]))
    return ("k=%.3g | zeros: %s | poles: %s"
            % (k, "; ".join(one(z) for z in zeros), "; ".join(one(p) for p in poles)))


# ---------------------------------------------------------------------------
def selftest():
    print("SELF-TEST")
    F = np.array([20, 25, 32, 40, 50, 64, 80, 101, 127, 160, 202, 254, 320, 403, 508, 640, 806],
                 dtype=float)
    w = np.ones_like(F)

    # (a) a known min-phase network must be recovered from its MAGNITUDE alone
    truth_z = [("c", 60.0, 0.8)]
    truth_p = [("c", 300.0, 0.9)]
    h = response(F, 1.0, truth_z, truth_p)
    tdb, tph = 20 * np.log10(np.abs(h)), np.degrees(np.angle(h))
    zn, pn, k, _ = fit(F, tdb, tph, w, ["c"], ["c"], "mag", ntry=12)
    got = np.degrees(np.angle(response(F, k, zn, pn)))
    e = float(np.max(np.abs(got - tph)))
    print("  (a) magnitude-only fit of a known min-phase net recovers its PHASE")
    print("      to %.2f deg  ->  %s" % (e, "OK" if e < 2.0 else "FAILED"))

    # (b) the all-pass monotonicity test. ⚠ It is NOT tail-free: min_phase needs
    #     the slopes outside the band, and this network's true asymptotes are FLAT
    #     at both ends (2 zeros, 2 poles). Declaring 12 dB/oct instead manufactures
    #     a +27 deg rise on a network that has none -- i.e. the test inherits
    #     exactly session 32's failure mode when the tails are guessed.
    s = 2j * math.pi * F
    ap = (2 * math.pi * 300.0 - s) / (2 * math.pi * 300.0 + s)
    # An all-pass makes the excess FALL, which is legal -- so the case that must be
    # flagged is its inverse, a network claiming MORE lead than its own magnitude
    # allows. That is precisely the shape of an unrealisable requirement.
    print("  (b) excess-phase monotonicity: a rise is impossible for a causal element")
    for tag, hh in (("min-phase", h), ("+ all-pass (legal)", h * ap),
                    ("+ INVERSE all-pass", h / ap)):
        for lf, hf in ((0.0, 0.0), (12.0, -12.0)):
            mp = min_phase(F, F, np.abs(hh), lf, hf)
            exc = np.unwrap(np.angle(hh)) * 180 / math.pi - mp
            rise = float(np.max(np.diff(exc - exc[0])))
            print("      %-22s tails %+5.0f/%+5.0f dB/oct   max rise %+7.1f deg  (%s)"
                  % (tag, lf, hf, rise, "flagged" if rise > 2.0 else "clean"))
    print("      -> with TRUE tails only the INVERSE all-pass is flagged (an all-pass")
    print("         itself makes the excess FALL, which is legal); with guessed tails")
    print("         everything is flagged. So the absolute test")
    print("         is only as good as the tails, and the branch comparison below is")
    print("         used instead: branch M minus branch P is 2.theta_ped, which does")
    print("         not involve min_phase at all and is therefore TAIL-FREE.")
    print()


# ---------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sweep", default="sweep_drv_-18")
    ap.add_argument("--csv-prefix", default="build/a3_dec_drv",
                    help="a3_blend_decompose CSV prefix (swap in a candidate render)")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()

    if args.selftest:
        selftest()
        return

    model = ps.load_model([d for d, _ in ps.DRIVES], args.csv_prefix)
    pedal = ps.load_pedal(args.sweep)
    beta = ps.fit_beta(pedal, model)
    res = ps.solve(pedal, model, beta)

    bands = [b for b in ps.PROBE_BANDS if b not in EXCLUDE]
    F = np.array(bands, dtype=float)
    mu = np.array([model[0.50][b][0] for b in bands])
    th_mdl = np.array([math.degrees(model[0.50][b][1]) for b in bands])
    th_ped = np.array([res[b]["theta"] for b in bands])
    lo = np.array([res[b]["lo"] for b in bands])
    hi = np.array([res[b]["hi"] for b in bands])
    s = np.array([res[b]["s"] for b in bands])
    rms = np.array([res[b]["rms"] for b in bands])

    gdb = 20 * np.log10(s)
    phiP = th_ped - th_mdl
    phiM = -th_ped - th_mdl

    print("A3 lead design -- the CORRECTED extra-transfer target, and whether any")
    print("causal element can supply it.   sweep=%s, pedal bleed beta=%+.2f dB\n" % (args.sweep, beta))
    print("1. THE TARGET.  G(f) = s . e^(i.extra) is what the model's OD path must be")
    print("   MULTIPLIED BY.  theta_mdl is SIGNED -- that is the correction.\n")
    print("%6s %6s %8s %9s %9s %8s %8s %8s %8s"
          % ("f", "mu", "|G| dB", "th_ped", "th_mdl", "extraP", "extraM", "rms", "band"))
    for i, b in enumerate(bands):
        note = "core" if b <= CORE_HI else "weak"
        print("%6d %6.2f %8.1f %9.1f %9.1f %8.1f %8.1f %8.2f %8s"
              % (b, mu[i], gdb[i], th_ped[i], th_mdl[i], phiP[i], phiM[i], rms[i], note))
    print("\n   'weak' = mu < ~1, so the total is bleed-dominated there and (s, theta)")
    print("   trade off; those bands anchor the magnitude TAIL, not the fit.")
    print("   320 Hz excluded: TrebleAttack-notch band, a known separate gap (GAP #2).")

    # ---- 2. branch -------------------------------------------------------
    print("\n\n2. WHICH SIGN BRANCH.  The solve returns |theta_ped|, so +theta and -theta")
    print("   fit identically; continuity permits only the two global branches below.")
    print("   TEST: any causal H = (minimum-phase) x (all-pass), and an all-pass's")
    print("   phase is MONOTONICALLY NON-INCREASING in f.  So")
    print("        excess(f) = arg(H) - phi_minphase(f)")
    print("   must be non-increasing.  A rising excess is impossible for ANY causal")
    print("   LTI element, whatever its order.\n")
    mp = min_phase(F, F, s, 12.0, 0.0)
    print("%6s %10s %12s %12s" % ("f", "phi_minph", "excess P", "excess M"))
    excP = phiP - mp
    excM = np.unwrap(np.radians(phiM)) * 180 / math.pi - mp
    for i, b in enumerate(bands):
        print("%6d %10.1f %12.1f %12.1f" % (b, mp[i], excP[i] - excP[0], excM[i] - excM[0]))
    print("\n   branch M rises by %+.0f deg end to end -> IMPOSSIBLE for any causal element."
          % (excM[-1] - excM[0]))
    print("   branch P rises by %+.0f deg end to end." % (excP[-1] - excP[0]))
    print("   => work in branch P (theta_ped positive throughout).")

    # ---- 3. constructive ceiling ----------------------------------------
    core = np.array([b <= CORE_HI for b in bands])
    w = (1.0 / (1.0 + rms)) * np.where(core, 1.0, 0.15)
    w = w / w.sum()

    print("\n\n3. CONSTRUCTIVE CEILING.  Fit a MINIMUM-PHASE rational to |G| ALONE; its")
    print("   phase is then not ours to choose.  Non-minimum-phase content can only")
    print("   SUBTRACT phase, so any shortfall here cannot be recovered by any causal")
    print("   element -- unlike a Bode integral, this needs no tail assumption.\n")
    families = [
        ("1 zero / 1 pole  (lead network)", ["r"], ["r"]),
        ("2 zeros / 2 poles, real", ["r", "r"], ["r", "r"]),
        ("2 zeros / 2 poles, complex pairs", ["c"], ["c"]),
        ("3 zeros / 3 poles", ["c", "r"], ["c", "r"]),
        ("4 zeros / 4 poles", ["c", "c"], ["c", "c"]),
    ]
    for label, kz, kp in families:
        zn, pn, k, _ = fit(F, gdb, phiP, w, kz, kp, "mag")
        h = response(F, k, zn, pn)
        em = 20 * np.log10(np.abs(h)) - gdb
        ep = np.degrees(np.angle(h)) - phiP
        # shortfall against the WEAKEST end of each band's confidence interval
        need_lo = lo - th_mdl
        slack = np.degrees(np.angle(h)) - need_lo
        print("  === %s" % label)
        print("      %s" % describe(zn, pn, k))
        print("      mag err dB : " + " ".join("%+6.1f" % v for v in em))
        print("      phase short: " + " ".join("%+6.0f" % v for v in ep))
        print("      vs interval: " + " ".join("%+6.0f" % v for v in slack)
              + "   (negative = below even the LOOSEST theta that fits)")
        cm = core & (rms < 2.0)
        print("      core bands, trustworthy fit only: mean phase shortfall %+.0f deg\n"
              % np.mean(ep[cm]))

    print("  (A 'joint' fit is not shown: it can only buy phase by abandoning the")
    print("   magnitude, and the magnitude is the half the captures pin hardest.)")

    # ---- 4. beta is not a nuisance: causality identifies it ----------------
    print("\n\n4. IDENTIFYING THE BLEED LEVEL FROM CAUSALITY.")
    print("   The solve fits (s, theta) per band at a GIVEN beta, and beta is the")
    print("   parameter session 31 left unresolved at +/-2 dB. It is not innocent:")
    print("   raising beta by 2.6 dB moves the required extra phase at 254 Hz from")
    print("   +38 to +120 deg. So beta and the missing element are COUPLED and cannot")
    print("   be settled one at a time -- which is why 'fit the phase first, the level")
    print("   later' has no fixed point.")
    print("   But magnitude and phase are not independent for a causal element, and")
    print("   THAT is an equation the levels alone do not provide. Scan beta; at each")
    print("   one fit a minimum-phase rational to |G| and ask how far its phase falls")
    print("   short. The beta where a causal element can actually do the job is the")
    print("   physically admissible one.\n")
    def target_at(b):
        r2 = {}
        for bb in bands:
            mu_d = [model[d][bb][0] for d, _ in ps.DRIVES]
            best, _ = ps.fit_band(pedal[bb], mu_d, b, n_theta=721, n_s=1601)
            r2[bb] = (math.degrees(best[0]), math.sqrt(best[1]), best[2])
        gd = np.array([20 * math.log10(max(r2[bb][2], 1e-6)) for bb in bands])
        ph = np.array([r2[bb][0] for bb in bands]) - th_mdl
        rm = np.array([r2[bb][1] for bb in bands])
        return gd, ph, rm

    # ⚠ The verdict band set is FIXED. A first version scored each beta on
    # "core bands whose drive fit is trustworthy (rms < 2)", which is
    # self-selecting: as beta falls the drive fit degrades, bands drop OUT of the
    # scoring set, and the score improves because it is being computed on fewer,
    # easier bands. beta = -21 scored best that way on 4 bands while fitting the
    # drive sweep worse at all 12.
    VERDICT = core.copy()

    def score(b, ntry=16):
        gd, ph, rm = target_at(b)
        ww = (1.0 / (1.0 + rm)) * np.where(core, 1.0, 0.15)
        ww = ww / ww.sum()
        zn, pn, kk, _ = fit(F, gd, ph, ww, ["c", "r"], ["c", "r"], "mag", ntry=ntry)
        hh = response(F, kk, zn, pn)
        em = 20 * np.log10(np.abs(hh)) - gd
        ep = np.degrees(np.angle(hh)) - ph
        # Bands where the solved theta rests on the grid edge (0 or 180) are solver
        # FAILURES, not measurements -- at 50 Hz theta collapses to 0 with a 4 dB
        # residual and, left in, it drives the fit to a Q=10 notch. Score on RMS,
        # not the mean: a mean near zero can hide +80/-50 band-by-band.
        th_p = ph + th_mdl
        edge = (th_p < 1.0) | (th_p > 179.0)
        use = VERDICT & ~edge
        return dict(beta=b, gd=gd, ph=ph, rms=rm, z=zn, p=pn, k=kk, em=em, ep=ep, cm=use,
                    magrms=float(np.sqrt(np.mean(em[use] ** 2))),
                    drive=float(np.mean(rm[VERDICT])), nedge=int(np.sum(VERDICT & edge)),
                    rmsshort=float(np.sqrt(np.mean(ep[use] ** 2))),
                    mean=float(np.mean(ep[use])), worst=float(np.min(ep[use])),
                    slope=(gd[bands.index(160)] - gd[bands.index(32)]) / math.log2(160 / 32))

    print("%8s %9s %6s %9s %9s %9s %9s %8s"
          % ("beta dB", "driveRMS", "edge", "magRMS", "shortRMS", "mean", "worst", "slope"))
    scan = []
    for k in range(-215, -139, 5):
        r = score(k / 10.0, ntry=12)
        scan.append(r)
        print("%8.1f %9.2f %6d %9.2f %9.0f %9.0f %9.0f %8.1f"
              % (r["beta"], r["drive"], r["nedge"], r["magrms"], r["rmsshort"],
                 r["mean"], r["worst"], r["slope"]))
    print("\n   driveRMS = how well that beta explains the 5-point DRIVE SWEEP at all")
    print("              12 core bands (the evidence that identifies s and theta).")
    print("   edge     = how many of those 12 had theta pin at 0 or 180, i.e. a")
    print("              DEGENERATE solve; those are excluded from the columns right")
    print("              of it, so a low beta is scored on fewer real measurements.")
    print("   mean/worst/shortRMS = how far a minimum-phase element falls short of the")
    print("              lead the captures demand. Negative is impossible for ANY causal")
    print("              element -- non-minimum-phase content only subtracts phase.")
    # ⚠ COMPUTED, never narrated. Session 33 hard-coded "driveRMS is minimised near
    # beta = -15.5, causality wants <= -18.5, they pull opposite ways, and shortRMS
    # never falls below ~28 deg ANYWHERE". After trebleC7 shipped, all three numbers
    # were wrong (the two criteria now agree to within ~1 dB) and the sentence sat
    # above a table contradicting it -- the third time this file has done exactly
    # what its own docstring warns about. Derive it from `scan` or do not print it.
    b_drive = min(scan, key=lambda r: r["drive"])
    b_caus = min(scan, key=lambda r: abs(r["mean"]))
    b_short = min(scan, key=lambda r: r["rmsshort"])
    gap = abs(b_drive["beta"] - b_caus["beta"])
    print("\n   THE TWO CRITERIA, LOCATED FROM THE SCAN ITSELF:")
    print("   driveRMS (how well beta explains the 5-point drive sweep) is minimised at")
    print("   beta = %+.1f (%.2f dB); causality (mean phase shortfall -> 0) lands at"
          % (b_drive["beta"], b_drive["drive"]))
    print("   beta = %+.1f. They disagree by %.1f dB." % (b_caus["beta"], gap))
    if gap <= 1.5:
        print("   => that is AGREEMENT within the scan's own resolution. The 3 dB standoff")
        print("   session 33 recorded (least-squares -15.5 vs causality <= -18.5) has")
        print("   CLOSED; beta is now identified, not merely bounded.")
    else:
        print("   => still a genuine standoff; beta is bounded, not identified. Do not")
        print("   pick one criterion and call it measured.")
    print("   Best shortRMS anywhere in the scan: %.0f deg (at beta = %+.1f)."
          % (b_short["rmsshort"], b_short["beta"]))
    if b_short["rmsshort"] > 25.0:
        print("   No beta makes the requirement cleanly realisable by a min-phase element.")
    else:
        print("   ⚠ Read this per band, not as a scalar: a mean/RMS near zero can still")
        print("   hide +40/-30 band by band. Part 5's table is the one to judge on.")

    # driveRMS is deliberately NOT a filter: it sits at 1.8-2.6 dB at EVERY beta
    # because the model's mu_d is non-monotone on the drive axis and the pedal's
    # is not (session 31 item 6). Its variation across the whole beta range is
    # 0.8 dB on a ~2 dB floor, so it discriminates beta only weakly -- which is
    # why the session-31 least-squares landing at -15.4 is not strong evidence.
    print("\n   PER-BAND DRIVE-FIT RESIDUAL vs beta -- whether the target is designable")
    print("   at all. The bands that carry the null (40-101 Hz) are the ones to read:\n")
    print("      %8s %s" % ("beta", "".join("%6d" % b for b in bands if b <= CORE_HI)))
    for r in scan[::3]:
        print("      %8.1f %s" % (r["beta"], "".join(
            "%6.1f" % r["rms"][i] for i, b in enumerate(bands) if b <= CORE_HI)))

    # ⚠ This verdict is COMPUTED, never asserted. Session 33 shipped a hard-coded
    # "40-101 Hz sits at 2-5 dB regardless of beta" here; once the drive axis was
    # fixed (session 34, trebleC7) the same sentence sat directly above a printed
    # table of 0.2 dB. A conclusion narrated in a string outlives the condition it
    # described -- the same class of error as the transcribed target this whole
    # file exists to correct. Derive it from `scan` or do not print it.
    nullIdx = [i for i, b in enumerate(bands) if 40 <= b <= 101]
    worst_over_beta = min(max(r["rms"][i] for i in nullIdx) for r in scan)
    best_row = min(scan, key=lambda r: max(r["rms"][i] for i in nullIdx))
    print("\n   Best achievable 40-101 Hz drive-fit residual over the whole beta scan:")
    print("   %.1f dB (at beta = %+.1f)." % (worst_over_beta, best_row["beta"]))
    if worst_over_beta > 1.5:
        print("   ⛔ The (s, theta) solve there is fitting against the model's own mu_d,")
        print("   which is wrong on the drive axis (session 31 item 6): mu_d PEAKS at")
        print("   drive 2:30 and falls by max, while the pedal's grows straight through")
        print("   the null. The phase target inherits that error exactly where A3 lives,")
        print("   so DO NOT design against it yet -- fix the drive axis first.")
    else:
        print("   ✅ Below 1.5 dB, so the drive-axis defect that made this target")
        print("   untrustworthy (session 33 item 5) is no longer binding and the phase")
        print("   target below IS worth designing against. Note beta is now sharply")
        print("   identified by this scan -- it was flat to within 0.8 dB before.")

    ok = [r for r in scan if abs(r["mean"]) < 15.0 and r["magrms"] < 1.5]
    if not ok:
        print("\n   NO beta in this range admits a causal element. The two-path model")
        print("   itself, not its bleed level, is what needs revisiting.")
        return
    bleed_model = model[0.50][40][2]
    best = min(ok, key=lambda r: abs(r["mean"]))
    print("\n   beta with the mean shortfall within 15 deg of 0: %s"
          % ", ".join("%.1f" % r["beta"] for r in ok))
    print("   Model bleed is %+.2f dB, so causality leans toward the model's bleed being"
          % bleed_model)
    print("   ~%.1f dB %s than the pedal's -- the SIGN session 29 measured directly from"
          % (abs(best["beta"] - bleed_model), "HIGHER" if best["beta"] < bleed_model else "LOWER"))
    print("   the drive-min LF total (-17.4..-18.3 dB), and the OPPOSITE of the session-31")
    print("   least-squares (-15.2). Do not promote this to a measurement: it leans on")
    print("   bands whose theta is pinned at 180, and driveRMS moves only 1.84 -> 2.10 dB")
    print("   across the whole range, so the least-squares was never strong evidence")
    print("   either. What is settled is that the bleed level is STILL open, and that it")
    print("   cannot be settled after the phase, because the phase target depends on it.\n")

    best = score(best["beta"], ntry=40)
    print("5. BEST-CASE ELEMENT at beta = %+.1f dB -- shown to be READ, not built.\n"
          % best["beta"])
    print("   %s" % describe(best["z"], best["p"], best["k"]))
    print("   %6s %9s %9s %9s %9s %8s" % ("f", "|G| req", "|H| dB", "phi req", "phi H", "rms"))
    hh = response(F, best["k"], best["z"], best["p"])
    for i, b in enumerate(bands):
        print("   %6d %9.1f %9.1f %9.1f %9.1f %8.2f"
              % (b, best["gd"][i], 20 * math.log10(abs(hh[i])),
                 best["ph"][i], math.degrees(np.angle(hh[i])), best["rms"][i]))
    # Same rule as above: the verdict is computed from what was just fitted.
    short = max(abs(best["ph"][i] - math.degrees(np.angle(hh[i])))
                for i, b in enumerate(bands) if b <= CORE_HI)
    if worst_over_beta > 1.5:
        print("\n   ⛔ DO NOT BUILD THIS. It is the best a causal element can do against")
        print("   a target that is itself unreliable at 40-101 Hz (best drive-fit")
        print("   residual %.1f dB), and it still misses individual bands by up to" % worst_over_beta)
        print("   %.0f deg. Fix the drive-axis magnitude defect first -- see the" % short)
        print("   session-33/34 entries in docs/phase9-validation.md.")
    else:
        print("\n   The target is now trustworthy (drive-fit residual %.1f dB), and this"
              % worst_over_beta)
        print("   element is the best causal fit to it: worst per-band phase shortfall")
        print("   %.0f deg. Judge it on the NULL (a3_drive_axis.py + the migrating null)," % short)
        print("   never on band-RMS, and re-fit beta jointly with it -- never after.")


if __name__ == "__main__":
    main()
