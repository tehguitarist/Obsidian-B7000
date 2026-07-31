#!/usr/bin/env python3.11
"""
nd_tone_ladder.py -- the REFERENCE's own harmonic ladder, read off a SINGLE 1 kHz TONE.

WHY THIS EXISTS (session 78).  Session 77 made "resolve the reference" the binding
constraint on the whole even-order item: every verdict in that session's 4x4 factorial
flips on whether the third-party chart's columns can be trusted, and session 75 had
reported that our own ND captures CONTRADICT the chart's ND column (measured H2-H3
-7.5 .. -0.5 dB against the chart's -27).  Session 77's next-step (a) therefore asked to
either obtain the chart's underlying data or "capture ND hot enough to reach
H3/H1 ~ -12 dB", after first measuring where ND's H3/H1 maxes out.

⭐⭐ NO NEW CAPTURE IS NEEDED, AND THE BLOCKER WAS NEVER THE DRIVE.  Two findings, both
from data that has been on disk since the first capture session:

 (1) The recorded premise is FALSE AS STATED.  `matrix_harmonics.py` printed
     "nothing in this matrix is hotter than H3 ~ -35 dB" as a HARDCODED STRING, and
     session 75 section 5 wrote "ND's H3 never exceeds ~ -25 dB anywhere in this matrix".
     Both are MEDIANS -- of different sets, which is why they disagree by 10 dB -- and the
     question ("does any condition reach -12 dB?") is a question about the MAXIMUM.
     Measured: raw H3/H1 reaches **-7.1 dB**, and **20 of 720 swept-anchor cells sit at or
     above the chart's -12 dB**, all bleed-free, none in the known-bad `gain-n12` group.
     ⇒ `computed-verdicts-not-narrated` + `split-the-aggregate-check-reachability`.

 (2) But the conclusion those numbers supported SURVIVES, for a better reason: the
     swept-anchor read cannot be put on the chart's convention.  Our report's harmonic
     extractor samples only 100/200/400 Hz (`comprehensive_report.THD_ANCHORS`), so a
     100 Hz anchor's H3 lands at 300 Hz -- right beside ND's own ~320 Hz notch -- while its
     fundamental sits on the pre-scoop shoulder.  Measured from ND's own FR, the bridge
     from our anchor to the chart's 800 Hz tone is **-9 to -24 dB and varies ~5 dB between
     captures**.  ⇒ the operating point is reachable; the CONVENTION is not matchable, and
     19 of those 20 hot cells are the single anchor whose correction happens to be smallest.

 (3) ⭐ THE INSTRUMENT WAS ALSO ALREADY ON DISK.  `gen_test_signal.py` writes a 12-point
     **1 kHz level ladder** (`lvl_-36 .. lvl_-3`, 3 dB steps) plus a `tone_1000` segment into
     EVERY capture -- and `comprehensive_report.py` never reads either for harmonic
     structure.  1 kHz is the chart's HW tone (997 Hz) to 0.3 %, and -- the load-bearing
     part -- **at a 1 kHz fundamental H2 (2 kHz) and H3 (3 kHz) both sit on the flat top of
     ND's mid plateau, so the H2-H3 filter correction is ~0 dB** instead of the swept
     anchors' 14 dB.  That is what makes this tone the right instrument and the swept
     anchors the wrong one.  Same family as `check-for-unread-data-first` (session 60 found
     `sweep_clean_-36` sitting unread in every capture; this is the second occurrence).

WHAT IT MEASURES.  Hn/H1 (n = 2..6) at 1 kHz, at 12 input levels x however many DRIVE and
switch settings the capture matrix holds, on the REFERENCE side only.  Then it anchors on
H3/H1 -- the chart's own definition of its operating point, and the project's established
anchor (session 72 item 1: anchor on the odd orders, where the two reference columns agree)
-- and reads H2-H3 and H4-H5 there against BOTH chart columns.

  python3.11 analysis/nd_tone_ladder.py [--report R.json] [--json OUT] [--selftest]

⚠ SCOPE, stated rather than glossed.
  * This measures **ND, not hardware.**  It can corroborate or contradict the chart's ND
    column; it says nothing directly about the chart's HW column.  What it changes is
    whether the chart is a document our own data contradicts.
  * The anchor is on H3 and the statistic contains H3, so selecting hot cells biases
    H2-H3 downward.  That is why the anchor is a CROSSING (interpolated to the target,
    not a threshold-and-pool) and why the spread across independent captures is printed.
  * ⚠ H3 IS NOT MONOTONE IN LEVEL -- it rises, peaks near -2.4 dB, then CRASHES (the
    JFET-ceiling-vs-clipper anti-phase null of sessions 12/13, reproduced here on the
    reference).  So "H3 = -12 dB" is crossed TWICE and the anchor MUST take the first
    upward crossing on the rising branch (session 72 item 4).  GATE 4 enforces it.
  * The matrix stimulus gives 0.8 s tones with 0.3 s gaps, against a ~220 ms output-coupling
    settling time (session 72 item 5c lost a cell to exactly this).  GATE 1 tests it
    directly instead of assuming the window is long enough.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from concurrent.futures import ProcessPoolExecutor

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import analyze as A                      # noqa: E402
import captures as C                     # noqa: E402
import gen_test_signal as G              # noqa: E402
# ONE definition of the chart table and of the extractor -- imported, never re-typed
# (the session-62 anti-divergence rule; session 33's transcription trap).
from harmonic_ladder import INHARM_MAX_DB, MIN_SPAN_DB, REF        # noqa: E402
from phase_harmonics import fit_harmonics, harm_db                 # noqa: E402

FS = 48000
TONE_HZ = 1000.0                 # the stimulus' own ladder tone; chart HW tone is 997 Hz
NMAX = 6
ORDERS = (2, 3, 4, 5, 6)
CAPDIR = "analysis/captures"

# Analysis window inside each 0.8 s segment, as fractions of the segment.  The LATE part is
# used because the ladder ASCENDS, so the contaminating neighbour is always the QUIETER one,
# and because ~220 ms of output-coupling settling has to be walked off first.  GATE 1 is what
# justifies these numbers rather than the comment.
WIN_LO, WIN_HI = 0.40, 0.95

# The chart's two stated operating points, taken from its own H3/H1 column.
ANCHOR_H3 = {"low": REF["low"]["ND"][3], "mid": REF["mid"]["ND"][3]}   # -42.0, -12.0


def lvl_segments():
    """The 1 kHz level ladder, in ASCENDING input order."""
    T = G.segment_times()
    out = []
    for name, (t0, t1) in T.items():
        if name.startswith("lvl_"):
            out.append((int(name.split("_")[1]), name, t0, t1))
    return sorted(out)


def extract(seg_audio, f0=TONE_HZ):
    """Hn/H1 in dB plus the inharmonic residual, on one tone segment."""
    H, _, resid = fit_harmonics(seg_audio, f0, fs=FS, nmax=NMAX)
    hd = harm_db(H)
    fund = abs(H[1]) + 1e-30
    # residual = everything the harmonic basis did not explain (aliasing, IMD, hum, noise)
    inh = 20.0 * np.log10(np.sqrt(np.mean(resid ** 2)) * np.sqrt(2.0) / fund + 1e-30)
    return {n: float(hd[n]) for n in ORDERS}, float(inh), float(abs(H[1]))


# ⚠⚠ PER-ORDER MEASURABILITY, AND THIS IS LOAD-BEARING FOR THE LOW-DRIVE ROW.
# The chart's low-drive column puts H4 at -60.5 dB and H5 at -75.5 dB re fundamental, while
# this instrument's inharmonic residual sits around -50 dB.  An Hn BELOW that residual is not
# a measurement of the harmonic -- the LS fit returns whatever noise happens to project onto
# that basis vector, which is bounded BELOW by roughly the residual, so a floored H5 reads too
# HIGH and therefore makes H4-H5 read too LARGE.  That is exactly the direction of the
# uncorrected reading (+21.3 against both chart columns' +14/+15), so it has to be guarded
# before the number can be quoted.  Same family as `ratio-statistics-need-a-denominator-guard`
# and `floor-guard-belongs-on-the-reference`: guard the quantity's own reliability, not the
# hypothesis under test.
ORDER_MARGIN_DB = 6.0        # Hn must clear the cell's own residual by this much


def measurable(hd, inharm, order):
    """Is this order above the cell's own noise/IMD residual by ORDER_MARGIN_DB?"""
    return hd[order] > inharm + ORDER_MARGIN_DB


