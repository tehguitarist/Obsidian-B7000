#!/usr/bin/env python3.11
"""GATE BC — DOES THE SHIPPED `OdDriveTilt` DELIVER ITEM 6's TARGET, AND WHAT DOES IT COST?

WHY THIS EXISTS (session 166, task E's third and final capped session)
----------------------------------------------------------------------
Task E's first two sessions refuted two ARCHITECTURES by measurement before anything was built:

    GATE BA (s164)  a LINEAR section DOWNSTREAM of the clipper contributes EXACTLY ZERO
                    drive-tilt (2.04e-14 dB/oct against a wild probe) -- the statistic is a
                    DIFFERENCE between stimulus rungs and a fixed stage cancels from it.
    GATE BB (s165)  a FIXED PRE-CLIPPER pre-emphasis needs a `dP'` spanning a factor of 50
                    across the DRIVE knob -- one sized to close DRIVE min delivers 2.0 % at
                    DRIVE max -- because the clipper's own `dgamma` collapses as the knob rises.

What survived is a section whose OWN COEFFICIENTS move with signal level.  `src/dsp/OdDriveTilt.h`
is that section: one RBJ high-shelf whose gain is driven by an envelope follower on the OD
region's input.  This gate is its acceptance test, against item 6's OWN three gates.

    gate 1  FREQUENCY-DEPENDENT, not a constant tilt.  The deficit STEEPENS
            (-0.39 / -0.78 / -1.44 dB/oct at 1613 / 2032 / 2560 Hz, GATE AG's AG4), so a
            constant-tilt correction is right at one frequency and wrong at the others by a
            growing amount.  BC3 scores the delivered profile against that shape AND against
            the constant-tilt class it has to beat.
    gate 2  POSITION CEILING -- at most -1.199 dB/oct of drive-dependent tilt at the vertex
            before the peak OVERSHOOTS its target.  ⚠ A CEILING, not a target.  BC2 checks the
            tilt against it and BC4 checks the consequence directly, by MEASURING the peak walk
            with GATE W's own locator rather than trusting the vertex law (which GATE AH showed
            cannot even be tested on our side).
    gate 3  CLEAN stays BIT-IDENTICAL -- the correction is OD-only.  BC1c.

⭐ WHAT MAKES THIS GATE POSSIBLE AT ALL is that the stage exposes `--fit odTiltEnabled`, so ON and
OFF are two renders of the SAME BINARY.  A gate that compared two BUILDS would be measuring a
rebuild (`rebaseline-all-derived-artefacts`), and could not hold anything else fixed.

WHAT THIS DOES NOT CLAIM
  * It does not price the MATRIX.  That is `comprehensive_report.py` and it is a separate,
    non-negotiable step before shipping -- this stage moves the OD path's treble at level, so it
    WILL move gate rows, and the size of that is a user decision, not this gate's.
  * It says nothing about hardware -- both sides are the ND captures (`reference-sources.md` §0),
    and §1 gives this region to neither reference outright.
  * It does not address item 6's OTHER symptoms (the bridged-T depth collapse, the bass-peak
    walk, the missing HF null).  Item 6's own scope note confines task E to the treble slope.

Usage:
  python3.11 analysis/od_drive_tilt_gate.py
  python3.11 analysis/od_drive_tilt_gate.py --json analysis/reports/s166_od_drive_tilt.json
"""
import argparse
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import analyze as A                      # noqa: E402
import captures as C                     # noqa: E402
import feature_locus_gate as W           # noqa: E402
import drive_tilt_shape_gate as AG       # noqa: E402  tilt_at / load_af6 — imported, not re-derived
import task_e_placement_gate as BA       # noqa: E402  slope(), fingerprint(), the PRIV rules

PRIV_DIR = os.path.join(os.path.dirname(HERE), "build", "s166_odtilt")
BA_REPORT = os.path.join(HERE, "reports", "s164_task_e_placement.json")

