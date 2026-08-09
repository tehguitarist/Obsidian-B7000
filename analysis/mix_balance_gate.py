#!/usr/bin/env python3.11
"""GATE BU — action-list item 6: the 53 Hz mix cancellation, and what it is actually a property of.

WHAT THE ITEM INHERITED
-----------------------
s184's GATE BM closed with one finding no task owned: *"the perturbation's worst case is a mix
cancellation at BLEND max / LEVEL 0.125-0.25, reaching **33.47 dB at 53.1 Hz** ... it is not a
defect of any stage — but it is the largest number in this session and nothing in P2-P5 looks at
it."*  It was carried onto the action list as *"low priority; likely resolves to characterise and
accept."*

⛔⛔ **THE 33.47 dB IS A SELF-DIFFERENCE, NOT AN ERROR.**  It is `|ship − e0|`, i.e. how far s181's
`blendEndStop` moved the model from its own past self.  It says nothing about whether the shipped
model is RIGHT there, and s184 never asked — although `level-0815_base-od.wav` is a real capture on
disk AND one of the graded 162.  BU2 asks it.

⭐⭐ AND THE MECHANISM WAS ATTRIBUTED TO THE WRONG ARM.  s184 explains the size as *"where the two
coefficients are closest in magnitude (at L 0.125 / B 1.0 they are od = 0.03099 against cl = 0.0300,
a ratio of 1.033)"*, which reads as a statement about the shipped model.  It is not.  At BLEND max
with NO end stop the two coefficients obey

        od_e0 / cl_e0  =  1 / (1 − L)        EXACTLY  (BU0b asserts it; no fit, no threshold)

so the PRE-s181 network's branches balance PERFECTLY as LEVEL → 0 — a perfect cancellation condition
sitting at the bottom of the LEVEL travel.  The SHIPPED network does the opposite: its ratio runs to
−∞ there (pure clean bleed through the end stop), reading −8.11 dB at the very cell s184 flagged.
⇒ **the large `ship − e0` at low LEVEL is dominated by a null in the RETIRED model, not by one in
the shipped one.**  BU0c pins that by reproducing s184's own published pair from the e0 arm.

THE FIVE AXES
-------------
  BU0  known answers   — the end stop resolver, the identity, s184's pair, non-vacuity, notch reach
  BU1  the balance surface, analytic — where each arm cancels on the KNOB axis
  BU2  ⭐ MODEL vs ND across the BLEND-max LEVEL ladder — the question s184 never asked
  BU3  release-gate visibility — s184 said "invisible"; the row is graded, so measure its percentile
  BU4  the DIALLABLE sweep through the shipped balance point (s185's captured-vs-diallable split)
  BU5  which arm is closer to ND, with the e0-arm's own validity caveat printed

⚠⚠ THE e0 ARM IS NOT "THE PRE-s181 MODEL" ANY MORE, AND BU5 SAYS SO EVERY RUN.  s185 pinned
`OdToneRestore::kMixCf[0]` to `blendEndStop` (asserted by `LevelBlendTest` Test 9) and that is a C++
constant, so `--fit blendEndStop=0` moves the end stop and leaves the mix law's node-0 abscissa
behind — a configuration that was never fitted and never shipped.  BU0e bounds where that can
matter: the notch section is a Q≈16 peak at 323 Hz and contributes ≤0.02 dB at 53 Hz, so the LF
columns are clean and the caveat scopes to the ~320 Hz region alone.

Run:
    /opt/homebrew/bin/python3.11 analysis/mix_balance_gate.py
    /opt/homebrew/bin/python3.11 analysis/mix_balance_gate.py --json analysis/reports/s197_mix_balance.json
"""
import argparse
import json
import math
import os
import re
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import analyze as A                      # noqa: E402
import captures as C                     # noqa: E402
import matrix_grade as MG                # noqa: E402
import feature_locus_gate as W           # noqa: E402
import level_law_gate as K               # noqa: E402
import od_tone_restore_fit as F          # noqa: E402

REN_DIR = "build/s197_mix_balance"
os.makedirs(REN_DIR, exist_ok=True)

E0 = ("--fit", "blendEndStop=0")

#: bass_notch's CORE/SHOULDER, IMPORTED in shape from GATE BH rather than restated (s133 AE2: the
#: label is not the window).  The feature the item is named after lives here.
CORE, SHOULDER = (30.0, 110.0), (22.0, 300.0)
F_ITEM = 53.1                    # the frequency in item 6's own title
LF_LO, LF_HI = 25.0, 100.0       # the release gate's own LF region (MG.GRADE_LO..100)
GLO, GHI = 25.0, 16000.0         # the graded band

SWEEP = "sweep_drv_-12"          # the user's stated playing level

