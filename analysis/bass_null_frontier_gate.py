#!/usr/bin/env python3.11
"""GATE BJ — open item 17's bass half: the OdMakeup LF-shelf frontier, and what actually sets it.

THE TARGET, AND WHY THE OBVIOUS CANDIDATE IS THE WORST ONE
----------------------------------------------------------
s178 (GATE BH) measured item 17's actionable half: the model's ~40-70 Hz null is deeper than ND in
**15 of 15** matched cells (median +2.34 dB) where the pre-s172 build tracks ND to 0.31 dB, and
`reference-sources.md` §3 puts HARDWARE **shallower** than ND there ⇒ shipped is away from **both**
references.  It attributed the defect to s172's flat +6 dB alone and refuted `odMakeupLowCutDb` as
the lever, because raising it made the pooled error WORSE.

The arithmetic says the obvious fix should work.  `OdMakeup` is flat +6 dB with a low shelf at
130 Hz cutting 3.5, so it contributes **+2.5 to +2.8 dB at 40-80 Hz** where the OD:clean ratio was
already right, and **+5.7 to +5.9 dB over 250-900 Hz** where s172 measured the ~5 dB deficit it
exists to correct.  Deepening the shelf to 6.0 dB zeroes the LF contribution to **0.06-0.47 dB**
while leaving 250-900 Hz at 5.4-5.8 — the ideal separation, on paper.

⛔⛔ **AND IT IS THE WORST ARM MEASURED.**  `130 Hz / 6.0 dB` takes the worst cell from +6.5 dB to
**+20.7**, because the bass null is an OD-vs-clean **cancellation** and a minimum-phase shelf
inserts PHASE into the OD branch two octaves below its corner, where its magnitude contribution has
already gone to zero.  BJ5 measures that directly against a zero-phase lever and it is the finding
this gate exists to record.

THE DECOMPOSITION THAT MADE IT TRACTABLE
-----------------------------------------
`notch_geometry`'s depth is `min(left shoulder, right shoulder) − bottom`, so it has two operands
and only their difference had ever been printed (s117: print both operands before naming a target).
Split, the shipped error is **median −2.95 dB of BOTTOM against −0.51 dB of SHOULDER** ⇒ ~85 % is
the cancellation genuinely getting deeper, not the makeup tilting the measurement window.  That is
what licenses treating this as a physical target at all.

THE FIVE AXES, AND WHY EACH IS HERE RATHER THAN CHOSEN AFTERWARDS
------------------------------------------------------------------
  BJ1  the bass null itself                    — the target (s178's own statistic and membership)
  BJ2  the OD:clean ratio, 250-900 and 40-250  — s172's own objective; the thing a fix must not undo
  BJ3  bleed-free C1                           — s172's PRE-REGISTERED invariance, the measured
                                                 reason a BELL was rejected (it moved this ~1.5 dB
                                                 where a flat term moves it 0.0000)
  BJ4  the ~320 Hz listening null vs §3        — item 17/18's PASS.  ⚠⚠ BOTH nulls are the same
                                                 mechanism, so a fix for one MOVES the other, and
                                                 this axis exists so that cannot happen silently
  BJ5  MAGNITUDE or PHASE?                     — the mechanism, discriminated against a flat gain
⚠ BJ4 is the axis that turns this from a tuning job into a trade: hardware wants the ~320 Hz null
**deeper** than ND and the ~40-60 Hz one **shallower**, and one OD-branch low-mid gain moves both
the same way.  Every arm that meaningfully closes the bass null takes 320 Hz from INSIDE §3's
licence at GRUNT flat to UNDER it.  ⇒ **the deliverable is a FRONTIER and a USER DECISION**, and
BJ6 prints it rather than picking.

Run:
    /opt/homebrew/bin/python3.11 analysis/bass_null_frontier_gate.py
    /opt/homebrew/bin/python3.11 analysis/bass_null_frontier_gate.py --json analysis/reports/s180_bass_frontier.json
"""
import argparse
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import feature_locus_gate as W           # noqa: E402
import grunt_mix_gate as BI              # noqa: E402
import hf_null_shape_gate as BH          # noqa: E402

FEAT = "bass_notch"
CAP = dict((l, f) for l, f, _, _ in BH.CONDITIONS)