RUNGS = AG.RUNGS

COND = {
    ("DRIVE", "min"): "drive-0700_level-1700_base-od.wav",
    ("DRIVE", "noon"): "level-1700_base-od.wav",
    ("DRIVE", "max"): "drive-1700_level-1700_base-od.wav",
    ("GRUNT", "flat"): "level-1700_grunt-flat_base-od.wav",
    ("GRUNT", "boost"): "level-1700_grunt-boost_base-od.wav",
}
BA_KEY = {("DRIVE", "min"): "flat/min", ("DRIVE", "noon"): "flat/noon",
          ("DRIVE", "max"): "flat/max"}
CLEAN_FILES = ["ref-clean.wav"]

# gate 2's POSITION CEILING and gate 1's shape, both from item 6.  The ceiling is a range in
# CLAUDE.md (-1.193 … -1.199); the tightest end is used, so the check cannot pass on the loose one.
CEILING = 1.193
# GATE AG's AG4 deficit profile and AG5's vertex reading — the SHAPE gate 1 requires.
AG4_PROFILE = {1613.0: -0.39, 2032.0: -0.78, 2560.0: -1.44}
AG5_VERTEX_DEFICIT = -2.038

FAILED = []


def die(tag, msg):
    sys.exit(f"GATE BC {tag} FAIL: {msg}")


def note(tag, msg):
    FAILED.append(f"{tag}: {msg}")
    print(f"   ** {tag} FAIL — {msg}")


def render(fname, on):
    out = os.path.join(PRIV_DIR,
                       fname.replace(".wav", "") + ("_on" if on else "_off") + "_plugin.wav")
    W.render(out, list(C.render_args(C.parse_capture(fname)))
             + ["--fit", f"odTiltEnabled={1 if on else 0}"])
    return out


def curves(fname, on):
    orig, ref = W._load_orig()
    al, _ = A.align(A.load(render(fname, on)), orig)
    return {sw: W.smooth(*A.transfer_h1(A.seg_of(al, sw), ref)) for sw in RUNGS}


def drive_tilt(per, f0):
    return BA.slope(per[RUNGS[-1]], f0) - BA.slope(per[RUNGS[0]], f0)


def bc0(out):
    print("=" * 98)
    print("BC0  MEMBERSHIP AND PROVENANCE")
    if os.path.abspath(PRIV_DIR) == os.path.abspath(W.REN_DIR):
        die("BC0", "the private render dir IS GATE W's cache.")
    for f in COND.values():
        if C.parse_capture(f).get("level") != 1.0:
            die("BC0", f"{f} is not bleed-free (GATE K2).")
    need, curv, vertex, _fr = AG.load_af6()
    tgt = {f: (v / AG5_VERTEX_DEFICIT) * need for f, v in AG4_PROFILE.items()}
    tgt[vertex] = need
    print(f"   conditions   : {len(COND)} bleed-free OD endpoints, 2 axes")
    print(f"   IMPORTED from GATE AF: required drive-tilt {need:+.4f} dB/oct at {vertex:.1f} Hz")
    print(f"   gate 2 CEILING (item 6, tightest end): |tilt| <= {CEILING:.3f} dB/oct")
    print(f"   gate 1 TARGET PROFILE (AG4's deficit shape scaled to the requirement):")
    for f in sorted(tgt):
        print(f"      {f:8.1f} Hz  {tgt[f]:+7.3f} dB/oct")
    out["bc0"] = {"need": need, "vertex": vertex, "ceiling": CEILING,
                  "target_profile": {str(k): v for k, v in tgt.items()}}
    return need, vertex, tgt


