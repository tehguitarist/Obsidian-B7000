#!/usr/bin/env python3.11
"""GATE BE — W1: CAN THE OD GAP CLOSE BY RAISING THE CLIPPER'S CEILING?

WHY THIS EXISTS (session 170; the live plan's W1, session 1 of a hard cap of 3)
------------------------------------------------------------------------------
Session 167 put W1 at the head of the plan on ONE analytical claim, and the claim is what makes
W1 different from the route session 142 already refuted:

    "the GRUNT off-flat null and the OD accuracy gap are THE SAME DEFECT.  Bleed-free the model
     is -1 dB midband at GRUNT cut and -6...-8 dB BROADBAND at GRUNT flat/boost.  GRUNT sets the
     clipper's coupling cap, and at 1 kHz the cut cap attenuates ~6 dB more => flat/boost drive
     the clipper ~6 dB harder, and that is exactly where the model collapses."

That is a MECHANISM claim with a dose in it, so it is falsifiable for free.  s142 refuted raising
`clipSat` while HOLDING THE OPERATING POINT FIXED (the co-scaling argument: the VTC is homogeneous,
so a physical ceiling needs +14.72 dB more drive at node W, which exceeds even the absolute supply
ceiling by 1.76x).  W1's new idea is to raise the ceiling and DELIBERATELY LET THE CLIPPER COMPRESS
LESS -- `kInputRef` unchanged -- which is a different experiment and is genuinely untried.

But the reason to try it is the GRUNT evidence, so the GRUNT evidence gets screened FIRST, before
any render.  `verify-the-PREMISE-not-the-prior-session's-framing-of-it` (ten occurrences).

GATES (validity exits non-zero; every physics OUTCOME is a computed verdict -- s108)
------------------------------------------------------------------------------------------------
BE0  MEMBERSHIP AND PROVENANCE.  The 9 bleed-free OD conditions (GRUNT x DRIVE) are asserted
     bleed-free from their SETTINGS, not their filenames (s114); the CLEAN control is asserted
     OD-free; the private render dir is asserted not to be GATE W's read-only cache (s159); the
     baseline report's epoch is asserted to be the current one.
BE1  THE PREMISE -- is the midband OD deficit GRUNT-DEPENDENT?  Reads the stored baseline, no
     render.  Prints the ABSOLUTE and the GAIN-MATCHED column side by side (s117: print both
     operands of any difference), because the two disagree and the whole framing rests on which
     one is quoted.
BE2  THE MECHANISM'S OWN DOSE, closed form from the shipped constants: how much harder does each
     GRUNT position drive the clipper?  Composed through the ADD-cap rule (s139's trap: FitParams
     stores clipC12/clipC13 as add-caps and `Clipper::gruntCapNow` returns c11+c12 / c11+c13 --
     reading them raw understates flat by 7.9 %).  Then the dose-response: a known ~7.6 dB dose
     against the measured deficit change.  A "saturates too early" defect MUST get worse where the
     clipper is driven harder.
BE3  THE STIMULUS DOSE-RESPONSE, every rung printed (s129: an endpoint pair is not a ladder).  The
     same requirement on a second, independent 12 dB axis.
BE4  THE SWEEP ITSELF (renders).  clipSatLo/Hi x L for L in [1.0, 5.442], `kInputRef` UNCHANGED.
     Three known answers: (a) L = 1.0 must reproduce the stored baseline; (b) CLEAN must be
     BIT-IDENTICAL at every L (the clipper is OD-only -- a CLEAN move means the override reached
     further than intended); (c) NON-VACUITY -- every OD render must MOVE, or the `--fit` override
     never reached the stage and every number below is a fiction.
BE5  THE LOCUS SHAPE, against W1's OWN PRE-REGISTERED STOP:

         "if the locus is monotone with NO interior optimum, that is the 'make the clipper see
          less' degeneracy this project has already hit four times (s5/s6 clipper fits, GAP #3b's
          C13, the rail-voltage fit, C15) -- REFUTE and STOP AT ONE SESSION."

     The stop is applied as written.  It is a computed verdict, not a narrated one.

WHAT THIS GATE DOES NOT CLAIM
-----------------------------
It does not re-litigate s142 (a PHYSICAL clipSat is unreachable on this supply -- that stands and
is not what W1 proposes).  It does not measure the full release gate: the matrix is only owed if
BE5 finds an interior optimum, and W1's own stop says so.
"""
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import analyze as A                     # noqa: E402
import captures as C                    # noqa: E402
import comprehensive_report as CR       # noqa: E402
import feature_locus_gate as W          # noqa: E402
from parallel import pmap, pmap_cpu     # noqa: E402

BASELINE = "analysis/reports/s166_odtilt.json"
PRIV_DIR = "build/s170_clipsat_headroom"
OUT_JSON = "analysis/reports/s170_clipsat_headroom.json"

# The bleed-free OD grid: GRUNT x DRIVE, all at LEVEL/BLEND max (GATE K2: bleed vanishes only
# where BOTH are max).  GRUNT cut carries no `grunt-` token -- `captures.py` defaults gruntIdx to
# cut, which is the s151 trap (every capture without a token sits at that control's DEFAULT).
COND = {}
for _g, _tok in (("cut", ""), ("flat", "_grunt-flat"), ("boost", "_grunt-boost")):
    for _d, _dtok in (("min", "drive-0700_"), ("noon", ""), ("max", "drive-1700_")):
        COND[(_g, _d)] = f"{_dtok}level-1700{_tok}_base-od.wav"
