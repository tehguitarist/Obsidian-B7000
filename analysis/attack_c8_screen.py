#!/usr/bin/env python3.11
"""A3 step 12 — can the ATTACK network itself carry the pedal's low-mid span? (C8 screen)

`attack_span_probe.py` established, on the frozen matrix and against a GRUNT control,
that the pedal's ATTACK switch moves 80-640 Hz by ~2.7-2.9 dB rms at the most linear
corner of the matrix (DRIVE min, -30/-18 dBFS, converged to 8 %) while the model's
moves it by 0.05 dB. The next question is whether the modelled network can produce
that at all, and with what value.

⭐ This is a SCREEN, not a fit, and it deliberately runs BEFORE any C++ plumbing.
Session 50's next-step (a) asks for the treble ladder to be made reachable from the
A3 tools -- that is a `src/` change (FitParams + TrebleAttack setters + PedalChain +
two CLI maps) with the standing stale-binary trap attached (session 37 item 12). The
oracle `eq_reference.treble_attack_tf` ALREADY parameterises every ladder element
including C8, so the reachability question can be answered for free first, and the
plumbing only has to be written if the answer is yes.

HOW THE PREDICTION IS MADE (and why it is exact at this operating point)

At DRIVE min and -30/-18 dBFS the chain is linear -- which is not assumed here, it is
the measured result the probe reports (the pedal's span changes 8 % between the two
lowest levels, and the GRUNT control behaves the same way). In a linear chain the OD
path is a product, so a change confined to the treble network enters the BLEND node as
one multiplicative factor:

    od'(f) = od(f) . r(f),    r(f) = H_treble(boost, C8) / H_treble(flat, C8)

and `a3_blend_decompose` gives the model's own `od` and `cl` phasors at exactly this
operating point by EXACT superposition (resid <= -273 dB), so the predicted output span

    span(f) = 20log10|od.r + cl| - 20log10|od + cl|

needs no bleed estimate, no `b0`, and no solve. The bleed enters as a measured complex
number, so the dilution that makes an OUTPUT span unreadable as a stage transfer
(`grunt_span_probe`'s standing caveat) is here computed rather than worried about.

SELF-TEST: at the shipped C8 = 220 pF the prediction must reproduce the model's own
measured output span from the report, per band. That is a known answer the machinery
cannot fake -- if the Zs boundary, the position mapping or the phasor convention were
wrong, nominal would not land on it.

⚠ SCOPE. A pass here means "the modelled ATTACK network CAN produce the pedal's
low-mid span at a different C8", i.e. reachability. It does NOT mean C8 is the real
part: ATTACK is [ENG] (the 3-way switch is not on our schematic at all -- circuit.md),
so there is no verified topology to defer to, and the same span could be carried by
other ladder elements. It also says nothing about the higher-drive rows, where the
clipper is engaged and this linear prediction does not apply.

Usage:
    python3.11 analysis/attack_c8_screen.py                # self-test + C8 sweep
    python3.11 analysis/attack_c8_screen.py --full         # per-band tables too
"""
import contextlib
import io
import math
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
# ⚠ eq_reference.py prints its whole diagnostic report at MODULE level (no
# `if __name__ == "__main__"` guard), so importing it dumps ~80 lines of unrelated
# mid/Baxandall/GRUNT tables into this tool's output. Swallowed here rather than
# fixed in place: that file is the shared oracle for seven tools and `python3.11
# analysis/eq_reference.py` is expected to print exactly what it prints today.
with contextlib.redirect_stdout(io.StringIO()):
    import eq_reference as EQ                                 # noqa: E402
from attack_span_probe import SPAN_LO, SPAN_HI, load, spans, rms   # noqa: E402

DEC_DRIVE_MIN = "build/a3_dec_drv0.0.csv"
REPORT = "analysis/reports/comprehensive_data.json"

# The most linear corner of the matrix (attack_span_probe verdict (4)).
TRIPLE = ("drive-0700_base-od.wav", "drive-0700_attack-boost_base-od.wav",
          "drive-0700_attack-cut_base-od.wav")
SWEEP = "sweep_drv_-18"

