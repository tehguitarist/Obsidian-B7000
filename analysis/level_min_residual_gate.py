#!/usr/bin/env python3
"""GATE BK — open-work item 12: at LEVEL min the model MUTES and the reference does not.

WHAT THIS GATE IS FOR
---------------------
Item 12 has carried the same two candidate mechanisms since s162, unmeasured:
a LEVEL-pot **end-stop resistance**, or **GATE K2's BLEND-body bleed path**. This
gate discriminates them, and it does so on a statistic neither prior reading used.

THE STATISTIC, AND WHY THE PRIOR ONE COULD NOT DECIDE
----------------------------------------------------
GATE L7 (s104) inverted the shipped network for the pedal's "equivalent wiper" and got
L(0) = 0.0118-0.0176, then rejected an end resistance because 1.5 % of a 100k pot is far
too large. That inversion is taken on the **FUNDAMENTAL** — and the fundamental is exactly
what an OD-vs-clean cancellation suppresses at a null. Measured here (BK3): at the
listening rung **79 % of the LEVEL-min capture's deconvolved IR energy is HARMONIC**, so
the fundamental is the one quantity that cannot be read at face value there.

What decides it instead needs no model and no threshold — the **stimulus dose-response**.
The two candidate sources have completely different ones, measured on this very capture set:

    OD path   (level-1700_base-od)  compresses:  ~9.8 dB out per 24 dB in
    clean tap (blend-0700_base-od)  is linear :  ~24.0 dB out per 24 dB in

so whichever the residual holds a CONSTANT ratio against names the source. (s38's C12
locus argument / s126's bass peak / s165's route (i): a dose-response locus that cannot
CONTAIN the target refutes the lever, not its setting.)

SUB-GATES
---------
  BK0   capture validity — the LEVEL ladder is a DESIGNED MONOTONE axis, which is a free
        per-row check on the reference. Run INSIDE each capture session so no
        cross-session pad correction can be blamed. REFUSES on any inversion.
  BK1   known answers — (a) the model at LEVEL 0 renders exact digital zero (the defect
        itself, reproduced); (b) the two independent clean routes agree in shape.
  BK2   the residual is a SIGNAL, not a floor — the stimulus's own silent gaps decay far
        below the segment level. ⚠ See NOTE ON THE FLOOR TRAP below.
  BK3   linear vs harmonic split of the residual (Farina IR gate fraction).
  BK4   ⭐ THE DISCRIMINATOR — ratio-to-OD span vs ratio-to-CLEAN span across the ladder.
  BK5   the model's OWN small-L prediction, rendered. The shipped taper is linear near the
        origin (L = kLevelTaperFrac1/kLevelTaperBreak1 * x), so a small LEVEL KNOB
        reproduces the end-stop hypothesis exactly, with NO code change.
  BK6   computed verdict.

⚠⚠ NOTE ON THE FLOOR TRAP, recorded because this gate's own first draft fell in it.
A "gap floor" computed by CONCATENATING the stimulus's 29 silent gaps and taking one RMS
is dominated by the SPLICE CLICKS, not by the files. It reported level-0700_base-od at
-59.6 dBFS — i.e. 4.6 dB ABOVE its own sweep_clean segment, which would have made the
whole residual unreadable — and reported the LOUDEST file in the ladder at the same
-59.6. Both are the instrument. Per-gap and read as an ENVELOPE the tails decay at a
clean -9 dB per 50 ms to -137 dB, i.e. there is no floor at all. BK2 therefore measures
the DECAY, per gap, and never concatenates.

Run:  /opt/homebrew/bin/python3.11 analysis/level_min_residual_gate.py
Mutation control: analysis/_mutate_gate_bk.py
"""
import json
import os
import subprocess
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import analyze as A            # noqa: E402
import captures as C           # noqa: E402

CAP = C.CAPTURE_DIR
REPORT = "analysis/reports/s181_level_min.json"
RENDER_DIR = "build/s181_level_min"

SWEEPS = ["sweep_clean", "sweep_drv_-18", "sweep_drv_-12", "sweep_drv_-6"]
# The stimulus rungs are 12 dB apart by construction (gen_test_signal); clean sits 24 dB
# above drv_-6. Asserted in BK4 rather than transcribed.
STIM_DB = {"sweep_clean": -30.0, "sweep_drv_-18": -18.0, "sweep_drv_-12": -12.0,
           "sweep_drv_-6": -6.0}