CLEAN_CTRL = "ref-clean.wav"

DRIVEN = ("sweep_drv_-18", "sweep_drv_-12", "sweep_drv_-6")
MID_LO, MID_HI = 100.0, 1000.0          # the "midband" the framing quotes
GRADE_LO, GRADE_HI = 100.0, 8000.0      # release_gate's own OD region

# The sweep.  L = 1.0 is the shipped point (a known answer, not a rung); 5.442 is s142's own
# co-scaling factor VDD/satsum = 5.636/1.0356, i.e. the physical ceiling, IMPORTED as arithmetic
# rather than transcribed.
L_RUNGS = (1.0, 1.25, 1.5, 2.0, 2.5, 3.0, 4.0, 5.442)

FAILED = []
REPORT = {}


def die(tag, msg):
    sys.exit(f"\nGATE BE — {tag} REFUSES: {msg}\n")


def note(tag, msg):
    FAILED.append(f"{tag}: {msg}")
    print(f"   ** {tag} FAIL — {msg}")


def _fp(name):
    """Read a shipped constant from source (never transcribed — s149's rule)."""
    import re
    for path in ("src/dsp/FitParams.h", "src/dsp/GainStaging.h"):
        src = open(path).read()
        m = re.search(rf"^\s*(?:static\s+)?(?:constexpr\s+)?double\s+{name}\s*=\s*"
                      r"([0-9.eE+-]+)\s*[;f]", src, re.M)
        if m:
            return float(m.group(1))
    die("BE0", f"constant `{name}` not found in FitParams.h or GainStaging.h")


# ------------------------------------------------------------------------------------------------
def band_slice(bands, lo, hi):
    return [i for i, f in enumerate(bands) if lo <= f <= hi]


def errs(fr, idx):
    """(absolute, gain-matched) model-pedal error over the band indices `idx`.

    `plugin_db` in a stored report ALREADY carries `gain_db_applied` (comprehensive_report adds it
    before storing), so the absolute reading subtracts it back off.  Mixing the two is exactly the
    confusion this gate exists to resolve."""
    g = fr["gain_db_applied"]
    matched = [fr["plugin_db"][i] - fr["pedal_db"][i] for i in idx]
    absolute = [m - g for m in matched]
    return absolute, matched


# ------------------------------------------------------------------------------------------------
def be0():
    print("=" * 100)
    print("BE0  MEMBERSHIP AND PROVENANCE")
    if os.path.abspath(PRIV_DIR) == os.path.abspath(W.REN_DIR):
        die("BE0", "the private render dir IS GATE W's read-only cache — refusing to render into it.")
    if not os.path.exists(BASELINE):
        die("BE0", f"baseline {BASELINE} absent.")

    for key, fn in COND.items():
        p = os.path.join(C.CAPTURE_DIR, fn)
        if not os.path.exists(p):
            die("BE0", f"capture {fn} absent — the membership is not the stated one.")
        s = C.parse_capture(fn)
        if float(s.get("level", -1)) != 1.0 or float(s.get("blend", -1)) != 1.0:
            die("BE0", f"{fn} is not bleed-free (level={s.get('level')} blend={s.get('blend')}) "
                       "— GATE K2: bleed vanishes only where BOTH LEVEL and BLEND are max.")
        want = {"cut": 1, "flat": 2, "boost": 0}[key[0]]
        if int(s.get("gruntIdx", -1)) != want:
            die("BE0", f"{fn} parses gruntIdx={s.get('gruntIdx')} but the grid calls it "
                       f"{key[0]} (={want}) — settings, not filenames (s114).")
    cs = C.parse_capture(CLEAN_CTRL)
    if cs.get("base") != "clean" and float(cs.get("blend", 1.0)) != 0.0:
        die("BE0", f"{CLEAN_CTRL} is not a CLEAN capture — the OD-only scope check needs one.")

    print(f"   OD grid    : {len(COND)} bleed-free conditions, GRUNT x DRIVE, all LEVEL=BLEND=1.0")
    print(f"   CLEAN ctrl : {CLEAN_CTRL}")
    print(f"   baseline   : {BASELINE}")
    print(f"   private dir: {PRIV_DIR}   (GATE W's cache {W.REN_DIR} is untouched)")

    ship = {n: _fp(n) for n in ("clipSatLo", "clipSatHi", "clipA0", "clipC11", "clipC12",
                                "clipC13", "clipR16", "kInputRefNominal")}
    satsum = ship["clipSatLo"] + ship["clipSatHi"]
    vdd = 5.636          # circuit.md / analysis/clipper_rail_selfconsistent.py, DERIVED not a prior
    print(f"\n   shipped clipSat sum {satsum:.4f} V against the derived VDD {vdd:.3f} V "
          f"=> {vdd / satsum:.3f}x low")
    if abs(L_RUNGS[-1] - vdd / satsum) > 0.02:
        die("BE0", f"the top rung {L_RUNGS[-1]} is not VDD/satsum ({vdd / satsum:.3f}) — "
                   "the sweep must reach the physical ceiling it is named for.")
    REPORT["shipped"] = ship
    REPORT["satsum"] = satsum
    REPORT["vdd"] = vdd
    return ship