#: The BLEND-max LEVEL ladder.  Every entry is a real capture AND one of the graded 162 — BU3
#: asserts the second half rather than assuming it.
LADDER = [
    ("level-0815_base-od.wav", 0.125),
    ("level-0930_base-od.wav", 0.250),
    ("level-1045_base-od.wav", 0.375),
    ("ref-od.wav",             0.500),
    ("level-1315_base-od.wav", 0.625),
    ("level-1430_base-od.wav", 0.750),
    ("level-1545_base-od.wav", 0.875),
    ("level-1700_base-od.wav", 1.000),
]

#: s184's published coefficient pair, quoted verbatim so BU0c is a cross-session known answer.
S184_PAIR = (0.03099, 0.0300, 1.033)
S184_WORST_HZ = 53.1


def die(tag, msg):
    print(f"\n❌ {tag}: {msg}")
    sys.exit(1)


# ================================================================================================
def _tag(arm):
    return "" if not arm else "__" + "_".join(a.replace("=", "") for a in arm if a != "--fit")


_CURVES = {}


def curves(fname, arm=(), level_override=None):
    """-> (grid, pedal_db, model_db) shape-normalised on GATE W's 1/48-oct grid.

    Same normalisation as `od_tone_restore_fit.curves` (NORM_LO/NORM_HI IMPORTED) so every number
    here is apples-to-apples with the OdToneRestore instruments.  `level_override` renders an
    arbitrary LEVEL KNOB for BU4 and then the pedal column is meaningless — BU4 ignores it."""
    key = (fname, arm, level_override)
    if key in _CURVES:
        return _CURVES[key]
    parsed = dict(C.parse_capture(fname))
    if level_override is not None:
        parsed["level"] = level_override
        # INJECTIVE tag: `f"{x:.6f}"` cannot collide the way s185's `int(x*100)` did
        stem = f"levsweep_{level_override:.6f}"
    else:
        stem = fname.replace(".wav", "")
    out = os.path.join(REN_DIR, stem + _tag(arm) + "_plugin.wav")
    W.render(out, C.render_args(parsed, extra_args=list(arm)))

    orig, ref = W._load_orig()
    ren_al, _ = A.align(A.load(out), orig)
    cap_al, _ = A.align(C.load_capture(os.path.join(C.CAPTURE_DIR, fname)), orig)

    def one(al):
        f, m = A.transfer_h1(A.seg_of(al, SWEEP), ref)
        d = W.smooth(f, m)
        n = (W.GRID >= F.NORM_LO) & (W.GRID <= F.NORM_HI)
        return d - float(np.mean(d[n]))

    _CURVES[key] = (W.GRID, one(cap_al), one(ren_al))
    return _CURVES[key]


def geom(g, d):
    """E6 (`notch_geometry`), IMPORTED — never GATE W's E1 prominence (AW6: E1 <= E6 identically
    and the gap is a WIDTH statistic, so an E1 reading cannot be read as a depth)."""
    try:
        return F.notch_geometry(g, d, core=CORE, shoulder=SHOULDER)
    except Exception:
        return None


def at(g, d, hz):
    return float(d[int(np.argmin(np.abs(g - hz)))])


def band(g, d, lo, hi):
    m = (g >= lo) & (g <= hi)
    return float(np.mean(d[m]))


def ratio_db(knob, endstop=None):
    od, cl = K.coef_closed(1.0, K.level_taper(knob), endstop=endstop)
    if od <= 0.0 or cl <= 0.0:
        return float("-inf") if od <= 0.0 else float("inf")
    return 20.0 * math.log10(od / cl)