def cells_from(cal):
    """Every `lvl_` cell of one ALIGNED signal, plus the split-window settling check.

    ⭐ ONE extractor, two sides.  The reference (`read_one`) and the model (`read_model`)
    differ ONLY in how the array is obtained -- everything downstream of this function is
    shared, so a model-vs-reference difference can never be an artefact of two subtly
    different readers (the session-62 anti-divergence rule, and the reason session 64 deleted
    `attack_render_gate`'s private copy of the notch oracle).
    """
    cells = {}
    for db, name, t0, t1 in _W["segs"]:
        dur = t1 - t0
        a = int(round((t0 + WIN_LO * dur) * FS))
        b = int(round((t0 + WIN_HI * dur) * FS))
        if b > len(cal):
            continue
        seg = cal[a:b]
        hd, inh, f1 = extract(seg)
        # GATE 1 material: the same cell read on the two halves of its own window.  If a
        # settling transient is still inside, the halves disagree.  Threshold-free and
        # cause-agnostic -- it does not need to know WHY they differ.
        m = len(seg) // 2
        hd_a, _, _ = extract(seg[:m])
        hd_b, _, _ = extract(seg[m:])
        split = max(abs(hd_a[n] - hd_b[n]) for n in (2, 3))
        cells[db] = dict(hd=hd, inharm=inh, fund=f1, split=float(split))
    return cells


def read_one(fname):
    """Every `lvl_` cell of one REFERENCE capture."""
    path = os.path.join(CAPDIR, fname)
    try:
        cap = C.load_capture(path)
        orig = _W["orig"]
        if not A.is_full_length(cap, orig):
            return fname, None, "truncated"
        cal, _ = A.align(cap, orig)
    except Exception as exc:                                  # noqa: BLE001
        return fname, None, f"read failed: {exc}"
    return fname, cells_from(cal), None


# --------------------------------------------------------------------------------------
# the MODEL side (session 79) -- our own renders, read by the identical extractor
# --------------------------------------------------------------------------------------
RENDER_BIN = "build/OfflineRender_artefacts/Release/OfflineRender"
RENDER_DIR = "build/nd_tone_ladder"
RENDER_OS = 8


def render_argv(fname, out, fit=()):
    """The render condition, DERIVED from the capture's own filename -- never hand-written.

    ⚠⚠ THIS IS THE SESSION-65 DEFECT AND IT COST A WHOLE SESSION'S HEADLINE.  That session's
    `attack_render_gate` hand-wrote `BASE = [--drive .. --level .. --blend ..]` and silently
    took the renderer's DEFAULT `--grunt 0` (= BOOST) while every capture was GRUNT CUT; the
    resulting 6.2 dB "OD-path shape error" was the flag, not the circuit.  Going through
    `C.render_args(C.parse_capture(...))` makes the condition a function of the filename, so
    the model is rendered at the capture's OWN operating point by construction and there is no
    list of flags that can drift out of sync with the matrix.
    """
    return ([RENDER_BIN, A.ORIG, out, "--os", str(RENDER_OS), "--trim-latency"]
            + C.render_args(C.parse_capture(fname))
            + [x for kv in fit for x in ("--fit", kv)])


def _stamp_path(out):
    return out + ".args.json"


def fit_tag(fit):
    """A short, stable directory tag for a FitParams override set.

    ⚠ ADDITIVE BY CONSTRUCTION: the empty fit returns "" and so keeps the exact
    `mdl_<fname>` path session 79 used, leaving that tool's cached renders valid and its
    numbers reproducible.  Only a NON-empty fit gets its own namespace.  Without this every
    candidate in a sweep writes to the same path, so screening N candidates re-renders all N
    every time the sweep is re-run -- and the render is ~90 % of the wall clock.
    """
    if not fit:
        return ""
    import hashlib
    return "fit_" + hashlib.sha1("\n".join(sorted(fit)).encode()).hexdigest()[:10]


def render_model(fname, fit=(), force=False):
    """Render one condition, with an argv+binary stamp so a stale render cannot be reused.

    `rebaseline-all-derived-artefacts` (s35/s45/s65): a render on disk is only valid for the
    exact argv AND the exact binary that produced it.  The stamp carries both, and a mismatch
    re-renders rather than silently comparing against yesterday's model.  The stamp remains
    the correctness guarantee; `fit_tag` only stops distinct candidates from evicting each
    other's cache entries.
    """
    tag = fit_tag(fit)
    rd = os.path.join(RENDER_DIR, tag) if tag else RENDER_DIR
    os.makedirs(rd, exist_ok=True)
    out = os.path.join(rd, "mdl_" + fname)
    argv = render_argv(fname, out, fit)
    want = {"argv": argv, "bin_mtime": os.path.getmtime(RENDER_BIN)}
    sp = _stamp_path(out)
    if not force and os.path.exists(out) and os.path.exists(sp):
        try:
            if json.load(open(sp)) == want:
                return out, False
        except Exception:                                     # noqa: BLE001
            pass
    subprocess.run(argv, check=True, capture_output=True)
    json.dump(want, open(sp, "w"))
    return out, True


def read_model(fname):
    """Every `lvl_` cell of our own render at that capture's condition."""
    try:
        out, fresh = render_model(fname, fit=_W.get("fit", ()))
        x = A.load(out)
        orig = _W["orig"]
        if not A.is_full_length(x, orig):
            return fname, None, "render truncated"
        cal, lag = A.align(x, orig)
    except Exception as exc:                                  # noqa: BLE001
        return fname, None, f"render failed: {exc}"
    cells = cells_from(cal)
    for c in cells.values():
        c["lag"] = int(lag)
    return fname, cells, None


_W = {}


def _init():
    _W["orig"] = A.load(A.ORIG)
    _W["segs"] = lvl_segments()


def _init_model(fit=()):
    # ⚠ NOT a module global: ProcessPoolExecutor uses `spawn` on macOS, so the child
    # re-imports this module and would see the module-level default, silently rendering
    # every candidate at the SHIPPED point while the report claimed otherwise.  The fit is
    # therefore passed through `initargs` -- the same class of bug as session 73's `tag`
    # rebind (invisible serially, wrong only under the pool).
    _init()
    _W["fit"] = tuple(fit)


# --------------------------------------------------------------------------------------
# gates
# --------------------------------------------------------------------------------------

def selftest() -> bool:
    """GATE 0 -- the extractor, against a ladder whose answer is known in closed form."""
    ok = True
    print("=" * 90)
    print("GATE 0 -- extractor identity on a synthesised ladder (closed-form answer)")
    print("=" * 90)
    n = int(0.55 * 0.8 * FS)
    t = np.arange(n) / FS
    want = {2: -14.0, 3: -23.5, 4: -31.0, 5: -40.0, 6: -47.0}
    x = np.sin(2 * np.pi * TONE_HZ * t)
    for k, db in want.items():
        x = x + (10 ** (db / 20.0)) * np.sin(2 * np.pi * k * TONE_HZ * t + 0.7 * k)
    hd, inh, _ = extract(x)
    worst = max(abs(hd[k] - want[k]) for k in want)
    print("  " + "  ".join(f"H{k} want {want[k]:+.1f} got {hd[k]:+.1f}" for k in want))
    print(f"  worst |error| = {worst:.3e} dB   inharmonic residual {inh:+.1f} dB   "
          f"{'PASS' if worst < 1e-6 else 'FAIL'}")
    ok &= worst < 1e-6

    # liveness of the inharmonic residual: it must SEE non-harmonic content, or GATE 2 is
    # a check that can never fire.
    y = x + 0.02 * np.sin(2 * np.pi * 1493.0 * t)
    _, inh2, _ = extract(y)
    print(f"  liveness: adding a -34 dB inharmonic tone moves the residual "
          f"{inh:+.1f} -> {inh2:+.1f} dB   {'PASS' if inh2 - inh > 20 else 'FAIL'}")
    ok &= (inh2 - inh) > 20

    # the H3-crossing locator, on a curve whose crossing is known exactly
    lv = np.array([-36, -33, -30, -27, -24], float)
    h3 = np.array([-20.0, -14.0, -8.0, -4.0, -2.0])      # crosses -12 at -32.0 exactly
    hit = crossing(lv, h3, -12.0)
    print(f"  crossing locator: want -32.000 dBFS, got {hit:+.3f}   "
          f"{'PASS' if abs(hit + 32.0) < 1e-9 else 'FAIL'}")
    ok &= abs(hit + 32.0) < 1e-9

    # and it must REFUSE the falling branch: same target crossed twice, take the first.
    # ⚠ MY FIRST VERSION OF THIS GATE ASSERTED THE WRONG NUMBER (-33.0, a hand-arithmetic
    # slip) and FAILED a locator that was correct.  The rising crossing is at -32.0 and the
    # falling one at -16.0; both are stated here so the gate is discriminating rather than
    # just satisfiable -- returning -16.0 must fail, not merely "not equal to -32".
    lv2 = np.array([-36, -30, -24, -18, -12], float)
    h3b = np.array([-20.0, -8.0, -2.0, -8.0, -20.0])     # up then down, crosses -12 twice
    hit2 = crossing(lv2, h3b, -12.0)
    good = abs(hit2 + 32.0) < 1e-9 and abs(hit2 + 16.0) > 1.0
    print(f"  first-upward-crossing only: -12 dB is crossed twice (rising -32.00, falling "
          f"-16.00); got {hit2:+.2f} dBFS   {'PASS' if good else 'FAIL'}")
    ok &= good
    print(f"\n  GATE 0 -> {'PASS' if ok else 'FAIL'}\n")
    return ok