# ------------------------------------------------------------------------------------------------
def be1(base, bands):
    print("=" * 100)
    print("BE1  THE PREMISE — IS THE MIDBAND OD DEFICIT GRUNT-DEPENDENT?")
    print("     (stored baseline, no render.  BOTH operands printed — s117.)")
    caps = {c["file"]: c for c in base["captures"]}
    mid = band_slice(bands, MID_LO, MID_HI)
    grade = band_slice(bands, GRADE_LO, GRADE_HI)
    print(f"     midband = {len(mid)} bands {bands[mid[0]]:.0f}-{bands[mid[-1]]:.0f} Hz; "
          f"graded region = {len(grade)} bands {bands[grade[0]]:.0f}-{bands[grade[-1]]:.0f} Hz")

    rows = {}
    print(f"\n   {'GRUNT':6s}{'sweep':16s}{'null gain':>10s}{'ABS mid':>10s}{'MATCH mid':>11s}"
          f"{'ABS 100-8k':>12s}{'MATCH 100-8k':>14s}")
    for g in ("cut", "flat", "boost"):
        fn = COND[(g, "noon")]
        c = caps.get(fn)
        if c is None:
            die("BE1", f"{fn} is not in {BASELINE} — membership mismatch.")
        for sw in DRIVEN:
            fr = c["fr"][sw]
            am, mm = errs(fr, mid)
            ag, mg = errs(fr, grade)
            rows[(g, sw)] = dict(gain=fr["gain_db_applied"],
                                 abs_mid=float(np.median(am)), match_mid=float(np.median(mm)),
                                 abs_grade=float(np.median(ag)), match_grade=float(np.median(mg)))
            r = rows[(g, sw)]
            print(f"   {g:6s}{sw:16s}{r['gain']:+10.2f}{r['abs_mid']:+10.2f}{r['match_mid']:+11.2f}"
                  f"{r['abs_grade']:+12.2f}{r['match_grade']:+14.2f}")

    # The verdict: the SPREAD across GRUNT, on each column, at each sweep.
    print(f"\n   {'sweep':16s}{'ABS mid spread':>16s}{'MATCH mid spread':>18s}")
    spread_abs, spread_match = [], []
    for sw in DRIVEN:
        a = [rows[(g, sw)]["abs_mid"] for g in ("cut", "flat", "boost")]
        m = [rows[(g, sw)]["match_mid"] for g in ("cut", "flat", "boost")]
        spread_abs.append(max(a) - min(a))
        spread_match.append(max(m) - min(m))
        print(f"   {sw:16s}{spread_abs[-1]:16.2f}{spread_match[-1]:18.2f}")

    sa, sm = max(spread_abs), max(spread_match)
    print(f"\n   worst-case GRUNT spread:  ABSOLUTE {sa:.2f} dB   GAIN-MATCHED {sm:.2f} dB")
    # Computed verdict.  The framing quotes a ~5-7 dB GRUNT difference; the bar is the framing's
    # own claim, halved, so a genuinely present half-sized effect would still pass.
    claim = 5.0
    if sa >= claim / 2.0:
        v = ("GRUNT-DEPENDENT — the framing's mechanism survives on the absolute reading")
    else:
        v = (f"GRUNT-INDEPENDENT — the absolute midband deficit varies by only {sa:.2f} dB across "
             f"GRUNT, against a framing that quotes ~{claim:.0f} dB.  The gain-matched column's "
             f"{sm:.2f} dB is manufactured by the per-row null gain")
    print(f"   VERDICT: {v}")
    REPORT["be1"] = {"rows": {f"{g}|{s}": r for (g, s), r in rows.items()},
                     "spread_abs_mid": sa, "spread_match_mid": sm, "verdict": v}
    return rows, mid, grade, caps


def be1b(caps, bands):
    """Where the GRUNT positions DO differ — the per-band curve, so the split is visible."""
    print("\n   Per-band ABSOLUTE error at sweep_drv_-12 (the axis the framing is about):")
    print(f"   {'Hz':>7}{'cut':>9}{'flat':>9}{'boost':>9}   {'max-min':>9}")
    idx = list(range(len(bands)))
    cols = {}
    for g in ("cut", "flat", "boost"):
        a, _ = errs(caps[COND[(g, "noon")]]["fr"]["sweep_drv_-12"], idx)
        cols[g] = a
    # Three regions, because pooling them hides the answer.  HF (>4 kHz) is NOT this gate's to
    # explain: GATE I owns it (drive-generated, on the pedal's side, and the standing rule forbids
    # calling it aliasing), and its 8-16 kHz spread would otherwise swamp the midband reading.
    reg = {"LF <100 Hz": [], "MID 100 Hz-4 kHz": [], "HF >4 kHz (GATE I's)": []}
    for i, f in enumerate(bands):
        vals = [cols[g][i] for g in ("cut", "flat", "boost")]
        sp = max(vals) - min(vals)
        key = "LF <100 Hz" if f < MID_LO else ("MID 100 Hz-4 kHz" if f <= 4100 else
                                               "HF >4 kHz (GATE I's)")
        reg[key].append(sp)
        print(f"   {f:7.0f}{vals[0]:+9.2f}{vals[1]:+9.2f}{vals[2]:+9.2f}   {sp:9.2f}")
    print()
    for k, v_ in reg.items():
        print(f"   GRUNT spread, {k:24s} max {max(v_):6.2f} dB   median {np.median(v_):6.2f} dB")
    lf, mb = max(reg["LF <100 Hz"]), max(reg["MID 100 Hz-4 kHz"])
    v = ((f"the GRUNT difference is a LOW-FREQUENCY one — {lf:.1f} dB below {MID_LO:.0f} Hz "
          f"against {mb:.1f} dB across the whole midband ({lf / mb:.1f}x).  That is exactly what "
          "switching the clipper's COUPLING CAP does, and it is not a midband headroom signature")
         if lf > 2.0 * mb else
         "the GRUNT difference is not confined to LF — the coupling-cap reading does not explain it")
    print(f"   VERDICT: {v}")
    REPORT["be1b"] = {"region_max": {k: max(v_) for k, v_ in reg.items()},
                      "region_median": {k: float(np.median(v_)) for k, v_ in reg.items()},
                      "verdict": v}