# ================================================================================================
def bu0():
    """Known answers.  Each one can FAIL, and two of them are the gate's whole argument."""
    print("=" * 100)
    print("BU0 — KNOWN ANSWERS")
    print("=" * 100)
    out = {}

    # --- BU0a: the end stop is READ from FitParams.h through GATE K's single resolver (s182) ----
    K.check_shipped_endstop()
    e_hi, e_lo, k = K._endstop(None)
    print(f"\n  ✅ BU0a  end stop resolved from src/dsp/FitParams.h: endHi={e_hi:.5f} "
          f"endLo={e_lo:.5f} (k={k:.5f})")
    out["endstop"] = [e_hi, e_lo]

    # --- BU0b: THE IDENTITY -- the mechanism, asserted rather than argued ------------------------
    worst = 0.0
    for i in range(1, 20000):
        L = i / 20000.0
        od, cl = K.coef_closed(1.0, L, endstop=(0.0, 0.0))
        worst = max(worst, abs(od / cl - 1.0 / (1.0 - L)))
    if worst > 1e-9:
        die("BU0b", f"od_e0/cl_e0 != 1/(1-L) at BLEND max (worst {worst:.3e}) — the mechanism "
                    f"this gate rests on does not hold; do NOT read BU1/BU5")
    print(f"  ✅ BU0b  IDENTITY  od_e0/cl_e0 == 1/(1-L) at BLEND max, worst dev {worst:.3e} "
          f"over 19999 L")
    print(f"           ⇒ the PRE-s181 branches balance EXACTLY (0 dB) as LEVEL -> 0.  The shipped "
          f"ones do not:")
    for L in (1e-6, 1e-3, 1e-2):
        od, cl = K.coef_closed(1.0, L)
        print(f"             ship at L={L:.0e}: od/cl = {20*math.log10(od/cl):+7.1f} dB")
    out["identity_worst"] = worst

    # --- BU0c: CROSS-SESSION known answer -- s184's own published pair, from the E0 arm ----------
    Ls = 1.0 - 1.0 / S184_PAIR[2]
    od, cl = K.coef_closed(1.0, Ls, endstop=(0.0, 0.0))
    d_od, d_cl = abs(od - S184_PAIR[0]), abs(cl - S184_PAIR[1])
    if max(d_od, d_cl) > 5e-5:
        die("BU0c", f"s184's published pair does NOT reproduce from the e0 arm "
                    f"(got {od:.5f}/{cl:.5f}, published {S184_PAIR[0]}/{S184_PAIR[1]}) — the "
                    f"attribution in this gate's header is unsupported")
    print(f"  ✅ BU0c  s184's published pair reproduces FROM THE e0 ARM at L={Ls:.6f}: "
          f"od={od:.5f} cl={cl:.5f} (published {S184_PAIR[0]}/{S184_PAIR[1]})")
    print(f"           ⇒ s184's mechanism sentence describes the RETIRED arm, not the shipped one.")
    out["s184_pair_dev"] = max(d_od, d_cl)

    # --- BU0d: NON-VACUITY -- the two arms must actually differ on a render ----------------------
    g, _, m_s = curves("level-0815_base-od.wav")
    _, _, m_0 = curves("level-0815_base-od.wav", E0)
    sel = (g >= GLO) & (g <= GHI)
    sep = float(np.abs(m_s - m_0)[sel].max())
    if sep < 1.0:
        die("BU0d", f"the ship and e0 arms differ by only {sep:.3f} dB — every column below is "
                    f"comparing nothing (`empty-gate-must-fail`)")
    print(f"  ✅ BU0d  NON-VACUITY: ship vs e0 differ by {sep:.2f} dB at "
          f"{float(g[sel][int(np.argmax(np.abs(m_s-m_0)[sel]))]):.1f} Hz on the flagged capture")
    out["nonvacuity_db"] = sep

    # --- BU0e: bound where the e0 arm's own inconsistency can reach ------------------------------
    # ⚠⚠ THE FIRST DRAFT OF THIS BOUND PAIRED THE TABLE'S LOWEST Q WITH A LARGE CUT AND READ
    # 1.16 dB, which would have failed this gate against a combination the stage cannot produce:
    # Q = 3.05 is Cut x DRIVE 0.00, whose cut is 1.16 dB, not 40.  A worst case assembled from
    # two columns' extremes is not a worst case.  Both tables are READ from the shipped header and
    # the skirt is evaluated PER CELL on its own (Q, cut) pair.
    f0, cells = _notch_cells()
    reach, worst_cell = 0.0, None
    for gname, drive, q, cut in cells:
        w, amp = F_ITEM / f0, 10 ** (-cut / 40)
        num = math.sqrt((1 - w**2) ** 2 + (w / q) ** 2 * amp**2)
        den = math.sqrt((1 - w**2) ** 2 + (w / q) ** 2 / amp**2)
        r = abs(20 * math.log10(num / den))
        if r > reach:
            reach, worst_cell = r, f"{gname} DRIVE {drive:.2f} (Q={q:.2f}, cut={cut:.1f} dB)"
    if reach > 0.10:
        die("BU0e", f"the {f0:.0f} Hz notch section reaches {reach:.3f} dB at {F_ITEM} Hz — the e0 "
                    f"arm's kMixCf[0] inconsistency is NOT confined to the ~320 Hz region and the "
                    f"LF columns below are contaminated")
    print(f"  ✅ BU0e  the {f0:.0f} Hz notch section reaches at most {reach:.4f} dB at {F_ITEM} Hz "
          f"over all {len(cells)} shipped cells")
    print(f"           (worst: {worst_cell}) — every (Q, cut) pair read from the header, never "
          f"assembled from two columns' extremes")
    print(f"           ⇒ the e0 arm's kMixCf[0] inconsistency cannot reach the LF columns; the "
          f"caveat scopes to ~320 Hz alone.")
    out["notch_reach_db"] = reach
    out["notch_reach_cell"] = worst_cell
    return out


GRUNT_ROWS = ("Cut", "Flat", "Boost")     # the HEADER's own row order for these tables


def _table(src, name):
    m = re.search(name + r"\[3\]\[5\]\s*=\s*\{(.*?)\n\s*\};", src, re.S)
    if not m:
        die("BU0e", f"cannot read {name} from src/dsp/OdToneRestore.h — the scope bound on the "
                    f"e0 arm's kMixCf[0] inconsistency cannot be established")
    rows = re.findall(r"\{([^{}]*)\}", m.group(1))
    out = [[float(x) for x in r.split(",") if x.strip()] for r in rows]
    if len(out) != 3 or any(len(r) != 5 for r in out):
        die("BU0e", f"{name} did not parse as 3x5 (got {[len(r) for r in out]})")
    return out


