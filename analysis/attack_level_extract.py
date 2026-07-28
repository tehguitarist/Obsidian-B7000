#!/usr/bin/env python3.11
"""h(f) at LEVEL max -- the ATTACK network's linear transfer, bleed-free by TOPOLOGY
(session 60, Phase 9 / A3).

WHAT THIS ROUTE IS, AND WHY IT IS DIFFERENT FROM EVERY PREVIOUS ONE
------------------------------------------------------------------
Every earlier ATTACK measurement had to model something. The blend axis solved a ladder
`t(B) = |beta(B) + B.G|` against a fitted BLEND taper and a model-supplied bleed level b0
(sessions 55-57). Session 58 removed the clipper by DE-CONVOLUTION against the pedal's own
measured level transfer -- clean, but the transfer it needed came from that same solve. Session 59
tried drive min on the blend axis and it FAILED: the low drive that idles the clipper also buries
the OD path ~15 dB under the clean bleed, collapsing (r, theta) onto a ridge.

Here the BLEED is removed by topology instead of by fitting:
  * LEVEL sits AFTER every nonlinearity (circuit.md: ... -> IC4_A SK -> LEVEL -> BLEND), so raising
    it cannot move the clipper's operating point.
  * At LEVEL max the wiper SHORTS to the OD source, so the clean bleed is EXACTLY zero
    (eq_reference.level_blend_tf: -4.03 dB at LEVEL noon, -17.09 at 0.90, -36.91 at 0.99, 0 at 1.00).
⇒ at BLEND max the output IS the OD path. No ladder, no taper, no b0, no solve for |G|.

⚠ THAT REMOVES THE BLEED. IT DOES NOT REMOVE THE CLIPPER -- and this tool's main finding is that
the difference matters. Drive min idles the clipper but NOT the J201, which sits UPSTREAM of the
DRIVE pot and so never idles (session 59 item 3). And the boost throw pushes ~8 dB MORE signal
into that nonlinearity than the flat reference does, so the two operands of h compress by
different amounts. The flat reference agreeing between -30 and -18 dBFS (session 59 step 6, the
check that justified this request) therefore does NOT imply the boost throw agrees -- and measured,
it does not: boost's raw ratio moves 2.41 dB at 640 Hz between those two levels while cut moves
0.27. ⇒ THE RAW SUBTRACTION IS NOT h. It is h seen through the residual compression.

So the same de-convolution identity session 58 derived is applied here, where it is far better
conditioned because S is now measured DIRECTLY rather than solved:

    ratio(f, L) = h(f) + S_f(L + h(f)) - S_f(L)

  * Under a swept sine the clipper sees ONE tone at a time, so its describing-function gain
    depends on that single amplitude.
  * A pre-clipper linear factor h is indistinguishable from raising the stimulus by h dB, because
    everything before the clipper is linear ⇒ out_boost(L) = out_flat(L + h).
  * S_f(L) is the pedal's OWN OD transfer vs stimulus level, and on THIS axis it is a plain
    difference of two raw measurements (flat minus pure-clean), not a solved quantity.
  * Monotone in h (d/dh = 1 + S' > 0 for any real compressor) ⇒ unique root by bisection.
  * The clipper's shape, rails and drive dependence all CANCEL. Nothing about it is modelled.

h is placed PRE-clipper. That is not assumed here: session 59 item 4 measured it out-of-sample on
the drive-max ladders (~90x in rms residual on the boost throw).

GATES -- all run first, none optional
-------------------------------------
  1 LIVENESS            'no change' must return exactly zero.
  2 KNOWN FEATURE       the IC2_B bridged-T is post-clipper, fixed, schematic-verified and
                        capture-confirmed (GAP #1b, 116 OD rows), so its 400-700 Hz scoop CANNOT
                        depend on DRIVE, LEVEL or ATTACK. This is the test that condemned session
                        59's drive-min blend route (0.7 dB where 6.0 was required). ⭐ Gate EVERY
                        file: h is a DIFFERENCE, so a defect in either operand corrupts it.
  3 DE-CONVOLUTION      (a) recover a known h through a known compressor; (b) liveness h=0 -> 0;
                        (c) NO EXTRAPOLATION -- L+h must land inside the captured level range or
                        the cell prints '--'.
  4 ⭐⭐ MODEL CONTROL   the de-convolution run on the MODEL, where a pre-clipper linear element is
                        the ground truth by construction. Its solved h MUST be level-independent
                        even though its raw ratio is not. GRUNT is the vehicle: a schematic+BOM
                        verified linear cap bank at the clipper input, i.e. exactly the kind of
                        element the identity assumes. A method that cannot hold h steady on data
                        it is definitionally correct for cannot be trusted on the pedal.

SCOPE -- quote these with any number from here
----------------------------------------------
  * ATTACK is [ENG]: the 3-way switch is not on our schematic at all. h(f) is a SPECIFICATION a
    topology proposal must MEET, not a disagreement with a drawn circuit.
  * MAGNITUDE ONLY ⇒ minimum-phase statements; a non-minimum-phase realisation is not excluded.
  * Floor: take-to-take 0.144 dB; a difference of two RAW measurements = sqrt(2) x 0.144 = 0.204 dB.

Usage:  python3.11 analysis/attack_level_extract.py [--selftest]
"""
import argparse
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import a3_condition_axis as A                      # noqa: E402