def bc1(off, on, vertex, out):
    print()
    print("=" * 98)
    print("BC1  KNOWN ANSWERS")
    rec = {}

    ref = off[("DRIVE", "noon")][RUNGS[0]]
    worst = max(abs((BA.slope(ref + T * np.log2(W.GRID / vertex), vertex) - BA.slope(ref, vertex))
                    - T) for T in (0.0, -0.5, 1.0, -2.5))
    print(f"   (a) injected tilt recovered, worst |error| = {worst:.3e} dB/oct")
    if worst > AG.INJECT_TOL:
        die("BC1a", f"the tilt estimator does not recover an injected tilt ({worst:.3e}).")

    # (b) OFF must reproduce GATE BA's stored baseline — which ALSO proves that
    # `--fit odTiltEnabled=0` genuinely disables the stage rather than merely changing it.
    try:
        with open(BA_REPORT) as fh:
            stored = json.load(fh)["ba3"]["per_cond"]
    except (OSError, KeyError) as e:
        die("BC1b", f"cannot read GATE BA's stored baseline from {BA_REPORT} ({e}).")
    print("   (b) tilt OFF reproduces GATE BA's STORED baseline (and so proves the --fit gate "
          "really disables):")
    worst_b = 0.0
    for k, key in BA_KEY.items():
        got = drive_tilt(off[k], vertex)
        worst_b = max(worst_b, abs(got - stored[key]))
        print(f"       {k[0]} {k[1]:5s}  stored {stored[key]:+.5f}   OFF {got:+.5f}   "
              f"d = {got - stored[key]:+.2e}")
    if worst_b > 1e-9:
        die("BC1b", f"OFF does not reproduce GATE BA's baseline ({worst_b:.3e} dB/oct) — either "
                    f"the gate does not disable the stage, or the baseline has moved (s77).")
    rec["baseline_worst"] = worst_b

    # (c) ⭐ GATE 3 — CLEAN bit-identical.
    print("   (c) ⭐ gate 3 — CLEAN must be BIT-IDENTICAL (the stage is OD-path only):")
    worst_c, n_c = 0.0, 0
    for f in CLEAN_FILES:
        if not os.path.exists(os.path.join(C.CAPTURE_DIR, f)):
            continue
        a, b = A.load(render(f, False)), A.load(render(f, True))
        n = min(len(a), len(b))
        d = float(np.max(np.abs(a[:n] - b[:n])))
        worst_c = max(worst_c, d)
        n_c += 1
        print(f"       {f:30s} max |on - off| = {d:.3e}")
    if n_c == 0:
        die("BC1c", "no CLEAN capture was found, so gate 3 was not tested — an untested gate 3 "
                    "is `empty-gate-must-fail`, not a pass.")
    if worst_c != 0.0:
        note("BC1c", f"CLEAN is NOT bit-identical ({worst_c:.3e}) — gate 3 FAILS and the stage "
                     f"is reaching the clean tap.")
    else:
        print(f"       ⇒ BIT-IDENTICAL over {n_c} capture(s) — gate 3 PASSES")
    rec["clean_worst"], rec["clean_n"] = worst_c, n_c

    # (d) non-vacuity — ON must change the OD render.
    d_od = max(max(float(np.max(np.abs(on[k][sw] - off[k][sw]))) for sw in RUNGS) for k in COND)
    print(f"   (d) non-vacuity: worst |ON - OFF| on the OD curves = {d_od:.3f} dB")
    if d_od < 0.1:
        die("BC1d", f"the stage barely changes the OD render ({d_od:.3e} dB) — every delivery "
                    f"number below would be measuring nothing.")
    rec["od_change"] = d_od
    out["bc1"] = rec