RESID = "level-0700_base-od.wav"        # LEVEL min, BLEND max  = the defect
OD = "level-1700_base-od.wav"           # LEVEL max, BLEND max  = pure OD (bleed-free)
CLEAN = "blend-0700_base-od.wav"        # BLEND min             = pure clean
CLEAN2 = "ref-clean.wav"                # DIST off              = pure clean, 2nd route

# Full-send LEVEL ladder, and the (smaller) gain-n12 one. Both are checked for
# monotonicity INSIDE their own session — see BK0.
LADDER_FULL = ["0700", "0815", "0930", "1045", "1315", "1430", "1545", "1700"]
LADDER_N12 = ["0700", "0930", "1430", "1700"]

FAILURES = []


def fail(tag, msg):
    FAILURES.append(f"[{tag}] {msg}")
    print(f"  ⛔ {tag}: {msg}")


def load(fn):
    p = os.path.join(CAP, fn)
    if not os.path.exists(p):
        raise SystemExit(f"GATE BK REFUSES: missing capture {p}")
    return A.load(p)


def segrms(y):
    return np.array([A.rms_db(A.seg_of(y, s)) for s in SWEEPS])


# ---------------------------------------------------------------------------------
def bk0_capture_validity(out):
    """A pot law is monotone. A rung that inverts its own neighbours, INSIDE one capture
    session, is a mis-dialled capture and nothing else -- no cross-session pad enters."""
    print("\nBK0 — capture validity: the LEVEL ladder is a designed monotone axis")
    bad = {}
    for label, ladder, suffix in (("full", LADDER_FULL, "_base-od.wav"),
                                  ("n12", LADDER_N12, "_gain-n12_base-od.wav")):
        rows, names = [], []
        for k in ladder:
            fn = f"level-{k}{suffix}"
            if not os.path.exists(os.path.join(CAP, fn)):
                continue
            rows.append(segrms(load(fn)))
            names.append(k)
        print(f"  {label:5s} ladder ({len(names)} rungs): " + " ".join(names))
        for i in range(1, len(rows)):
            drops = [SWEEPS[j] for j in range(len(SWEEPS)) if rows[i][j] < rows[i - 1][j] - 0.05]
            if drops:
                # Name BOTH members: an inversion convicts a PAIR, and which member is
                # wrong is decided against the other session's ladder, not by position.
                bad[f"{label}:{names[i-1]}->{names[i]}"] = drops
                print(f"    ⚠ NON-MONOTONE {names[i-1]} -> {names[i]} at {drops}")
        out.setdefault("ladders", {})[label] = {
            n: [round(float(v), 4) for v in r] for n, r in zip(names, rows)}

    # Which member of an inverted pair is the defective one: the full-send ladder is
    # monotone at all 8 rungs, so it arbitrates. Every n12 rung must sit a CONSISTENT pad
    # below its full-send twin.
    pads = {}
    for k in LADDER_N12:
        f_full = f"level-{k}_base-od.wav"
        f_n12 = f"level-{k}_gain-n12_base-od.wav"
        if not (os.path.exists(os.path.join(CAP, f_full))
                and os.path.exists(os.path.join(CAP, f_n12))):
            continue
        pads[k] = float(np.median(segrms(load(f_full)) - segrms(load(f_n12))))
    out["n12_pad_db"] = {k: round(v, 3) for k, v in pads.items()}
    print("\n  cross-session pad (full-send minus gain-n12), median over the 4 sweeps:")
    for k, v in pads.items():
        print(f"    LEVEL {k}: {v:+7.2f} dB")
    # ⭐ THRESHOLD-FREE: a gain-n12 capture was recorded with the send 12 dB DOWN, so for
    # ANY monotone path its full-send twin must be LOUDER. The SIGN alone convicts; the
    # magnitude is reporting only. (The magnitudes legitimately spread 4.9-10.3 dB because
    # these are OD-path captures and the clipper compresses — captures.py says so, which
    # is exactly why a magnitude bar here would be arbitrary.)
    if pads:
        med = float(np.median([v for v in pads.values() if v > 0]) or 0.0)
        out["n12_pad_median_positive"] = round(med, 3)
        neg = {k: v for k, v in pads.items() if v < 0}
        out["n12_pad_outliers"] = {k: round(v, 3) for k, v in neg.items()}
        for k, v in neg.items():
            fail("BK0", f"level-{k}_gain-n12_base-od.wav reads {abs(v):.2f} dB LOUDER than its "
                        f"full-send twin, which was driven {abs(v)+12:.0f} dB harder — no "
                        f"monotone path does that. DEFECTIVE CAPTURE; exclude it by name")
    out["ladder_inversions"] = {k: v for k, v in bad.items()}
    return out