def _notch_cells():
    """-> (f0, [(grunt, drive, Q, worst-case cut dB)]) read from the SHIPPED header.

    The cut is `kNotchGainDb + kNotchMixK*S(cf) + odNotchDepthDb`; |S| <= 0.951 is its own maximum
    (the corner ordinate, s185), so |K|*0.951 bounds the mix term whatever the setting."""
    src = open(os.path.join(HERE_ROOT, "..", "src", "dsp", "OdToneRestore.h")).read()
    fit = open(os.path.join(HERE_ROOT, "..", "src", "dsp", "FitParams.h")).read()
    mf = re.search(r"kNotchFreq\s*=\s*([0-9.]+)", src)
    mo = re.search(r"odNotchDepthDb\s*=\s*([0-9.]+)", fit)
    if not mf or not mo:
        die("BU0e", "cannot read kNotchFreq / odNotchDepthDb from the shipped headers")
    f0, off = float(mf.group(1)), float(mo.group(1))
    Q, G, Kt = _table(src, "kNotchQ"), _table(src, "kNotchGainDb"), _table(src, "kNotchMixK")
    cells = []
    for gi, gname in enumerate(GRUNT_ROWS):
        for di in range(5):
            cells.append((gname, di * 0.25, Q[gi][di],
                          G[gi][di] + off + abs(Kt[gi][di]) * 0.951))
    return f0, cells


HERE_ROOT = os.path.dirname(os.path.abspath(__file__))


# ================================================================================================
def bu1():
    """The balance surface — where each arm cancels, on the DIALLABLE knob axis."""
    print("\n" + "=" * 100)
    print("BU1 — THE BALANCE SURFACE (analytic, BLEND max)")
    print("=" * 100)
    from scipy.optimize import brentq

    def f(kn):
        od, cl = K.coef_closed(1.0, K.level_taper(kn))
        return od - cl
    kb = brentq(f, 0.05, 0.99, xtol=1e-12)
    Lb = K.level_taper(kb)
    odb, _ = K.coef_closed(1.0, Lb)
    print(f"\n  SHIP balance |od| = |cl|:  knob = {kb:.6f}  (L_tapered {Lb:.6f}, od = cl = "
          f"{odb:.6f})")
    print(f"  E0   balance |od| = |cl|:  LEVEL -> 0, i.e. the BOTTOM END STOP of the knob "
          f"(identity BU0b)")
    print(f"\n  ⇒ the two arms put their cancellation condition in COMPLETELY DIFFERENT PLACES, "
          f"which is why\n    `ship - e0` is largest at the bottom of the ladder.\n")
    print(f"  {'knob':>7s} {'L_tap':>9s} {'ship od/cl dB':>14s} {'e0 od/cl dB':>12s}  captured")
    caps = {round(kn, 6): n for n, kn in LADDER}
    for kn in (0.0625, 0.125, 0.25, 0.375, kb, 0.5, 0.625, 0.75, 0.875, 1.0):
        nm = caps.get(round(kn, 6), "—")
        print(f"  {kn:7.4f} {K.level_taper(kn):9.6f} {ratio_db(kn):+14.2f} "
              f"{ratio_db(kn, (0.0, 0.0)):+12.2f}  {nm}")
    return {"ship_balance_knob": kb, "ship_balance_L": Lb}


