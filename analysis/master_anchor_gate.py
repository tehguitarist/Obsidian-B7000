#!/usr/bin/env python3
"""
GATE T — the MASTER ladder's top two detents, and what they do to `kOutputMakeup`.

WHY THIS EXISTS
---------------
Session 112 found `master-1545_gain-n12_base-clean.wav` and `master-1700_gain-n12_base-clean.wav`
carry the same signal, and diagnosed it as CLIPPING ("the n12 ladder had no resolution above
master-1430 -- even at gain-n12 the chain is pinned at the top two").  That diagnosis is REFUTED
here, and the replacement diagnosis matters because it reaches a SHIPPED CONSTANT:

  * The pinning is real but is confined to ONE segment (`lvl_-3`, the hottest ladder rung).
    Every other segment -- including `sweep_clean` at ~-30 dBFS RMS, and `lvl_-36` at -33 dBFS --
    is nowhere near the ceiling.
  * The two files nevertheless agree at EVERY segment, to ~3 decimal places, across a >30 dB
    span of segment levels.  A ceiling cannot do that: clipping is not a pure gain, so it cannot
    move a -33 dBFS segment by the same number of dB as a -0.1 dBFS one.
    => the two files are ONE capture at ONE knob position (duplicated / mis-dialled), and that
       position is neither detent -- it sits at +14.053 dB re noon where the TRUE values are
       +16.480 (1545) and +18.500 (1700).

  * `analysis/master_taper_makeup.py` anchors `kOutputMakeup` at exactly that file:
        MASTERS[-1] = (1.00, "master-1700_gain-n12_base-clean.wav")
        kOutputMakeup = R_cap(1.0) / R_mdl(1.0; makeup=1)
    read on `sweep_clean` -- a segment this gate proves is UNPINNED, so the anchor is not
    corrupted by clipping; it is corrupted by knob position, by 4.447 dB.
    => `kOutputMakeup = 2.599` is LOW by 4.447 dB.  Corrected single-point value: 4.337.

  * The same file is the denominator of every taper point (`ratio = lv[m] / lv[1.0]`), so it
    contaminates `masterTaperExp` too.

  * And session 106's "`kOutputMakeup` is CONFIRMED RIGHT and must not be touched (+0.007 dB at
    master-1700)" is INVALID: it re-confirmed against the same corrupted capture.

WHAT THIS GATE DOES NOT DO
--------------------------
It does NOT propose shipping 4.337.  A one-parameter taper cannot fit the corrected ladder at all
(per-point exponent spans 1.74..3.51), so the makeup and the taper have to be re-derived together,
and that is Phase 10 C (MASTER taper), which the user explicitly scheduled LAST in session 106.
This gate exists so the next session inherits the measurement rather than the refuted story.

No render.  Reads the capture wavs only.
Run:  /opt/homebrew/bin/python3.11 analysis/master_anchor_gate.py
"""
import os, sys, math, json, argparse
import numpy as np
from scipy.io import wavfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gen_test_signal as G

CAPDIR = "analysis/captures"

# Detent token -> knob value.  7 o'clock = 0.0 ... 5 o'clock (1700) = 1.0 over 10 clock-hours.
KNOB = {"0700": 0.000, "0815": 0.125, "0930": 0.250, "1045": 0.375, "1200": 0.500,
        "1315": 0.625, "1430": 0.750, "1545": 0.875, "1700": 1.000}

# The two detents whose gain-n12 captures are the duplicate pair.
DUP_DETENTS = ("1545", "1700")

NOMINAL_N12_TO_N18_PAD = 6.000      # 18 dB send minus 12 dB send
PAD_TOL              = 0.010        # dB.  s112 measured this at 6.000 on four linear twins.
PURE_GAIN_SPAN_TOL   = 0.010        # dB.  A pure gain is flat in frequency AND in level.
DUP_IDENTITY_DBFS    = -60.0        # two takes of one output differ far below this
DETENT_STEP_MIN_DB   = 0.50         # a real detent must move the output by at least this

SHIPPED_MAKEUP     = 2.599          # src/dsp/GainStaging.h  kOutputMakeupNominal
SHIPPED_TAPER_EXP  = 1.998          # src/dsp/FitParams.h    masterTaperExp

_TIMES = G.segment_times()
_fail = []


