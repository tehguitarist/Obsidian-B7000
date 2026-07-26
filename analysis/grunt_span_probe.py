#!/usr/bin/env python3.11
"""GAP #3b / C13: the GRUNT switch's matched-pair SPAN, plugin vs pedal.

The GAP #4 method, applied to GRUNT. The capture matrix holds three captures that
differ in NOTHING but the GRUNT position (same drive/level/blend/EQ/attack, same
input), so a position-to-position DIFFERENCE cancels every POST-BLEND multiplier
EXACTLY -- every EQ band, the gain-match, the output makeup.

⚠⚠ IT DOES **NOT** CANCEL THE CLEAN/OD BLEND BALANCE, and an earlier version of
this docstring claimed it did (corrected session 38). The measured total is
`OD(pos) + bleed` -- the bleed is ADDITIVE, inside the log, so it does not divide
out of a position-to-position ratio the way a post-BLEND gain does. Consequences,
both load-bearing:

  * the span at the OUTPUT is NOT the GRUNT network's own response. The OD path's
    GRUNT span is a monotone high-pass SHELF at every value (verified by exact
    decomposition, `a3_blend_decompose`), but once |OD| falls below the bleed at
    LF the OUTPUT span presents as a BUMP. Session 23 read the model's shelf
    against the pedal's output bump and concluded "no cap can convert one into
    the other" -- true of the OD path, but the BLEND sum does the conversion, and
    once trebleC7/clipC15 fixed the OD/bleed ratio the model's output span became
    a bump on its own with the GRUNT caps untouched. Same category error as GAP
    #1b (session 21: isolated stage transfer vs the pedal's output shape).
  * ⛔ this metric MUST NOT be used to select a SHARED OD-path element. It is
    sensitive to the OD/bleed ratio, i.e. to A3, so it scores an element that
    attenuates the OD path as an improvement. Measured directly: it prefers
    `clipC15 = 1.5 nF` (3.654/1.755) over the shipped 5.2 nF (6.862/4.507) -- the
    value session 37 rejected on beta-free evidence. Use it ONLY for GRUNT-side
    elements (C11/C12/C13, R16), where the position-to-position difference really
    is the differential.

Whatever is left, read with those caveats, is the GRUNT coupling network:

    span(pos) = transfer(pos) - transfer(cut)        per 1/3-oct band

measured separately in the pedal and in the plugin. `pedal_db` in the report is
the RAW pedal transfer; the report shifts the PLUGIN by `gain_db_applied` to
match it, so that shift is removed here before differencing (otherwise a
per-capture gain-match leaks into a cross-capture difference).

Why this and not the aggregate band-RMS: only `clipC13` moves the Boost position,
so a candidate can improve the aggregate by flattening Boost toward Flat --
scoring well while destroying the switch's differentiation. That is exactly the
joint mid-cap fit REJECTED in GAP #4 (it collapsed LO-MID "250" onto the 500 Hz
position's own cap). The span shows it; the aggregate hides it.

The pairs, with gruntIdx: 0 = Boost, 1 = Cut, 2 = Flat.
  drive=0.50 (noon): ref-od.wav (cut) / grunt-flat / grunt-boost
  drive=0.00 (min) : drive-0700_base-od (cut) / _grunt-flat / _grunt-boost
The drive-min triple is the one that discriminates cap VALUE from clipper
compression: at minimum drive the clipper is ~linear, so the span there is the
coupling network's own linear response, not a compression artifact.

Usage:
    python3.11 analysis/grunt_span_probe.py reports/comprehensive_data.json
    python3.11 analysis/grunt_span_probe.py BASE.json CAND1.json CAND2.json ...
"""
import json
import sys

# (label, drive, cut-capture, flat-capture, boost-capture)
TRIPLES = [
    ("drive-min (0700)", 0.00, "drive-0700_base-od.wav",
     "drive-0700_grunt-flat_base-od.wav", "drive-0700_grunt-boost_base-od.wav"),
    ("drive-0930", 0.25, "drive-0930_base-od.wav",
     "drive-0930_grunt-flat_base-od.wav", "drive-0930_grunt-boost_base-od.wav"),
    ("drive-noon (ref)", 0.50, "ref-od.wav",
     "grunt-flat_base-od.wav", "grunt-boost_base-od.wav"),
]