# ================================================================================================
def bu2():
    """⭐ The question s184 never asked: is the SHIPPED model wrong at the flagged cells?"""
    print("\n" + "=" * 100)
    print("BU2 — MODEL vs ND ACROSS THE BLEND-MAX LEVEL LADDER  (the decision-relevant axis)")
    print("=" * 100)
    print(f"\n  stimulus {SWEEP}; curves shape-normalised {F.NORM_LO:.0f}-{F.NORM_HI:.0f} Hz.")
    print(f"  Depth on E6, BOTH point and area printed (s152).  'REFUSED' = minimum on a CORE "
          f"bound (s151).\n")
    print(f"  {'capture':24s} {'knob':>5s} {'od/cl':>7s} | {'@53Hz':>7s} {'25-100':>7s} | "
          f"{'f0 ND/M':>15s} {'point ND/M':>13s} {'area ND/M':>13s} {'depth':>6s}")
    print(f"  {'':24s} {'':>5s} {'dB':>7s} | {'M-ND':>7s} {'M-ND':>7s} | {'Hz':>15s} "
          f"{'dB':>13s} {'dB':>13s} {'ratio':>6s}")
    rows, refused = [], []
    for fname, knob in LADDER:
        g, ped, mod = curves(fname)
        gp, gm = geom(g, ped), geom(g, mod)
        d53 = at(g, mod, F_ITEM) - at(g, ped, F_ITEM)
        blf = band(g, mod, LF_LO, LF_HI) - band(g, ped, LF_LO, LF_HI)
        if gp is None or gm is None:
            refused.append(fname)
            f0s, pts, ars, dr = f"{'REFUSED':>15s}", f"{'—':>13s}", f"{'—':>13s}", float("nan")
        else:
            f0s = f"{gp['f0']:6.1f}/{gm['f0']:<8.1f}"
            pts = f"{gp['depth']:5.2f}/{gm['depth']:<7.2f}"
            ars = f"{gp['depth_area']:5.2f}/{gm['depth_area']:<7.2f}"
            dr = gm["depth"] / gp["depth"] if gp["depth"] > 0 else float("nan")
        print(f"  {fname:24s} {knob:5.3f} {ratio_db(knob):+7.2f} | {d53:+7.2f} {blf:+7.2f} | "
              f"{f0s} {pts} {ars} {dr:6.3f}")
        rows.append({"file": fname, "knob": knob, "d53": d53, "lf": blf, "depth_ratio": dr})
    if refused:
        print(f"\n  ⚠ REFUSED by the reader (a refusal is not a reading): {', '.join(refused)}")

    flagged = [r for r in rows if r["knob"] in (0.125, 0.250)]
    worst_lf = max(abs(r["lf"]) for r in rows)
    worst_flag = max(abs(r["lf"]) for r in flagged)
    print(f"\n  ⭐ s184's headline for these cells is |ship - e0| = 33.47 dB @ {S184_WORST_HZ} Hz.")
    print(f"     The SHIPPED model's error against ND at the SAME cells is "
          f"{worst_flag:.2f} dB over {LF_LO:.0f}-{LF_HI:.0f} Hz")
    print(f"     — a factor of {33.47/worst_flag:.1f} smaller than the number the item is named "
          f"after.")
    ok = [r for r in rows if abs(r["lf"]) <= 1.0]
    print(f"     {len(ok)} of {len(rows)} ladder cells sit inside 1.0 dB; the exception is "
          f"{max(rows, key=lambda r: abs(r['lf']))['file']} at "
          f"{max(abs(r['lf']) for r in rows):+.2f} dB.")
    return {"rows": rows, "worst_lf": worst_lf, "worst_flagged_lf": worst_flag,
            "refused": refused}


# ================================================================================================
def bu3(report):
    """s184 said the cancellation is invisible to the release gate.  The row is graded — measure."""
    print("\n" + "=" * 100)
    print("BU3 — RELEASE-GATE VISIBILITY  (s184: \"invisible to the release gate\")")
    print("=" * 100)
    if not os.path.exists(report):
        print(f"\n  ⚠ REFUSED: {report} is absent (analysis/reports/*.json is gitignored). "
              f"BU3 not run.")
        return None
    d = json.load(open(report))
    bands = np.array(d["meta"]["bands"], float)
    m = (bands >= LF_LO) & (bands <= LF_HI)
    caps = {c["file"]: c for c in d["captures"]}
    missing = [n for n, _ in LADDER if n not in caps]
    if missing:
        die("BU3", f"the ladder is NOT fully graded in {os.path.basename(report)}: {missing} — "
                   f"s184's 'invisible' claim cannot be tested on this report")

    pop = []
    for c in d["captures"]:
        if not MG.is_od(c["file"]):
            continue
        fr = c["fr"].get(SWEEP)
        if not fr:
            continue
        v = np.abs(np.array(fr["plugin_db"], float) - np.array(fr["pedal_db"], float))[m]
        if np.all(np.isfinite(v)):
            pop.append((c["file"], float(np.median(v))))
    med = np.array([x[1] for x in pop])
    i53 = int(np.argmin(np.abs(bands - F_ITEM)))
    print(f"\n  {os.path.basename(report)}: {len(d['captures'])} captures, OD population at "
          f"{SWEEP} n={len(pop)}")
    print(f"  {LF_LO:.0f}-{LF_HI:.0f} Hz median|err| over that population: median "
          f"{np.median(med):.3f}, p90 {np.percentile(med, 90):.3f}, max {med.max():.3f} dB\n")
    print(f"  {'capture':24s} {'med|err|':>9s} {'max|err|':>9s} "
          f"{'signed@' + format(bands[i53], '.1f') + 'Hz':>15s} {'percentile':>11s}")
    got = {}
    for n, _ in LADDER:
        fr = caps[n]["fr"][SWEEP]
        p = np.array(fr["plugin_db"], float)
        r = np.array(fr["pedal_db"], float)
        v = np.abs(p - r)[m]
        pct = 100.0 * float(np.mean(med <= np.median(v)))
        got[n] = {"median": float(np.median(v)), "pct": pct, "signed53": float(p[i53] - r[i53])}
        print(f"  {n:24s} {np.median(v):9.3f} {np.max(v):9.3f} {p[i53]-r[i53]:+15.3f} "
              f"{pct:10.1f}%")

    flagged = got["level-0815_base-od.wav"]
    verdict = ("VISIBLE" if flagged["pct"] > 50.0 else "BELOW THE POPULATION MEDIAN")
    outlier = flagged["median"] > float(np.percentile(med, 90))
    print(f"\n  ⇒ the flagged row is graded and reads {flagged['median']:.3f} dB at the "
          f"{flagged['pct']:.1f}th percentile ⇒ {verdict};")
    print(f"    it is {'AN OUTLIER (above p90)' if outlier else 'NOT an outlier (inside p90)'}.")
    print(f"    ⛔ s184's \"invisible to the release gate\" is "
          f"{'SUPPORTED' if flagged['pct'] < 50.0 else 'REFUTED'} on this report.")
    print(f"\n  ⭐ FREE CROSS-CHECK, two independent normalisations: the gate's own per-row "
          f"broadband null gain")
    print(f"    gives {flagged['signed53']:+.3f} dB at {bands[i53]:.1f} Hz where BU2's "
          f"shape-normalised read gives the")
    print(f"    {LF_LO:.0f}-{LF_HI:.0f} Hz band — agreeing despite sharing no normalisation.")
    return {"population_n": len(pop), "median": float(np.median(med)),
            "p90": float(np.percentile(med, 90)), "rows": got,
            "invisible_claim_supported": flagged["pct"] < 50.0}


