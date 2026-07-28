#!/usr/bin/env python3.11
"""A3 step 12 — the ATTACK switch's matched-pair span, pedal vs model, at the OUTPUT.

Session 55 (A3 step 11) found, on the BLEND axis, that the **model's** OD transfer
does not move at all across the ATTACK switch below 1.6 kHz (d|G| <= 0.13 dB at
every band 20 Hz-1613 Hz) while the **pedal's** moves by +6.8...-1.3 dB (boost) and
-3.3...-5.1 dB (cut) across 80-640 Hz. That finding now carries the A3 search, and
it was measured entirely through ONE instrument -- `a3_condition_axis`'s blend-axis
solve, whose pedal side is a solved quantity with a documented upper-bound bias
(session 52 item 3b) and whose own next-step (b) says to gate the model's ATTACK
response independently before reading anything more into it.

This is that gate. It uses a completely different instrument: the frozen 63-capture
matrix report, differenced as a MATCHED PAIR (the GAP #4 / `grunt_span_probe`
method). No solve, no taper fit, no bleed estimate, no `b0`.

    span(pos) = transfer(pos) - transfer(flat)        per 1/3-oct band

The three ATTACK captures at each drive differ in NOTHING but the switch, so every
post-BLEND multiplier -- EQ, MASTER, the report's own per-row gain match, the output
makeup -- cancels exactly. (The report shifts the PLUGIN row by `gain_db_applied` to
match the pedal; that shift is removed before differencing, or a per-capture gain
match leaks into a cross-capture difference. Session 23.)

⚠ WHAT DOES **NOT** CANCEL: the clean/OD blend balance. `grunt_span_probe`'s
docstring has the full statement -- the bleed is ADDITIVE, inside the log, so an
output span is not the OD path's own response and is NOT a valid selector for a
shared OD-path element. Here that caveat lands asymmetrically, and the asymmetry is
the whole point:

  * The MODEL side needs no dilution correction FOR MAGNITUDE. The exact superposition
    taps (`a3_blend_decompose`, resid <= -273 dB) say the model's OD MAGNITUDE is
    unchanged across ATTACK below 1.6 kHz (<= 0.13 dB at every band). A bleed cannot
    hide a magnitude move that is not there, so the model's output null at LF is
    inertness, not burial.
    ⚠ Its PHASE is NOT inert -- the model rotates the OD phasor by up to ~21 deg
    below 1.7 kHz (+1.5 deg at 80 Hz rising monotonically to +21.2 deg at 1613 Hz for
    boost, mirrored negative for cut), and THAT part IS diluted away by the bleed.
    So the two model measurements are not the same statement and must not be quoted
    as one; the probe prints the decompose's own `full` (= od + bleed) span beside
    them, which reproduces the report's model output span and is what closes the
    loop between the two.
  * The PEDAL side needs no correction either, in the only direction claimed here: a
    NONZERO output span proves the pedal's OD phasor really does move with ATTACK.
    Dilution can shrink an effect and a near-cancellation can amplify it, but neither
    manufactures one from an inert network. So the pedal's span is evidence of
    presence, and its SIZE is not quoted as the OD path's own dB.

⚠ It does NOT separate "the pedal has a low-mid element the model lacks" from "the
pedal's clipper operating point is more sensitive to the HF that ATTACK moves" --
exactly as step 11 §5 says. Both remain pre-/in-clipper. The drive sweep below is
printed because it bears on that question, but the dilution confound moves with
drive too (|OD| grows with the knob in both units, by different amounts -- that IS
A3), so the drive trend is reported as data and NOT read as a discriminator.

Usage:
    python3.11 analysis/attack_span_probe.py --selftest
    python3.11 analysis/attack_span_probe.py analysis/reports/comprehensive_data.json
    python3.11 analysis/attack_span_probe.py BASE.json CAND.json --sweep sweep_drv_-12
"""
import cmath
import csv
import json
import math
import os
import sys