# The GRUNT coupling corners live here (circuit.md: 896 / 144 / 36 Hz at A0 ~20-30),
# so this is where the switch actually does something. Above ~600 Hz all three
# positions are on their plateau and the span is ~0 by construction.
SPAN_LO, SPAN_HI = 25.0, 640.0


def load(path):
    d = json.load(open(path))
    return d["meta"]["bands"], {c["file"]: c for c in d["captures"]}


def raw(fr):
    """(plugin_raw_db, pedal_raw_db) -- undo the report's plugin-side gain match."""
    g = fr["gain_db_applied"]
    return [p - g for p in fr["plugin_db"]], list(fr["pedal_db"])


def spans(caps, cut_f, pos_f, sweep):
    """(plugin_span, pedal_span) per band, or None if either capture/sweep is missing."""
    if cut_f not in caps or pos_f not in caps:
        return None
    c, p = caps[cut_f]["fr"], caps[pos_f]["fr"]
    if sweep not in c or sweep not in p:
        return None
    pc, dc = raw(c[sweep])
    pp, dp = raw(p[sweep])
    if max(dc) < -60 or max(dp) < -60:
        return None
    return [a - b for a, b in zip(pp, pc)], [a - b for a, b in zip(dp, dc)]


def rms(v):
    return (sum(x * x for x in v) / len(v)) ** 0.5


def report(path, label, sweep, verbose):
    bands, caps = load(path)
    idx = [i for i, b in enumerate(bands) if SPAN_LO <= b <= SPAN_HI]
    print(f"\n### {label}   [sweep {sweep}, span band {SPAN_LO:.0f}-{SPAN_HI:.0f} Hz]")
    errs = []
    for tlabel, _drive, cut_f, flat_f, boost_f in TRIPLES:
        row = []
        for pos, pos_f in (("flat", flat_f), ("boost", boost_f)):
            s = spans(caps, cut_f, pos_f, sweep)
            if s is None:
                continue
            pl, pd = s
            err = rms([pl[i] - pd[i] for i in idx])
            row.append((pos, pl, pd, err))
            errs.append(err)
        if not row:
            continue
        print(f"  {tlabel}")
        for pos, pl, pd, err in row:
            print(f"    {pos:<6} span@40Hz  pedal {pd[3]:+7.2f}  plugin {pl[3]:+7.2f}"
                  f"   | @100Hz  {pd[7]:+7.2f} / {pl[7]:+7.2f}"
                  f"   | span-err RMS {err:6.2f} dB")
        # The ordering check: does boost deliver MORE low end than flat, as measured?
        if len(row) == 2:
            fl, bo = row[0], row[1]
            for name, i, hz in (("40 Hz", 3, 40), ("100 Hz", 7, 100)):
                dped = bo[2][i] - fl[2][i]
                dplg = bo[1][i] - fl[1][i]
                flag = "" if (dped > 0) == (dplg > 0) else "   <-- ORDER INVERTED"
                print(f"    boost-minus-flat @{name:<7} pedal {dped:+7.2f}"
                      f"   plugin {dplg:+7.2f}{flag}")
        if verbose:
            print(f"    {'band':>8}" + "".join(f"{bands[i]:>9.0f}" for i in idx))
            for pos, pl, pd, _e in row:
                print(f"    {pos + ' ped':>8}" + "".join(f"{pd[i]:9.2f}" for i in idx))
                print(f"    {pos + ' plg':>8}" + "".join(f"{pl[i]:9.2f}" for i in idx))
    if errs:
        print(f"  MEAN span-err RMS over {len(errs)} pos-pairs: {sum(errs) / len(errs):.3f} dB")
    return sum(errs) / len(errs) if errs else float("nan")


def main():
    paths = [a for a in sys.argv[1:] if not a.startswith("--")]
    verbose = "--verbose" in sys.argv
    sweeps = ["sweep_clean", "sweep_drv_-6"]
    if not paths:
        print(__doc__)
        sys.exit(1)
    summary = {}
    for sweep in sweeps:
        for p in paths:
            summary.setdefault(sweep, []).append((p, report(p, p, sweep, verbose)))
    print("\n### summary — mean span-err RMS (lower = the switch's RANGE matches the pedal)")
    print(f"{'report':<52}" + "".join(f"{s:>16}" for s in sweeps))
    for i, p in enumerate(paths):
        name = p.split("/")[-1]
        print(f"{name:<52}" + "".join(f"{summary[s][i][1]:16.3f}" for s in sweeps))


if __name__ == "__main__":
    main()