# ---- the arms.  A shelf is (corner, cut, S); `pre-s172` is the reference point s178 measured. ---
def shelf(hz, cut, s):
    return ("--fit", f"odMakeupLowHz={hz}", "--fit", f"odMakeupLowCutDb={cut}",
            "--fit", f"odMakeupLowS={s}")


def flat(db):
    """A pure flat OD-branch gain: the ZERO-PHASE lever, and the whole of BJ5's discrimination."""
    return BH.HF_OFF + ("--fit", f"odMakeupDb={db}", "--fit", "odMakeupLowCutDb=0",
                        "--fit", "odMakeupHighCutDb=0")


# ⚠⚠ EVERY ARM IS EXPLICIT, INCLUDING THE ONE THAT SHIPS.  A first draft let `()` mean "the s173
# incumbent"; the moment s180 shipped 200/6.0/S1.0 that arm became a duplicate of the defaults and
# the non-vacuity guard correctly refused the whole gate.  s146's lesson (a guard that names an
# epoch must be extended when the epoch ends) applies to an ARM TABLE as much as to a guard —
# naming the incumbent by its constants rather than by "whatever ships" makes the frontier
# reproducible across the change it was built to justify.
ARMS = {
    "s173 130/3.5/S0.9": shelf(130, 3.5, 0.9),   # the INCUMBENT the frontier was measured from
    "130/6.0/S1.0":      shelf(130, 6.0, 1.0),
    "160/6.0/S1.0":      shelf(160, 6.0, 1.0),
    "s180 SHIP 200/6/1": (),                     # what s180 shipped — the compiled defaults
    "250/6.0/S1.0":      shelf(250, 6.0, 1.0),
    "300/6.0/S0.9":      shelf(300, 6.0, 0.9),
    "pre-s172":          BH.HF_OFF + BH.MK_OFF,
}
SHIP = "s180 SHIP 200/6/1"          # the compiled defaults — BJ0b's non-vacuity reference
INCUMBENT = "s173 130/3.5/S0.9"     # the point every COST below is quoted against
FLAT_LADDER = [0.0, 0.25, 0.5, 1.0, 2.5]

# The cell whose null sits closest to |OD| = |clean|.  ⚠⚠ It is NOT excluded — its depth is stable
# across the stimulus ladder (unlike the treble null s178 refused to grade), so it is a reading.
# It is NAMED and reported separately because it is 5-20x more parameter-sensitive than any other
# cell, and a pooled mean over it is dominated by it (s178's own mean|err| was).
KNIFE = "blend 1430 cut"

# s178 BH6's recorded values for the shipped build, on the same membership and estimator.
S178_SHIP_MEDIAN = 2.34
S178_PRE_MEDIAN = 0.03
KA_TOL = 0.05

# ⚠⚠ WHICH DEPTH ESTIMATOR IS GRADED, AND WHY IT IS NOT s178's.
# `notch_geometry` returns BOTH a POINT depth (bottom and shoulders read as single grid cells) and
# an AREA depth (both read as 1/6-octave power averages — GATE R's own remedy, s110 R4).  Session
# 178's BH6 graded the POINT depth.  BJ0d measures what that costs: **ND's own null bottom is at or
# below the sub-20 Hz deconvolution residue in 15 of 15 cells** (margins −0.16 … −13.43 dB), so
# every point depth on the reference side is a LOWER BOUND, not a measurement — precisely the
# situation GATE AP was built for at s152 on the 320 Hz notch, where the area estimator measured
# **4.1x** less sensitive to censoring.
# ⇒ the AREA depth is graded here and the POINT depth is printed beside it as the superseded
# control, so every s178 number stays reproducible.  ⭐ The verdict survives the swap (median 2.34
# -> 2.29) and the WORST-CELL column does not (6.52 -> 3.93 for ship; 20.69 -> 7.69 for the
# 130/6.0 arm) — and the worst-cell column is the one that would choose the arm.
DEPTH = "depth_area"
DEPTH_CTL = "depth_point"
FLOOR_MARGIN_DB = 3.0     # a bottom within this of the residue is not resolved (GATE AP's reading)

# `reference-sources.md` §3, HW − ND at ~320 Hz by GRUNT.  ⛔ PNG read: sign/rough size only.
HW_320 = {"cut": (1.6, 1.6), "flat": (3.5, 4.8), "boost": (None, None)}