# ------------------------------------------------------------------------------------------------
def be2(ship, rows):
    print("=" * 100)
    print("BE2  THE MECHANISM'S OWN DOSE — HOW MUCH HARDER DOES GRUNT DRIVE THE CLIPPER?")
    print("     closed form from the SHIPPED constants; no render, no fit, no threshold.")
    # The clipper input branch: the GRUNT cap in series into (R16 + Zin), Zin = R18/(1+a0).
    # ADD-CAP COMPOSITION — s139: FitParams stores clipC12/clipC13 as ADD-caps and
    # Clipper::gruntCapNow() returns c11 / c11+c12 / c11+c13.  Reading them raw is the trap.
    c11, c12, c13 = ship["clipC11"], ship["clipC12"], ship["clipC13"]
    caps_g = {"cut": c11, "flat": c11 + c12, "boost": c11 + c13}
    r16, a0 = ship["clipR16"], ship["clipA0"]
    zin = 330.0e3 / (1.0 + a0)          # Clipper.h kR18
    rtot = r16 + zin
    print(f"   R16 {r16:.0f}  Zin = R18/(1+a0) = 330k/{1 + a0:.3f} = {zin:.0f}  => Rtot {rtot:.0f}")
    if not (caps_g["cut"] < caps_g["flat"] < caps_g["boost"]):
        die("BE2", "the composed GRUNT caps are not ordered cut < flat < boost — "
                   "the ADD-cap composition is wrong.")

    def drive_db(cap, f):
        zc = 1.0 / (2.0 * np.pi * f * cap)
        return 20.0 * np.log10(rtot / np.hypot(rtot, zc))

    fmid = 1000.0
    d = {g: drive_db(cap, fmid) for g, cap in caps_g.items()}
    print(f"\n   {'GRUNT':7s}{'composed cap':>15s}{'|H| @1kHz dB':>15s}{'re cut, dB':>13s}")
    for g in ("cut", "flat", "boost"):
        print(f"   {g:7s}{caps_g[g] * 1e9:13.2f}nF{d[g]:+15.3f}{d[g] - d['cut']:+13.3f}")
    dose = {g: d[g] - d["cut"] for g in d}
    print(f"\n   => the DOSE: flat drives the clipper {dose['flat']:+.2f} dB harder than cut, "
          f"boost {dose['boost']:+.2f} dB.")

    # The dose-response.  A "saturates too early" defect must get WORSE (more negative) where the
    # clipper is driven harder.
    print(f"\n   {'sweep':16s}{'d(deficit)/d(drive) flat':>26s}{'boost':>12s}")
    slopes = []
    for sw in DRIVEN:
        base = rows[("cut", sw)]["abs_mid"]
        sl = {}
        for g in ("flat", "boost"):
            sl[g] = (rows[(g, sw)]["abs_mid"] - base) / dose[g]
            slopes.append(sl[g])
        print(f"   {sw:16s}{sl['flat']:+26.3f}{sl['boost']:+12.3f}")
    worst = max(slopes)          # most positive = deficit SHRINKS as drive rises
    best = min(slopes)           # most negative = deficit grows, the predicted direction
    print(f"\n   dB of extra deficit per dB of extra clipper drive: range [{best:+.3f}, {worst:+.3f}]")
    if best < -0.10:
        v = (f"the deficit DOES grow with clipper drive (worst {best:+.3f} dB/dB) — "
             "consistent with a headroom/compression mechanism")
    else:
        v = (f"REFUTED ON THE DOSE — a {dose['boost']:.1f} dB change in how hard the clipper is "
             f"driven moves the midband deficit by at most {abs(best) * dose['boost']:.2f} dB, and "
             f"{sum(1 for s in slopes if s > 0)} of {len(slopes)} cells move the WRONG WAY (the "
             "deficit SHRINKS where the clipper is pushed harder).  A ceiling that is too low must "
             "hurt MORE where it is approached harder.")
    print(f"   VERDICT: {v}")
    REPORT["be2"] = {"caps_nF": {g: caps_g[g] * 1e9 for g in caps_g}, "zin": zin,
                     "dose_db": dose, "slopes": slopes, "verdict": v}
    return dose