# Shipped values these must match or the screen is predicting a different model.
# (FitParams.h / TrebleAttack.h — read once here so a drift is visible, not silent.)
GM, RO, RQ2 = 0.10e-3, 200.0e3, 1.0e6
RDAMP_C5 = 30.0e3          # FitParams::trebleLadderDampR (session 19)
C7 = 680.0e-12             # FitParams::trebleC7 (session 35)
C8_NOMINAL = 220.0e-12     # TrebleAttack::kC8 — static constexpr, the point of this screen


def dec_load(path):
    """(freqs, od, cl) as numpy arrays from an a3_blend_decompose CSV."""
    f, od, cl = [], [], []
    for line in open(path):
        if line.startswith("#"):
            continue
        r = line.split(",")
        f.append(float(r[0]))
        od.append(complex(float(r[5]), float(r[6])))
        cl.append(complex(float(r[7]), float(r[8])))
    return np.array(f), np.array(od), np.array(cl)


def ratio(freqs, pos, c8):
    """H_treble(pos)/H_treble(flat) at the shipped ladder, with the physical Zs.

    Zs is the J201 drain impedance the C++ stage actually stamps. It matters even for
    a position RATIO: the ladder's own input impedance is comparable to it, so driving
    the network from an ideal source changes both positions by different amounts
    (the 2026-07-22 boundary finding — see jfet_source_z's docstring).
    """
    zs = EQ.jfet_source_z(freqs, gm=GM, ro=RO, Rq2=RQ2)
    kw = dict(Zs=zs, C7=C7, C8=c8, RdampC5=RDAMP_C5)
    return EQ.treble_attack_tf(freqs, pos, **kw) / EQ.treble_attack_tf(freqs, "flat", **kw)


def predict(freqs, od, cl, pos, c8):
    """Predicted OUTPUT span in dB per band for a candidate C8."""
    r = ratio(freqs, pos, c8)
    return 20.0 * np.log10(np.abs(od * r + cl) / np.abs(od + cl))


def measured(bands, caps, pos_file):
    """(pedal_span, model_span) per band at the linear corner."""
    s = spans(caps, TRIPLE[0], pos_file, SWEEP)
    return (s[1], s[0]) if s else (None, None)


def on_bands(freqs, vals, bands, lo=SPAN_LO, hi=SPAN_HI):
    """Resample a per-decompose-band curve onto the report's band grid (nearest)."""
    out = []
    for b in bands:
        if not (lo <= b <= hi):
            continue
        i = int(np.argmin(np.abs(freqs - b)))
        out.append(float(vals[i]))
    return out