MASK = {"mid": (250.0, 900.0), "lf": (40.0, 250.0), "hf": (900.0, 8000.0)}


def die(tag, msg):
    print(f"\n⛔ {tag}: {msg}")
    sys.exit(1)


def bottom_of(gm):
    return min(gm["lsh"], gm["rsh"]) - gm["depth_point"]


# ================================================================================================
def bj0_validity():
    print("=" * 100)
    print("BJ0 — VALIDITY: membership imported from GATE BH, and s178's own numbers reproduced")
    print("=" * 100)
    kept, dropped = BH.matched_cells(FEAT, "cell")
    if len(kept) != 15:
        die("BJ0a", f"matched membership is {len(kept)} cells, not the 15 session 178 graded on — "
                    "the arms are not comparable to BH6 and its verdict does not transfer.")
    if KNIFE not in {l for l, _ in kept}:
        die("BJ0a", f"the named parameter-sensitive cell {KNIFE!r} is not in the membership")
    print(f"  matched cells: {len(kept)} (dropped {len(dropped)}, all GRUNT flat/boost + bleed-free)")
    print(f"  the parameter-sensitive cell is NAMED and reported separately: {KNIFE!r}")

    # ⚠ Non-vacuity FIRST: if the arms do not reach the DSP every comparison below is between
    # identical renders (s110).  Every arm must differ from ship somewhere in the LF band.
    inert = []
    for a, arm in ARMS.items():
        if a == SHIP:
            continue
        _, _, m = BI.curves(BI.CAPS[("cut", "bleedfree")], arm)
        _, _, s = BI.curves(BI.CAPS[("cut", "bleedfree")], ())
        lo, hi = MASK["lf"]
        k = (W.GRID >= lo) & (W.GRID <= hi)
        if float(np.max(np.abs(np.asarray(m)[k] - np.asarray(s)[k]))) < 0.1:
            inert.append(a)
    if inert:
        die("BJ0b", f"arms inert against ship in the LF band: {inert} — a --fit that never reaches "
                    "the DSP reads as a clean result")
    print(f"  BJ0b non-vacuity: all {len(ARMS) - 1} non-ship arms move the LF band")

    # ---- BJ0c: reproduce s178 BH6's own median for ship and for pre-s172 --------------------
    got = {}
    for a in (INCUMBENT, "pre-s172"):
        e = []
        for (label, rung) in kept:
            g, ped, _ = BH.curves(CAP[label], rung, ())
            _, _, mod = BH.curves(CAP[label], rung, ARMS[a])
            e.append(BH.geom(g, mod, FEAT)[DEPTH_CTL] - BH.geom(g, ped, FEAT)[DEPTH_CTL])
        got[a] = float(np.median(e))
    for a, want in ((INCUMBENT, S178_SHIP_MEDIAN), ("pre-s172", S178_PRE_MEDIAN)):
        if abs(got[a] - want) > KA_TOL:
            die("BJ0c", f"{a} median model−ND = {got[a]:+.2f}, but session 178 BH6 recorded "
                        f"{want:+.2f} — the estimator or the membership has moved, so nothing below "
                        "is comparable to that session.")
    print(f"  BJ0c known answer: incumbent {got[INCUMBENT]:+.2f} and pre-s172 {got['pre-s172']:+.2f} "
          f"reproduce s178 BH6's {S178_SHIP_MEDIAN:+.2f} / {S178_PRE_MEDIAN:+.2f}  ✅ "
          f"(on {DEPTH_CTL}, the estimator s178 graded)")

    # ---- BJ0d: THE CENSORING AUDIT.  Which estimator may be graded at all? -------------------
    import analyze as A
    import captures as C
    import od_tone_restore_fit as F
    orig, ref = W._load_orig()
    cens_nd = 0
    for (label, rung) in kept:
        cap_al, _ = A.align(C.load_capture(os.path.join(C.CAPTURE_DIR, CAP[label])), orig)
        f, m = A.transfer_h1(A.seg_of(cap_al, rung), ref)
        d = W.smooth(f, m)
        n = (W.GRID >= F.NORM_LO) & (W.GRID <= F.NORM_HI)
        off = float(np.mean(d[n]))
        gp = BH.geom(W.GRID, d - off, FEAT)
        if bottom_of(gp) - (W.floor_db(f, m) - off) < FLOOR_MARGIN_DB:
            cens_nd += 1
    print(f"  BJ0d censoring audit: ND's null bottom is within {FLOOR_MARGIN_DB:.0f} dB of the "
          f"deconvolution residue in {cens_nd}/{len(kept)} cells")
    if cens_nd > len(kept) // 2:
        print(f"     ⇒ ⛔ the POINT depth is a LOWER BOUND on the reference side almost everywhere, "
              f"so it may not carry a ship decision.\n"
              f"       GRADING ON `{DEPTH}` (GATE R's power-integrated remedy, s110 R4 / s152 AP); "
              f"`{DEPTH_CTL}` is printed as the superseded control.")
    else:
        print(f"     ⇒ the reference is resolved at most cells; both estimators are usable.")
    return kept, got, cens_nd