# ------------------------------------------------------------------------------------------------
def be3(rows):
    print("=" * 100)
    print("BE3  THE STIMULUS DOSE-RESPONSE — every rung (s129), on a second 12 dB axis")
    print(f"\n   {'GRUNT':7s}" + "".join(f"{s.replace('sweep_drv_', ''):>10s}" for s in DRIVEN)
          + f"{'span':>9s}{'monotone':>11s}")
    spans, monos = [], []
    for g in ("cut", "flat", "boost"):
        v = [rows[(g, sw)]["abs_mid"] for sw in DRIVEN]
        span = max(v) - min(v)
        mono = (v[0] >= v[1] >= v[2]) or (v[0] <= v[1] <= v[2])
        spans.append(span)
        monos.append(mono)
        print(f"   {g:7s}" + "".join(f"{x:+10.2f}" for x in v)
              + f"{span:9.2f}{'yes' if mono else 'NO':>11s}")
    print(f"\n   worst span across a 12 dB stimulus range: {max(spans):.2f} dB;  "
          f"monotone in {sum(monos)} of 3")
    if max(spans) >= 2.0 and sum(monos) == 3:
        v = (f"stimulus-DEPENDENT and monotone in 3/3 (span {max(spans):.2f} dB) — the "
             "compression-law reading survives on this axis")
    else:
        v = (f"NOT a compression signature — over 12 dB of stimulus the midband deficit moves at "
             f"most {max(spans):.2f} dB and is monotone in only {sum(monos)} of 3.  A ~3.5 dB "
             "level offset invariant to 12 dB of stimulus is not a headroom defect")
    print(f"   VERDICT: {v}")
    REPORT["be3"] = {"spans": spans, "monotone": monos, "verdict": v}


# ------------------------------------------------------------------------------------------------
def render_at(fname, L, ship):
    """Render one condition with clipSat scaled by L; kInputRef UNCHANGED (that is the experiment)."""
    args = list(C.render_args(C.parse_capture(fname)))
    if L != 1.0:
        args += ["--fit", f"clipSatLo={ship['clipSatLo'] * L:.10g}",
                 "--fit", f"clipSatHi={ship['clipSatHi'] * L:.10g}"]
    tag = f"L{L:.4f}".replace(".", "p")
    out = os.path.join(PRIV_DIR, f"{fname.replace('.wav', '')}__{tag}.wav")
    W.render(out, args)
    return out


def score(fname, out, bands, mid, grade):
    orig, _ = W._load_orig()
    cap_al, _ = A.align(A.load(os.path.join(C.CAPTURE_DIR, fname)), orig)
    ren_al, _ = A.align(A.load(out), orig)
    res = {}
    for sw in DRIVEN:
        methods, gain_db = CR.fr_at_bands(cap_al, ren_al, orig, sw, bands)
        fr = {"plugin_db": methods[CR.DEFAULT_FR_METHOD]["plugin_db"],
              "pedal_db": methods[CR.DEFAULT_FR_METHOD]["pedal_db"],
              "gain_db_applied": gain_db}
        am, mm = errs(fr, mid)
        ag, mg = errs(fr, grade)
        res[sw] = dict(gain=gain_db,
                       abs_mid=float(np.median(am)), match_mid=float(np.median(mm)),
                       abs_grade=float(np.median(ag)), match_grade=float(np.median(mg)),
                       rms_grade=float(np.sqrt(np.mean(np.square(mg)))),
                       # per-band absolute error over the GRADED region, kept so BE5b can ask
                       # whether this lever delivers a SCALAR or a SHAPE.
                       abs_grade_bands=[float(x) for x in ag])
    return res


def _score_one(t):
    """Module-level so `pmap_cpu` can pickle it."""
    fname, _L, out, bands, mid, grade = t
    return score(fname, out, bands, mid, grade)