def crossing(levels, h3, target):
    """First UPWARD crossing of `target`, linearly interpolated in dBFS.

    Load-bearing, not a convenience: H3 vs level rises, peaks, then CRASHES through an
    anti-phase null, so `target` is generally crossed twice and the two crossings are
    completely different operating points (session 72 item 4 measured the two H2 values
    44.7 dB apart).  NaN if the rising branch never reaches it.
    """
    for i in range(len(h3) - 1):
        if h3[i] <= target <= h3[i + 1] and h3[i + 1] > h3[i]:
            f = (target - h3[i]) / (h3[i + 1] - h3[i])
            return float(levels[i] + f * (levels[i + 1] - levels[i]))
    return float("nan")


def interp_at(levels, vals, at):
    return float(np.interp(at, levels, vals))


def anchor_hits(data, contam, noisy, settings, c23, c45):
    """Anchor each capture on its own H3/H1 crossing and read the pair statistics there.

    Factored out (session 79) so the MODEL is anchored by exactly the same rule as the
    reference -- including the first-upward-crossing requirement, which is not a detail:
    H3 is non-monotone in level on BOTH sides, so a side anchored on the falling branch is
    at a completely different operating point (session 72 measured two such H2 values
    44.7 dB apart) and the comparison would be meaningless while looking perfectly sane.
    """
    lv = np.array([d for d, _, _, _ in lvl_segments()], float)
    hits = {k: [] for k in ANCHOR_H3}
    nonmono = 0
    for fn, cc in sorted(data.items()):
        ok_db = [d for d in lv if (fn, int(d)) not in contam and (fn, int(d)) not in noisy
                 and int(d) in cc]
        if len(ok_db) < 4:
            continue
        ok_db = np.array(sorted(ok_db), float)
        h = {n: np.array([cc[int(d)]["hd"][n] for d in ok_db]) for n in ORDERS}
        if h[3].argmax() < len(h[3]) - 1:
            nonmono += 1
        for lbl, tgt in ANCHOR_H3.items():
            at = crossing(ok_db, h[3], tgt)
            if not np.isfinite(at):
                continue
            row = {n: interp_at(ok_db, h[n], at) for n in ORDERS}
            # per-order measurability at the anchor: interpolate the residual too, and
            # mark which orders clear it.  A pair is only reported if BOTH its orders do.
            inh_at = interp_at(ok_db, np.array([cc[int(d)]["inharm"] for d in ok_db]), at)
            meas = {n: row[n] > inh_at + ORDER_MARGIN_DB for n in ORDERS}
            hits[lbl].append(dict(file=fn, at_dbfs=at, drive=settings[fn]["drive"],
                                  grunt=settings[fn]["gruntIdx"], hd=row,
                                  inharm=inh_at, meas=meas,
                                  ok23=bool(meas[2] and meas[3]),
                                  ok45=bool(meas[4] and meas[5]),
                                  h23=row[2] - row[3], h45=row[4] - row[5],
                                  # ⚠⚠ SIGN CORRECTED (session 79).  Session 78 had `- c23`,
                                  # which DOUBLES the chain's tilt instead of removing it:
                                  #   Hn_out = Hn_gen + g(nf)
                                  #   => (H2-H3)_out = (H2-H3)_gen - [g(3f)-g(2f)] = gen - c23
                                  #   => gen = out + c23
                                  # Harmless in session 78 only because its c23 was -0.02 dB;
                                  # it becomes a real 2*c23 error once the transfer is measured
                                  # on the bleed-free path.  `gate_corr_sign()` pins this.
                                  h23c=row[2] - row[3] + c23,
                                  h45c=row[4] - row[5] + c45))
    return hits, nonmono


def gate_corr_sign():
    """GATE 3b -- the filter correction must REMOVE the chain's tilt, not double it.

    A closed-form case with a known answer: a nonlinearity that generates H2 and H3 at
    EXACTLY equal level, behind a filter that lifts 3f by 6 dB.  The de-embedded pair
    statistic must come back to 0.00; the wrong sign returns -12.  Session 78 shipped the
    wrong sign and it was invisible because its measured correction was -0.02 dB.
    """
    print("=" * 90)
    print("GATE 3b -- correction SIGN, against a closed-form case")
    print("=" * 90)
    g2, g3 = 0.0, 6.0
    c23 = g3 - g2
    gen = 0.0                                   # H2 == H3 by construction
    out = (gen + g2) - (gen + g3)               # what a meter at the output reads
    good, bad = out + c23, out - c23
    print(f"  generated (H2-H3) = {gen:+.2f} dB   chain tilt c23 = g(3f)-g(2f) = {c23:+.2f} dB")
    print(f"  a meter at the output reads {out:+.2f} dB")
    print(f"  de-embed as out + c23 = {good:+.2f}   (want {gen:+.2f})   "
          f"{'PASS' if abs(good - gen) < 1e-9 else 'FAIL'}")
    print(f"  the session-78 form out - c23 = {bad:+.2f}   -- doubles the tilt, correctly REJECTED")
    ok = abs(good - gen) < 1e-9 and abs(bad - gen) > 1.0
    print(f"\n  GATE 3b -> {'PASS' if ok else 'FAIL'}")
    print()
    if not ok:
        raise SystemExit("GATE 3b FAILED -- the correction sign convention is wrong.")


def side_gates(data, label, max_split):
    """GATES 1 and 2, applied identically to whichever side is passed in.

    Factored (session 79) so the MODEL is held to the same settling and inharmonic-residual
    standard as the reference.  It matters more on the model side, not less: at OS 8 our own
    aliasing floor still reaches -12..-16 dB re fundamental at the hottest drive/level corners
    (session 72 item 6), so a model cell can be unmeasurable where the reference cell is fine.
    """
    print("=" * 90)
    print(f"GATE 1 -- {label}: window settling, two halves of each cell's own window must agree")
    print("=" * 90)
    splits = [(c["split"], fn, db) for fn, cc in data.items() for db, c in cc.items()]
    splits.sort(reverse=True)
    worst = splits[0][0] if splits else float("nan")
    ncontam = sum(1 for s, _, _ in splits if s > max_split)
    print(f"  cells {len(splits)}   worst |H2/H3 half-vs-half| = {worst:.3f} dB   "
          f"contaminated (> {max_split:.1f} dB): {ncontam}")
    for s, fn, db in splits[:5]:
        print(f"      {s:6.3f} dB   {db:+4d} dBFS   {fn}")
    print(f"  ⚠ the stimulus gives 0.8 s tones against ~220 ms of output-coupling settling,")
    print(f"    so this is measured, not assumed.  The ladder ASCENDS, so each cell's")
    print(f"    contaminating neighbour is the QUIETER one -- the benign direction.")
    contam = {(fn, db) for s, fn, db in splits if s > max_split}
    print()

    print("=" * 90)
    print(f"GATE 2 -- {label}: inharmonic residual under {INHARM_MAX_DB:+.0f} dB re fundamental")
    print("=" * 90)
    inh = [(c["inharm"], fn, db) for fn, cc in data.items() for db, c in cc.items()]
    inh.sort(reverse=True)
    nloud = sum(1 for v, _, _ in inh if v > INHARM_MAX_DB)
    print(f"  worst {inh[0][0]:+.1f} dB   median {np.median([v for v, _, _ in inh]):+.1f} dB   "
          f"cells over the limit: {nloud} of {len(inh)}")
    for v, fn, db in inh[:4]:
        print(f"      {v:+7.1f} dB   {db:+4d} dBFS   {fn}")
    noisy = {(fn, db) for v, fn, db in inh if v > INHARM_MAX_DB}
    print()
    return contam, noisy, float(worst), len(noisy)