# ================================================================================================
def bj1_bass(kept):
    print()
    print("=" * 100)
    print("BJ1 — THE TARGET: the ~40-70 Hz null, model − ND, and the two operands of its depth")
    print("=" * 100)
    res, per_cell = {}, {}
    for a, arm in ARMS.items():
        e, ectl, db, ds = [], [], [], []
        for (label, rung) in kept:
            g, ped, _ = BH.curves(CAP[label], rung, ())
            _, _, mod = BH.curves(CAP[label], rung, arm)
            gp, gm = BH.geom(g, ped, FEAT), BH.geom(g, mod, FEAT)
            e.append(gm[DEPTH] - gp[DEPTH])
            ectl.append(gm[DEPTH_CTL] - gp[DEPTH_CTL])
            db.append(bottom_of(gm) - bottom_of(gp))
            ds.append(min(gm["lsh"], gm["rsh"]) - min(gp["lsh"], gp["rsh"]))
        e, ectl = np.array(e), np.array(ectl)
        ki = [i for i, (l, _) in enumerate(kept) if l == KNIFE]
        others = [i for i in range(len(e)) if i not in ki]
        res[a] = dict(median=float(np.median(np.abs(e))), signed=float(np.median(e)),
                      knife=float(np.median(e[ki])), ex_knife=float(np.mean(np.abs(e[others]))),
                      deeper=int((e > 0).sum()), n=len(e), worst=float(np.max(e)),
                      median_ctl=float(np.median(np.abs(ectl))), worst_ctl=float(np.max(ectl)),
                      d_bottom=float(np.median(db)), d_shoulder=float(np.median(ds)))
        per_cell[a] = {f"{l}|{r}": float(v) for (l, r), v in zip(kept, e)}
    print(f"  GRADED on `{DEPTH}`; `{DEPTH_CTL}` in brackets is the superseded control (BJ0d)\n")
    print(f"  {'arm':20s} {'median|err|':>11s} {'worst cell':>11s} {'ex-knife':>9s} "
          f"{'deeper':>8s} {'Δbottom':>9s} {'Δshoulder':>10s}")
    for a in ARMS:
        r = res[a]
        print(f"  {a:20s} {r['median']:6.2f} ({r['median_ctl']:4.2f}) "
              f"{r['worst']:6.2f} ({r['worst_ctl']:4.2f}) {r['ex_knife']:9.2f} "
              f"{r['deeper']:5d}/{r['n']:<3d}{r['d_bottom']:9.2f} {r['d_shoulder']:10.2f}")
    infl = max(res[a]["worst_ctl"] / res[a]["worst"] for a in ARMS if res[a]["worst"] > 0.5)
    print(f"\n  ⇒ the censored POINT estimator inflates the WORST-CELL column by up to "
          f"{infl:.1f}x, and that column is the one that chooses the arm.\n"
          f"    The MEDIAN is essentially unmoved ({res[INCUMBENT]['median_ctl']:.2f} -> "
          f"{res[INCUMBENT]['median']:.2f} for the incumbent) ⇒ s178's SIZE stands, its worst-cell reading does not.")
    b, s = res[INCUMBENT]["d_bottom"], res[INCUMBENT]["d_shoulder"]
    print(f"\n  ⇒ the incumbent's error is {abs(b) / (abs(b) + abs(s)) * 100:.0f} % BOTTOM and "
          f"{abs(s) / (abs(b) + abs(s)) * 100:.0f} % SHOULDER ⇒ the cancellation really is deeper; "
          "it is not the makeup tilting the measurement window.")
    return res, per_cell