def bc2(off, on, need, vertex, out):
    print()
    print("=" * 98)
    print("BC2  ⭐ DELIVERY — the drive-tilt the stage supplies at the vertex")
    print("   AF6's requirement is what the model must ACQUIRE, so the graded quantity is the")
    print("   ON-minus-OFF CHANGE, not the resulting total.  Both are printed (s117).")
    print()
    print(f"   {'condition':16s}{'OFF':>10s}{'ON':>10s}{'delivered':>12s}{'vs need':>10s}"
          f"{'vs ceiling':>12s}")
    rows, over = {}, []
    for k in COND:
        a, b = drive_tilt(off[k], vertex), drive_tilt(on[k], vertex)
        d = b - a
        rows[f"{k[0]}/{k[1]}"] = [a, b, d]
        ok = abs(d) <= CEILING
        if not ok:
            over.append(k)
        print(f"   {k[0] + ' ' + k[1]:16s}{a:+10.4f}{b:+10.4f}{d:+12.4f}{d / need:10.2f}x"
              f"{'  OK' if ok else '  ** OVER **':>12s}")
    ds = [v[2] for v in rows.values()]
    print(f"\n   delivered {min(ds):+.4f} .. {max(ds):+.4f} dB/oct over {len(ds)} conditions "
          f"(spread {max(ds) - min(ds):.4f})")
    print("   ⭐ The delivery is UNIFORM by construction: the envelope is taken on the OD region's")
    print("     INPUT, which is flat and moves 1:1 with stimulus at every DRIVE setting — so the")
    print("     level DIFFERENCE between rungs is the same 24 dB at every condition.  That is")
    print("     exactly what GATE BB found a fixed pre-clipper section could NOT do (its")
    print("     coefficient collapsed 34x across the same knob).")
    if over:
        note("BC2", f"{len(over)} condition(s) exceed gate 2's ceiling of {CEILING:.3f} dB/oct")
    else:
        print(f"   ⇒ gate 2's CEILING respected at all {len(ds)} conditions")
    out["bc2"] = {"rows": rows, "over": [f"{k[0]}/{k[1]}" for k in over]}


def bc3(off, on, tgt, out):
    print()
    print("=" * 98)
    print("BC3  GATE 1 — is the correction FREQUENCY-DEPENDENT, or a constant tilt?")
    print("   Item 6's gate 1 refutes the constant-tilt class outright.  The delivered profile is")
    print("   scored against the required shape AND against that class, at DRIVE noon.")
    print()
    k = ("DRIVE", "noon")
    need = tgt[max(tgt)]
    print(f"   {'f (Hz)':>9s}{'delivered':>12s}{'target':>10s}{'error':>10s}")
    errs, const_errs = [], []
    prof = {}
    for f in sorted(tgt):
        d = drive_tilt(on[k], f) - drive_tilt(off[k], f)
        prof[str(f)] = d
        errs.append(d - tgt[f])
        const_errs.append(need - tgt[f])
        print(f"   {f:9.1f}{d:+12.4f}{tgt[f]:+10.3f}{d - tgt[f]:+10.3f}")
    rms = float(np.sqrt(np.mean(np.square(errs))))
    rms_const = float(np.sqrt(np.mean(np.square(const_errs))))
    print(f"\n   rms error   SHIPPED {rms:.4f} dB/oct   vs a CONSTANT tilt {rms_const:.4f}")
    better = rms_const / rms if rms > 1e-12 else np.inf
    if rms < rms_const:
        print(f"   ⇒ gate 1 PASSES — the shipped shape beats the refuted constant-tilt class by "
              f"{better:.0f}x")
    else:
        note("BC3", f"the shipped shape is NOT better than a constant tilt ({rms:.4f} vs "
                    f"{rms_const:.4f}) — gate 1 FAILS")
    out["bc3"] = {"profile": prof, "rms": rms, "rms_const": rms_const, "better": better}