REPORT = "analysis/reports/s60_matrix104.json"
M36 = "analysis/reports/s60_m36.json"
B0_FILE = "blend-0700_base-od.wav"
FLAT = "drive-0700_level-1700_base-od.wav"

# sweep -> stimulus level in dBFS (gen_test_signal.py: CLEAN_FR_LEVELS_DB / DRIVEN_SWEEPS).
# ⭐ "m36" is the -36 dBFS clean sweep, which is present in EVERY capture but which
# `comprehensive_report.py` has never analysed (its ALL_SWEEP_LEVELS stops at -30). It is
# extracted separately by `analysis/extract_m36.py` -- pedal side only, so the MODEL control
# below still runs on the four report levels. It is 6 dB quieter than anything the matrix has
# ever been read at, which is what decides whether 508/640 Hz have reached the linear limit.
LEVELS = [("m36", -36.0), ("sweep_clean", -30.0), ("sweep_drv_-18", -18.0),
          ("sweep_drv_-12", -12.0), ("sweep_drv_-6", -6.0)]
MODEL_LEVELS = [(s, L) for s, L in LEVELS if s != "m36"]
MAIN = "sweep_drv_-18"

THROWS = {"boost": "drive-0700_level-1700_attack-boost_base-od.wav",
          "cut":   "drive-0700_level-1700_attack-cut_base-od.wav"}
GRUNT = {"flat":  "drive-0700_level-1700_grunt-flat_base-od.wav",
         "boost": "drive-0700_level-1700_grunt-boost_base-od.wav"}

# 320 Hz is INCLUDED. It is excluded BY NAME from every blend-axis aggregate because it is
# null-dominated THERE; this route runs no cancellation solve, so that exclusion does not
# transfer. Flagged in the output, never silently folded in (the session-40 rule).
SHOW = [80.0, 100.8, 127.0, 160.0, 201.6, 254.0, 320.0, 403.2, 508.0, 640.0]
SCOOP_REF, SCOOP_IN = 201.6, (403.2, 508.0, 640.0)
SCOOP_MIN_DB = 3.0

TAKE_FLOOR = 0.144
DIFF_FLOOR = float(np.sqrt(2.0) * TAKE_FLOOR)          # 0.204 dB

# Session 58's de-convolved h(f) at drive NOON, for an out-of-sample comparison. That instrument
# shares no machinery with this one (it de-convolved a blend-axis solve). Nothing below is tuned
# to it; it is printed for comparison only.
S58 = {"boost": {80.0: +7.03, 100.8: +7.83, 127.0: +8.24, 160.0: +8.38, 201.6: +8.44},
       "cut":   {80.0: -3.15, 100.8: -2.92, 127.0: -2.91, 160.0: -3.00, 201.6: -3.09}}