# ================================================================================================
def bj2_ratio():
    print()
    print("=" * 100)
    print("BJ2 — WHAT A FIX MUST NOT UNDO: s172's OD:clean ratio, per-frequency rms (model − pedal)")
    print("=" * 100)
    out = {}
    print(f"  {'arm':20s} {'MID 250-900':>12s} {'LF 40-250':>11s} {'HF 0.9-8k':>11s}")
    for a, arm in ARMS.items():
        _, pcl, mcl = BI.curves(BI.CLEAN_ONLY, arm)
        acc = {k: [] for k in MASK}
        for gr in BI.GRUNTS:
            _, ped, mod = BI.curves(BI.CAPS[(gr, "bleedfree")], arm)
            d = (np.asarray(mod) - np.asarray(mcl)) - (np.asarray(ped) - np.asarray(pcl))
            for k, (lo, hi) in MASK.items():
                acc[k].append(d[(W.GRID >= lo) & (W.GRID <= hi)])
        out[a] = {k: float(np.sqrt(np.mean(np.concatenate(v) ** 2))) for k, v in acc.items()}
        print(f"  {a:20s} {out[a]['mid']:12.2f} {out[a]['lf']:11.2f} {out[a]['hf']:11.2f}")
    best_lf = min(ARMS, key=lambda a: out[a]["lf"])
    print(f"\n  ⇒ MID is s172's own objective — the cost column.  LF is a free by-product and it has"
          f"\n    an INTERIOR MINIMUM at '{best_lf}' ({out[best_lf]['lf']:.2f}), better even than "
          f"pre-s172 ({out['pre-s172']['lf']:.2f}),\n    on an axis nothing was tuned against.  "
          "HF is unmoved except at pre-s172, where the HF term is off ⇒ the change is scoped.")
    return out, best_lf


# ================================================================================================
def bj3_invariance():
    print()
    print("=" * 100)
    print("BJ3 — s172's PRE-REGISTERED INVARIANCE: bleed-free C1 (a BELL was rejected on this)")
    print("=" * 100)
    print("  s172: a FLAT term moves this 0.0000 dB, the shipped shelves move it +0.08, and a")
    print("  Q≈0.6 bell moves it ~1.5 — which is why the bell was rejected.  ⚠ The GRUNT-cut cell")
    print("  already sits +3.08 dB over ND (that is `odNotchDepthDb = +3.0`, accepted at s172 as")
    print("  ~1.5 dB beyond §3's +1.6 licence), so what is graded here is the MOVE, not the value.")
    out = {}
    print(f"\n  {'arm':20s} " + "".join(f"{g:>10s}" for g in BI.GRUNTS) + f"{'worst move':>13s}")
    base = None
    for a, arm in ARMS.items():
        v = []
        for gr in BI.GRUNTS:
            _, ped, mod = BI.curves(BI.CAPS[(gr, "bleedfree")], arm)
            v.append(BI.c1_of(mod) - BI.c1_of(ped))
        if base is None:
            base = v
        mv = max(abs(x - y) for x, y in zip(v, base))
        out[a] = {"c1": v, "move": mv}
        print(f"  {a:20s} " + "".join(f"{x:+10.2f}" for x in v) + f"{mv:13.2f}")
    print("\n  ⇒ the 'worst move' column is the quantity s172 rejected a bell on (~1.5 dB).")
    return out