def be4(ship, bands, mid, grade, base_rows, jobs):
    print("=" * 100)
    print("BE4  THE SWEEP — clipSat x L, kInputRef UNCHANGED (the clipper compresses LESS)")
    os.makedirs(PRIV_DIR, exist_ok=True)

    work = [(fname, L) for L in L_RUNGS for fname in
            sorted(set(list(COND.values()) + [CLEAN_CTRL]))]
    print(f"   {len(work)} renders ({len(L_RUNGS)} rungs x {len(set(COND.values())) + 1} conditions)"
          f" at jobs={jobs} ...")
    paths = dict(zip(work, pmap(lambda t: render_at(t[0], t[1], ship), work, jobs)))

    # ---- known answer (b): CLEAN must be BIT-IDENTICAL at every L (the clipper is OD-only).
    ref = A.load(paths[(CLEAN_CTRL, 1.0)])
    clean_max = 0.0
    for L in L_RUNGS[1:]:
        d = float(np.max(np.abs(A.load(paths[(CLEAN_CTRL, L)]) - ref)))
        clean_max = max(clean_max, d)
    print(f"\n   KA(b) CLEAN scope: worst |delta| over all rungs = {clean_max:.3e}")
    if clean_max != 0.0:
        note("BE4", f"CLEAN moved ({clean_max:.3e}) — the clipSat override reached outside the "
                    "OD path, so every OD number below is confounded.")
    else:
        print("         => bit-identical: the override is OD-only, as the topology requires.")

    # ---- known answer (c): NON-VACUITY — every OD render must move at some rung.
    inert = []
    for fname in sorted(set(COND.values())):
        r0 = A.load(paths[(fname, 1.0)])
        moved = max(float(np.max(np.abs(A.load(paths[(fname, L)]) - r0))) for L in L_RUNGS[1:])
        if moved == 0.0:
            inert.append(fname)
    print(f"   KA(c) non-vacuity: {len(inert)} of {len(set(COND.values()))} OD conditions INERT")
    if inert:
        die("BE4", f"the --fit override never reached the stage for {inert} — "
                   "every number in this gate would be a fiction.")

    # ---- score.  PROCESSES, not threads: the per-item work is numpy (four Farina transfers per
    # sweep), and `parallel.pmap_cpu`'s own docstring measures threads as SLOWER on exactly this
    # shape of workload.
    todo = [(fn, L, out, bands, mid, grade) for (fn, L), out in paths.items() if fn != CLEAN_CTRL]
    print(f"   scoring {len(todo)} renders x {len(DRIVEN)} sweeps ...")
    scored = dict(zip([(t[0], t[1]) for t in todo], pmap_cpu(_score_one, todo, jobs)))

    # ---- known answer (a): L = 1.0 must reproduce the stored baseline.
    print("\n   KA(a) baseline reproduction at L = 1.0 (abs midband, sweep_drv_-12):")
    worst = 0.0
    for g in ("cut", "flat", "boost"):
        fn = COND[(g, "noon")]
        got = scored[(fn, 1.0)]["sweep_drv_-12"]["abs_mid"]
        want = base_rows[(g, "sweep_drv_-12")]["abs_mid"]
        worst = max(worst, abs(got - want))
        print(f"         {g:6s} stored {want:+7.3f}   re-rendered {got:+7.3f}   "
              f"delta {got - want:+7.4f}")
    if worst > 0.01:
        note("BE4", f"L=1.0 does not reproduce the stored baseline (worst {worst:.4f} dB) — "
                    "the baseline has silently moved (s77's SHIP_RECORD).")
    else:
        print(f"         => reproduces to {worst:.4f} dB.")

    # BE5b's reference: the per-band absolute error at the SHIPPED point, keyed by condition.
    REPORT["be5_base_err"] = {f"{fn}|{sw}": scored[(fn, 1.0)][sw]["abs_grade_bands"]
                              for fn in sorted(set(COND.values())) for sw in DRIVEN}
    REPORT["be4"] = {"clean_max_delta": clean_max, "baseline_worst": worst,
                     "scored": {f"{k[0]}|{k[1]}": v for k, v in scored.items()}}
    return scored