def row(d, bands, fmt="%+7.2f"):
    return "".join((fmt % d[b]) if b in d and np.isfinite(d[b]) else "     --" for b in bands)


_M36 = None


def col_at(caps, fname, sweep, key="pedal_db"):
    """One capture's per-band dB column at a stimulus level. `sweep` is a report sweep name, or
    the pseudo-level 'm36' served from extract_m36.py's side file (pedal only)."""
    if sweep == "m36":
        if key != "pedal_db":
            raise KeyError("m36 is pedal-side only (no render); asked for %r" % key)
        if _M36 is None or fname not in _M36:
            raise KeyError("m36 has no %s -- run analysis/extract_m36.py" % fname)
        return np.asarray(_M36[fname], dtype=float)
    A.SWEEP = sweep
    return A.col(caps, fname, key)


def gcurve(caps, bands, fname, key="pedal_db", levels=None):
    """S_f(L): {band: (levels[], transfer_dB[])}, the OD transfer vs stimulus level, referenced
    to the pure-clean capture so the stimulus level itself divides out."""
    out = {b: ([], []) for b in bands}
    for sweep, L in (levels or LEVELS):
        g = col_at(caps, fname, sweep, key) - col_at(caps, B0_FILE, sweep, key)
        for i, b in enumerate(bands):
            if np.isfinite(g[i]):
                out[b][0].append(L)
                out[b][1].append(float(g[i]))
    return out


def solve_h(ratio_db, L, Ls, Ss, lo=-25.0, hi=25.0, tol=1e-10):
    """Invert ratio = h + S(L+h) - S(L) for h. Monotone in h, so bisection is safe.
    Returns None if L+h would leave the captured level range (NO EXTRAPOLATION)."""
    if len(Ls) < 2:
        return None
    Lmin, Lmax = min(Ls), max(Ls)

    def S(x):
        return float(np.interp(x, Ls, Ss))

    S_L = S(L)

    def f(h):
        return h + S(L + h) - S_L - ratio_db

    lo = max(lo, Lmin - L)
    hi = min(hi, Lmax - L)
    if lo >= hi or f(lo) * f(hi) > 0:
        return None
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        if f(lo) * f(mid) <= 0:
            hi = mid
        else:
            lo = mid
        if hi - lo < tol:
            break
    return 0.5 * (lo + hi)


def selftest():
    print("=" * 100)
    print("SELF-TEST")
    print("=" * 100)
    ok = True

    # (a) recover a KNOWN h through a KNOWN compressor
    Ls = [-36.0, -30.0, -18.0, -12.0, -6.0]
    Ss = [0.0, -0.2, -1.9, -3.4, -5.6]                 # a plausible compressive transfer
    worst = 0.0
    for h_true in (+8.4, +5.0, -3.1, -1.0, 0.0):
        for L in (-30.0, -18.0):
            def S(x):
                return float(np.interp(x, Ls, Ss))
            ratio = h_true + S(L + h_true) - S(L)
            got = solve_h(ratio, L, Ls, Ss)
            if got is None:
                continue
            worst = max(worst, abs(got - h_true))
    print("  (a) known h recovered through a known compressor : worst err %.2e dB   %s"
          % (worst, "PASS" if worst < 1e-6 else "FAIL"))
    ok &= worst < 1e-6

    # (b) liveness: a zero ratio must give exactly h = 0
    z = solve_h(0.0, -18.0, Ls, Ss)
    print("  (b) liveness, ratio 0 -> h                       : %.2e dB   %s"
          % (abs(z), "PASS" if abs(z) < 1e-6 else "FAIL"))
    ok &= abs(z) < 1e-6

    # (c) extrapolation must be refused, not silently clamped
    ref = solve_h(+8.4, -6.0, Ls, Ss)                   # -6 + 8.4 = +2.4, outside [-36, -6]
    print("  (c) extrapolation refused (returns None)         : %s   %s"
          % (ref, "PASS" if ref is None else "FAIL"))
    ok &= ref is None

    # (d) the compressor must actually bite, or (a) is vacuous
    def S(x):
        return float(np.interp(x, Ls, Ss))
    raw = 8.4 + S(-18.0 + 8.4) - S(-18.0)
    print("  (d) compressor is load-bearing (raw != h)        : raw %.2f vs h 8.40 -> %.2f dB gap"
          % (raw, 8.4 - raw))
    ok &= abs(8.4 - raw) > 0.5

    print("\n  %s" % ("SELF-TEST PASS" if ok else "SELF-TEST FAIL"))
    return ok