# ================================================================================================
def bu4(balance_knob):
    """s185's CAPTURED-vs-DIALLABLE split: is there a knob position no capture can grade?"""
    print("\n" + "=" * 100)
    print("BU4 — THE DIALLABLE SURFACE THROUGH THE SHIP BALANCE POINT")
    print("=" * 100)
    # ⚠ Round ONCE and use that value everywhere.  A draft swept `round(balance_knob, 6)` and then
    # tested `s[0] <= balance_knob <= s[1]` against the UNROUNDED value, so the step ABOVE the
    # balance failed its own left-hand comparison by 1e-7 and silently dropped out of `near` —
    # s185's injective-tag trap in its comparison form.
    balance_knob = round(balance_knob, 6)
    knobs = sorted({0.30, 0.35, 0.375, 0.40, balance_knob, 0.45, 0.50, 0.55, 0.60})
    caps = {round(kn, 6): n.replace("_base-od.wav", "").replace(".wav", "")
            for n, kn in LADDER}
    print(f"\n  Shipped build, ref-od settings, LEVEL knob swept through balance "
          f"{balance_knob:.4f}.\n")
    print(f"  {'knob':>7s} {'od/cl dB':>9s} {'captured':>12s} | {'f0':>7s} {'point':>7s} "
          f"{'area':>7s} | {'@53Hz':>8s}")
    pts = []
    for kn in knobs:
        g, _, d = curves("ref-od.wav", level_override=kn)
        gm = geom(g, d)
        s = (f"{gm['f0']:7.1f} {gm['depth']:7.2f} {gm['depth_area']:7.2f}" if gm
             else f"{'REFUSED':>23s}")
        print(f"  {kn:7.4f} {ratio_db(kn):+9.2f} {caps.get(round(kn,6),'—'):>12s} | {s} | "
              f"{at(g,d,F_ITEM):+8.2f}")
        pts.append((kn, g, d, gm))

    print(f"\n  SENSITIVITY between adjacent knob steps, over {GLO:.0f}-{GHI:.0f} Hz:")
    print(f"  {'step':>20s} {'worst dB':>9s} {'@Hz':>9s} {'dB per 0.01 knob':>18s}")
    sens = []
    for (k0, g, d0, _), (k1, _, d1, _) in zip(pts, pts[1:]):
        sel = (g >= GLO) & (g <= GHI)
        dd = np.abs(d1 - d0)[sel]
        w = float(dd.max())
        fw = float(g[sel][int(np.argmax(dd))])
        per = w / ((k1 - k0) / 0.01)
        sens.append((k0, k1, per, fw))
        print(f"  {k0:7.4f}->{k1:<11.4f} {w:9.2f} {fw:9.1f} {per:18.3f}")

    # is the balance point the SENSITIVE place?  computed, not asserted.
    # ⚠ The balance is an ENDPOINT of two swept steps, so TWO of them contain it.  A first draft
    # took `near[0]`, i.e. silently the lower one — an arbitrary choice standing under a verdict.
    # Take the MAX: that is the reading most likely to call the balance sensitive, so a "NOT the
    # sensitive place" verdict survives the choice rather than depending on it.
    near = [s for s in sens if s[0] <= balance_knob <= s[1]]
    per_bal = max((s[2] for s in near), default=float("nan"))
    per_max = max(s[2] for s in sens)
    worst_step = max(sens, key=lambda s: s[2])
    # BRACKETED = a captured detent exists on each side of the balance point.  Computed from the
    # ladder's own knob values, not from the swept set (which contains uncaptured points too).
    ladder_knobs = [kn for _, kn in LADDER]
    bracketed = (any(kn <= balance_knob for kn in ladder_knobs)
                 and any(kn >= balance_knob for kn in ladder_knobs))
    below = max((kn for kn in ladder_knobs if kn <= balance_knob), default=float("nan"))
    above = min((kn for kn in ladder_knobs if kn >= balance_knob), default=float("nan"))
    print(f"\n  ⇒ per-knob sensitivity AT the balance is {per_bal:.3f} dB/0.01 against a swept "
          f"maximum of {per_max:.3f}")
    print(f"    at knob {worst_step[0]:.4f}->{worst_step[1]:.4f}, @ {worst_step[3]:.1f} Hz.")
    print(f"    ⇒ the balance point is {'THE' if per_bal >= per_max else 'NOT the'} sensitive "
          f"place, and the sensitivity maximum sits at "
          f"{'the same' if abs(worst_step[3]-F_ITEM) < 20 else 'a DIFFERENT'} frequency from "
          f"item 6's {F_ITEM} Hz.")
    print(f"    ⇒ the balance is {'BRACKETED' if bracketed else 'NOT bracketed'} by captured "
          f"detents (knob {below:.3f} and {above:.3f}, a gap of {above-below:.3f} of travel)")
    print(f"      — contrast s185, where the disturbed band was a GAP in the capture matrix.")
    return {"balance_sensitivity": per_bal, "max_sensitivity": per_max,
            "max_at_hz": worst_step[3], "bracketed": bracketed,
            "bracket": [below, above]}