def filter_bridge(report_path, which="pedal_db"):
    """GATE 3 -- a side's OWN linear gain at 2f..5f re f, from the report's `sweep_clean` FR.

    This is the number that makes the 1 kHz tone the right instrument and the swept
    100/200/400 Hz anchors the wrong one.  A pair statistic like H2-H3 only needs the
    filter's DIFFERENCE between the two orders (session 72 item 2), so what matters is
    g(3f) - g(2f).

    ⚠⚠ THE TRANSFER MUST BE THE **OD PATH'S**, NOT THE BLENDED OUTPUT -- session 79 found
    this the hard way, and it inverted the sign of the correction.  Harmonics are generated
    at the clipper and reach the output ONLY down the OD path; the clean bleed carries none.
    H2-H3 is a difference of two Hn/H1 ratios, so H1 -- the one quantity the bleed DOES
    contribute to -- cancels exactly.  So the operative correction is the OD path's own
    g(3f)-g(2f).  Read off a BLENDED capture instead, the bleed FILLS the recovery
    bridged-T's scoop that the 1 kHz fundamental sits in, and the measured slope collapses
    toward zero and changes sign.  Both are printed at run time (the blended one as a
    CONTROL) rather than quoted here, so neither figure can go stale in a comment.

    The bleed-free MODEL figure is the one comparable to `harmonic_ladder.py`'s independent
    render-based measurement (+1.18 dB at 997 Hz, its BASE_ARGS being blend/level max) --
    the ND row is a different device and is not expected to match it.
    ⇒ restricted to captures that are bleed-free BY TOPOLOGY (BLEND max shorts the clean
    leg out, LEVEL max shorts the wiper to the OD source -- session 59 item 6), and the
    condition is DERIVED per file via `captures.render_args`, never guessed from the name.

    `which` selects the side: "pedal_db" = the reference (ND), "plugin_db" = our model.
    ⭐ Reading BOTH is what licenses the model-vs-ND comparison: the difference of two
    corrected pair statistics needs only
        (g_mdl(3f)-g_mdl(2f)) - (g_nd(3f)-g_nd(2f)),
    and the licensing argument is NOT "both chains are flat" (neither is) but "both chains
    model the SAME post-clipper filter, so their corrections very nearly cancel".  The net
    is computed and printed at run time, and it IS applied to every reported difference.
    """
    d = json.load(open(report_path))
    bands = np.asarray(d["meta"]["bands"], float)
    lb = np.log(bands)
    rows, blended = [], []
    for c in d["captures"]:
        f = c["file"]
        if "base-od" not in f and not f.startswith("ref-od"):
            continue
        if "gain-n12" in f:
            continue
        clean = (c.get("fr") or {}).get("sweep_clean")
        if not clean or which not in clean:
            continue
        g = np.asarray(clean[which], float)

        def at(fz):
            return float(np.interp(np.log(fz), lb, g))

        row = dict(file=f,
                   g2=at(2 * TONE_HZ) - at(TONE_HZ),
                   g3=at(3 * TONE_HZ) - at(TONE_HZ),
                   g4=at(4 * TONE_HZ) - at(TONE_HZ),
                   g5=at(5 * TONE_HZ) - at(TONE_HZ))
        (rows if bleed_free(f) else blended).append(row)
    if not rows:
        raise SystemExit("GATE 3: no bleed-free (BLEND=LEVEL=max) OD capture found -- "
                         "refusing to fall back to the blended transfer, which is the "
                         "wrong one for a harmonic (see filter_bridge docstring).")
    return rows, blended


def bleed_free(fname):
    """True when a capture's own condition makes the clean bleed EXACTLY zero.

    DERIVED from the renderer's argument list rather than matched against the `level-1700`
    filename token, so a future capture that reaches the same condition by another route is
    included automatically and a renamed one is not silently dropped.
    """
    try:
        # `argv`, not `args` -- `args` is the argparse namespace in main() and reusing the
        # name here is exactly the session-73 `tag`-rebind trap one scope over.
        argv = C.render_args(C.parse_capture(fname))
    except Exception:
        return False

    def val(flag):
        return float(argv[argv.index(flag) + 1]) if flag in argv else None

    return val("--blend") == 1.0 and val("--level") == 1.0


# --------------------------------------------------------------------------------------
# MODEL vs REFERENCE (session 79)
# --------------------------------------------------------------------------------------