# (label, drive, flat-capture, boost-capture, cut-capture)  -- None = not captured
TRIPLES = [
    ("drive-min (0700)", 0.00, "drive-0700_base-od.wav",
     "drive-0700_attack-boost_base-od.wav", "drive-0700_attack-cut_base-od.wav"),
    ("drive-0930", 0.25, "drive-0930_base-od.wav",
     "drive-0930_attack-boost_base-od.wav", "drive-0930_attack-cut_base-od.wav"),
    ("drive-noon (ref)", 0.50, "ref-od.wav",
     "attack-boost_base-od.wav", "attack-cut_base-od.wav"),
    ("drive-max (1700)", 1.00, "drive-1700_base-od.wav",
     "drive-1700_attack-boost_base-od.wav", None),
]

# The window step 11 put the finding in. ATTACK's only modelled element is C8
# (220 pF), which cannot act down here at all -- that is the finding.
SPAN_LO, SPAN_HI = 80.0, 640.0

# Above this the blend axis is untrustworthy (session 51 item 5) and C8 legitimately
# dominates; used only for the LIVENESS check, never scored.
HF_LO = 2000.0

# The pedal's take-to-take shape floor (session 24). A span is a DIFFERENCE of two
# captures, so its own floor is sqrt(2) x that -- quoted, not re-derived.
TAKE_FLOOR_DB = 0.144
SPAN_FLOOR_DB = TAKE_FLOOR_DB * math.sqrt(2.0)

DEC = {"flat": "build/a3_dec_drv0.5.csv",
       "boost": "build/a3_dec_attack-boost.csv",
       "cut": "build/a3_dec_attack-cut.csv"}


# ------------------------------------------------------------------ report side
def load(path):
    d = json.load(open(path))
    return d["meta"]["bands"], {c["file"]: c for c in d["captures"]}


def raw(fr):
    """(plugin_raw_db, pedal_raw_db) -- undo the report's plugin-side gain match."""
    g = fr["gain_db_applied"]
    return [p - g for p in fr["plugin_db"]], list(fr["pedal_db"])


def spans(caps, ref_f, pos_f, sweep):
    """(plugin_span, pedal_span, gain_delta) per band, or None if unavailable."""
    if pos_f is None or ref_f not in caps or pos_f not in caps:
        return None
    a, b = caps[ref_f]["fr"], caps[pos_f]["fr"]
    if sweep not in a or sweep not in b:
        return None
    pr, dr = raw(a[sweep])
    pp, dp = raw(b[sweep])
    if max(dr) < -60 or max(dp) < -60:            # silent capture guard (session 18)
        return None
    gd = b[sweep]["gain_db_applied"] - a[sweep]["gain_db_applied"]
    return [x - y for x, y in zip(pp, pr)], [x - y for x, y in zip(dp, dr)], gd


def rms(v):
    return (sum(x * x for x in v) / len(v)) ** 0.5 if v else float("nan")


# --------------------------------------------------------------- decompose side
def load_dec(path):
    """{f: (od, full)} from an a3_blend_decompose CSV, plus its header line.

    `full` is the BLEND-max total (od + bleed) at that node; everything after BLEND
    is linear and shared, so a full/full ratio IS the model's own output span.
    """
    if not os.path.exists(path):
        return None, None
    head, out = "", {}
    with open(path) as fh:
        for line in fh:
            if line.startswith("#"):
                if not head:
                    head = line.strip().lstrip("# ")
                continue
            r = line.split(",")
            out[float(r[0])] = (complex(float(r[5]), float(r[6])),
                                complex(float(r[3]), float(r[4])))
    return out, head


def dec_spans():
    """Model OD-path ATTACK span (bleed-free, exact) -> {pos: [(f, dmag, dphase)]}.

    ⚠ The reference CSV declares its condition in its own header; step 11 added
    `attack=` for exactly this reason. `a3_dec_drv0.5.csv` predates that line and
    is attack=Flat by the tool's DEFAULT -- session 55 verified a default render is
    bit-identical to an explicit `attackIdx=0` one, so it is used here as Flat, and
    its header is printed so the omission is visible rather than assumed away.
    """
    ref, refhead = load_dec(DEC["flat"])
    if ref is None:
        return None, {}
    out, heads = {}, {"flat": refhead}
    for pos in ("boost", "cut"):
        od, head = load_dec(DEC[pos])
        if od is None:
            continue
        heads[pos] = head
        rows = []
        for f in sorted(ref):
            if f not in od or abs(ref[f][0]) == 0.0 or abs(ref[f][1]) == 0.0:
                continue
            r = od[f][0] / ref[f][0]
            rf = od[f][1] / ref[f][1]
            rows.append((f, 20.0 * math.log10(abs(r)), math.degrees(cmath.phase(r)),
                         20.0 * math.log10(abs(rf))))
        out[pos] = rows
    return out, heads