def bc4(out):
    print()
    print("=" * 98)
    print("BC4  ⭐⭐ GATE 2's CONSEQUENCE — the PEAK WALK, measured not predicted")
    print("   GATE AH (s137) showed the vertex law CANNOT be tested on our side (predicted")
    print("   +0.601 % vs measured +0.194 %, both under the locator's resolution), so the walk is")
    print("   MEASURED here with GATE W's own locator on GATE W6's own statistic.")
    print("   ⚠ The pedal's -7.35 % is a COMPARAND, never a bar: gate 2 is a CEILING, so what")
    print("     must not happen is OVERSHOOT.")
    print()
    _nm, kind, win, _l = W.FEAT_BY_NAME["treble_peak"]

    def walk(fname, on):
        orig, ref = W._load_orig()
        al, _ = A.align(A.load(render(fname, on)), orig)
        fs = [W.locate(W.smooth(*A.transfer_h1(A.seg_of(al, sw), ref)), win, kind)["f0"]
              for sw in RUNGS]
        return fs, 100.0 * (fs[-1] / fs[0] - 1.0)

    ped = 100.0 * (AG.W6_PEDAL_PEAK_HZ[1] / AG.W6_PEDAL_PEAK_HZ[0] - 1.0)
    rows, bad = {}, []
    for k in (("DRIVE", "noon"), ("DRIVE", "max")):
        for on in (False, True):
            fs, wk = walk(COND[k], on)
            rows[f"{k[0]}/{k[1]}|{'on' if on else 'off'}"] = [fs, wk]
            print(f"   {k[0]} {k[1]:5s} tilt {'ON ' if on else 'OFF'}  "
                  + " -> ".join(f"{x:7.1f}" for x in fs) + f"   walk {wk:+6.2f} %")
        wk_on = rows[f"{k[0]}/{k[1]}|on"][1]
        if wk_on < ped:
            bad.append(k)
    print(f"   {'PEDAL (GATE W6, imported)':44s}" + " " * 12 + f"   walk {ped:+6.2f} %")
    print()
    for k in (("DRIVE", "noon"), ("DRIVE", "max")):
        a = rows[f"{k[0]}/{k[1]}|off"][1]
        b = rows[f"{k[0]}/{k[1]}|on"][1]
        print(f"   {k[0]} {k[1]:5s}: {a:+.2f} % -> {b:+.2f} %, i.e. {100 * b / ped:.0f} % of the "
              f"pedal's walk, {'NO overshoot' if b >= ped else '** OVERSHOOT **'}")
    if bad:
        note("BC4", f"{len(bad)} condition(s) OVERSHOOT the pedal's walk — gate 2's ceiling is "
                    f"breached in its own units")
    else:
        print("   ⇒ gate 2 PASSES in its own units: the peak now walks, and does not overshoot")
    print("   ⭐ Before this stage the model's treble peak was classified FIXED by GATE W6 (0.2 %")
    print("     across the ladder).  This is the first time in the project it has moved with")
    print("     drive at all.")
    out["bc4"] = {"rows": rows, "pedal_pct": ped, "overshoot": [f"{k[0]}/{k[1]}" for k in bad]}


def bc5(off, on, out):
    print()
    print("=" * 98)
    print("BC5  COLLATERAL — the OTHER named features, through GATE W's own locator")
    print("   GATE BB priced route (i)'s collateral at 6 of 6 probes more than HALVING a named")
    print("   feature's prominence, with `mid_peak` going 2.27 -> 0.00 dB.  Same instrument here.")
    print()
    feats = ("mid_notch", "mid_peak", "bt_notch", "treble_peak", "treble_notch")
    k = ("DRIVE", "noon")
    res = {}
    for lab, per in (("OFF", off[k]), ("ON", on[k])):
        d = per[RUNGS[1]]
        cells = []
        for n in feats:
            _nm, kind, win, _l = W.FEAT_BY_NAME[n]
            r = W.locate(d, win, kind)
            cells.append((r["f0"], r["prom"]))
        res[lab] = cells
        print(f"   {lab:4s} " + "  ".join(f"{n}:{a:7.1f}/{b:5.2f}" for n, (a, b) in
                                          zip(feats, cells)))
    moved = []
    for i, n in enumerate(feats):
        if n == "treble_peak":
            continue                       # the target — it is SUPPOSED to move
        f_off, p_off = res["OFF"][i]
        f_on, p_on = res["ON"][i]
        if abs(f_on / max(f_off, 1e-9) - 1.0) > 0.005 or (p_off > 0.5 and p_on < 0.5 * p_off):
            moved.append(n)
    print(f"\n   ⇒ {len(moved)} of {len(feats) - 1} non-target features moved materially: "
          f"{', '.join(moved) if moved else '(none)'}")
    print("   ⚠ `treble_peak` is EXCLUDED from that count — it is the target and is supposed to")
    print("     move; BC4 grades it.")
    out["bc5"] = {"features": {k2: [list(c) for c in v] for k2, v in res.items()},
                  "moved": moved}