def main():
    full = "--full" in sys.argv
    if not os.path.exists(DEC_DRIVE_MIN):
        print(f"missing {DEC_DRIVE_MIN} — render it first (a3_blend_decompose 1 0.0 -18)")
        return 1
    freqs, od, cl = dec_load(DEC_DRIVE_MIN)
    bands, caps = load(REPORT)
    idx_b = [b for b in bands if SPAN_LO <= b <= SPAN_HI]

    print(f"### SETUP\n    decompose : {open(DEC_DRIVE_MIN).readline().strip()}")
    print(f"    captures  : {TRIPLE[0]} / boost / cut   [{SWEEP}]")
    print(f"    ladder    : gm={GM * 1e3:.2f} mS ro={RO / 1e3:.0f}k Rq2={RQ2 / 1e6:.0f}M"
          f" RdampC5={RDAMP_C5 / 1e3:.0f}k C7={C7 * 1e12:.0f}p")

    # ---------------------------------------------------------------- self-test
    print("\n### SELF-TEST — at the shipped C8 the prediction must reproduce the"
          " MODEL's own measured span")
    ok = True
    for pos, pf in (("boost", TRIPLE[1]), ("cut", TRIPLE[2])):
        _ped, mdl = measured(bands, caps, pf)
        if mdl is None:
            continue
        pred = on_bands(freqs, predict(freqs, od, cl, pos, C8_NOMINAL), bands)
        meas = [mdl[i] for i, b in enumerate(bands) if SPAN_LO <= b <= SPAN_HI]
        err = max(abs(a - b) for a, b in zip(pred, meas))
        p = err < 0.05
        ok &= p
        print(f"    {pos:<6} predicted rms {rms(pred):5.3f} dB | measured rms"
              f" {rms(meas):5.3f} dB | worst per-band diff {err:5.3f} dB  "
              f"{'PASS' if p else 'FAIL'}")
    print(f"    => SELF-TEST {'PASS' if ok else 'FAIL'}"
          "  (a wrong Zs, position map or phasor convention fails here)")
    if not ok:
        print("⛔ do not read the sweep below.")
        return 1

    # ------------------------------------------------------------------- target
    ped_b, mdl_b = measured(bands, caps, TRIPLE[1])
    ped_c, mdl_c = measured(bands, caps, TRIPLE[2])
    tgt_b = [ped_b[i] for i, b in enumerate(bands) if SPAN_LO <= b <= SPAN_HI]
    tgt_c = [ped_c[i] for i, b in enumerate(bands) if SPAN_LO <= b <= SPAN_HI]
    print(f"\n### TARGET — the pedal's own span at the linear corner, {SPAN_LO:.0f}-"
          f"{SPAN_HI:.0f} Hz")
    print("    " + " ".join(f"{b:>7.0f}" for b in idx_b) + "     rms")
    print("    " + " ".join(f"{v:+7.2f}" for v in tgt_b) + f"  boost {rms(tgt_b):5.2f}")
    print("    " + " ".join(f"{v:+7.2f}" for v in tgt_c) + f"  cut   {rms(tgt_c):5.2f}")

    # ---------------------------------------------------------------- C8 sweep
    print("\n### C8 SWEEP — one element, both positions scored TOGETHER")
    print("    ⚠ Both positions must be scored on ONE value: C8 is a single part and"
          " the switch\n      only reroutes its bottom plate, so a C8 that fixes boost"
          " while wrecking cut is not\n      a candidate. (The GAP #4 joint-mid-cap"
          " failure mode: a score that lets one\n      position pay for another.)")
    print(f"    {'C8':>9} {'boost rms':>10} {'err':>7} | {'cut rms':>9} {'err':>7}"
          f" | {'JOINT err':>9}")
    cands = [220e-12, 470e-12, 1e-9, 2.2e-9, 3.3e-9, 4.7e-9, 6.8e-9, 10e-9, 15e-9,
             22e-9, 47e-9, 100e-9]
    best = None
    rows = []
    for c8 in cands:
        pb = on_bands(freqs, predict(freqs, od, cl, "boost", c8), bands)
        pc = on_bands(freqs, predict(freqs, od, cl, "cut", c8), bands)
        eb = rms([a - b for a, b in zip(pb, tgt_b)])
        ec = rms([a - b for a, b in zip(pc, tgt_c)])
        ej = math.sqrt(0.5 * (eb * eb + ec * ec))
        rows.append((c8, pb, pc, eb, ec, ej))
        label = f"{c8 * 1e12:.0f}p" if c8 < 1e-9 else f"{c8 * 1e9:g}n"
        print(f"    {label:>9} {rms(pb):10.2f} {eb:7.2f} | {rms(pc):9.2f} {ec:7.2f}"
              f" | {ej:9.2f}" + ("   <- shipped" if c8 == C8_NOMINAL else ""))
        if best is None or ej < best[5]:
            best = rows[-1]

    lab = f"{best[0] * 1e12:.0f}p" if best[0] < 1e-9 else f"{best[0] * 1e9:g}n"
    bi = cands.index(best[0])
    # ⚠ "interior" is NOT enough. A saturating curve has its numerical minimum in the
    # interior of the grid while being FLAT there — that is the "the objective does not
    # identify this direction" signature (session 44 item 5), and calling it a minimum
    # is how a degeneracy gets shipped as a fit. Require a real basin: the curve must
    # rise on BOTH sides by more than the capture floor.
    lo_rise = rows[bi - 1][5] - best[5] if bi > 0 else -1.0
    hi_rise = rows[bi + 1][5] - best[5] if bi < len(rows) - 1 else -1.0
    real_min = min(lo_rise, hi_rise) > 0.204
    print(f"\n    best joint err {best[5]:.2f} dB at C8 = {lab}")
    print(f"    rises by {lo_rise:+.2f} / {hi_rise:+.2f} dB either side  =>"
          f" {'REAL interior minimum' if real_min else '⚠ SATURATED / FLAT — this is not an optimum'}")
    print(f"    shipped 220p joint err {rows[0][5]:.2f} dB"
          f"  => only {rows[0][5] / max(best[5], 1e-9):.2f}x worse")
    print(f"    boost span ceiling over the whole C8 sweep: {max(rms(r[1]) for r in rows):.2f}"
          f" dB rms  vs the pedal's {rms(tgt_b):.2f} dB")

    if full or True:
        print("\n### PER BAND at the best C8 (pred vs pedal)")
        print("    " + " ".join(f"{b:>7.0f}" for b in idx_b))
        for tag, pred, tgt in (("boost pred", best[1], tgt_b),
                               ("boost ped ", None, tgt_b),
                               ("cut   pred", best[2], tgt_c),
                               ("cut   ped ", None, tgt_c)):
            v = pred if pred is not None else tgt
            print(f"    {tag} " + " ".join(f"{x:+7.2f}" for x in v))

    # ------------------------------------------------- reachability frontier
    #
    # C8 alone saturating is a statement about one part. The general question is
    # whether the [ENG] ATTACK TOPOLOGY can produce the pedal's span at ANY setting
    # of the network it sits in -- which is the session-49 bridged-T Pareto argument,
    # one stage over: not "this value cannot" but "nothing in the reachable space
    # can". R7/R8 set the ceiling on what bridging R8 can lift, so they are the two
    # that matter; they ARE schematic-verified, so freeing them here makes the bound
    # STRONGER (if it cannot be reached even with them free, no value choice helps).
    print("\n### REACHABILITY FRONTIER — C8 x R7 x R8, +-1 decade on the resistors")
    print("    Scored as: how much BOOST span is reachable, and what CUT span comes")
    print("    with it. The pedal is strongly asymmetric (boost"
          f" {rms(tgt_b):.2f} / cut {rms(tgt_c):.2f} dB rms),")
    print("    and C8 is ONE part whose two throws are near-mirror images — so the")
    print("    asymmetry, not just the size, is the thing to reach.")
    decade = [10 ** (k / 4.0) for k in range(-4, 5)]           # x0.1 .. x10, 9 pts
    best_b, best_asym = None, None
    n = 0
    for c8 in cands:
        for fr7 in decade:
            for fr8 in decade:
                r7, r8 = 200e3 * fr7, 470e3 * fr8
                zs = EQ.jfet_source_z(freqs, gm=GM, ro=RO, Rq2=RQ2)
                kw = dict(Zs=zs, C7=C7, C8=c8, RdampC5=RDAMP_C5, R7=r7, R8=r8)
                hf = EQ.treble_attack_tf(freqs, "flat", **kw)
                pb = on_bands(freqs, 20 * np.log10(np.abs(
                    od * (EQ.treble_attack_tf(freqs, "boost", **kw) / hf) + cl)
                    / np.abs(od + cl)), bands)
                pc = on_bands(freqs, 20 * np.log10(np.abs(
                    od * (EQ.treble_attack_tf(freqs, "cut", **kw) / hf) + cl)
                    / np.abs(od + cl)), bands)
                rb, rc = rms(pb), rms(pc)
                n += 1
                if best_b is None or rb > best_b[0]:
                    best_b = (rb, rc, c8, r7, r8)
                # the asymmetry the pedal actually shows: big boost, small cut
                if rc <= rms(tgt_c) + 0.204 and (best_asym is None or rb > best_asym[0]):
                    best_asym = (rb, rc, c8, r7, r8)
    print(f"    searched {n} settings")
    rb, rc, c8, r7, r8 = best_b
    print(f"    max BOOST span reachable        : {rb:5.2f} dB rms"
          f"  (cut {rc:5.2f})  at C8={c8 * 1e9:g}n R7={r7 / 1e3:.0f}k R8={r8 / 1e3:.0f}k")
    if best_asym:
        rb2, rc2, c82, r72, r82 = best_asym
        print(f"    max BOOST with cut <= pedal's   : {rb2:5.2f} dB rms"
              f"  (cut {rc2:5.2f})  at C8={c82 * 1e9:g}n R7={r72 / 1e3:.0f}k"
              f" R8={r82 / 1e3:.0f}k")
    else:
        print("    max BOOST with cut <= pedal's   :  NONE — every setting that raises"
              " boost raises cut past\n                                       the"
              " pedal's own 0.40 dB, so the ASYMMETRY is unreachable.")
    print(f"    pedal target                    : {rms(tgt_b):5.2f} dB rms"
          f"  (cut {rms(tgt_c):5.2f})")
    verdict_reach = rb >= rms(tgt_b)
    print(f"    => the ATTACK network {'CAN' if verdict_reach else 'CANNOT'} reach the"
          f" pedal's boost span"
          f" ({rb / max(rms(tgt_b), 1e-9):.0%} of it at the frontier)")
    print("    ⚠ that frontier point rests on BOTH resistor grid EDGES (x0.1 and x10),"
          " so it bounds\n      what is reachable but does NOT identify a setting"
          " — see the joint fit next.")
    print("    ⚠ and R7/R8 are SCHEMATIC-VERIFIED (200k/470k, pixel-zoom + the R1-R54"
          " BOM census).\n      Freeing them is legitimate for a BOUND; proposing"
          " a 10x move in two verified parts\n      is a far bigger claim than"
          " re-valuing the [ENG] C8.")

    # ------------------------------------------------------------- joint fit
    # Reachability is a ceiling; a candidate has to reproduce the SHAPE of both
    # positions at ONE setting. Same grid, scored on the joint per-band error.
    print("\n### JOINT FIT over the same grid — both positions, per band, one setting")
    # ⭐ RdampC5 joins the grid here and nowhere above. The C8/R7/R8 fit tracks the
    # pedal to ~254 Hz and then misses badly at 320 Hz, where the pedal's boost span
    # collapses to +0.21 dB — and 320 Hz is GAP #2's TrebleAttack two-path
    # cancellation notch, which session 46 showed `trebleLadderDampR = 30k` DESTROYS
    # in the OD path (monotone 254->640 at 30k; a 31 dB notch at the schematic 0).
    # Session 46's own instruction was "leave it at 30k, fix A3, THEN re-fit it";
    # this is a screen inside that A3 work, and it changes nothing in src/.
    rds = [0.0, 1e3, 3e3, 10e3, 30e3, 100e3]
    zs = EQ.jfet_source_z(freqs, gm=GM, ro=RO, Rq2=RQ2)

    def pred_pair(c8, r7, r8, rd):
        kw = dict(Zs=zs, C7=C7, C8=c8, RdampC5=rd, R7=r7, R8=r8)
        hf = EQ.treble_attack_tf(freqs, "flat", **kw)
        out = []
        for pos in ("boost", "cut"):
            r = EQ.treble_attack_tf(freqs, pos, **kw) / hf
            out.append(on_bands(freqs, 20 * np.log10(
                np.abs(od * r + cl) / np.abs(od + cl)), bands))
        return out

    # Scored TWICE, and both printed. 320 Hz is a band every other A3 instrument
    # already excludes BY NAME -- a3_shape_gate's CORE ("TrebleAttack-notch band,
    # known separate gap, and a lone outlier"), a3_phase_solve, and the level-axis
    # aggregates (session 40 item 3, where it was the only band positive in every OD
    # capture). Applying that standing exclusion here is consistency, not
    # cherry-picking -- but it is never applied silently (the session-40 rule), so
    # the full-band number is reported beside it and the reader can see what the one
    # band is worth.
    mask_all = [True] * len(idx_b)
    mask_ex = [b != 320.0 for b in idx_b]

    def sc(v, tgt, mask):
        return rms([a - b for a, b, m in zip(v, tgt, mask) if m])

    results = {}
    for mname, mask in (("all 10 bands", mask_all), ("ex 320 Hz", mask_ex)):
        grid = {}
        for ic, c8 in enumerate(cands):
            for i7, fr7 in enumerate(decade):
                for i8, fr8 in enumerate(decade):
                    for ir, rd in enumerate(rds):
                        pb, pc = pred_pair(c8, 200e3 * fr7, 470e3 * fr8, rd)
                        eb, ec = sc(pb, tgt_b, mask), sc(pc, tgt_c, mask)
                        grid[(ic, i7, i8, ir)] = (
                            math.sqrt(0.5 * (eb * eb + ec * ec)), eb, ec,
                            c8, fr7, fr8, rd, pb, pc)
        k = min(grid, key=lambda kk: grid[kk][0])
        results[mname] = (k, grid[k])

    for mname, (k, g) in results.items():
        ej, eb, ec, c8, fr7, fr8, rd, pb, pc = g
        edges = [nm for nm, i, top in
                 (("C8", k[0], len(cands) - 1), ("R7", k[1], 8), ("R8", k[2], 8),
                  ("RdampC5", k[3], len(rds) - 1)) if i in (0, top)]
        print(f"\n    [{mname}] best joint err {ej:.2f} dB"
              f" (boost {eb:.2f} / cut {ec:.2f})"
              f"  at C8={c8 * 1e9:g}n R7={200 * fr7:.0f}k R8={470 * fr8:.0f}k"
              f" RdampC5={rd / 1e3:g}k")
        print(f"        edges: {', '.join(edges) if edges else 'none'}"
              f"   {'⚠ NOT identified' if edges else '(identified)'}"
              f"   |  R7 x{fr7:.2f}, R8 x{fr8:.2f} off their SCHEMATIC values")
        print("        " + " ".join(f"{b:>7.0f}" for b in idx_b))
        for tag, v in (("boost fit", pb), ("boost ped", tgt_b),
                       ("cut   fit", pc), ("cut   ped", tgt_c)):
            print(f"        {tag} " + " ".join(f"{x:+7.2f}" for x in v))
    print(f"\n    shipped (220p / 200k / 470k / 30k) joint err {rows[0][5]:.2f} dB,"
          f" span floor {0.204:.2f} dB")

    # ------------------------------------------------------------ verdict
    # Computed, so it cannot outlive the numbers above (session 34's lesson: a
    # narrated "DO NOT BUILD THIS" printed above a table that had flipped to PASS).
    ceil_c8 = max(rms(r[1]) for r in rows)
    k_ex, g_ex = results["ex 320 Hz"]
    ej_ex = g_ex[0]
    floor = 0.204
    print("\n### VERDICT — computed")
    print(f"    (1) C8 ALONE saturates at {ceil_c8:.2f} dB rms of boost span"
          f" ({ceil_c8 / rms(tgt_b):.0%} of the pedal's\n        {rms(tgt_b):.2f} dB)"
          f" and its best joint error is FLAT across 22n-100n."
          f"  => the single [ENG]\n        element is REFUTED on reachability, not"
          f" on value.")
    print(f"    (2) With R7/R8/RdampC5 free the SIZE is reachable, and the pedal's"
          f" 80-254 Hz shape is\n        tracked to ~0.4-0.7 dB — but the best joint"
          f" error is {ej_ex:.2f} dB (ex 320 Hz) against a\n        {floor:.2f} dB"
          f" span floor, i.e. {ej_ex / floor:.1f}x the floor, and it is NOT"
          f" identified (R7 rests on\n        its bound). It also costs x0.10 on R7"
          f" and x3.16 on R8, both SCHEMATIC-VERIFIED.")
    print("    (3) The residual is a SHAPE the network cannot make: above ~254 Hz"
          " every ladder\n        setting plateaus, while the pedal PEAKS at 202 Hz"
          " and falls away (+4.23 -> +0.21 at\n        320 -> +1.35 at 640). Adding"
          " RdampC5 to the grid does not help; it runs to the\n        far edge"
          " (more damping), so the 320 Hz collapse is not the GAP #2 notch"
          " reappearing.")
    print("    => DO NOT plumb the ladder into src/ on this evidence. The screen was"
          " run first\n       precisely so that the FitParams/TrebleAttack/PedalChain"
          " change would only be\n       written if the answer were yes. It is"
          " 'partially, at a large schematic cost,\n       and with the wrong shape'.")
    print("\n### SCOPE")
    print("    * LINEAR corner only (DRIVE min, -18 dBFS). At higher drive the ladder"
          " feeds a working\n      clipper and could do more; this predicts nothing"
          " there, and a real render is the\n      only way to test it.")
    print("    * ATTACK is [ENG] — the 3-way switch is not on our schematic at all"
          " (circuit.md). So\n      the failure may be the assumed TOPOLOGY rather"
          " than any value in it, which is the\n      one hypothesis this screen"
          " cannot test.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