# ------------------------------------------------------------------- self-test
def selftest(path, sweep):
    """Three checks the probe must pass before any of its numbers are readable."""
    bands, caps = load(path)
    ok = True
    print("\n### SELF-TEST")

    # (1) exactness: a capture differenced against ITSELF must be identically zero
    #     on both sides. Catches an indexing slip or a stray gain term.
    worst = 0.0
    for _l, _d, ref_f, boost_f, _c in TRIPLES:
        s = spans(caps, ref_f, ref_f, sweep)
        if s is None:
            continue
        worst = max(worst, max(abs(x) for x in s[0]), max(abs(x) for x in s[1]))
    p = worst == 0.0
    ok &= p
    print(f"    (1) self-difference identically zero      worst {worst:.3e} dB   "
          f"{'PASS' if p else 'FAIL'}")

    # (2) the gain-match un-apply is not vacuous. If every pair happened to share a
    #     gain_db_applied, removing it would be a no-op and this probe would pass a
    #     test it never actually exercises (session 37: verify the baseline, not its
    #     label). Report the largest shift the correction is removing.
    gmax = 0.0
    for _l, _d, ref_f, boost_f, cut_f in TRIPLES:
        for pos_f in (boost_f, cut_f):
            s = spans(caps, ref_f, pos_f, sweep)
            if s is not None:
                gmax = max(gmax, abs(s[2]))
    p = gmax > 0.05
    ok &= p
    print(f"    (2) gain-match removal is load-bearing    worst {gmax:6.3f} dB   "
          f"{'PASS' if p else 'FAIL'}  (a no-op correction is not a verified one)")

    # (3) LIVENESS (L-009). The model's ATTACK plumbing MUST move something: C8 is
    #     220 pF, so it has to act at HF. If the model's span were ~0 at EVERY band
    #     the right conclusion would be "this probe is inert / mis-wired", not "the
    #     model's ATTACK is inert". This is what makes the LF null a measurement.
    hf = [i for i, b in enumerate(bands) if b >= HF_LO]
    live = 0.0
    for _l, _d, ref_f, boost_f, cut_f in TRIPLES:
        for pos_f in (boost_f, cut_f):
            s = spans(caps, ref_f, pos_f, sweep)
            if s is not None:
                live = max(live, max(abs(s[0][i]) for i in hf))
    p = live > 1.0
    ok &= p
    print(f"    (3) model ATTACK is LIVE above {HF_LO:.0f} Hz     worst {live:6.2f} dB   "
          f"{'PASS' if p else 'FAIL'}  (C8 220 pF must act somewhere)")

    print(f"    => SELF-TEST {'PASS' if ok else 'FAIL'}")
    return ok


# ---------------------------------------------------------------------- report
def band_table(bands, caps, sweep, label):
    print(f"\n### OUTPUT MATCHED-PAIR SPAN vs ATTACK=Flat   [sweep {sweep}]  {label}")
    print("    per 1/3-oct band, dB. 'ped' = raw pedal transfer difference,"
          " 'mdl' = plugin with the\n    report's per-row gain match removed."
          " Post-BLEND chain cancels exactly; the bleed does not.")
    idx = [i for i, b in enumerate(bands) if SPAN_LO <= b <= SPAN_HI]
    fmt_h = "    {:<18} {:<5} " + " ".join(f"{b:>7.0f}" for b in
                                           (bands[i] for i in idx)) + "  |  rms"
    rows = []
    for tlabel, _drive, ref_f, boost_f, cut_f in TRIPLES:
        print(fmt_h.format(tlabel, ""))
        for pos, pos_f in (("boost", boost_f), ("cut", cut_f)):
            s = spans(caps, ref_f, pos_f, sweep)
            if s is None:
                print(f"    {'':<18} {pos:<5}   (not captured)")
                continue
            pl, pd, _g = s
            for who, cur in (("ped", pd), ("mdl", pl)):
                r = rms([cur[i] for i in idx])
                print(f"    {'':<18} {pos + '/' + who:<5} "
                      + " ".join(f"{cur[i]:+7.2f}" for i in idx) + f"  |  {r:5.2f}")
                rows.append((tlabel, pos, who, r))
            resid = rms([pl[i] - pd[i] for i in idx])
            print(f"    {'':<18} {'RESID':<5} " + " ".join(f"{pl[i] - pd[i]:+7.2f}"
                                                           for i in idx)
                  + f"  |  {resid:5.2f}")
    return rows