def bc6(out):
    print()
    print("=" * 98)
    print("BC6  VERDICT")
    g1 = out["bc3"]["rms"] < out["bc3"]["rms_const"]
    g2 = (not out["bc2"]["over"]) and (not out["bc4"]["overshoot"])
    g3 = out["bc1"]["clean_worst"] == 0.0
    print(f"   gate 1  frequency-dependent, not a constant tilt      "
          f"{'PASS' if g1 else 'FAIL'}   "
          f"(rms {out['bc3']['rms']:.4f} vs {out['bc3']['rms_const']:.4f}, "
          f"{out['bc3']['better']:.0f}x)")
    print(f"   gate 2  position ceiling respected, no overshoot      "
          f"{'PASS' if g2 else 'FAIL'}")
    print(f"   gate 3  CLEAN bit-identical                           "
          f"{'PASS' if g3 else 'FAIL'}   ({out['bc1']['clean_worst']:.1e})")
    print(f"   collateral: {len(out['bc5']['moved'])} non-target feature(s) moved")
    ok = g1 and g2 and g3
    print()
    if ok:
        print("   ⇒ THE STAGE MEETS ITEM 6's THREE GATES.")
        print("   ⛔ THAT IS NOT A SHIP DECISION.  This stage moves the OD path's treble at level,")
        print("     so it WILL move release-gate rows — `comprehensive_report.py` prices that and")
        print("     the trade is a USER decision, exactly as s162's and s163's were.")
    else:
        print("   ⇒ THE STAGE DOES NOT MEET ITEM 6's GATES — do not ship it.")
    print()
    print(f"   BC6-MEMBERSHIP conditions=[{','.join(sorted(COND.values()))}]")
    print(f"   BC6-VERDICT gate1={g1} gate2={g2} gate3={g3} "
          f"delivered_spread={max(v[2] for v in out['bc2']['rows'].values()) - min(v[2] for v in out['bc2']['rows'].values()):.4f}")
    out["bc6"] = {"gate1": bool(g1), "gate2": bool(g2), "gate3": bool(g3), "meets": bool(ok)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", default=None)
    args = ap.parse_args()
    os.makedirs(PRIV_DIR, exist_ok=True)
    out = {}
    need, vertex, tgt = bc0(out)

    before = BA.fingerprint(W.REN_DIR)
    print(f"\n   rendering {2 * (len(COND) + len(CLEAN_FILES))} conditions (tilt ON and OFF) ...")
    off = {k: curves(f, False) for k, f in COND.items()}
    on = {k: curves(f, True) for k, f in COND.items()}
    print("   done")

    bc1(off, on, vertex, out)
    bc2(off, on, need, vertex, out)
    bc3(off, on, tgt, out)
    bc4(out)
    bc5(off, on, out)
    bc6(out)

    if BA.fingerprint(W.REN_DIR) != before:
        die("BC0", "GATE W's render cache CHANGED during this run.")
    print(f"\n   GATE W cache integrity: {len(before)} files unchanged")
    if args.json:
        with open(args.json, "w") as fh:
            json.dump(out, fh, indent=1)
        print(f"   wrote {args.json}")
    print("=" * 98)
    sys.exit(1 if FAILED else 0)


if __name__ == "__main__":
    main()