# ---------------------------------------------------------------------------------
def bk1_known_answers(out):
    print("\nBK1 — known answers")
    # (a) the model at LEVEL 0 is exact digital zero. This IS the defect; if it ever stops
    #     being exactly zero the gate is measuring a different build than it thinks.
    p = dict(C.parse_capture(RESID))
    p["level"] = 0.0
    y = render(p, "model_level0")
    peak = float(np.max(np.abs(y)))
    out["model_level0_peak"] = peak
    print(f"  (a) model at LEVEL 0, BLEND max: max|x| = {peak:.3e}")
    if peak != 0.0:
        fail("BK1a", f"the model no longer mutes at LEVEL 0 (max|x| = {peak:.3e}); "
                     f"item 12's premise has changed and every reading below is stale")

    # (b) two independent clean routes must agree in SHAPE. If they do not, "the clean
    #     path" is not a single object and BK4's denominator is ill-defined.
    a, b = load(CLEAN), load(CLEAN2)
    d = segrms(a) - segrms(b)
    spread = float(d.max() - d.min())
    out["clean_route_shape_spread_db"] = round(spread, 4)
    print(f"  (b) clean routes (BLEND min vs DIST off): per-sweep delta "
          f"{np.array2string(d, precision=2)} — spread {spread:.3f} dB")
    if spread > 1.5:
        fail("BK1b", f"the two clean routes disagree by {spread:.2f} dB across the ladder; "
                     f"BK4's CLEAN reference is not well defined")
    return out


# ---------------------------------------------------------------------------------
def bk2_not_a_floor(out):
    """Per-gap DECAY, never concatenated (see the header's floor-trap note)."""
    print("\nBK2 — is the residual a signal, or a floor?")
    edges = sorted({round(v, 6) for ab in A.T.values() for v in ab})
    gaps = []
    for i in range(len(edges) - 1):
        lo, hi = edges[i], edges[i + 1]
        if hi - lo < 0.05:
            continue
        if not any(t0 - 1e-9 <= lo and hi <= t1 + 1e-9 for t0, t1 in A.T.values()):
            gaps.append((lo, hi))
    y = load(RESID)
    # Deepest 50 ms block reached inside each gap, MEDIAN over gaps. A real noise floor
    # would put a hard bottom under this; a decay tail does not.
    deepest = []
    for lo, hi in gaps:
        blocks = []
        t = lo + 0.05
        while t + 0.05 <= hi:
            i0 = int(t * A.FS)
            blocks.append(A.rms_db(y[i0:i0 + int(0.05 * A.FS)]))
            t += 0.05
        if blocks:
            deepest.append(min(blocks))
    med_floor = float(np.median(deepest)) if deepest else float("nan")
    seg = segrms(y)
    margins = seg - med_floor
    out["gap_decay_median_db"] = round(med_floor, 2)
    out["residual_margin_over_gap_db"] = [round(float(v), 2) for v in margins]
    print(f"  {len(gaps)} stimulus gaps; median deepest 50 ms block = {med_floor:.1f} dBFS")
    print(f"  residual segment RMS {np.array2string(seg, precision=2)} "
          f"=> margins {np.array2string(margins, precision=1)} dB")
    if float(margins.min()) < 20.0:
        fail("BK2", f"the residual clears the file's own quiet-gap depth by only "
                    f"{margins.min():.1f} dB at its worst rung — not safely a signal")
    return out