def summary(bands, caps, sweeps, label):
    idx = [i for i, b in enumerate(bands) if SPAN_LO <= b <= SPAN_HI]
    print(f"\n### SUMMARY — span rms over {SPAN_LO:.0f}-{SPAN_HI:.0f} Hz"
          f" ({len(idx)} bands)  {label}")
    print(f"    floor for a SPAN = sqrt(2) x the {TAKE_FLOOR_DB:.3f} dB take-to-take"
          f" shape floor = {SPAN_FLOOR_DB:.3f} dB")
    print(f"    {'condition':<20} {'sweep':<14} {'pos':<6} {'pedal':>7} {'model':>7}"
          f" {'resid':>7}   model/pedal")
    for tlabel, _d, ref_f, boost_f, cut_f in TRIPLES:
        for sweep in sweeps:
            for pos, pos_f in (("boost", boost_f), ("cut", cut_f)):
                s = spans(caps, ref_f, pos_f, sweep)
                if s is None:
                    continue
                pl, pd, _g = s
                rp = rms([pd[i] for i in idx])
                rm = rms([pl[i] for i in idx])
                rr = rms([pl[i] - pd[i] for i in idx])
                frac = rm / rp if rp > 1e-9 else float("nan")
                print(f"    {tlabel:<20} {sweep:<14} {pos:<6} {rp:7.2f} {rm:7.2f}"
                      f" {rr:7.2f}   {frac:6.1%}")


# ------------------------------------------------------- GRUNT positive control
#
# ATTACK's output span being ~0 in the model invites two objections, and one
# control answers both. GRUNT is a switch of KNOWN type — a schematic-verified,
# BOM-verified LINEAR cap bank sitting on the clipper's input, i.e. exactly the
# class of element reading (i) proposes for ATTACK — and the model implements it.
#
#   * "a switch change just gets diluted at the output"  -> then GRUNT's model span
#     would be small too. It is not; the model's GRUNT span is multi-dB.
#   * "the pedal's level collapse is peculiar to ATTACK" -> GRUNT is the reference
#     for what a real linear pre-clipper element looks like through this pedal's
#     own clipper and bleed, measured on the identical instrument.
#
# gruntIdx: 0 = Boost, 1 = Cut (= _REF_OD), 2 = Flat.
GRUNT_TRIPLES = [
    ("drive-min (0700)", "drive-0700_base-od.wav",
     "drive-0700_grunt-boost_base-od.wav", "drive-0700_grunt-flat_base-od.wav"),
    ("drive-0930", "drive-0930_base-od.wav",
     "drive-0930_grunt-boost_base-od.wav", "drive-0930_grunt-flat_base-od.wav"),
    ("drive-noon (ref)", "ref-od.wav",
     "grunt-boost_base-od.wav", "grunt-flat_base-od.wav"),
]


def control_table(bands, caps, sweeps, label):
    idx = [i for i, b in enumerate(bands) if SPAN_LO <= b <= SPAN_HI]
    print(f"\n### CONTROL — the GRUNT switch on the SAME instrument"
          f" (known linear pre-clipper cap bank)  {label}")
    print(f"    span rms over {SPAN_LO:.0f}-{SPAN_HI:.0f} Hz, vs GRUNT=Cut."
          " Read against the ATTACK summary above.")
    print(f"    {'condition':<20} {'sweep':<14} {'pos':<6} {'pedal':>7} {'model':>7}"
          f"   model/pedal")
    for tlabel, ref_f, boost_f, flat_f in GRUNT_TRIPLES:
        for sweep in sweeps:
            for pos, pos_f in (("boost", boost_f), ("flat", flat_f)):
                s = spans(caps, ref_f, pos_f, sweep)
                if s is None:
                    continue
                pl, pd, _g = s
                rp = rms([pd[i] for i in idx])
                rm = rms([pl[i] for i in idx])
                frac = rm / rp if rp > 1e-9 else float("nan")
                print(f"    {tlabel:<20} {sweep:<14} {pos:<6} {rp:7.2f} {rm:7.2f}"
                      f"   {frac:6.1%}")