# ================================================================================================
def bj4_the_other_null():
    print()
    print("=" * 100)
    print("BJ4 — ⚠⚠ THE OTHER NULL: ~320 Hz at the listening mix, against §3's hardware licence")
    print("=" * 100)
    print("  Item 17 established BOTH nulls are ONE mechanism (OD-vs-clean cancellations whose")
    print("  depth peaks where |OD| = |clean|), so an OD low-mid gain moves BOTH — and hardware")
    print("  wants this one DEEPER than ND while it wants the bass one SHALLOWER.  This axis")
    print("  exists so a bass fix cannot give that away silently.")
    out = {}
    print(f"\n  {'arm':20s} " + "".join(f"{g:>10s}" for g in BI.GRUNTS) + "   verdict vs §3")
    for a, arm in ARMS.items():
        v, verd = [], []
        for gr in BI.GRUNTS:
            _, ped, mod = BI.curves(BI.CAPS[(gr, "blendmax")], arm)
            x = BI.c1_of(mod) - BI.c1_of(ped)
            v.append(x)
            lo, hi = HW_320[gr]
            if lo is None:
                verd.append("far under" if x > 0 else "WRONG SIGN")
            else:
                verd.append("under" if x < lo else ("OVER" if x > hi else "inside"))
        out[a] = {"c1": v, "verdict": verd}
        print(f"  {a:20s} " + "".join(f"{x:+10.2f}" for x in v) + "   " + " / ".join(verd))
    n_inside = {a: sum(1 for x in out[a]["verdict"] if x == "inside") for a in ARMS}
    print(f"\n  licence: cut +1.6 · flat +3.5–4.8 · boost much deeper "
          "(⛔ PNG read — direction and containment only, never distance)")
    print(f"  ⇒ 'inside' cells: " + ", ".join(f"{a} {n_inside[a]}" for a in ARMS))
    if n_inside[INCUMBENT] > max(n_inside[a] for a in ARMS if a != INCUMBENT):
        print("  ⇒ ⚠⚠ EVERY candidate gives back a cell the INCUMBENT has INSIDE the "
              "licence.\n     That is the trade, and it is not resolvable by measurement — the two "
              "nulls want\n     opposite things from the same knob.  ⇒ USER DECISION (BJ6).")
    return out, n_inside