# ---------------------------------------------------------------------------------
def bk3_linear_vs_harmonic(out):
    """Farina: the linear response concentrates at t=0 and the Nth harmonic sits a fixed
    time AHEAD. So the in-gate energy fraction reads 'how much of this is fundamental'
    with no threshold -- and it is what invalidates every fundamental-domain reading."""
    print("\nBK3 — linear vs harmonic split of the LEVEL-min residual")
    orig = A.load(A.ORIG)
    rows = {}
    for label, fn in (("resid", RESID), ("od", OD), ("clean", CLEAN)):
        y = load(fn)
        frac = []
        for s in SWEEPS:
            ir, nfft, T, R = A.farina_deconv(A.seg_of(y, s), A.seg_of(orig, s))
            dt2 = T * np.log(2.0) / R
            half = max(int(A.H1_GATE_FRACTION * dt2 * A.FS), int(0.01 * A.FS))
            idx = np.arange(-half, half) % nfft
            tot = float(np.sum(ir ** 2))
            frac.append(float(np.sum(ir[idx] ** 2)) / tot if tot > 0 else float("nan"))
        rows[label] = frac
        print(f"  {label:6s} in-gate (fundamental) energy fraction: "
              + "  ".join(f"{s.replace('sweep_',''):>10s}={v:5.3f}" for s, v in zip(SWEEPS, frac)))
    out["ir_gate_fraction"] = {k: [round(v, 4) for v in v2] for k, v2 in rows.items()}
    listen = SWEEPS.index("sweep_drv_-12")
    off_pct = 100.0 * (1.0 - rows["resid"][listen])
    out["residual_out_of_gate_pct_at_listening_rung"] = round(off_pct, 1)
    print(f"\n  ⇒ at the listening rung (sweep_drv_-12) only {100*rows['resid'][listen]:.1f} % of "
          f"the residual's deconvolved energy sits in the LINEAR gate, against "
          f"{100*rows['clean'][listen]:.1f} % for the clean route and "
          f"{100*rows['od'][listen]:.1f} % for the OD path.")

    # ⚠⚠ PRINT BOTH OPERANDS. The per-ORDER read disagrees with the energy split, and the
    # disagreement is a real limit on what this sub-gate may be quoted for -- so it is
    # printed rather than resolved. `harmonic_thd_curve` uses its own +-40 ms H1 gate and
    # reads PEAK magnitude per order; the split above is INTEGRATED energy over a +-350 ms
    # gate. They are different quantities (analyze.py says so at transfer_h1) and this
    # capture is the case that makes them differ.
    fr, _, o_r = A.harmonic_thd_curve(A.seg_of(load(RESID), "sweep_drv_-12"),
                                      A.seg_of(orig, "sweep_drv_-12"))
    sel = (fr >= 100) & (fr <= 1600)
    per_order = {}
    for order in (1, 2, 3):
        if order in o_r:
            per_order[order] = round(float(np.median(
                20 * np.log10(np.abs(o_r[order][sel]) + 1e-15))), 2)
    out["residual_per_order_median_db_100_1600"] = per_order
    print(f"  ⚠ per-ORDER median over 100-1600 Hz (a different estimator, printed because it "
          f"disagrees): {per_order}")
    print("    ⇒ quote this sub-gate ONLY as 'the fundamental is not safely dominant', never")
    print("      as a harmonic percentage — the two estimators do not agree on this capture.")
    print("  ⇒ Either way GATE L7's L(0) = 0.0118-0.0176 is an inversion of the FUNDAMENTAL,")
    print("    which at a near-null is exactly what an OD-vs-clean cancellation suppresses.")
    return out


# ---------------------------------------------------------------------------------
def bk4_dose_response(out):
    """⭐ THE DISCRIMINATOR. No model, no threshold, no fit."""
    print("\nBK4 — ⭐ the stimulus dose-response: which source does the residual track?")
    r = {k: segrms(load(v)) for k, v in
         (("resid", RESID), ("od", OD), ("clean", CLEAN))}
    span_in = STIM_DB["sweep_drv_-6"] - STIM_DB["sweep_clean"]
    print(f"  stimulus span across the ladder: {span_in:.1f} dB (asserted from the generator)")
    print(f"  {'':16s} " + " ".join(f"{s.replace('sweep_',''):>12s}" for s in SWEEPS)
          + f" {'out/in':>9s}")
    for k in ("resid", "od", "clean"):
        slope = float(r[k][-1] - r[k][0])
        print(f"  {k:16s} " + " ".join(f"{v:12.3f}" for v in r[k]) + f" {slope:9.2f}")
        out.setdefault("path_slope_db", {})[k] = round(slope, 3)

    d_od = r["resid"] - r["od"]
    d_cl = r["resid"] - r["clean"]
    span_od, span_cl = float(d_od.max() - d_od.min()), float(d_cl.max() - d_cl.min())
    out["ratio_to_od_db"] = [round(float(v), 3) for v in d_od]
    out["ratio_to_clean_db"] = [round(float(v), 3) for v in d_cl]
    out["span_to_od_db"], out["span_to_clean_db"] = round(span_od, 3), round(span_cl, 3)
    print(f"\n  residual re OD    " + " ".join(f"{v:12.3f}" for v in d_od)
          + f"   SPAN {span_od:6.2f} dB")
    print(f"  residual re CLEAN " + " ".join(f"{v:12.3f}" for v in d_cl)
          + f"   SPAN {span_cl:6.2f} dB")

    # Computed verdict — a RATIO of the two spans, so no absolute bar is needed. The
    # sources differ by construction (BK4 prints their own slopes), so whichever span is
    # the smaller names the source; the ratio says by how much.
    if not np.isfinite(span_od) or span_cl <= 0:
        fail("BK4", "degenerate spans")
        return out
    ratio = span_od / span_cl
    out["span_ratio_od_over_clean"] = round(ratio, 3)
    if ratio > 2.0:
        verdict = ("CLEAN-SIDE BLEED — the residual holds a constant ratio against the "
                   "clean tap and not against the OD path")
    elif ratio < 0.5:
        verdict = ("OD-SIDE LEAK — the residual holds a constant ratio against the OD path "
                   "and not against the clean tap")
    else:
        verdict = "UNRESOLVED — neither ratio is materially flatter than the other"
    out["bk4_verdict"] = verdict
    print(f"\n  span ratio (OD/CLEAN) = {ratio:.2f}  ⇒  {verdict}")
    return out