# ------------------------------------------------------------------------------------------------
def be5(scored):
    print("=" * 100)
    print("BE5a  THE LOCUS — AND IT MUST BE READ SIGNED")
    print("      ⚠ `mean|error|` of a MONOTONE signed error has a V at the zero crossing BY")
    print("        CONSTRUCTION.  This gate's own first draft published that V as an 'interior")
    print("        optimum'.  The stop is about the MECHANISM's locus, so read the signed one.")
    satsum = REPORT["satsum"]
    print(f"\n   {'L':>7}{'satsum V':>10}  |  " + "".join(f"{g:>9s}" for g in ("cut", "flat", "boost"))
          + f"{'SIGNED':>10s}{'mean|abs|':>11s}  |{'match rms':>11s}")
    curve_signed, curve_abs, curve_rms = [], [], []
    for L in L_RUNGS:
        per = {g: float(np.mean([scored[(COND[(g, d)], L)][sw]["abs_mid"]
                                 for d in ("min", "noon", "max") for sw in DRIVEN]))
               for g in ("cut", "flat", "boost")}
        allabs = [abs(scored[(COND[(g, d)], L)][sw]["abs_mid"])
                  for g in ("cut", "flat", "boost") for d in ("min", "noon", "max") for sw in DRIVEN]
        allrms = [scored[(COND[(g, d)], L)][sw]["rms_grade"]
                  for g in ("cut", "flat", "boost") for d in ("min", "noon", "max") for sw in DRIVEN]
        curve_signed.append(float(np.mean(list(per.values()))))
        curve_abs.append(float(np.mean(allabs)))
        curve_rms.append(float(np.mean(allrms)))
        print(f"   {L:7.3f}{satsum * L:10.3f}  |  " + "".join(f"{per[g]:+9.3f}" for g in
              ("cut", "flat", "boost")) + f"{curve_signed[-1]:+10.3f}{curve_abs[-1]:11.3f}"
              f"  |{curve_rms[-1]:11.3f}")

    def shape(name, y, signed_ok=False):
        i = int(np.argmin(y))
        dif = np.diff(y)
        mono = bool(np.all(dif >= -1e-12) or np.all(dif <= 1e-12))
        interior = (0 < i < len(y) - 1) and not mono
        depth = min(y[0] - y[i], y[-1] - y[i])
        print(f"   {name:26s} argmin L={L_RUNGS[i]:6.3f}  monotone={str(mono):5s}  "
              f"interior optimum={str(interior):5s}  depth re both ends {depth:+7.3f} dB")
        return dict(argmin_L=L_RUNGS[i], interior=interior, monotone=mono, depth=float(depth))

    print()
    ss = shape("SIGNED midband error", curve_signed)
    sa = shape("mean|abs| midband", curve_abs)
    sr = shape("gain-matched graded rms", curve_rms)
    if ss["monotone"] and sa["interior"]:
        print("\n   ⇒ the signed error is MONOTONE while its absolute value is not: the mean|abs|")
        print("     minimum is the ZERO CROSSING of a monotone gain, not an optimum.  Only the")
        print("     signed column and the gain-matched column can carry the stop's verdict.")

    # ---- BE5b: is this lever a GAIN?  The decisive question, and it costs no render.
    print("\n" + "=" * 100)
    print("BE5b  IS THE LEVER A GAIN?  (level part vs shape part of what clipSat delivers)")
    print("      Per band, the CHANGE in absolute error from L=1.0 to each rung, split into its")
    print("      MEAN (a pure scalar — which the 162-capture matrix deletes by construction) and")
    print("      the RESIDUAL rms (the shape the scalar cannot explain).")
    print(f"\n   {'L':>7}{'level part dB':>15}{'shape part dB':>15}{'shape/level':>13}"
          f"{'shape re the 5.5 dB error':>27}")
    base_err = REPORT["be5_base_err"]
    rows = []
    for L in L_RUNGS[1:]:
        deltas = []
        for g in ("cut", "flat", "boost"):
            for d in ("min", "noon", "max"):
                for sw in DRIVEN:
                    a1 = np.array(scored[(COND[(g, d)], L)][sw]["abs_grade_bands"])
                    a0 = np.array(base_err[f"{COND[(g, d)]}|{sw}"])
                    deltas.append(a1 - a0)
        dl = np.array(deltas)
        level = float(np.mean(np.abs(dl.mean(axis=1))))
        resid = float(np.sqrt(np.mean(np.square(dl - dl.mean(axis=1, keepdims=True)))))
        rows.append(dict(L=L, level=level, shape=resid))
        print(f"   {L:7.3f}{level:15.3f}{resid:15.3f}{resid / level:13.3f}"
              f"{100.0 * resid / curve_rms[0]:26.1f}%")

    best = min(rows, key=lambda r: abs(r["L"] - sa["argmin_L"]))
    print(f"\n   At the mean|abs| argmin (L = {best['L']:.3f}): the lever delivers "
          f"{best['level']:.3f} dB of LEVEL and {best['shape']:.3f} dB of SHAPE "
          f"({100.0 * best['shape'] / best['level']:.1f} % as much shape as level).")
    rr = [r["shape"] / r["level"] for r in rows]
    print(f"   The shape/level ratio is {min(rr):.3f}-{max(rr):.3f} across the WHOLE sweep — the "
          "lever\n   makes ONE fixed shape scaled by how far it is turned, not a tunable family.")

    # ---- The bar-free half.  Delivering shape is not the same as delivering the RIGHT shape.
    # Project the lever's per-band shape change onto the defect's own per-band shape and report
    # cos^2 -- a SHARE, which needs no threshold to read (GATE AR's r^2, s154).  Both vectors are
    # de-meaned first, so a pure scalar is free to BOTH sides and the projection is about shape only.
    print("\n   ⭐ ALIGNMENT — is the shape it delivers the shape the defect needs?")
    print("      cos^2 between the lever's per-band shape change and the residual shape error.")
    print("      A SHARE: 1.0 = the lever points exactly at the defect, 0.0 = orthogonal.")
    print(f"\n   {'L':>7}{'median cos^2':>14}{'best reachable rms dB':>24}{'vs 5.5 dB now':>16}")
    align = []
    for L in L_RUNGS[1:]:
        cs, reach = [], []
        for g in ("cut", "flat", "boost"):
            for d in ("min", "noon", "max"):
                for sw in DRIVEN:
                    e = np.array(base_err[f"{COND[(g, d)]}|{sw}"])
                    dv = np.array(scored[(COND[(g, d)], L)][sw]["abs_grade_bands"]) - e
                    e = e - e.mean()
                    dv = dv - dv.mean()
                    if np.linalg.norm(dv) < 1e-12 or np.linalg.norm(e) < 1e-12:
                        continue
                    c2 = float(np.dot(e, dv) ** 2 / (np.dot(e, e) * np.dot(dv, dv)))
                    cs.append(c2)
                    # the best this DIRECTION can reach, with its amplitude chosen freely per
                    # condition (i.e. strictly more than any single shipped constant could do).
                    # `1 - c2` is clamped at 0: a perfectly aligned direction gives c2 = 1 to
                    # within float rounding, and an unclamped sqrt of -2e-16 returns nan, which
                    # then propagates silently through the verdict as "not aligned".
                    reach.append(float(np.sqrt(np.mean(np.square(e)) * max(0.0, 1.0 - c2))))
        base_rms = float(np.mean([np.sqrt(np.mean(np.square(
            np.array(base_err[f"{COND[(g, d)]}|{sw}"])
            - np.array(base_err[f"{COND[(g, d)]}|{sw}"]).mean())))
            for g in ("cut", "flat", "boost") for d in ("min", "noon", "max") for sw in DRIVEN]))
        mc, mr_ = float(np.median(cs)), float(np.mean(reach))
        align.append(dict(L=L, cos2=mc, reachable=mr_, base=base_rms))
        print(f"   {L:7.3f}{mc:14.3f}{mr_:24.3f}{base_rms:16.3f}")
    a_best = min(align, key=lambda r: r["reachable"])
    print(f"\n   Best case over the whole sweep, amplitude free per condition: shape error "
          f"{a_best['base']:.3f} -> {a_best['reachable']:.3f} dB "
          f"({100.0 * (1 - a_best['reachable'] / a_best['base']):.1f} % of it).")
    REPORT["be5_align"] = align

    print("\n" + "=" * 100)
    print("BE5c  W1's PRE-REGISTERED STOP, applied as written:")
    print('      "if the locus is monotone with NO interior optimum, that is the \'make the clipper')
    print('       see less\' degeneracy ... REFUTE and STOP AT ONE SESSION."')
    # The stop asks about the MECHANISM's locus.  Two ways it can fail to fire:
    #   (i)  the SIGNED locus turns over -- an actual interior optimum, no bar needed; or
    #   (ii) the lever points at the defect -- graded BAR-FREE on the alignment SHARE, because the
    #        gain-matched column's 0.084 dB would otherwise be judged against a number I invented
    #        (`a-threshold-you-guessed-is-not-a-guard`; s154's "a verdict that flips on 1 % of its
    #        own bar is not a verdict").  A share needs no threshold: aligned means cos^2 -> 1.
    ali = REPORT["be5_align"]
    a_best = min(ali, key=lambda r: r["reachable"])
    closes = 1.0 - a_best["reachable"] / a_best["base"]
    survive = []
    if not ss["monotone"]:
        survive.append(f"the SIGNED midband error turns over at L={ss['argmin_L']:.3f}")
    if closes >= 0.5:
        survive.append(f"the lever's shape is ALIGNED with the defect (closes "
                       f"{100 * closes:.1f} % of the shape error at free amplitude)")
    if survive:
        v = ("STOP DOES NOT FIRE — " + "; ".join(survive) + ".  W1 continues to S2.")
    else:
        v = (f"STOP FIRES, on both of its own terms and one more.  (1) The SIGNED midband error is "
             f"MONOTONE across the whole sweep, {curve_signed[0]:+.2f} dB at L=1.0 to "
             f"{curve_signed[-1]:+.2f} dB at the physical ceiling, {len(L_RUNGS) - 1} of "
             f"{len(L_RUNGS) - 1} steps one-signed — no interior optimum exists; the mean|abs| V at "
             f"L={sa['argmin_L']:.3f} is that monotone curve's ZERO CROSSING. (2) What it delivers "
             f"is {min(r['shape'] / r['level'] for r in rows):.2f}-"
             f"{max(r['shape'] / r['level'] for r in rows):.2f} dB of shape per dB of LEVEL, a "
             f"ratio constant across the sweep — ONE fixed direction, and the matrix deletes the "
             f"level part by construction. (3) BAR-FREE: that direction is NOT the defect's — "
             f"median cos^2 {a_best['cos2']:.3f}, so even with its amplitude chosen freely PER "
             f"CONDITION (more than any shipped constant could do) it closes only "
             f"{100 * closes:.1f} % of the shape error. ⇒ clipSat is a LEVEL lever wearing a "
             "headroom name: the 'make the clipper see less' degeneracy for the FIFTH time. "
             "W1 is REFUTED at one session of its three.")
    print(f"\n   VERDICT: {v}")
    REPORT["be5"] = {"L": list(L_RUNGS), "curve_signed": curve_signed, "curve_abs": curve_abs,
                     "curve_rms": curve_rms, "shape_signed": ss, "shape_abs": sa, "shape_rms": sr,
                     "gain_decomposition": rows, "closes_frac": closes, "verdict": v}