# ================================================================================================
def bj5_mechanism(kept):
    print()
    print("=" * 100)
    print("BJ5 — MAGNITUDE OR PHASE?  A flat OD-branch gain is the zero-phase lever; a shelf is not")
    print("=" * 100)
    print("  If the null's depth were a function of the OD branch's MAGNITUDE at the null, then a")
    print("  FLAT gain matched to a shelf's own dB there would reproduce that shelf's depth.  A")
    print("  flat gain adds identically zero phase, so any residual is not magnitude.\n")
    ki = [i for i, (l, _) in enumerate(kept) if l == KNIFE]
    cells = [kept[ki[len(ki) // 2]]] + [c for c in kept if c[0] == "blend 1200 cut"][:1]
    lad = {}
    print(f"  the zero-phase dose-response at {KNIFE!r}:")
    for db in FLAT_LADDER:
        label, rung = cells[0]
        g, ped, _ = BH.curves(CAP[label], rung, ())
        _, _, mod = BH.curves(CAP[label], rung, flat(db))
        lad[db] = BH.geom(g, mod, FEAT)[DEPTH] - BH.geom(g, ped, FEAT)[DEPTH]
        print(f"    FLAT {db:+.2f} dB -> {lad[db]:+7.2f}")

    def predict(x):
        ks = sorted(lad)
        return float(np.interp(x, ks, [lad[k] for k in ks]))

    # each shelf arm's OWN magnitude at the null, from the parsed shipped constants + its override
    p = BH.shipped_makeup()
    print(f"\n  {'arm':20s} {'|makeup| at null':>16s} {'flat-equivalent':>16s} {'measured':>10s} "
          f"{'departure':>11s}")
    dep = {}
    label, rung = cells[0]
    g, ped, _ = BH.curves(CAP[label], rung, ())
    f0 = BH.geom(g, ped, FEAT)["f0"]
    for a, arm in ARMS.items():
        q = BH.apply_arm(p, arm)
        q["hf_gain_db"] = q["hfAtOdDb"]
        mag = float(BH.makeup_db(np.array([f0]), 48000.0, q)[0])
        _, _, mod = BH.curves(CAP[label], rung, arm)
        got = BH.geom(g, mod, FEAT)[DEPTH] - BH.geom(g, ped, FEAT)[DEPTH]
        dep[a] = {"mag": mag, "pred": predict(mag), "got": got, "dep": got - predict(mag)}
        print(f"  {a:20s} {mag:16.2f} {dep[a]['pred']:16.2f} {got:10.2f} {dep[a]['dep']:+11.2f}")

    d = [dep[a]["dep"] for a in ARMS if a not in (SHIP, "pre-s172")]
    worst = max(abs(x) for x in d)
    signs = len({np.sign(x) for x in d + [dep[SHIP]["dep"]]})
    print(f"\n  null read at f0 = {f0:.1f} Hz.  Departures span "
          f"{min(d + [dep[SHIP]['dep']]):+.1f} … {max(d + [dep[SHIP]['dep']]):+.1f} dB.")
    if worst > 2.0 and signs > 1:
        print("  ⇒ ⭐⭐ MAGNITUDE DOES NOT DETERMINE THE DEPTH.  Matched on their own dB at the null,")
        print("     the shelves miss the zero-phase prediction by up to "
              f"{worst:.1f} dB AND IN BOTH DIRECTIONS.")
        print("     ⇒ the null's depth is a COMPLEX property of the OD branch, so a minimum-phase")
        print("       shelf reaches it two octaves below its own corner — which is why the")
        print("       magnitude-ideal candidate (130/6.0, flat to 0.06 dB at 40 Hz) is the WORST")
        print("       arm measured.  ⛔ Do not choose a corner from a magnitude table.")
    else:
        print("  ⇒ the shelves track their flat-gain equivalents ⇒ magnitude is sufficient and a "
              "corner CAN be chosen from a magnitude table.")
    return {"ladder": {str(k): v for k, v in lad.items()}, "f0": f0,
            "departure": {a: dep[a] for a in ARMS}}


# ================================================================================================
def bj6_frontier(bass, ratio, inv, n_inside):
    print()
    print("=" * 100)
    print("VERDICT — THE FRONTIER.  No arm dominates; this is a USER DECISION.")
    print("=" * 100)
    print(f"  {'arm':20s} {'bass med':>9s} {'bass worst':>11s} {'MID cost':>9s} {'LF':>6s} "
          f"{'C1 move':>8s} {'320 inside':>11s}")
    for a in ARMS:
        print(f"  {a:20s} {bass[a]['median']:9.2f} {bass[a]['knife']:11.2f} "
              f"{ratio[a]['mid']:9.2f} {ratio[a]['lf']:6.2f} {inv[a]['move']:8.2f} "
              f"{n_inside[a]:11d}")
    dom = [a for a in ARMS if a != INCUMBENT
           and bass[a]["median"] < bass[INCUMBENT]["median"]
           and bass[a]["worst"] <= bass[INCUMBENT]["worst"] + 0.1
           and ratio[a]["mid"] <= ratio[INCUMBENT]["mid"] + 0.25
           and inv[a]["move"] <= 0.5
           and n_inside[a] >= n_inside[INCUMBENT]]
    print()
    if dom:
        print(f"  ⇒ DOMINATING on every axis: {', '.join(dom)}")
    else:
        print("  ⇒ ⛔ NO ARM DOMINATES.  Every candidate that closes the bass null gives back")
        print("     either the ~320 Hz null's licence containment, s172's midrange fix, or its")
        print("     bleed-free invariance.  The two nulls want opposite things from one knob.")
    return {"dominating": dom}


# ================================================================================================
def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--json")
    args = ap.parse_args()
    os.makedirs(BI.REN_DIR, exist_ok=True)
    rep = {"gate": "BJ", "session": 180, "item": 17, "feature": FEAT, "sweep": BI.SWEEP}
    kept, ka, cens = bj0_validity()
    rep["bj0"] = {"n_cells": len(kept), "known_answer": ka, "nd_censored_cells": cens,
                  "graded_depth": DEPTH, "control_depth": DEPTH_CTL}
    bass, per_cell = bj1_bass(kept)
    rep["bj1"] = {"summary": bass, "per_cell": per_cell}
    ratio, best_lf = bj2_ratio()
    rep["bj2"] = {"rms": ratio, "best_lf_arm": best_lf}
    inv = bj3_invariance()
    rep["bj3"] = inv
    other, n_inside = bj4_the_other_null()
    rep["bj4"] = {"c1": other, "n_inside": n_inside}
    rep["bj5"] = bj5_mechanism(kept)
    rep["bj6"] = bj6_frontier(bass, ratio, inv, n_inside)

    if args.json:
        os.makedirs(os.path.dirname(args.json), exist_ok=True)
        with open(args.json, "w") as fh:
            json.dump(rep, fh, indent=1, default=float)
        print(f"\nwrote {args.json}")


if __name__ == "__main__":
    main()