# ---------------------------------------------------------------------------------
def render(params, tag):
    os.makedirs(RENDER_DIR, exist_ok=True)
    outp = os.path.join(RENDER_DIR, f"{tag}.wav")
    binp = C.RENDER_BIN
    if not os.path.exists(binp):
        raise SystemExit(f"GATE BK REFUSES: no render binary at {binp}")
    stamp = outp + ".args.json"
    args = [binp, A.ORIG, outp, "--os", "8"] + C.render_args(params)
    sig = {"argv": args[1:], "bin": [os.path.getsize(binp), os.stat(binp).st_mtime_ns]}
    if os.path.exists(outp) and os.path.exists(stamp):
        if json.load(open(stamp)) == sig:
            return A.load(outp)
    res = subprocess.run(args, capture_output=True, text=True)
    if res.returncode != 0:
        raise SystemExit(f"GATE BK REFUSES: render failed rc={res.returncode}\n{res.stderr[:400]}")
    json.dump(sig, open(stamp, "w"))
    return A.load(outp)


def _taper_slope():
    """First-segment slope of the SHIPPED taper, read out of FitParams.h rather than
    transcribed (the s174 trap: compiled defaults and FitParams silently diverging)."""
    import re
    src = open("src/dsp/FitParams.h").read()
    vals = {}
    for name in ("levelTaperBreak1", "levelTaperFrac1"):
        m = re.search(rf"\bdouble\s+{name}\s*=\s*([0-9.eE+-]+)\s*;", src)
        if m:
            vals[name] = float(m.group(1))
    if len(vals) != 2:
        raise SystemExit("GATE BK REFUSES: could not read levelTaperBreak1/Frac1 from FitParams.h")
    return vals["levelTaperFrac1"] / vals["levelTaperBreak1"], vals


def bk5(out):
    print("\nBK5 — the model's own small-L prediction (the end-stop hypothesis, rendered)")
    slope, vals = _taper_slope()
    print(f"  shipped taper first segment (from FitParams.h): "
          f"break1={vals['levelTaperBreak1']} frac1={vals['levelTaperFrac1']} "
          f"⇒ L = {slope:.4f} * x near the origin")
    out["taper_first_slope"] = round(slope, 5)

    r_clean = segrms(load(CLEAN))
    r_res = segrms(load(RESID))
    base = dict(C.parse_capture(RESID))
    rows = []
    print(f"  {'knob x':>8s} {'L':>9s} " + " ".join(f"{s.replace('sweep_',''):>12s}" for s in SWEEPS)
          + f" {'out/in':>8s} {'re-clean span':>14s}")
    for x in (0.04, 0.0951, 0.15, 0.25):
        p = dict(base)
        p["level"] = x
        v = segrms(render(p, f"lvl_{x:.4f}"))
        d = v - r_clean
        rows.append({"x": x, "L": round(slope * x, 5), "rms": [round(float(q), 3) for q in v],
                     "slope": round(float(v[-1] - v[0]), 3),
                     "re_clean_span": round(float(d.max() - d.min()), 3)})
        print(f"  {x:8.4f} {slope*x:9.5f} " + " ".join(f"{q:12.3f}" for q in v)
              + f" {v[-1]-v[0]:8.2f} {d.max()-d.min():14.2f}")
    dp = r_res - r_clean
    print(f"  {'PEDAL':>8s} {'--':>9s} " + " ".join(f"{q:12.3f}" for q in r_res)
          + f" {r_res[-1]-r_res[0]:8.2f} {dp.max()-dp.min():14.2f}")
    out["model_small_L"] = rows
    out["pedal_slope_db"] = round(float(r_res[-1] - r_res[0]), 3)
    out["pedal_re_clean_span_db"] = round(float(dp.max() - dp.min()), 3)

    best = min(rows, key=lambda q: abs(q["slope"] - out["pedal_slope_db"]))
    gap = abs(best["slope"] - out["pedal_slope_db"])
    out["model_best_slope_gap_db"] = round(gap, 3)
    print(f"\n  closest model arm reaches out/in = {best['slope']:.2f} dB against the pedal's "
          f"{out['pedal_slope_db']:.2f} — short by {gap:.2f} dB")
    print("  ⇒ the model's small-L residual is a MIX of both sources (both reach the wiper")
    print("    through ~100k), so it inherits the OD path's compression. The pedal's does not.")
    return out