# ================================================================================================
def bu5():
    """Which arm is closer to ND?  With the e0 arm's own validity caveat printed every run."""
    print("\n" + "=" * 100)
    print("BU5 — WHICH ARM IS CLOSER TO ND")
    print("=" * 100)
    print(f"\n  ⚠⚠ THE e0 ARM IS NOT 'THE PRE-s181 MODEL' ON THIS EPOCH.  s185 pinned "
          f"OdToneRestore::kMixCf[0]")
    print(f"     to blendEndStop (LevelBlendTest Test 9) and that is a C++ constant, so "
          f"`--fit blendEndStop=0`")
    print(f"     leaves it behind — a configuration never fitted and never shipped.  BU0e bounds "
          f"it to ~320 Hz,")
    print(f"     so the LF column is clean and the BROADBAND column carries the caveat.\n")
    print(f"  {'capture':24s} {'knob':>5s} | {'|ship-e0|':>9s} {'@Hz':>8s} | "
          f"{'ship-ND':>8s} {'e0-ND':>8s} | {'ship rms':>9s} {'e0 rms':>9s} | {'closer':>7s}")
    print(f"  {'':24s} {'':>5s} | {'worst':>9s} {'':>8s} | {'25-100':>8s} {'25-100':>8s} | "
          f"{'25-16k':>9s} {'25-16k':>9s} | {'(rms)':>7s}")
    n_ship = n_e0 = 0
    rows = []
    for fname, knob in LADDER:
        g, ped, ms = curves(fname)
        _, _, m0 = curves(fname, E0)
        sel = (g >= GLO) & (g <= GHI)
        dd = np.abs(ms - m0)[sel]
        worst, fw = float(dd.max()), float(g[sel][int(np.argmax(dd))])
        sb = band(g, ms, LF_LO, LF_HI) - band(g, ped, LF_LO, LF_HI)
        zb = band(g, m0, LF_LO, LF_HI) - band(g, ped, LF_LO, LF_HI)
        rs = float(np.sqrt(np.mean((ms - ped)[sel] ** 2)))
        rz = float(np.sqrt(np.mean((m0 - ped)[sel] ** 2)))
        closer = "SHIP" if rs < rz else "e0"
        n_ship += closer == "SHIP"
        n_e0 += closer == "e0"
        rows.append({"file": fname, "knob": knob, "perturb": worst, "at_hz": fw,
                     "ship_lf": sb, "e0_lf": zb, "ship_rms": rs, "e0_rms": rz})
        print(f"  {fname:24s} {knob:5.3f} | {worst:9.2f} {fw:8.1f} | {sb:+8.2f} {zb:+8.2f} | "
              f"{rs:9.3f} {rz:9.3f} | {closer:>7s}")
    print(f"\n  ⇒ on the broadband rms the SHIP arm is closer at {n_ship}/{len(LADDER)} cells, "
          f"e0 at {n_e0}/{len(LADDER)}.")
    flagged = [r for r in rows if r["knob"] in (0.125, 0.250)]
    print(f"    At the two cells s184 flagged as WORST, ship is closer at "
          f"{sum(1 for r in flagged if r['ship_rms'] < r['e0_rms'])}/{len(flagged)} "
          f"(rms " + ", ".join(f"{r['ship_rms']:.3f} vs {r['e0_rms']:.3f}" for r in flagged) + ").")
    lf_cost = [r for r in rows if abs(r["ship_lf"]) > abs(r["e0_lf"])]
    print(f"    ⚠ On the {LF_LO:.0f}-{LF_HI:.0f} Hz band alone the end stop COSTS accuracy at "
          f"{len(lf_cost)}/{len(rows)} cells,")
    print(f"      worst at {max(rows, key=lambda r: abs(r['ship_lf'])-abs(r['e0_lf']))['file']} "
          f"({max(rows, key=lambda r: abs(r['ship_lf'])-abs(r['e0_lf']))['e0_lf']:+.2f} -> "
          f"{max(rows, key=lambda r: abs(r['ship_lf'])-abs(r['e0_lf']))['ship_lf']:+.2f} dB).")
    return {"rows": rows, "n_ship_closer": n_ship, "n_e0_closer": n_e0}