def compare_model(data, mdata, contam, noisy, mcontam, mnoisy, settings,
                  c23, c45, mc23, mc45):
    """Our model against ND, on the 1 kHz ladder, two ways.

    (A) CELL-MATCHED -- same capture, same input level, so the two sides see LITERALLY the
        same stimulus at the same operating point.  No anchor, no crossing, no interpolation:
        the strongest form of matched pair this project has for harmonic structure, and the
        one `harmonic_ladder.py`'s pair machinery exists to approximate.
    (B) ANCHORED -- each side anchored on its OWN H3/H1 crossing, i.e. the chart's convention
        applied to both.  Weaker (it compares two different operating points) but it is the
        convention every prior even-order session used, so it is what makes those numbers
        comparable.

    ⚠⚠ THE MEASURABILITY GUARD IS ASYMMETRIC AND THE DIRECTION MATTERS.  A model cell whose
    Hn sits under the MODEL's own aliasing residual reads too HIGH, so including it makes
    (model - ND) read too HIGH -- i.e. it UNDERSTATES a model deficit.  Guarding on the model
    would instead select away exactly the cells where the model under-produces, which is
    `floor-guard-belongs-on-the-reference` (session 74 item 6) and inverted a conclusion by
    11.6 dB last time.  So the PRIMARY read is guarded on the REFERENCE ONLY and is a
    one-sided bound in a known direction; the both-guarded read is printed beside it as the
    other bound.  Neither is silently preferred.
    """
    print("=" * 90)
    print("MODEL vs ND -- (A) CELL-MATCHED: same capture, same level, no anchor, no correction")
    print("=" * 90)
    net23 = mc23 - c23
    net45 = mc45 - c45
    print(f"  net filter correction applied to d(H2-H3): {net23:+.2f} dB   "
          f"to d(H4-H5): {net45:+.2f} dB")
    print()

    rows = []
    for fn in sorted(set(data) & set(mdata)):
        for db in sorted(set(data[fn]) & set(mdata[fn])):
            nd, md = data[fn][db], mdata[fn][db]
            ref_clean = (fn, db) not in contam and (fn, db) not in noisy
            mdl_clean = (fn, db) not in mcontam and (fn, db) not in mnoisy
            if not ref_clean:
                continue                       # reference-side condition, decided first
            rows.append(dict(file=fn, db=db, drive=settings[fn]["drive"],
                             nd=nd["hd"], md=md["hd"],
                             nd_inh=nd["inharm"], md_inh=md["inharm"],
                             mdl_clean=mdl_clean))
    if not rows:
        print("  ⛔ no cells clean on the reference side -- nothing to compare.")
        return {}

    print(f"  {len(rows)} reference-clean cells across "
          f"{len({r['file'] for r in rows})} captures")
    print()
    print(f"  ⭐ PER-ORDER ABSOLUTE (model - ND), signed.  A pair statistic cancels a")
    print(f"     common-mode error exactly, so the absolutes are printed FIRST")
    print(f"     (`difference-statistics-hide-common-mode`, session 74 item 5).")
    print()
    print(f"      {'order':>6} {'n':>5} {'median d':>10} {'p10':>8} {'p90':>8}   "
          f"{'ND med':>8} {'model med':>10}")
    perorder = {}
    for n in ORDERS:
        # reference-only guard: the REFERENCE order must be measurable.  The model's own
        # measurability is reported separately below, never used to select.
        sub = [r for r in rows if r["nd"][n] > r["nd_inh"] + ORDER_MARGIN_DB]
        if len(sub) < 5:
            print(f"      H{n:<5} {len(sub):>5}   -- too few reference-measurable cells")
            perorder[n] = {"n": len(sub), "measurable": False}
            continue
        d = np.array([r["md"][n] - r["nd"][n] for r in sub])
        ndv = np.array([r["nd"][n] for r in sub])
        mdv = np.array([r["md"][n] for r in sub])
        p10, p90 = np.percentile(d, 10), np.percentile(d, 90)
        print(f"      H{n:<5} {len(sub):>5} {np.median(d):>+10.2f} {p10:>+8.2f} {p90:>+8.2f}   "
              f"{np.median(ndv):>+8.1f} {np.median(mdv):>+10.1f}")
        perorder[n] = {"n": len(sub), "measurable": True,
                       "median_delta_db": float(np.median(d)),
                       "p10": float(p10), "p90": float(p90),
                       "nd_median": float(np.median(ndv)),
                       "model_median": float(np.median(mdv))}
    print()

    # how often is the MODEL cell itself below its own residual?  This is the size of the
    # one-sided bias in the reference-only read, quantified rather than asserted.
    print(f"      model-side measurability at those same cells (how one-sided the bound is):")
    for n in ORDERS:
        sub = [r for r in rows if r["nd"][n] > r["nd_inh"] + ORDER_MARGIN_DB]
        if not sub:
            continue
        below = sum(1 for r in sub if r["md"][n] <= r["md_inh"] + ORDER_MARGIN_DB)
        if perorder[n].get("measurable"):
            perorder[n]["model_below_own_residual"] = below
        print(f"        H{n}: {below:>4} of {len(sub)} model cells sit at/under the model's own "
              f"residual  ⇒ d(H{n}) is a LOWER bound on the deficit by that much")
    print()

    # the pair statistic
    print(f"  ⭐⭐ THE PAIR STATISTIC -- d(H2-H3) = (model H2-H3) - (ND H2-H3), the quantity")
    print(f"     that needs no ABSOLUTE level match and only a {abs(net23):.2f} dB filter correction")
    print(f"     (the two sides' corrections nearly cancel -- GATE 3; it IS applied below).")
    print()
    pair = {}
    for nm, hi, lo, net in (("H2-H3", 2, 3, net23), ("H4-H5", 4, 5, net45)):
        for guard, gl in (("ref-only", False), ("both-sides", True)):
            sub = [r for r in rows
                   if r["nd"][hi] > r["nd_inh"] + ORDER_MARGIN_DB
                   and r["nd"][lo] > r["nd_inh"] + ORDER_MARGIN_DB
                   and ((not gl) or (r["md"][hi] > r["md_inh"] + ORDER_MARGIN_DB
                                     and r["md"][lo] > r["md_inh"] + ORDER_MARGIN_DB))]
            if len(sub) < 5:
                print(f"      {nm} [{guard:>10}]  n={len(sub):<4} -- too few cells")
                continue
            # RAW (output-domain) difference first -- assumption-free, and the domain the
            # 129-capture matrix actually scores.  `+ net` de-embeds to the generated domain
            # (sign per gate_corr_sign); both are reported because the correction rests on a
            # FULL-CHAIN FR standing in for the POST-clipper transfer a harmonic really sees.
            draw = np.array([(r["md"][hi] - r["md"][lo]) - (r["nd"][hi] - r["nd"][lo])
                             for r in sub])
            d = draw + net
            ndp = np.array([r["nd"][hi] - r["nd"][lo] for r in sub])
            mdp = np.array([r["md"][hi] - r["md"][lo] for r in sub])
            p10, p90 = np.percentile(d, 10), np.percentile(d, 90)
            print(f"      {nm} [{guard:>10}]  n={len(sub):<4} "
                  f"ND {np.median(ndp):>+7.2f}   model {np.median(mdp):>+7.2f}   "
                  f"d_raw {np.median(draw):>+7.2f}   d_corr {np.median(d):>+7.2f}  "
                  f"(p10..p90 {p10:+.2f} .. {p90:+.2f})")
            pair[f"{nm}_{guard}"] = {"n": len(sub), "nd_median": float(np.median(ndp)),
                                     "model_median": float(np.median(mdp)),
                                     "delta_median_raw": float(np.median(draw)),
                                     "delta_median": float(np.median(d)),
                                     "p10": float(p10), "p90": float(p90)}
    print()
    print(f"  ⚠ H4-H5 is quoted for completeness only -- its ND-side correction is {c45:+.2f} dB")
    print(f"    against H2-H3's {c23:+.2f}, and the net model-vs-ND term is {net45:+.2f} dB against")
    print(f"    {net23:+.2f}.  H2-H3 is the statistic; H4-H5 carries the correction risk.")
    print()

    # ---- (B) the anchored comparison ---------------------------------------------------
    print("=" * 90)
    print("MODEL vs ND -- (B) ANCHORED: each side at its own H3/H1 crossing (chart convention)")
    print("=" * 90)
    mhits, mnonmono = anchor_hits(mdata, mcontam, mnoisy, settings, mc23, mc45)
    nhits, _ = anchor_hits(data, contam, noisy, settings, c23, c45)
    print(f"  ⚠ model H3 is non-monotone in level in {mnonmono} of {len(mdata)} renders too, so")
    print(f"    the model is anchored by the identical first-upward-crossing rule.")
    print()
    anch = {}
    for lbl in ("low", "mid"):
        tgt = ANCHOR_H3[lbl]
        nsub = {x["file"]: x for x in nhits[lbl] if x["ok23"]}
        msub = {x["file"]: x for x in mhits[lbl] if x["ok23"]}
        common = sorted(set(nsub) & set(msub))
        print(f"  --- anchored at H3/H1 = {tgt:+.0f} dB "
              f"(ND reaches it in {len(nsub)}, model in {len(msub)}, BOTH in {len(common)}) ---")
        if len(common) < 3:
            print(f"      ⛔ too few captures where BOTH sides reach this anchor "
                  f"-- not reported.")
            anch[lbl] = {"n_common": len(common), "reported": False}
            print()
            continue
        ndv = np.array([nsub[f]["h23c"] for f in common])
        mdv = np.array([msub[f]["h23c"] for f in common])
        d = mdv - ndv
        # ⭐ the anchor LEVELS themselves are a finding: if the model needs a very different
        # input level to reach the same H3, its whole gain staging into the clipper differs,
        # and that is a different defect from the even-order shape under test.
        dl = np.array([msub[f]["at_dbfs"] - nsub[f]["at_dbfs"] for f in common])
        print(f"      H2-H3   ND {np.median(ndv):>+7.2f}   model {np.median(mdv):>+7.2f}   "
              f"d {np.median(d):>+7.2f}   (p10..p90 {np.percentile(d, 10):+.2f} .. "
              f"{np.percentile(d, 90):+.2f})")
        print(f"      anchor input level: model - ND = {np.median(dl):+.2f} dB "
              f"({dl.min():+.1f} .. {dl.max():+.1f}) -- if this is large the two sides reach")
        print(f"      the same H3 at different drive, which is a GAIN-STAGING difference, not")
        print(f"      an even-order one.")
        anch[lbl] = {"n_common": len(common), "reported": True,
                     "nd_median": float(np.median(ndv)),
                     "model_median": float(np.median(mdv)),
                     "delta_median": float(np.median(d)),
                     "p10": float(np.percentile(d, 10)),
                     "p90": float(np.percentile(d, 90)),
                     "anchor_level_delta_db": float(np.median(dl))}
        print()

    # ⭐⭐ THE OPERATIVE GUARD.  If the two anchors disagree in SIGN, the pooled cell-matched
    # d(H2-H3) is an average of two opposite-signed errors and is the WRONG thing to gate a
    # candidate on -- it will read "small" for a model that is badly wrong in both regimes,
    # in opposite directions.  Derived, so it states the opposite when the data does
    # (`computed-verdicts-not-narrated`, `split-the-aggregate-check-reachability`).
    lo_a, mi_a = anch.get("low", {}), anch.get("mid", {})
    if lo_a.get("reported") and mi_a.get("reported"):
        dlo, dmi = lo_a["delta_median"], mi_a["delta_median"]
        pooled = pair.get("H2-H3_both-sides", {}).get("delta_median")
        print("=" * 90)
        print("DOES THE POOLED CELL-MATCHED NUMBER MEAN ANYTHING?  (the two anchors vs the pool)")
        print("=" * 90)
        pstr = f"   pooled cell-matched {pooled:+.2f}" if pooled is not None else ""
        print(f"  d(H2-H3)   low-drive anchor {dlo:+.2f}   mid-drive anchor {dmi:+.2f}{pstr}")
        if dlo * dmi < 0:
            print(f"  ⛔ THE TWO ANCHORS DISAGREE IN SIGN, so the pooled number is a MIXTURE and")
            print(f"     MUST NOT be used as the gate: our model is {abs(dlo):.1f} dB BELOW ND at low")
            print(f"     drive and {abs(dmi):.1f} dB ABOVE it at mid drive, and pooling cancels")
            print(f"     {min(abs(dlo), abs(dmi)):.1f} dB of real error.  Gate on the two anchors SEPARATELY.")
            # Robustness of each sign is what makes the split a finding rather than noise.
            for lbl, a in (("low", lo_a), ("mid", mi_a)):
                same = (a["p10"] > 0) == (a["p90"] > 0)
                print(f"     {lbl}-drive: p10..p90 {a['p10']:+.2f} .. {a['p90']:+.2f}  "
                      f"({'sign ROBUST -- interval excludes 0' if same else '⚠ interval SPANS 0'})")
        else:
            print(f"  the two anchors agree in sign, so the pooled number is a legitimate summary.")
        print()

    print("  ⚠ NOT CLAIMED.  This is model vs ND, and ND's even orders are ~27 dB below")
    print("    hardware's (reference-sources.md section 4), so 'matches ND' on an EVEN-order")
    print("    statistic is not the target -- it is the thing the even-order item exists to")
    print("    move away from.  What this instrument gives is the SIZE and SIGN of our")
    print("    departure from ND on a statistic that needs no filter correction, which is the")
    print("    quantity the 129-capture matrix must be checked against when anything moves.")
    print()
    return {"cell_matched_per_order": {str(k): v for k, v in perorder.items()},
            "cell_matched_pair": pair, "anchored": anch,
            "net_corr_h2h3_db": float(net23), "net_corr_h4h5_db": float(net45),
            "n_cells": len(rows)}