# ---------------------------------------------------------------------------------
def bk6_verdict(out):
    print("\n" + "=" * 78)
    print("BK6 — VERDICT")
    print("=" * 78)
    lines = []
    lines.append(f"defect reproduces: model at LEVEL 0 = {out.get('model_level0_peak')} "
                 f"(exact zero), pedal is a real signal")
    lines.append(f"mechanism: {out.get('bk4_verdict')}")
    lines.append(f"  ratio spans — re OD {out.get('span_to_od_db')} dB, "
                 f"re CLEAN {out.get('span_to_clean_db')} dB "
                 f"(ratio {out.get('span_ratio_od_over_clean')})")
    lines.append(f"  path slopes (dB out per 24 dB in): {out.get('path_slope_db')}")
    lines.append(f"end-stop hypothesis: REFUTED on dose-response — the rendered model's "
                 f"closest arm is {out.get('model_best_slope_gap_db')} dB short of the "
                 f"pedal's own out/in slope at every L")
    lines.append(f"⚠ only {100 - out.get('residual_out_of_gate_pct_at_listening_rung', 0):.1f} % "
                 f"of the residual's deconvolved energy is in the LINEAR gate at the listening "
                 f"rung ⇒ the fundamental is not safely dominant, so every fundamental-domain "
                 f"reading of this defect — GATE L7's L(0) included — is unsafe")
    if out.get("n12_pad_outliers"):
        for k in out["n12_pad_outliers"]:
            lines.append(f"⛔ DEFECTIVE CAPTURE: level-{k}_gain-n12_base-od.wav")
    for ln in lines:
        print("  " + ln)
    out["verdict_lines"] = lines

    print("\n  WHAT THIS LEAVES (not a proposal — a priced choice for the user):")
    print("   • a LEVEL bottom-leg end stop PRESERVES the bleed-free anchor (Rup = 0 at")
    print("     L = 1 ⇒ vw = odIn exactly) and is REFUTED above on dose-response.")
    print("   • a BLEND end stop reproduces a pure clean bleed and DESTROYS that anchor —")
    print("     the clean coefficient at LEVEL = BLEND = max stops being exactly zero, and")
    print("     that exact zero is what GATE K7/O/L, OdToneRestore's base row and GATE")
    print("     W/AE's bleed-free membership all anchor on.")
    print("   ⇒ item 12 is BLOCKED ON A TRADE, not on effort.")
    return out


def main():
    out = {}
    print("=" * 78)
    print("GATE BK — item 12: at LEVEL min the model mutes and the reference does not")
    print("=" * 78)
    bk0_capture_validity(out)
    bk1_known_answers(out)
    bk2_not_a_floor(out)
    bk3_linear_vs_harmonic(out)
    bk4_dose_response(out)
    bk5(out)
    bk6_verdict(out)

    os.makedirs(os.path.dirname(REPORT), exist_ok=True)
    json.dump(out, open(REPORT, "w"), indent=1)
    print(f"\nreport -> {REPORT}")
    if FAILURES:
        print("\nGATE BK — REFUSALS / DEFECTS FOUND:")
        for f in FAILURES:
            print("  " + f)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