def fail(tag, msg):
    _fail.append(f"{tag}: {msg}")
    print(f"  ** {tag} FAIL -- {msg}")


def load(path):
    fs, x = wavfile.read(path)
    if x.dtype.kind == "i":
        x = x.astype(np.float64) / np.iinfo(x.dtype).max
    else:
        x = x.astype(np.float64)
    return fs, (x[:, 0] if x.ndim > 1 else x)


def seg(path, name):
    fs, x = load(path)
    t0, t1 = _TIMES[name]
    return fs, x[int(t0 * fs):int(t1 * fs)]


def seg_rms_db(path, name, trim=True):
    _, s = seg(path, name)
    if trim:                      # drop the ramps at each end
        n = len(s)
        s = s[n // 10: -n // 10]
    return 20 * math.log10(math.sqrt(np.mean(s ** 2)) + 1e-300)


def seg_peak(path, name):
    _, s = seg(path, name)
    return float(np.abs(s).max())


def bands(path, name="sweep_clean", nb=29, lo=25.0, hi=16300.0):
    fs, s = seg(path, name)
    f = np.fft.rfftfreq(len(s), 1 / fs)
    X = np.abs(np.fft.rfft(s))
    e = np.geomspace(lo, hi, nb + 1)
    out = []
    for i in range(nb):
        m = (f >= e[i]) & (f < e[i + 1])
        out.append(10 * math.log10(np.mean(X[m] ** 2)) if m.any() else np.nan)
    return np.array(out)


def cap(name):
    return f"{CAPDIR}/{name}"


def n12(det):
    return cap(f"master-{det}_gain-n12_base-clean.wav")


def n18(det):
    return cap(f"master-{det}_gain-n18_base-clean.wav")


def detent_corrections():
    """dB to ADD to a duplicated detent's n12 capture reading to put it on the corrected ladder.

    THE ONE DEFINITION of session 115's ladder correction.  `t4_ladder` below consumes it, so
    GATE T's own monotonicity known answer exercises it on every run; GATE O imports it rather
    than transcribing "4.447", so the two cannot drift.

    Only DUP_DETENTS are corrupted (T3: the two top n12 files carry the SAME signal, at a knob
    position that is neither detent).  Every other detent reads its own level and gets 0.0.

    Derivation, per detent: the fresh gain-n18 capture promoted through the DIRECTLY measured
    n12->n18 pad (T2: 6.000 dB, flat to 0.0002, derived WITHOUT the contaminated ref-clean.wav),
    minus what the corrupted n12 file actually reads.  `noon` cancels, so this is independent of
    the ladder's anchor.
    """
    pad = _pad_quiet()
    return {det: (seg_rms_db(n18(det), "sweep_clean") + pad) - seg_rms_db(n12(det), "sweep_clean")
            for det in DUP_DETENTS}


def _pad_quiet():
    """T2's pad, without the printing -- so importers do not inherit GATE T's stdout."""
    d = bands(cap("ref-clean_gain-n12.wav")) - bands(cap("ref-clean_gain-n18.wav"))
    d = d[np.isfinite(d)]
    pad, span = float(d.mean()), float(d.max() - d.min())
    if abs(pad - NOMINAL_N12_TO_N18_PAD) > PAD_TOL or span > PURE_GAIN_SPAN_TOL:
        raise RuntimeError(f"master_anchor_gate: n12->n18 pad {pad:.4f} dB (span {span:.4f}) is "
                           f"not the flat {NOMINAL_N12_TO_N18_PAD} dB pad T2 requires -- refusing "
                           f"to hand a correction to an importer.  Run GATE T for the diagnosis")
    return pad


# ---------------------------------------------------------------------------------------------
def t1_membership():
    """Asserted membership.  Exits rather than warns."""
    print("\n[T1] MEMBERSHIP")
    missing = [d for d in KNOB if not os.path.exists(n12(d))]
    if missing:
        fail("T1", f"gain-n12 ladder incomplete, missing detents {missing}")
    else:
        print(f"  gain-n12 ladder complete: {len(KNOB)} detents 0700..1700")
    for d in DUP_DETENTS:
        if not os.path.exists(n18(d)):
            fail("T1", f"gain-n18 replacement for {d} is absent -- the ladder top cannot be corrected")
    for f in ("ref-clean_gain-n12.wav", "ref-clean_gain-n18.wav"):
        if not os.path.exists(cap(f)):
            fail("T1", f"{f} absent -- the pad cannot be derived without the contaminated ref-clean")
    # knob map must be the one captures.py parses (monotone, endpoints exact)
    ks = [KNOB[d] for d in sorted(KNOB)]
    if ks != sorted(ks) or ks[0] != 0.0 or ks[-1] != 1.0:
        fail("T1", "knob map is not monotone 0..1")
    else:
        print("  knob map monotone, endpoints exactly 0.0 / 1.0")


def t2_pad():
    """The n12->n18 pad, derived WITHOUT the contaminated ref-clean.wav (GATE S2).

    Known answer: the clean path is linear, so this is a pure gain -- flat in frequency -- and
    must equal the nominal 6.000 dB.  Control: routing it through the contaminated ref-clean.wav
    must give the IDENTICAL number, because that file appears on both sides and cancels.
    """
    print("\n[T2] n12->n18 PAD  (known answer: 6.000 dB, flat)")
    d = bands(cap("ref-clean_gain-n12.wav")) - bands(cap("ref-clean_gain-n18.wav"))
    ok = np.isfinite(d)
    pad, span = d[ok].mean(), d[ok].max() - d[ok].min()
    print(f"  direct   : {pad:.4f} dB   span {span:.4f} dB over {ok.sum()} bands")
    if abs(pad - NOMINAL_N12_TO_N18_PAD) > PAD_TOL:
        fail("T2", f"pad {pad:.4f} != nominal {NOMINAL_N12_TO_N18_PAD} (tol {PAD_TOL})")
    if span > PURE_GAIN_SPAN_TOL:
        fail("T2", f"pad is not flat (span {span:.4f} dB) -- the clean path is linear, so it must be")

    # control: same quantity via the contaminated file; it cancels, so the answer must not move
    a = bands(cap("ref-clean.wav"))
    ctl = ((a - bands(cap("ref-clean_gain-n18.wav"))) - (a - bands(cap("ref-clean_gain-n12.wav"))))
    ctl = ctl[np.isfinite(ctl)].mean()
    print(f"  control  : {ctl:.4f} dB  (via the contaminated ref-clean.wav -- it cancels)")
    if abs(ctl - pad) > 1e-6:
        fail("T2", "the contaminated file did NOT cancel -- the derivation is not what it claims")
    return pad


def t3_not_saturation():
    """REFUTES s112.  The duplicate pair is a duplicate, not a ceiling.

    Two independent arguments, either of which is sufficient:
      (a) the files are sample-identical to far below any audible level;
      (b) their level difference is a PURE GAIN -- identical at segments spanning >30 dB.
          Clipping is by definition NOT a pure gain: it cannot move a -33 dBFS segment and a
          -0.1 dBFS segment by the same number of dB.
    """
    print("\n[T3] IS IT SATURATION?  (s112 said yes; this tests it)")
    a, b = n12(DUP_DETENTS[0]), n12(DUP_DETENTS[1])

    _, xa = load(a)
    _, xb = load(b)
    n = min(len(xa), len(xb))
    dif = xa[:n] - xb[:n]
    pk = float(np.abs(dif).max())
    pk_db = 20 * math.log10(pk + 1e-300)
    print(f"  (a) sample-wise max|diff| = {pk:.3e} ({pk_db:+.1f} dBFS)")
    if pk_db > DUP_IDENTITY_DBFS:
        fail("T3", f"files are NOT duplicates ({pk_db:+.1f} dBFS) -- re-examine before quoting T6")

    # (b) per-segment level difference, over segments chosen to span a wide level range
    probe = ["lvl_-36", "lvl_-24", "sweep_clean", "cal_1k", "lvl_-6", "lvl_-3"]
    print(f"  (b) per-segment level of each file, and their difference:")
    diffs, pins = [], {}
    for s in probe:
        la, lb = seg_rms_db(a, s), seg_rms_db(b, s)
        diffs.append(la - lb)
        pa = seg_peak(a, s)
        pins[s] = int((np.abs(seg(a, s)[1]) >= 0.985).sum())
        print(f"      {s:14s} {la:8.3f} / {lb:8.3f} dBFS   diff {la-lb:+7.4f}   "
              f"peak {20*math.log10(pa):7.2f} dBFS   pinned {pins[s]}")
    span = max(diffs) - min(diffs)
    lvl_span = max(seg_rms_db(a, s) for s in probe) - min(seg_rms_db(a, s) for s in probe)
    print(f"  => difference is constant to {span:.4f} dB across a {lvl_span:.1f} dB span of segment level")
    if span > PURE_GAIN_SPAN_TOL:
        fail("T3", f"difference is level-dependent ({span:.4f} dB) -- saturation NOT excluded")
    if lvl_span < 25.0:
        fail("T3", f"probe segments span only {lvl_span:.1f} dB -- too narrow to exclude saturation")

    # the pinning IS real, but only in one segment -- state where, so the record is honest
    pinned = [s for s, c in pins.items() if c]
    clean = [s for s, c in pins.items() if not c]
    print(f"  pinned segments : {pinned or 'none'}")
    print(f"  unpinned        : {clean}")
    if "sweep_clean" in pinned:
        fail("T3", "sweep_clean IS pinned -- the makeup anchor WOULD be clipping-corrupted; re-scope T6")
    if not pinned:
        fail("T3", "no segment is pinned at all -- s112's peak observation does not reproduce")
    print("  => VERDICT: a pure gain across >30 dB of level is NOT a ceiling.")
    print("     The pair is ONE capture duplicated / mis-dialled.  s112's saturation reading is REFUTED.")


def t4_ladder(pad):
    """Corrected ladder.  Known answer: a pot law must be MONOTONE in the knob."""
    print("\n[T4] CORRECTED LADDER  (gain-n18 promoted through the measured pad)")
    noon = seg_rms_db(n12("1200"), "sweep_clean")
    corr = detent_corrections()          # the shared definition GATE O imports
    # Known answer: the quiet path importers use must reproduce T2's printed pad exactly, or the
    # number GATE O receives is not the number GATE T validated.
    if abs(_pad_quiet() - pad) > 1e-9:
        fail("T4", f"detent_corrections() used pad {_pad_quiet():.6f} but T2 printed {pad:.6f} -- "
                   f"importers would receive a correction this gate never checked")
    L, raw = {}, {}
    for det, k in KNOB.items():
        raw[k] = seg_rms_db(n12(det), "sweep_clean") - noon
        L[k] = raw[k] + corr.get(det, 0.0)

    print(f"  {'detent':8s} {'knob':>6s} {'n12 file':>10s} {'TRUE':>9s} {'step':>8s}")
    prev = None
    for det in sorted(KNOB, key=lambda d: KNOB[d]):
        k = KNOB[det]
        st = "" if prev is None else f"{L[k]-prev:+8.2f}"
        note = f"   <- n12 file {raw[k]-L[k]:+.3f} dB off" if det in DUP_DETENTS else ""
        print(f"  {det:8s} {k:6.3f} {raw[k]:+10.3f} {L[k]:+9.3f} {st:>8s}{note}")
        prev = L[k]

    ks = sorted(L)
    steps = [L[ks[i + 1]] - L[ks[i]] for i in range(len(ks) - 1)]
    if min(steps) <= 0:
        fail("T4", f"corrected ladder is NOT monotone (min step {min(steps):+.3f} dB)")
    else:
        print(f"  monotone: every step > 0 (min {min(steps):+.2f} dB, max {max(steps):+.2f} dB)")

    # the uncorrected ladder must FAIL that same test -- otherwise the correction is doing nothing
    rsteps = [raw[ks[i + 1]] - raw[ks[i]] for i in range(len(ks) - 1)]
    print(f"  control: UNcorrected ladder min step {min(rsteps):+.3f} dB "
          f"({'flat at the top, as reported' if min(rsteps) < DETENT_STEP_MIN_DB else 'NOT flat'})")
    if min(rsteps) >= DETENT_STEP_MIN_DB:
        fail("T4", "the uncorrected ladder has no flat spot -- the defect does not reproduce")
    return L


def t5_anchor(L):
    """The consequence for kOutputMakeup."""
    print("\n[T5] THE kOutputMakeup ANCHOR")
    bad = seg_rms_db(n12("1700"), "sweep_clean")
    noon = seg_rms_db(n12("1200"), "sweep_clean")
    true_abs = L[1.0] + noon
    err = true_abs - bad
    print(f"  master_taper_makeup.py anchors at MASTERS[-1] = master-1700_gain-n12_base-clean.wav")
    print(f"    file reads  {bad:+8.3f} dBFS on sweep_clean  (UNPINNED -- see T3)")
    print(f"    TRUE 1700   {true_abs:+8.3f} dBFS")
    print(f"  => anchor is LOW by {err:.3f} dB")
    corrected = SHIPPED_MAKEUP * 10 ** (err / 20)
    print(f"  kOutputMakeup  shipped {SHIPPED_MAKEUP:.3f}  ->  {corrected:.3f}   ({err:+.2f} dB)")
    if err < 1.0:
        fail("T5", f"anchor error {err:.3f} dB is too small to be the reported defect")
    return err, corrected


def t6_no_power_law(L):
    """A pot taper is one number; this ladder is not one number."""
    print("\n[T6] CAN A POWER LAW FIT THE CORRECTED LADDER?")
    ps = {}
    for k in sorted(L):
        if k in (0.0, 1.0):
            continue
        d = L[k] - L[1.0]
        ps[k] = d / (20 * math.log10(k))
        print(f"    m={k:.3f}  d={d:+8.3f} dB   p={ps[k]:.3f}")
    lo, hi = min(ps.values()), max(ps.values())
    fitpts = [0.25, 0.50, 0.75]
    num = sum((-20 * math.log10(k)) * (-(L[k] - L[1.0])) for k in fitpts)
    den = sum((20 * math.log10(k)) ** 2 for k in fitpts)
    p_ls = num / den
    print(f"  LS p over m=0.25/0.50/0.75 : {p_ls:.3f}   (shipped masterTaperExp = {SHIPPED_TAPER_EXP})")
    print(f"  per-point p spans {lo:.2f}..{hi:.2f}  (ratio {hi/lo:.2f}x)")
    if hi / lo < 1.25:
        fail("T6", "per-point exponents agree -- a power law WOULD fit, contradicting the write-up")
    print("  => no single exponent fits; makeup and taper must be re-derived TOGETHER (Phase 10 C).")
    return p_ls


def t7_tool_staleness():
    """master_taper_makeup.py's own inputs moved in s112."""
    print("\n[T7] IS THE CALIBRATION TOOL STILL RUNNABLE?")
    needed = ["master-0700_base-clean.wav", "master-0930_base-clean.wav", "ref-clean.wav",
              "master-1430_gain-n12_base-clean.wav", "master-1700_gain-n12_base-clean.wav"]
    gone = [n for n in needed if not os.path.exists(cap(n))]
    for n in needed:
        print(f"    {n:44s} {'present' if n not in gone else '** MISSING (archived in s112)'}")
    if gone:
        print(f"  => master_taper_makeup.py exits rc=2 on {len(gone)} missing capture(s).")
        print("     It CANNOT be re-run as-is; Phase 10 C must re-point it at the gain-n12 ladder.")
    else:
        fail("T7", "all captures present -- the staleness this gate reports does not reproduce")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", default="analysis/reports/s115_master_anchor.json")
    a = ap.parse_args()

    print("=" * 94)
    print("GATE T -- MASTER ladder top detents and the kOutputMakeup anchor")
    print("=" * 94)

    t1_membership()
    pad = t2_pad()
    t3_not_saturation()
    L = t4_ladder(pad)
    err, corrected = t5_anchor(L)
    p_ls = t6_no_power_law(L)
    t7_tool_staleness()

    print("\n" + "=" * 94)
    if _fail:
        print(f"GATE T: {len(_fail)} FAILURE(S)")
        for f in _fail:
            print("  " + f)
    else:
        print("GATE T: OK -- all guards pass")
    print("=" * 94)

    os.makedirs(os.path.dirname(a.json), exist_ok=True)
    with open(a.json, "w") as fh:
        json.dump({"pad_db": pad, "anchor_error_db": err,
                   "kOutputMakeup_shipped": SHIPPED_MAKEUP,
                   "kOutputMakeup_corrected": corrected,
                   "masterTaperExp_shipped": SHIPPED_TAPER_EXP,
                   "masterTaperExp_ls_corrected": p_ls,
                   "ladder_re_noon": {str(k): L[k] for k in sorted(L)},
                   "failures": _fail}, fh, indent=2)
    print(f"wrote {a.json}")
    return 1 if _fail else 0


if __name__ == "__main__":
    sys.exit(main())