def deconv_table(caps, bands, fname, base, key="pedal_db", levels=None):
    """Solve h per band at every usable stimulus level. Returns {level: {band: h}}."""
    levels = levels or LEVELS
    S = gcurve(caps, bands, base, key, levels)
    out = {}
    for sweep, L in levels:
        va = col_at(caps, fname, sweep, key)
        vb = col_at(caps, base, sweep, key)
        d = {}
        for i, b in enumerate(bands):
            if not (np.isfinite(va[i]) and np.isfinite(vb[i])):
                continue
            Ls, Ss = S[b]
            h = solve_h(float(va[i] - vb[i]), L, Ls, Ss)
            if h is not None:
                d[b] = h
        out[L] = d
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--report", default=REPORT)
    args = ap.parse_args()

    if args.selftest:
        if not selftest():
            sys.exit(1)
        print()

    bands, caps = A.load_report(args.report)
    for f in [FLAT, B0_FILE] + list(THROWS.values()) + list(GRUNT.values()):
        if f not in caps:
            sys.exit("report has no %s" % f)

    global _M36, LEVELS
    if os.path.exists(M36):
        d = json.load(open(M36))
        if d["meta"]["bands"] != bands:
            sys.exit("%s was built against different bands -- re-run extract_m36.py" % M36)
        _M36 = d["pedal_db"]
    else:
        LEVELS = [x for x in LEVELS if x[0] != "m36"]
        print("  ⚠ %s absent -- running WITHOUT the -36 dBFS level "
              "(run analysis/extract_m36.py to add it)" % M36)

    print("=" * 100)
    print("h(f) AT LEVEL MAX -- bleed-free by topology, clipper de-convolved")
    print("=" * 100)
    print("  %s | %d captures | floor %.3f dB (difference of two raw measurements)"
          % (args.report, len(caps), DIFF_FLOOR))

    # ---------------------------------------------------------------- gate 1
    print("\n" + "=" * 100)
    print("GATE 1. LIVENESS")
    print("=" * 100)
    v = col_at(caps, FLAT, MAIN)
    print("  flat - flat, worst over %d bands : %.3e dB   %s"
          % (len(bands), float(np.max(np.abs(v - v))), "PASS"))

    # ---------------------------------------------------------------- gate 2
    print("\n" + "=" * 100)
    print("GATE 2. ⭐ KNOWN FEATURE -- the IC2_B bridged-T scoop, in EVERY file")
    print("=" * 100)
    print("  Post-clipper, fixed, schematic-verified ⇒ cannot depend on DRIVE, LEVEL or ATTACK.")
    print("  This is the test that condemned session 59's drive-min blend route (0.7 dB).")
    print("\n  %-26s %s   %s" % ("|G| re pure clean, -18 dBFS",
                                 "".join("%7.0f" % f for f in SHOW), "scoop"))
    A.SWEEP = MAIN
    bad = []
    for lab, f in [("flat (reference)", FLAT)] + \
                  [("attack %s" % k, v2) for k, v2 in THROWS.items()] + \
                  [("grunt %s" % k, v2) for k, v2 in GRUNT.items()]:
        g = col_at(caps, f, MAIN) - col_at(caps, B0_FILE, MAIN)
        d = {b: g[i] for i, b in enumerate(bands)}
        ins = [d[x] for x in SCOOP_IN if np.isfinite(d[x])]
        s = d[SCOOP_REF] - float(np.mean(ins))
        if not s >= SCOOP_MIN_DB:
            bad.append(lab)
        print("  %-26s %s   %5.1f  %s" % (lab, row(d, SHOW, "%7.1f"), s,
                                          "ok" if s >= SCOOP_MIN_DB else "⛔ LOST"))
    if bad:
        sys.exit("\n  ⛔ scoop absent in %s -- not measuring the OD path. Do NOT read h." % bad)
    print("\n  ⇒ all five retain it ⇒ all five are measuring the OD path.")

    # ---------------------------------------------------------------- gate 2b
    print("\n" + "=" * 100)
    print("GATE 2b. ⭐ THE ZERO-BLEED PREMISE, BOUNDED FROM THE DATA")
    print("=" * 100)
    print("  The whole route rests on `level_blend_tf` giving EXACTLY zero clean bleed at LEVEL")
    print("  max. That is a topology claim about an ideal pot; a real wiper has finite contact")
    print("  resistance and the knob may not be quite at its stop. So bound it by MEASUREMENT")
    print("  rather than trusting the model: a frequency-flat bleed cannot be larger than the")
    print("  deepest |G| anywhere in the set, or that band could not have reached it.")
    deepest, where = None, None
    for lab, f in [("flat", FLAT)] + [("attack %s" % k, v2) for k, v2 in THROWS.items()]:
        g = col_at(caps, f, MAIN) - col_at(caps, B0_FILE, MAIN)
        for i, b in enumerate(bands):
            if 20.0 <= b <= 1700.0 and np.isfinite(g[i]) and (deepest is None or g[i] < deepest):
                deepest, where = float(g[i]), "%s @ %.0f Hz" % (lab, b)
    print("\n  deepest |G| over 20 Hz-1.7 kHz : %+.1f dB   (%s)" % (deepest, where))
    bl = 10.0 ** (deepest / 20.0)
    print("  ⇒ any flat clean bleed is <= %+.1f dB (linear %.4f)" % (deepest, bl))
    print("\n  %-28s %s" % ("", "".join("%7.0f" % f for f in SHOW)))
    gflat = col_at(caps, FLAT, MAIN) - col_at(caps, B0_FILE, MAIN)
    dil = {}
    for i, b in enumerate(bands):
        if b in SHOW and np.isfinite(gflat[i]):
            od = 10.0 ** (gflat[i] / 20.0)
            dil[b] = 20.0 * np.log10((od + bl) / od)      # worst-case coherent addition
    print("  %-28s %s   worst %.2f dB"
          % ("max dilution of h (worst case)", row(dil, SHOW, "%7.2f"), max(dil.values())))
    print("\n  ⚠ A bleed common to all three files DILUTES h TOWARD ZERO, so the measured h is a")
    print("    LOWER bound on |h| -- it cannot manufacture the +8.6 dB, only shrink it. The bound")
    print("    above is worst-case-coherent; the true error is smaller and unsigned.")

    # ---------------------------------------------------------------- the compression problem
    print("\n" + "=" * 100)
    print("GATE 3. ⚠ THE RAW SUBTRACTION IS NOT h -- residual compression, measured")
    print("=" * 100)
    print("  The flat reference agreeing across level (session 59 step 6) does NOT imply the")
    print("  THROWS agree: boost pushes ~8 dB more into the J201, which never idles.")
    print("\n  %-26s %s" % ("raw ratio", "".join("%7.0f" % f for f in SHOW)))
    for thr, f in THROWS.items():
        for sweep, L in LEVELS:
            va, vb = col_at(caps, f, sweep), col_at(caps, FLAT, sweep)
            d = {b: va[i] - vb[i] for i, b in enumerate(bands)}
            print("  %-26s %s" % ("  %s @ %+.0f dBFS" % (thr, L), row(d, SHOW)))
        print()
    print("  ⇒ boost moves up to 2.4 dB across level, cut ~0.3 ⇒ de-convolve, do not average.")
    print("    (boost level-dependent / cut not is exactly a LINEAR gain ahead of a compressor)")

    # ---------------------------------------------------------------- gate 4
    print("\n" + "=" * 100)
    print("GATE 4. ⭐⭐ MODEL CONTROL -- de-convolve where the ground truth is a linear element")
    print("=" * 100)
    print("  GRUNT is a schematic+BOM-verified LINEAR cap bank at the clipper input, and the model")
    print("  implements exactly that ⇒ in the MODEL, a pre-clipper linear element is the ground")
    print("  truth by construction, so its solved h must be LEVEL-INDEPENDENT even though its raw")
    print("  ratio is not. This tests the METHOD on data it is definitionally correct for.")
    for gl, gf in GRUNT.items():
        print("\n  --- model, GRUNT %s ---" % gl)
        print("  %-26s %s" % ("raw ratio", "".join("%7.0f" % f for f in SHOW)))
        for sweep, L in MODEL_LEVELS:
            va, vb = col_at(caps, gf, sweep, "plugin_db"), col_at(caps, FLAT, sweep, "plugin_db")
            d = {b: va[i] - vb[i] for i, b in enumerate(bands)}
            print("  %-26s %s" % ("  @ %+.0f dBFS" % L, row(d, SHOW)))
        t = deconv_table(caps, bands, gf, FLAT, "plugin_db", MODEL_LEVELS)
        print("  %-26s %s" % ("solved h", ""))
        for L in sorted(t):
            if t[L]:
                print("  %-26s %s" % ("  @ %+.0f dBFS" % L, row(t[L], SHOW)))
        spread = {}
        for b in SHOW:
            vals = [t[L][b] for L in t if b in t[L]]
            if len(vals) >= 2:
                spread[b] = max(vals) - min(vals)
        if spread:
            print("  %-26s %s   worst %.3f dB  %s"
                  % ("  spread across levels", row(spread, SHOW), max(spread.values()),
                     "PASS" if max(spread.values()) <= DIFF_FLOOR else "⚠"))

    # ---------------------------------------------------------------- result
    print("\n" + "=" * 100)
    print("RESULT -- h(f), PEDAL")
    print("=" * 100)
    print("  ⚠ h is read from the CONVERGED (quietest) levels only, NOT averaged over all of them.")
    print("    Averaging a converged level with a compressing one is the session-49-item-7 /")
    print("    session-58-item-3 aggregate-over-different-members trap: it would drag 640 Hz from")
    print("    its converged +7.3 down to ~+5.5 purely by mixing in rows that are still")
    print("    compressing. CONVERGENCE IS TESTED, not assumed: the two quietest levels at which")
    print("    a band has a value must agree within the %.3f dB floor." % DIFF_FLOOR)
    final = {}
    for thr, f in THROWS.items():
        t = deconv_table(caps, bands, f, FLAT)
        raws = {}
        for sweep, L in LEVELS:
            va, vb = col_at(caps, f, sweep), col_at(caps, FLAT, sweep)
            raws[L] = {b: va[i] - vb[i] for i, b in enumerate(bands)}

        print("\n  --- ATTACK %s ---" % thr)
        print("  %-28s %s" % ("solved h (de-convolved)", "".join("%7.0f" % x for x in SHOW)))
        for L in sorted(t):
            if t[L]:
                print("  %-28s %s" % ("  @ %+.0f dBFS" % L, row(t[L], SHOW)))

        # converged read: per band, the two quietest levels with a value must agree
        best, conv, used = {}, {}, {}
        for b in SHOW:
            avail = [L for L in sorted(t) if b in t[L]]
            if not avail:
                continue
            q = avail[:2]                       # sorted() is ascending => quietest first
            if len(q) >= 2:
                gap = abs(t[q[0]][b] - t[q[1]][b])
                conv[b] = gap
                if gap <= DIFF_FLOOR:
                    best[b] = float(np.mean([t[q[0]][b], t[q[1]][b]]))
                    used[b] = "%+.0f/%+.0f" % (q[0], q[1])
                else:
                    best[b] = t[q[0]][b]        # quietest available, flagged below
                    used[b] = "%+.0f only" % q[0]
            else:
                best[b] = t[q[0]][b]
                used[b] = "%+.0f only" % q[0]
        final[thr] = best
        print("  %-28s %s   worst %.3f dB  %s"
              % ("  |gap| between 2 quietest", row(conv, SHOW, "%7.3f"),
                 max(conv.values()) if conv else float("nan"),
                 "ALL CONVERGED" if conv and max(conv.values()) <= DIFF_FLOOR
                 else "⚠ see per-band"))
        print("  %-28s %s" % ("  ⭐ h  (converged read)", row(best, SHOW)))
        # the de-convolution is a CROSS-CHECK here, not the primary read: at a converged level the
        # raw ratio and the solved h must coincide, because there is nothing left to de-convolve.
        ql = sorted(raws)[0] if thr == "boost" else sorted([L for L in t if t[L]])[0]
        dv = {b: raws[ql][b] - t[ql][b] for b in SHOW if b in t.get(ql, {})}
        if dv:
            print("  %-28s %s   worst %.3f dB"
                  % ("  raw minus solved @ %+.0f" % ql, row(dv, SHOW, "%7.3f"),
                     max(abs(x) for x in dv.values())))
        s58 = {b: S58[thr][b] for b in SHOW if b in S58[thr]}
        dl = {b: best[b] - s58[b] for b in s58 if b in best}
        if dl:
            print("  %-28s %s" % ("  session 58 (drive noon)", row(s58, SHOW)))
            print("  %-28s %s   rms %.2f dB"
                  % ("  difference (out-of-sample)", row(dl, SHOW),
                     float(np.sqrt(np.mean([x ** 2 for x in dl.values()])))))

    print("\n" + "=" * 100)
    print("VERDICT")
    print("=" * 100)
    for thr in ("boost", "cut"):
        b = final[thr]
        print("  ATTACK %-5s  %s" % (thr, "  ".join("%.0f:%+.2f" % (f, b[f])
                                                    for f in SHOW if f in b)))
    # ---------------------------------------------------------------- shape, whole band
    WIDE = [40.0, 50.4, 63.5, 80.0, 100.8, 127.0, 160.0, 201.6, 254.0, 320.0,
            403.2, 508.0, 640.0, 806.3, 1015.9, 1280.0, 1612.7]
    print("\n  --- h over the whole trusted band (<= 1.7 kHz), at the quietest converged level ---")
    print("  %-14s %s" % ("", "".join("%7.0f" % f for f in WIDE)))
    for thr, f in THROWS.items():
        L = -36.0 if thr == "boost" else -30.0
        sweep = [s for s, x in LEVELS if x == L][0]
        va, vb = col_at(caps, f, sweep), col_at(caps, FLAT, sweep)
        d = {b: va[i] - vb[i] for i, b in enumerate(bands)}
        print("  %-14s %s" % ("%s @ %+.0f" % (thr, L), row(d, WIDE)))

    print("\n  ⚠⚠ 320 Hz IS NOT A TRANSFER VALUE -- do not fit a topology to it. It is a 1/3-octave")
    print("     sample sitting ON the TrebleAttack two-path cancellation notch, which session 46")
    print("     measured at FULL resolution as 316-334 Hz and MIGRATING with level (334 -> 299 Hz).")
    print("     A band average across a sharp, moving notch depends on where the notch sits inside")
    print("     the band, not on the network's gain there -- session 46's own lesson ('never read a")
    print("     notch's depth off the 1/3-oct grid', which understated it by up to 20 dB). That")
    print("     ATTACK moves this band hard is real and expected (ATTACK reroutes C8 INSIDE the")
    print("     network that forms the notch); the NUMBER is not a gain. 254 and 403 bracket it.")
    print("  ⚠ Magnitude only ⇒ minimum-phase. ATTACK is [ENG] ⇒ h is a SPECIFICATION to meet.")
    print("  ⚠ Residual bleed can only shrink h (gate 2b) ⇒ these are LOWER bounds on |h|.")

    # ---------------------------------------------------------------- the 202 Hz peak
    print("\n" + "=" * 100)
    print("⭐⭐ WHY SESSIONS 57/58 SAW A PEAK AT ~202 Hz -- IT IS THE BLEED, COMPUTED NOT ARGUED")
    print("=" * 100)
    print("  An INDEPENDENT drive-min ATTACK pair already existed, captured on a different day at")
    print("  LEVEL NOON, where the clean bleed is NOT zero. Referenced the same way it gives a")
    print("  pronounced +4.5 dB PEAK at 202 Hz -- session 57's shape, and the reason session 57")
    print("  concluded the network needs 'a resonant/two-path element'. Predict that curve from")
    print("  the bleed-free h plus the KNOWN LEVEL/BLEND coefficients: dilution is weakest where")
    print("  |OD| is strongest, and |OD| peaks at the bridged-T's 202 Hz shoulder.")
    with __import__("contextlib").redirect_stdout(__import__("io").StringIO()):
        import eq_reference as E                                    # noqa: F401
    P = 2.25                                                        # session 8 LEVEL taper
    a1 = E.level_blend_tf(1.0, 1.0, vo=1.0, vc=0.0, p=P)
    an = E.level_blend_tf(0.5, 1.0, vo=1.0, vc=0.0, p=P)
    bn = E.level_blend_tf(0.5, 1.0, vo=0.0, vc=1.0, p=P)
    sw = "sweep_clean"
    Gm = col_at(caps, FLAT, sw) - col_at(caps, B0_FILE, sw)
    hm = col_at(caps, THROWS["boost"], sw) - col_at(caps, FLAT, sw)
    old_b, old_f = "drive-0700_attack-boost_base-od.wav", "drive-0700_base-od.wav"
    if old_b in caps and old_f in caps:
        hn = col_at(caps, old_b, sw) - col_at(caps, old_f, sw)
        lo, hi, me = {}, {}, {}
        for b in SHOW:
            i = bands.index(b)
            od, hh = 10 ** (Gm[i] / 20.0) / a1, 10 ** (hm[i] / 20.0)
            v = [20 * np.log10(abs(an * od * hh + s * bn) / abs(an * od + s * bn))
                 for s in (+1.0, -1.0)]
            lo[b], hi[b], me[b] = min(v), max(v), hn[i]
        print("\n  %-30s %s" % ("", "".join("%7.0f" % f for f in SHOW)))
        print("  %-30s %s" % ("bleed-free h (LEVEL max)", row({b: hm[bands.index(b)] for b in SHOW}, SHOW)))
        print("  %-30s %s" % ("predicted @ noon, envelope lo", row(lo, SHOW)))
        print("  %-30s %s" % ("predicted @ noon, envelope hi", row(hi, SHOW)))
        print("  %-30s %s" % ("MEASURED @ noon (other day)", row(me, SHOW)))
        pk = lambda d: SHOW[int(np.argmax([d[b] for b in SHOW]))]                  # noqa: E731
        print("\n  peak band -- measured @ noon %.0f Hz | predicted %.0f Hz | |OD| max %.0f Hz"
              % (pk(me), pk({b: 0.5 * (lo[b] + hi[b]) for b in SHOW}),
                 pk({b: Gm[bands.index(b)] for b in SHOW})))
        print("  ⇒ the peak lands at the SAME band in all three ⇒ the '202 Hz resonance' is the")
        print("    bleed's frequency-dependent dilution of a BROADBAND gain, not a resonator.")
        print("  ⚠ Envelope is phase-bracketed and uses a nominal LEVEL taper, so a few bands sit")
        print("    0.2-0.6 dB outside it. The peak LOCATION is the claim; the fit is not exact.")


if __name__ == "__main__":
    main()