# --------------------------------------------------------------------------------------

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--report", default="analysis/reports/s74_baseline129.json",
                    help="a comprehensive_report JSON, used ONLY for ND's own linear FR (GATE 3)")
    ap.add_argument("--json", default=None)
    ap.add_argument("--jobs", type=int, default=min(8, (os.cpu_count() or 4) - 2))
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--max-split", type=float, default=1.0,
                    help="GATE 1: max allowed H2/H3 disagreement between the two halves of "
                         "a cell's own analysis window, dB")
    ap.add_argument("--model", action="store_true",
                    help="ALSO render our own plugin at every capture's own condition and "
                         "compare, cell by cell.  Without this the tool is reference-only and "
                         "byte-for-byte the session-78 instrument.")
    ap.add_argument("--fit", action="append", default=[],
                    help="repeatable FitParams override for the MODEL renders (key=value). "
                         "Implies nothing on the reference side.")
    ap.add_argument("--force-render", action="store_true",
                    help="ignore the render stamp cache and re-render every condition")
    args = ap.parse_args()

    if args.selftest:
        return 0 if selftest() else 1

    if not selftest():
        print("⛔ GATE 0 FAILED -- refusing to report numbers from an unvalidated extractor.")
        return 1

    # ---- which captures ---------------------------------------------------------------
    files = []
    for fn in sorted(os.listdir(CAPDIR)):
        if not fn.endswith(".wav"):
            continue
        if "base-od" not in fn and not fn.startswith("ref-od"):
            continue
        if "gain-n12" in fn:
            continue                     # session 48: known-bad capture group
        try:
            s = C.parse_capture(fn)
        except Exception:                # noqa: BLE001
            continue
        # CONDITION-based exclusions only, decidable before any number is read
        # (session 74 item 6: never guard on the quantity under test).
        if s.get("blend") == 0.0 or s.get("level") == 0.0:
            continue
        files.append((fn, s))

    print("=" * 90)
    print("ND's OWN HARMONIC LADDER at 1 kHz -- read off the `lvl_` segments of the captures")
    print("=" * 90)
    print(f"  captures            : {len(files)} OD captures (gain-n12 and BLEND/LEVEL=0 excluded)")
    print(f"  tone                : {TONE_HZ:.0f} Hz   (chart HW tone 997 Hz, ND tone 800 Hz)")
    print(f"  levels              : {[d for d, _, _, _ in lvl_segments()]} dBFS")
    print(f"  window              : {WIN_LO:.2f}..{WIN_HI:.2f} of each 0.8 s segment")
    print()

    with ProcessPoolExecutor(max_workers=max(1, args.jobs), initializer=_init) as ex:
        results = list(ex.map(read_one, [f for f, _ in files]))

    data, bad = {}, []
    for fn, cells, err in results:
        if err:
            bad.append((fn, err))
        else:
            data[fn] = cells
    if bad:
        print(f"  ⚠ {len(bad)} capture(s) unreadable:")
        for fn, err in bad[:6]:
            print(f"      {fn}: {err}")
    settings = dict(files)

    contam, noisy, g1w, g2n = side_gates(data, "REFERENCE (ND captures)", args.max_split)

    # ---- the MODEL side ---------------------------------------------------------------
    mdata, mcontam, mnoisy = {}, set(), set()
    if args.model:
        print("=" * 90)
        print("MODEL SIDE -- our own renders, one per capture, at that capture's OWN condition")
        print("=" * 90)
        print(f"  renderer            : {RENDER_BIN}  (OS {RENDER_OS}, --trim-latency)")
        print(f"  condition           : DERIVED per file via captures.render_args(parse_capture())")
        print(f"  fit overrides       : {args.fit if args.fit else '(none -- shipped defaults)'}")
        ex_fn = files[0][0]
        print(f"  example argv        : {' '.join(render_argv(ex_fn, '<out>', tuple(args.fit)))}")
        print()
        with ProcessPoolExecutor(max_workers=max(1, args.jobs), initializer=_init_model,
                                 initargs=(tuple(args.fit),)) as ex:
            mres = list(ex.map(read_model, [f for f, _ in files]))
        mbad = []
        for fn, cells, err in mres:
            if err:
                mbad.append((fn, err))
            else:
                mdata[fn] = cells
        if mbad:
            print(f"  ⚠ {len(mbad)} render(s) unusable:")
            for fn, err in mbad[:6]:
                print(f"      {fn}: {err}")
        print(f"  rendered/read       : {len(mdata)} of {len(files)}")
        print()

        # GATE M -- the renders must actually track the condition.  Without this, a broken
        # argv path (session 65's missing --grunt) or a silently-ignored --fit would give a
        # perfectly plausible table of identical numbers.  Two distinct DRIVE settings must
        # produce distinct ladders; identical ones mean the condition never reached the binary.
        print("=" * 90)
        print("GATE M -- model renders must TRACK the condition (not all be the same render)")
        print("=" * 90)
        bydrive = {}
        for fn in mdata:
            bydrive.setdefault(settings[fn]["drive"], []).append(fn)
        drives = sorted(bydrive)
        if len(drives) >= 2:
            a_fn, b_fn = bydrive[drives[0]][0], bydrive[drives[-1]][0]
            common = sorted(set(mdata[a_fn]) & set(mdata[b_fn]))
            dmax = max(abs(mdata[a_fn][d]["hd"][3] - mdata[b_fn][d]["hd"][3]) for d in common)
            print(f"  DRIVE {drives[0]:.2f} ({a_fn})")
            print(f"     vs {drives[-1]:.2f} ({b_fn})")
            print(f"  max |dH3| across the shared ladder = {dmax:.3f} dB   "
                  f"{'PASS' if dmax > 1.0 else '⛔ FAIL -- renders do not track DRIVE'}")
            if dmax <= 1.0:
                print("  ⛔ refusing to report a model-vs-reference comparison from renders that "
                      "do not respond to the condition.")
                return 1
        print()

        mcontam, mnoisy, _, _ = side_gates(mdata, "MODEL (our renders)", args.max_split)

    # ---- GATE 3: the filter correction ------------------------------------------------
    print("=" * 90)
    print("GATE 3 -- ND's own linear gain at 2f..5f re f at a 1 kHz fundamental")
    print("=" * 90)
    gate_corr_sign()
    fb, fb_blended = filter_bridge(args.report)
    g2 = np.array([r["g2"] for r in fb]); g3 = np.array([r["g3"] for r in fb])
    g4 = np.array([r["g4"] for r in fb]); g5 = np.array([r["g5"] for r in fb])
    print(f"  ⚠ measured on the {len(fb)} BLEED-FREE captures (BLEND=LEVEL=max, condition")
    print(f"    DERIVED per file), because a harmonic only ever travels the OD path.")
    print(f"  over {len(fb)} captures, median (spread):")
    print(f"      g(2f)-g(f) = {np.median(g2):+6.2f} dB  ({g2.min():+.1f} .. {g2.max():+.1f})")
    print(f"      g(3f)-g(f) = {np.median(g3):+6.2f} dB  ({g3.min():+.1f} .. {g3.max():+.1f})")
    print(f"      g(4f)-g(f) = {np.median(g4):+6.2f} dB  ({g4.min():+.1f} .. {g4.max():+.1f})")
    print(f"      g(5f)-g(f) = {np.median(g5):+6.2f} dB  ({g5.min():+.1f} .. {g5.max():+.1f})")
    corr23 = float(np.median(g3 - g2))
    corr45 = float(np.median(g5 - g4))
    print()
    print(f"  ⭐ the PAIR corrections -- what H2-H3 and H4-H5 actually need:")
    print(f"      H2-H3 correction  g(3f)-g(2f) = {corr23:+.2f} dB   "
          f"(spread {np.min(g3 - g2):+.2f} .. {np.max(g3 - g2):+.2f})")
    print(f"      H4-H5 correction  g(5f)-g(4f) = {corr45:+.2f} dB   "
          f"(spread {np.min(g5 - g4):+.2f} .. {np.max(g5 - g4):+.2f})")
    print(f"  ⇒ at 1 kHz, H2 and H3 land at 2 and 3 kHz, close together on the mid plateau, so")
    print(f"    the pair correction is SMALL.  Compare the swept 100/200/400 Hz anchors, whose")
    print(f"    bridge to the chart's 800 Hz tone is -9 .. -24 dB and capture-dependent.")
    print()

    # ⚠⚠ The control that keeps session 79's own defect from coming back.  Reading this
    # correction off the BLENDED output (as the first version of this gate did) collapses it
    # and flips its sign, because the clean bleed fills the bridged-T scoop the fundamental
    # sits in.  Both are printed so the two can never be quietly confused again.
    if fb_blended:
        b2 = np.array([r["g2"] for r in fb_blended]); b3 = np.array([r["g3"] for r in fb_blended])
        bcorr23 = float(np.median(b3 - b2))
        print(f"  ⚠ CONTROL -- the SAME quantity read off the {len(fb_blended)} BLENDED captures:")
        print(f"      g(3f)-g(2f) = {bcorr23:+.2f} dB   vs the bleed-free {corr23:+.2f} dB")
        print(f"    ⇒ the mixer moves it by {abs(bcorr23 - corr23):.2f} dB"
              f"{' and inverts its sign' if bcorr23 * corr23 < 0 else ''}.  The bleed carries no")
        print(f"      harmonics, so the blended figure is the WRONG transfer here; it is printed")
        print(f"      only to keep that mistake visible.")
        print(f"    ⚠ cross-check like with like: harmonic_ladder.py's render-based +1.18 dB is a")
        print(f"      measurement of OUR MODEL's chain at blend/level max, so it corroborates the")
        print(f"      MODEL row below, NOT this ND row.")
        print()

    mcorr23 = mcorr45 = float("nan")
    if args.model:
        mfb, _ = filter_bridge(args.report, which="plugin_db")
        m2 = np.array([r["g2"] for r in mfb]); m3 = np.array([r["g3"] for r in mfb])
        m4 = np.array([r["g4"] for r in mfb]); m5 = np.array([r["g5"] for r in mfb])
        mcorr23 = float(np.median(m3 - m2))
        mcorr45 = float(np.median(m5 - m4))
        print(f"  ⭐⭐ AND THE SAME FOR OUR MODEL -- this is what licenses the model-vs-ND")
        print(f"     comparison.  A difference of two corrected pair statistics needs ONLY the")
        print(f"     DIFFERENCE of the two corrections:")
        print(f"      model H2-H3 correction = {mcorr23:+.2f} dB   (ND {corr23:+.2f})  "
              f"⇒ net {mcorr23 - corr23:+.2f} dB")
        print(f"      model H4-H5 correction = {mcorr45:+.2f} dB   (ND {corr45:+.2f})  "
              f"⇒ net {mcorr45 - corr45:+.2f} dB")
        net23 = abs(mcorr23 - corr23)
        # ⚠ The licensing argument is NOT "both are flat" -- each side carries ~+1 dB.  It is
        # that both chains model the SAME post-clipper filter, so the corrections nearly
        # cancel.  Stating it the other way would be a claim the data contradicts.
        print(f"  ⇒ NEITHER chain is flat here (each ~{corr23:+.1f} dB), but they very nearly CANCEL,")
        print(f"    because both model the same post-clipper filter.  Net {net23:.2f} dB "
              f"{'-- negligible against the ~9-10 dB effects below' if net23 < 1.0 else '-- NOT negligible'}"
              f"; it IS applied.")
        print(f"  ⚠ H4-H5 is the untrustworthy pair on BOTH sides (session 78): its ND correction")
        print(f"    alone is {corr45:+.2f} dB with a wide spread.  Quote H2-H3.")
        print()

    # ---- the ladder, anchored ---------------------------------------------------------
    print("=" * 90)
    print("THE ANCHORED READ -- ND's H2-H3 and H4-H5 at the chart's own H3/H1 operating points")
    print("=" * 90)
    lv = np.array([d for d, _, _, _ in lvl_segments()], float)
    hits, nonmono = anchor_hits(data, contam, noisy, settings, corr23, corr45)
    print(f"  ⚠ H3 peaks before the last level in {nonmono} of {len(data)} captures -- i.e. H3 is")
    print(f"    NOT monotone in level (the sessions-12/13 anti-phase null, on the REFERENCE).")
    print(f"    Every anchor below is the FIRST UPWARD crossing; GATE 0 proves the locator")
    print(f"    refuses the falling branch.")
    print()

    out = {}
    for lbl in ("low", "mid"):
        tgt = ANCHOR_H3[lbl]
        H = hits[lbl]
        hw23 = REF[lbl]["HW"][2] - REF[lbl]["HW"][3]
        nd23 = REF[lbl]["ND"][2] - REF[lbl]["ND"][3]
        hw45 = REF[lbl]["HW"][4] - REF[lbl]["HW"][5]
        nd45 = REF[lbl]["ND"][4] - REF[lbl]["ND"][5]
        print(f"  --- chart '{lbl} drive', anchored where ND's own H3/H1 = {tgt:+.1f} dB ---")
        if not H:
            print(f"      ⛔ NOT REACHED on the rising branch in any capture "
                  f"-- this operating point is not in the matrix at 1 kHz.")
            out[lbl] = {"n": 0}
            print()
            continue
        atl = np.array([x["at_dbfs"] for x in H])
        print(f"      reached in {len(H)} independent captures, at {atl.min():+.1f} .. "
              f"{atl.max():+.1f} dBFS input")
        H23 = [x for x in H if x["ok23"]]
        H45 = [x for x in H if x["ok45"]]
        print(f"      per-order measurability (Hn > residual + {ORDER_MARGIN_DB:.0f} dB): "
              f"H2-H3 usable in {len(H23)}/{len(H)}, H4-H5 in {len(H45)}/{len(H)}")
        print(f"      {'stat':>8} {'ND measured':>18} {'filt-corr':>10} | {'chart ND':>9} "
              f"{'chart HW':>9} | verdict")
        rowout = {}
        for nm, sub, key, keyc, cnd, chw in (("H2-H3", H23, "h23", "h23c", nd23, hw23),
                                            ("H4-H5", H45, "h45", "h45c", nd45, hw45)):
            if len(sub) < 3:
                print(f"      {nm:>8} {'--':>11}       {'--':>10} | {cnd:>+9.1f} {chw:>+9.1f} | "
                      f"⛔ NOT MEASURABLE ({len(sub)} usable captures) -- the orders sit at or "
                      f"under this instrument's own residual")
                rowout[nm] = {"n_usable": len(sub), "measurable": False}
                continue
            raw = np.array([x[key] for x in sub])
            cor = np.array([x[keyc] for x in sub])
            med = float(np.median(cor))
            p10, p90 = (float(np.percentile(cor, q)) for q in (10, 90))
            dnd, dhw = abs(med - cnd), abs(med - chw)
            span = abs(chw - cnd)
            # ⚠ DO NOT NAME A WINNER THE DATA DOES NOT SUPPORT.  My first version picked the
            # nearer column unconditionally and printed "matches chart HW" for a measurement
            # 12.5 dB from HW and 14.5 dB from ND on a 27 dB span -- a 2 dB preference read as
            # a discrimination.  A column is only "matched" if it is inside the measured
            # 10-90 spread AND clearly nearer than the other.
            in_nd, in_hw = (p10 <= cnd <= p90), (p10 <= chw <= p90)
            width = p90 - p10
            # ⚠ SECOND DEFECT IN MY OWN VERDICT, caught by its own printout: at the low anchor
            # it said "consistent with chart ND only" while the |d| columns beside it showed HW
            # NEARER (8.9 vs 9.6) -- because HW missed the p90 edge by 0.4 dB.  A 0.4 dB miss is
            # not a discrimination.  The decidable question is whether the measured spread is
            # even NARROWER than the thing it is being asked to resolve: if the 10-90 width over
            # conditions exceeds the whole HW-vs-ND separation, this statistic cannot separate
            # the columns at all, whichever one happens to fall just inside.
            if span < MIN_SPAN_DB:
                v = f"columns agree ({span:.1f} dB apart) -- not a discriminator"
            elif width >= span:
                v = (f"⛔ spread over conditions ({width:.1f} dB) EXCEEDS the whole HW-vs-ND "
                     f"separation ({span:.1f} dB) -- cannot discriminate")
            elif in_nd and in_hw:
                v = "spread covers BOTH columns -- discriminates neither"
            elif in_nd:
                v = f"consistent with chart ND only (|d| {dnd:.1f} vs HW {dhw:.1f})"
            elif in_hw:
                v = f"consistent with chart HW only (|d| {dhw:.1f} vs ND {dnd:.1f})"
            else:
                mid = 0.5 * (cnd + chw)
                v = (f"⛔ CONTRADICTS BOTH (|d| ND {dnd:.1f}, HW {dhw:.1f}; "
                     f"{'~midway' if abs(med - mid) < 0.15 * span else 'outside both'})")
            print(f"      {nm:>8} {np.median(raw):>+11.1f} raw   {med:>+10.1f} | "
                  f"{cnd:>+9.1f} {chw:>+9.1f} | {v}")
            print(f"      {'':>8} spread {p10:+.1f} .. {p90:+.1f} "
                  f"(10-90 pct over {len(sub)} captures)")
            rowout[nm] = {"n_usable": len(sub), "measurable": True,
                          "raw_median": float(np.median(raw)), "corr_median": med,
                          "p10_p90": [p10, p90], "spread_width_db": float(width),
                          "column_span_db": float(span),
                          "chart_ND": cnd, "chart_HW": chw,
                          "d_ND": dnd, "d_HW": dhw, "verdict": v}
        out[lbl] = {"n": len(H), "target_h3": tgt,
                    "at_dbfs": [float(x) for x in atl], "stats": rowout,
                    "cells": [{k: (v if not isinstance(v, dict) else
                                   {str(kk): vv for kk, vv in v.items()})
                               for k, v in x.items()} for x in H]}
        print()

    # ---- what explains the spread AT the anchor? -------------------------------------
    # If H2-H3 at a fixed H3 anchor were a clean function of the DRIVE knob, the chart's
    # unstated "mid drive" could be LOCATED and its column tested at one condition instead
    # of against a 16 dB envelope.  If it is not, the chart under-specifies its own
    # operating point and no capture can settle it.  This is the difference between "we
    # need a hotter capture" and "we need the chart's conditions".
    print("=" * 90)
    print("IS THE ANCHOR ENOUGH?  ND's H2-H3 at a FIXED H3, broken down by DRIVE")
    print("=" * 90)
    drivespread = {}
    for lbl in ("low", "mid"):
        sub = [x for x in hits[lbl] if x["ok23"]]
        if len(sub) < 3:
            continue
        print(f"  --- chart '{lbl} drive' anchor (H3 = {ANCHOR_H3[lbl]:+.0f} dB), "
              f"{len(sub)} usable captures ---")
        print(f"      {'DRIVE':>7} {'n':>3} {'H2-H3 median':>13} {'min':>8} {'max':>8}")
        byd = {}
        for d in sorted({x["drive"] for x in sub}):
            v = np.array([x["h23c"] for x in sub if x["drive"] == d])
            byd[d] = [float(np.median(v)), float(v.min()), float(v.max()), len(v)]
            print(f"      {d:>7.2f} {len(v):>3} {np.median(v):>+13.1f} "
                  f"{v.min():>+8.1f} {v.max():>+8.1f}")
        allv = np.array([x["h23c"] for x in sub])
        meds = np.array([byd[d][0] for d in byd])
        within = float(np.median([byd[d][2] - byd[d][1] for d in byd]))
        print(f"      total spread {allv.max() - allv.min():.1f} dB | "
              f"explained by DRIVE (spread of the per-drive medians) {meds.max() - meds.min():.1f} dB | "
              f"residual WITHIN one drive setting {within:.1f} dB")
        drivespread[lbl] = {"by_drive": {str(k): v for k, v in byd.items()},
                            "total_db": float(allv.max() - allv.min()),
                            "between_drive_db": float(meds.max() - meds.min()),
                            "within_drive_db": within}
        print()

    # ---- the reachability fact session 75/77 got wrong --------------------------------
    print("=" * 90)
    print("REACHABILITY -- the maximum ND H3/H1 this instrument sees, vs the recorded claim")
    print("=" * 90)
    allh3 = [(c["hd"][3], fn, db) for fn, cc in data.items() for db, c in cc.items()
             if (fn, db) not in contam and (fn, db) not in noisy]
    allh3.sort(reverse=True)
    v3 = np.array([x[0] for x in allh3])
    print(f"  1 kHz tone, {len(v3)} clean cells:  MAX {v3.max():+.1f} dB   "
          f"p95 {np.percentile(v3, 95):+.1f}   median {np.median(v3):+.1f}")
    print(f"  cells at or above the chart's mid-drive H3/H1 = {ANCHOR_H3['mid']:+.0f} dB : "
          f"{int((v3 >= ANCHOR_H3['mid']).sum())}")
    print(f"  ⚠ the recorded claims were 'never above ~ -25 dB' (session 75 section 5) and")
    print(f"    'nothing hotter than H3 ~ -35 dB' (a hardcoded string in matrix_harmonics).")
    print(f"    Both are MEDIANS, of different sets; the question is about the MAXIMUM.")
    print()

    cmp_out = {}
    if args.model:
        cmp_out = compare_model(data, mdata, contam, noisy, mcontam, mnoisy,
                                settings, corr23, corr45, mcorr23, mcorr45)

    if args.json:
        json.dump({
            "tone_hz": TONE_HZ, "window": [WIN_LO, WIN_HI],
            "n_captures": len(data), "levels_dbfs": [int(x) for x in lv],
            "model": bool(args.model), "model_fit": list(args.fit),
            "model_render_os": RENDER_OS if args.model else None,
            "filter_corr_model_h2h3_db": mcorr23 if args.model else None,
            "filter_corr_model_h4h5_db": mcorr45 if args.model else None,
            "comparison": cmp_out,
            "gate1_worst_split_db": g1w, "gate1_contaminated": len(contam),
            "gate2_over_limit": len(noisy), "gate2_limit_db": INHARM_MAX_DB,
            "filter_corr_h2h3_db": corr23, "filter_corr_h4h5_db": corr45,
            "filter_g_median": {"g2": float(np.median(g2)), "g3": float(np.median(g3)),
                                "g4": float(np.median(g4)), "g5": float(np.median(g5))},
            "max_h3_over_h1_db": float(v3.max()),
            "n_cells_at_or_above_chart_mid": int((v3 >= ANCHOR_H3["mid"]).sum()),
            "n_h3_nonmonotone_captures": nonmono,
            "order_margin_db": ORDER_MARGIN_DB,
            "anchored": out, "drive_breakdown": drivespread,
        }, open(args.json, "w"), indent=1)
        print(f"  wrote {args.json}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