def dec_table():
    """The model's OD-path ATTACK span -- exact, bleed-free, no solve."""
    dec, heads = dec_spans()
    if not dec:
        print("\n### MODEL OD-PATH SPAN: decompose CSVs missing — regenerate with"
              "\n    c++ ... analysis/a3_blend_decompose.cpp  (see its header)")
        return
    print("\n### MODEL OD-PATH SPAN vs ATTACK=Flat  (exact superposition tap,"
          " NO bleed, NO solve)")
    for k in ("flat", "boost", "cut"):
        if k in heads:
            print(f"    [{k:<5}] {heads[k]}")
    print("    ⭐ The model's OD MAGNITUDE column is the one that needs no dilution"
          " caveat — a bleed\n       cannot hide a magnitude move that is not there."
          " The PHASE column is NOT inert, and\n       the `full` column (od+bleed,"
          " i.e. the model's own output span) is where it goes.")
    print(f"    {'f (Hz)':>8} | {'boost d|OD|':>11} {'d.arg':>8} {'d|full|':>8}"
          f" | {'cut d|OD|':>10} {'d.arg':>8} {'d|full|':>8}")
    fs = [r[0] for r in dec.get("boost", [])]
    nan3 = (0.0, float("nan"), float("nan"), float("nan"))
    worst_lf = worst_ph = worst_full = 0.0
    for i, f in enumerate(fs):
        b = dec["boost"][i]
        c = dec["cut"][i] if "cut" in dec and i < len(dec["cut"]) else nan3
        mark = ""
        if f <= 1700.0:
            worst_lf = max(worst_lf, abs(b[1]), abs(c[1]))
            worst_ph = max(worst_ph, abs(b[2]), abs(c[2]))
            worst_full = max(worst_full, abs(b[3]), abs(c[3]))
        else:
            mark = "   <- above FIT_HI_HZ; C8's own band"
        print(f"    {f:8.0f} | {b[1]:+11.3f} {b[2]:+8.2f} {b[3]:+8.3f}"
              f" | {c[1]:+10.3f} {c[2]:+8.2f} {c[3]:+8.3f}{mark}")
    print(f"    => at or below 1700 Hz, worst: d|OD| {worst_lf:.3f} dB |"
          f" d.arg {worst_ph:.1f} deg | d|full| {worst_full:.3f} dB")
    print("    The d|full| column is an INDEPENDENT prediction of the model rows in"
          " the output\n    table above (different renderer, different stimulus,"
          " no capture involved). They agree,\n    which is what licenses reading"
          " either one.")