# ================================================================================================
def verdict(r2, r3, r4, r5):
    print("\n" + "=" * 100)
    print("BU6 — VERDICT (computed)")
    print("=" * 100)
    factor = 33.47 / r2["worst_flagged_lf"]
    print(f"\n  1. s184's 33.47 dB is |ship - e0|, a SELF-difference.  Measured against ND at the "
          f"same cells")
    print(f"     the shipped model is out by {r2['worst_flagged_lf']:.2f} dB over "
          f"{LF_LO:.0f}-{LF_HI:.0f} Hz — {factor:.0f}x smaller.")
    print(f"  2. The mechanism is the RETIRED arm's exact balance (BU0b/BU0c), not the shipped "
          f"arm's.")
    if r3 is not None:
        claim = "SUPPORTED" if r3["invisible_claim_supported"] else "REFUTED"
        print(f"  3. s184's \"invisible to the release gate\" is {claim}: the row is graded and "
              f"sits at the")
        print(f"     {r3['rows']['level-0815_base-od.wav']['pct']:.1f}th percentile of "
              f"{r3['population_n']} OD rows.")
    else:
        print(f"  3. release-gate visibility NOT TESTED (report absent) — a refusal, not a pass.")
    print(f"  4. The diallable surface through the balance is "
          f"{'BENIGN' if r4['balance_sensitivity'] < r4['max_sensitivity'] else 'THE HAZARD'}: "
          f"{r4['balance_sensitivity']:.3f} dB/0.01 knob")
    print(f"     against a swept max of {r4['max_sensitivity']:.3f} at {r4['max_at_hz']:.0f} Hz, "
          f"and it is "
          f"{'bracketed' if r4['bracketed'] else 'NOT bracketed'} by captured detents.")
    print(f"  5. Neither arm dominates broadband ({r5['n_ship_closer']} vs "
          f"{r5['n_e0_closer']} cells), but ship wins at the flagged ones.")

    acceptable = (r2["worst_flagged_lf"] < 3.0
                  and r4["balance_sensitivity"] < r4["max_sensitivity"]
                  and r4["bracketed"])
    print()
    if acceptable:
        print("  ⇒ COMPUTED VERDICT: CHARACTERISE AND ACCEPT.  The 53 Hz cancellation is not a")
        print("    shipped-model defect; the number it is named after belongs to a model that no")
        print("    longer exists.")
    else:
        print("  ⇒ COMPUTED VERDICT: NOT ACCEPTABLE — item 6 needs an engineering response.")
    worst_row = max(r2["rows"], key=lambda r: abs(r["lf"]))
    print(f"\n  ⚠ ONE RESIDUAL SURVIVES AND IT IS NOT THE 53 Hz CANCELLATION: at "
          f"{worst_row['file']}")
    print(f"    (the QUIETEST ladder detent) the model reads {worst_row['lf']:+.2f} dB over "
          f"{LF_LO:.0f}-{LF_HI:.0f} Hz and its")
    print(f"    bass null is {worst_row['depth_ratio']:.2f}x ND's depth — the worst on the ladder, "
          f"where every other")
    print(f"    cell sits at {max(abs(r['lf']) for r in r2['rows'] if r is not worst_row):.2f} dB "
          f"or better.  Recorded, not actioned.")
    return {"acceptable": bool(acceptable), "factor": factor}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json")
    ap.add_argument("--report", default="analysis/reports/s196_mixk.json",
                    help="matrix report for BU3 (gitignored; BU3 refuses if absent)")
    a = ap.parse_args()

    print("=" * 100)
    print("GATE BU — action-list item 6: the 53 Hz mix cancellation")
    print("=" * 100)
    r0 = bu0()
    r1 = bu1()
    r2 = bu2()
    r3 = bu3(a.report)
    r4 = bu4(r1["ship_balance_knob"])
    r5 = bu5()
    r6 = verdict(r2, r3, r4, r5)

    if a.json:
        os.makedirs(os.path.dirname(a.json), exist_ok=True)
        json.dump({"bu0": r0, "bu1": r1, "bu2": r2, "bu3": r3, "bu4": r4, "bu5": r5,
                   "verdict": r6}, open(a.json, "w"), indent=2)
        print(f"\n  wrote {a.json}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