# ------------------------------------------------------------------------------------------------
def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--jobs", type=int, default=max(1, (os.cpu_count() or 4) - 2))
    ap.add_argument("--no-render", action="store_true",
                    help="run BE0-BE3 only (the premise screen costs no renders)")
    a = ap.parse_args()

    bands = [round(b, 1) for b in A.fractional_octave_freqs(20.0, 20000.0, 3)]
    base = json.load(open(BASELINE))
    if [round(x, 1) for x in base["meta"]["bands"]] != bands:
        die("BE0", "the baseline's band list is not this tool's — the two instruments disagree.")

    ship = be0()
    rows, mid, grade, caps = be1(base, bands)
    be1b(caps, bands)
    be2(ship, rows)
    be3(rows)
    if not a.no_render:
        scored = be4(ship, bands, mid, grade, rows, a.jobs)
        be5(scored)

    print("=" * 100)
    os.makedirs(os.path.dirname(OUT_JSON), exist_ok=True)
    json.dump(REPORT, open(OUT_JSON, "w"), indent=1)
    print(f"wrote {OUT_JSON}")
    if FAILED:
        print("\nGATE BE: VALIDITY FAILURES")
        for f in FAILED:
            print("  " + f)
        sys.exit(1)
    print("GATE BE: all validity checks passed (physics verdicts above are computed, not gated).")


if __name__ == "__main__":
    main()