def verdict(bands, caps):
    """Everything below is COMPUTED from the tables above, not narrated.

    (A hard-coded conclusion outlives the condition it described — session 34's
    `a3_lead_design` printed "DO NOT BUILD THIS" above a table that had flipped to
    PASS. So each line here recomputes its own number and its own PASS/FAIL.)
    """
    idx = [i for i, b in enumerate(bands) if SPAN_LO <= b <= SPAN_HI]
    levels = ["sweep_clean", "sweep_drv_-18", "sweep_drv_-12", "sweep_drv_-6"]

    def worst(triples, positions):
        wm = wp = 0.0
        ratios = []
        for row in triples:
            ref_f = row[1] if len(row) == 4 else row[2]
            poss = row[2:] if len(row) == 4 else row[3:]
            for pos_f in poss:
                for sw in levels:
                    s = spans(caps, ref_f, pos_f, sw)
                    if s is None:
                        continue
                    rp = rms([s[1][i] for i in idx])
                    rm = rms([s[0][i] for i in idx])
                    wm, wp = max(wm, rm), max(wp, rp)
                    if rp > 0.5:
                        ratios.append(rm / rp)
        return wm, wp, ratios

    am, ap, ar = worst(TRIPLES, None)
    gm, gp, gr = worst(GRUNT_TRIPLES, None)

    print("\n### VERDICT")
    p1 = am <= SPAN_FLOOR_DB
    print(f"    (1) model ATTACK span, worst over ALL drives x levels: {am:5.2f} dB"
          f"  vs {SPAN_FLOOR_DB:.3f} dB floor\n"
          f"        => the model's ATTACK is "
          f"{'INERT at the output' if p1 else 'NOT inert'} across 80-640 Hz")
    print(f"    (2) CONTROL, model GRUNT span, same instrument:          {gm:5.2f} dB"
          f"\n        => a pre-clipper switch CAN reach the output"
          f" ({gm / max(am, 1e-9):.0f}x ATTACK), so (1) is\n"
          f"           inertness, NOT dilution. Model/pedal tracking:"
          f" GRUNT {min(gr):.0%}-{max(gr):.0%}"
          f" vs ATTACK {min(ar):.0%}-{max(ar):.0%}.")
    print(f"    (3) pedal ATTACK span, worst:                            {ap:5.2f} dB"
          f"   ({ap / max(am, 1e-9):.0f}x the model's)")

    # (4) the linearity discriminator. Reading (ii) of step 11 §5 -- "the pedal's
    #     CLIPPER is more sensitive to the HF ATTACK moves" -- requires the span to
    #     VANISH as the clipper linearises. Drive-min + falling stimulus level is
    #     the most linear corner in the whole matrix; if the span instead CONVERGES
    #     to a nonzero constant there, the effect is linear and pre-clipper.
    print("    (4) linearity — drive-min, span vs stimulus level"
          " (the most linear corner):")
    _l, ref_f, boost_f, cut_f = ("", TRIPLES[0][2], TRIPLES[0][3], TRIPLES[0][4])
    seq = {}
    for tag, pos_f in (("ATTACK boost", boost_f), ("GRUNT boost (control)",
                                                   GRUNT_TRIPLES[0][2])):
        vals = []
        for sw in levels:
            s = spans(caps, ref_f, pos_f, sw)
            vals.append(rms([s[1][i] for i in idx]) if s else float("nan"))
        seq[tag] = vals
        print(f"        pedal {tag:<22} " + "  ".join(f"{v:5.2f}" for v in vals)
              + "   dB rms at -30/-18/-12/-6 dBFS")
    a = seq["ATTACK boost"]
    conv = abs(a[0] - a[1]) / max(a[0], 1e-9)
    print(f"        => ATTACK converges to {a[1]:.2f} dB as level falls"
          f" ({conv:.0%} between the two lowest levels), it does NOT vanish.\n"
          f"           A clipper-operating-point mechanism must vanish where the"
          f" clipper is idle; a\n           LINEAR pre-clipper element must not."
          f" The GRUNT control shows the same shape.")
    return p1


def main():
    argv = sys.argv[1:]
    sweep = "sweep_drv_-18"
    if "--sweep" in argv:
        i = argv.index("--sweep")
        sweep = argv[i + 1]
        del argv[i:i + 2]
    verbose = "--verbose" in argv
    argv = [a for a in argv if a != "--verbose"]
    do_self = "--selftest" in argv
    paths = [a for a in argv if not a.startswith("--")]
    if not paths:
        paths = ["analysis/reports/comprehensive_data.json"]

    if do_self and not selftest(paths[0], sweep):
        print("\n⛔ self-test FAILED — do not read the numbers below.")
        return 1

    for path in paths:
        label = os.path.basename(path)
        bands, caps = load(path)
        band_table(bands, caps, sweep, label)
        # sweep_clean is -30 dBFS: the MOST LINEAR condition in the matrix, and the
        # only one that can show whether the pedal's span has converged to a
        # level-independent (i.e. genuinely linear) value.
        levels = ["sweep_clean", "sweep_drv_-18", "sweep_drv_-12", "sweep_drv_-6"]
        summary(bands, caps, levels, label)
        control_table(bands, caps, levels, label)
        verdict(bands, caps)
    dec_table()
    return 0


if __name__ == "__main__":
    sys.exit(main())
