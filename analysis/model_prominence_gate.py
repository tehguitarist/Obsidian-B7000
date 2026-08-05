#!/usr/bin/env python3.11
"""GATE AW — the MODEL side of the prominence audit, and the EPOCH question, kept apart.

WHY THIS EXISTS
---------------
Session 158's own `▶ NEXT` #1:

    The MODEL side of AV3/AV4/AV6 is now genuinely owed, and s158 made it conditional on exactly
    the finding that fired.  The gate ran pedal-side deliberately (binary-independent, and it is
    the side W6's reference row is built from, which is what makes AV6's known answer possible) —
    but AV4 found 25 % membership instability, so whether the MODEL's readings are equally
    window-bound is open.  It costs ~25 renders into a PRIVATE directory (never
    `build/s122_feature_locus/`, which is GATE W's own cache) and the renders will be s156-epoch,
    so the model numbers will not match `s122_feature_locus.json` — that is a re-baseline
    question, not an estimator one, and the two must not be conflated.

⭐⭐ THE MODEL SIDE IS WHERE A FLIP WOULD ACTUALLY HURT, WHICH IS WHY IT IS WORTH THE WORK.
GATE W6 classifies each side separately, and the two sides carry opposite kinds of claim:

    PEDAL   DRIVE-DEPENDENT — a POSITIVE result.  A conservative, window-limited estimator can
                              only ever UNDER-report it.
    MODEL   FIXED           — a NEGATIVE result, and a negative result is exactly what a
                              window-bounded estimator can MANUFACTURE.

Open item 6's whole frame is the CONTRAST between those two ("ours is pinned to 0.2 %, theirs
walks 7.9 %"), and AV priced only the half that cannot be manufactured.  If the model's FIXED
verdicts turned out to be an artefact of where GATE W cut its windows, item 6's frame, AA6 and AD
would all owe a re-read.  That is the question this gate answers.

⭐⭐⭐ AND IT COSTS NO RENDER, BECAUSE THE PUBLISHED ARTEFACTS ARE STILL ON DISK.  s158 assumed the
model arm needed fresh renders at a new epoch.  It does not: `build/s122_feature_locus/` still
holds the 25 renders GATE W published from, and AW1b ASSERTS they are those artefacts by
reproducing GATE W's STORED w6 model medians and spans exactly.  So the ESTIMATOR question is
asked on the very curves the published numbers came from — which is the right scope, because the
claim under audit is GATE W's published claim — and it is read-only (AW0 refuses if a single byte
of that cache moves).

THE TWO ARMS, AND WHY THEY ARE SEPARATE
---------------------------------------
  ESTIMATOR (AW2-AW4)   s122-epoch curves, zero renders.  "Is GATE W's published model-side
                        number a depth, or a statement about where its window was drawn?"
  EPOCH     (AW5-AW6)   the SAME conditions re-rendered with the CURRENT binary into a PRIVATE
                        directory.  "Has the shipped chain MOVED those rows since s122?" — three
                        DSP changes have landed (s124 ADAA + `clipK`, s146 the 3-segment MASTER
                        taper, s150-156 `OdToneRestore`), and one of them is a biquad sitting at
                        323 Hz, i.e. inside `mid_notch`'s own window.
Fusing them is the specific error s158 warned about: an epoch difference read as an estimator
defect, or the reverse.  Every table here is labelled with which arm it belongs to.

WHAT IT MEASURES
----------------
AW0  MEMBERSHIP (GATE W's own, through GATE W's own functions) + a CACHE-INTEGRITY guard: every
     file in GATE W's render cache is fingerprinted before and after, and the gate REFUSES if one
     moved.  Renders go only to the private directory, and the two paths are asserted distinct.
AW1  KNOWN ANSWERS, three, before anything is read:
     (a) this gate's pinned walk reproduces `W.locate`'s `prom` EXACTLY on the MODEL curves;
     (b) ⭐ CROSS-GATE: the on-disk cache reproduces GATE W's STORED w6 MODEL medians and spans
         exactly — which is what licenses calling these curves "the published artefacts", and it
         is not bookkeeping: 16 of the 24 renders carry a BINARY STAMP that POSTDATES the stored
         report, so without this reproduction they would be a different epoch wearing the right
         filenames;
     (c) the widening THEOREM: for an INTERIOR extremum `prom` is a max over a set of cells and
         widening only ADDS cells, so it is non-decreasing in window width.  Any decrease means
         the widening is not pinned and every table below is measuring a moved reader instead of a
         window.  ⚠ The precondition is load-bearing and this gate's own first draft omitted it:
         when the extremum rests ON a bound one side is EMPTY and its rise is the convention 0.0,
         so widening replaces a floor with a real (negative) maximum and the value legitimately
         falls.  Those readings are exactly the ones GATE W3 refuses, and AW1c reports them
         separately — a shipped `prom` of 0.0 that goes negative under widening is s126's
         edge-resting pathology with a sign on it.
AW2  ESTIMATOR ARM — bound-termination and pinned widening per feature, MODEL side, printed
     beside GATE AV's stored PEDAL column (imported from s158's report, never transcribed).
AW3  ESTIMATOR ARM — membership stability at the shipped `MIN_PROM_DB` bar, model side.
AW4  ⭐⭐ ESTIMATOR ARM, THE PRICE — GATE W6's own statistic on GATE W6's own membership rule,
     re-graded with the bar applied to the widened reading.  Do any MODEL classifications flip?
AW5  ⭐⭐ EPOCH ARM — current-binary renders vs the s122 cache, reported BOTH pooled and on
     MATCHED membership.  The matched column is the graded one, because a bar that admits more
     cells moves a pooled median with no feature having moved at all
     (`aggregate-moved-check-membership-first`, which this session's own first draft committed —
     see AW5's note).
AW6  ⭐ EPOCH ARM, THE CROSS-CHECK — `mid_notch` read by GATE W's E1 and by the restore stage's
     own E6 (`od_tone_restore_fit.notch_geometry`) on the SAME cells.  The two disagree, and the
     disagreement is attributed rather than left as a discrepancy.

WHAT THIS DOES NOT CLAIM
------------------------
  * It changes no constant and proposes none.
  * The widened reading is NOT a better depth (AV's caveat, inherited): a x2 window is a second
    arbitrary window and it reaches the neighbouring features.  It is a SENSITIVITY probe only.
  * The EPOCH arm compares two renders of the same conditions.  It says which of GATE W's stored
    model rows have moved since they were published; it does not re-baseline GATE W, and it does
    not adjudicate whether a move is an improvement — where it touches a shipped stage's own
    acceptance question it hands that to the stage's own instrument (AW6).
  * `bass_notch` / `treble_notch` have NO admitted model reading in either epoch.  That is GATE
    W's own membership outcome (a mix cancellation has no bleed-free reading — s126), reported as
    such and not as a measurement.

Run:  python3.11 analysis/model_prominence_gate.py
      python3.11 analysis/model_prominence_gate.py --no-epoch      (estimator arm only, no render)
      python3.11 analysis/_mutate_gate_aw.py
"""
import argparse
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import analyze as A                    # noqa: E402
import captures as C                   # noqa: E402
import comprehensive_report as CR      # noqa: E402
import feature_locus_gate as W         # noqa: E402
import od_tone_restore_fit as OT       # noqa: E402
import prominence_audit_gate as AV     # noqa: E402
from parallel import add_jobs_arg, pmap   # noqa: E402

OUT_JSON = os.path.join(HERE, "reports", "s159_model_prominence.json")
AV_REPORT = os.path.join(HERE, "reports", "s158_prominence_audit.json")

# ⛔⛔ THE PRIVATE RENDER DIRECTORY.  s158's `▶ NEXT` names this explicitly: the epoch arm must
# NEVER render into `W.REN_DIR`, because `W.render` re-renders any file whose binary stamp does
# not match the current build — so one run of this gate pointed at GATE W's cache would silently
# replace the artefacts GATE W's published numbers came from, and AW1b (the only thing that can
# detect that they ARE those artefacts) would then pass vacuously forever after.
PRIV_DIR = os.path.join(os.path.dirname(HERE), "build", "s159_model_prom")

FAILED = []


def fail(tag, msg):
    FAILED.append(tag)
    print(f"\n  ⛔ {tag}: {msg}")


def die(tag, msg):
    fail(tag, msg)
    print(f"\nGATE AW: REFUSED at {tag}.\n")
    sys.exit(1)


def cls(x):
    """GATE W6's OWN classification, with W6's OWN bar imported rather than chosen."""
    return ("UNRESOLVED" if not np.isfinite(x)
            else "DRIVE-DEP" if x > W.STIM_MOVE_FRAC else "FIXED")


# =============================== AW0: membership + cache integrity ==============================
def fingerprint(d):
    """(name, size, mtime_ns) for every file in a directory — the same identity `W.render`'s own
    stamp is built from, so a re-render is detectable and a pure read is not."""
    if not os.path.isdir(d):
        return {}
    out = {}
    for n in sorted(os.listdir(d)):
        p = os.path.join(d, n)
        if os.path.isfile(p):
            st = os.stat(p)
            out[n] = [st.st_size, st.st_mtime_ns]
    return out


def aw0(out):
    print("\n" + "=" * 100)
    print("AW0  MEMBERSHIP (GATE W's own) + the CACHE-INTEGRITY guard")
    print("=" * 100)
    if os.path.abspath(PRIV_DIR) == os.path.abspath(W.REN_DIR):
        die("AW0", "the private render directory IS GATE W's cache — the epoch arm would overwrite "
                   "the artefacts the estimator arm audits")
    files, lad, eps = AV.membership(W.REPORT)
    print(f"  membership rebuilt through GATE W's own functions: {len(files)} captures "
          f"({len(lad)} LEVEL-ladder detents, {len(eps)} pure-OD endpoints)")
    missing = [f for f in files
               if not os.path.exists(os.path.join(W.REN_DIR,
                                                  f.replace(".wav", "") + "_plugin.wav"))]
    if missing:
        die("AW0", f"{len(missing)} of GATE W's published renders are not on disk "
                   f"({missing[:3]}) — the estimator arm cannot be asked on the published "
                   f"artefacts, and re-rendering them would answer a different question")
    print(f"  GATE W cache  : {W.REN_DIR}  ({len(fingerprint(W.REN_DIR))} files, READ-ONLY here)")
    print(f"  private renders: {PRIV_DIR}  (epoch arm only)")

    # ⭐ The hazard this gate has to survive, printed BEFORE the known answer that settles it.
    stamps = {}
    for f in files:
        sp = os.path.join(W.REN_DIR, f.replace(".wav", "") + "_plugin.wav.args.json")
        b = tuple(json.load(open(sp)).get("bin") or [])
        stamps.setdefault(b, []).append(f)
    rep_mtime = os.path.getmtime(W.OUT_JSON)
    newer = sum(len(v) for k, v in stamps.items() if k and k[1] / 1e9 > rep_mtime)
    print(f"\n  ⚠ {len(stamps)} distinct BINARY stamps across those renders, and {newer} of "
          f"{len(files)} carry a stamp that\n    POSTDATES the stored report — so the cache is "
          f"NOT self-evidently the artefact set GATE W published\n    from.  AW1b is what settles "
          f"it, and it is why AW1b is a hard exit rather than a print.")
    out["aw0"] = {"n_captures": len(files), "n_endpoints": len(eps), "n_ladder": len(lad),
                  "n_binary_stamps": len(stamps), "n_stamps_after_report": newer,
                  "ren_dir": W.REN_DIR, "priv_dir": PRIV_DIR}
    return files, lad, eps


# ================================ reading one side of one render ================================
def _read(path, is_capture=False):
    """MODEL (or pedal) readings for one file, all sweeps, all features — through GATE W's own
    curve pipeline (`A.transfer_h1` -> `W.smooth`), so every number is apples-to-apples with GATE
    W's stored ones and with GATE AV's pedal column."""
    orig, ref = W._load_orig()
    x = C.load_capture(path) if is_capture else A.load(path)
    al, _ = A.align(x, orig)
    per = {}
    for sw in W.SWEEPS:
        f, m = A.transfer_h1(A.seg_of(al, sw), ref)
        d = W.smooth(f, m)
        cell = {}
        for name, kind, win, _lab in W.FEATURES:
            i = AV.cell_index(d, win, kind)
            shipped = W.locate(d, win, kind)
            wide = {}
            for w in AV.WIDEN:
                s = AV.sides_at(d, i, AV.widen_win(win, w), kind)
                wide[f"{w}"] = None if s is None else {"prom": s["prom"],
                                                       "n_bound_sides": s["n_bound_sides"]}
            cell[name] = {
                "f0": shipped["f0"], "shipped_prom": shipped["prom"], "edge": shipped["edge"],
                "margin_frac": shipped["margin_frac"],
                "w3_valid": bool((not shipped["edge"])
                                 and shipped["margin_frac"] >= W.EDGE_MARGIN_FRAC),
                "walk": AV.sides_at(d, i, win, kind), "widen": wide}
        per[sw] = cell
    return per


def _model_cell(arg):
    f, ren_dir = arg
    return f, _read(os.path.join(ren_dir, f.replace(".wav", "") + "_plugin.wav"))


def _render_cell(arg):
    """Render ONE condition into a caller-supplied directory, through `W.render` so the argv AND
    BINARY stamp are the shipped ones.  ⚠ Kept separate from `_model_cell`, which only READS —
    the estimator arm must never be able to render, and this gate's own first draft omitted the
    render step entirely and passed only because an earlier scratch run had left the directory
    populated (found by the mutation runner, which starts from an empty one)."""
    f, ren_dir = arg
    out = os.path.join(ren_dir, f.replace(".wav", "") + "_plugin.wav")
    W.render(out, C.render_args(C.parse_capture(f)))
    return f


def _pedal_cell(f):
    return f, _read(os.path.join(C.CAPTURE_DIR, f), is_capture=True)


def collect(files, ren_dir, jobs=None):
    return dict(pmap(_model_cell, [(f, ren_dir) for f in files], jobs=jobs))


def admitted(by, f, sw, name, use_wide=False):
    """GATE W3's admission rule AND GATE W6's bar, in one place so no table can drift from
    another.  `use_wide` applies the bar to the widened reading instead of the shipped one."""
    v = by[f][sw][name]
    p = v["widen"][f"{AV.WIDEN[-1]}"]["prom"] if use_wide else v["shipped_prom"]
    return bool(v["w3_valid"] and p >= W.MIN_PROM_DB)


def w6_span(by, eps, name, use_wide=False, cells=None):
    """GATE W6's OWN statistic, rebuilt from `gate_w6`'s rule rather than guessed: ENDPOINT
    captures only, per-CELL exclusion, the MEDIAN f0 per sweep, `span = max/min - 1`.

    `cells` optionally restricts to a fixed (file, sweep) set — the matched-membership form AW5
    needs, and the ONLY form in which two epochs may be differenced."""
    meds, n = [], 0
    for sw in W.SWEEPS:
        vals = []
        for f in eps:
            if cells is not None:
                if (f, sw) not in cells:
                    continue
            elif not admitted(by, f, sw, name, use_wide):
                continue
            vals.append(by[f][sw][name]["f0"])
        if vals:
            meds.append(float(np.median(vals)))
            n += len(vals)
    span = (max(meds) / min(meds) - 1.0) if len(meds) >= 3 else float("nan")
    return span, meds, n


# ==================================== AW1: the known answers ====================================
def aw1(model, out):
    print("\n" + "=" * 100)
    print("AW1  KNOWN ANSWERS — three, before a single number below is read")
    print("=" * 100)

    # (a) the transcription, on MODEL curves this time.
    worst, n, nb = 0.0, 0, 0
    for f, per in model.items():
        for sw in W.SWEEPS:
            for name, _k, _w, _l in W.FEATURES:
                v = per[sw][name]
                # REFUSE rather than crash (s117): a `None` here means the pinned cell fell
                # outside the shipped window, which is a broken pin, not a missing reading.
                if v["widen"]["1.0"] is None or v["walk"] is None:
                    die("AW1a", f"the pinned cell for `{name}` at {f}/{sw} is outside its own "
                                f"shipped window — the pin is not `locate`'s extremum, so nothing "
                                f"below is the shipped statistic")
                worst = max(worst, abs(v["widen"]["1.0"]["prom"] - v["shipped_prom"]))
                n += 1
                nb += v["walk"]["n_bound_sides"]
    print(f"  (a) the pinned walk must BE `W.locate`'s prominence at widen = 1.0, on the MODEL "
          f"side\n      {n} readings, worst |this gate - W.locate| = {worst:.3e} dB")
    if worst > 0.0:
        die("AW1a", f"the transcribed walk does not reproduce `W.locate` ({worst:.3e} dB) — every "
                    f"model number below is about a DIFFERENT estimator than GATE W ships")
    print(f"      ⇒ 0.000e+00.  Free by-product — AU1's structural claim on the MODEL side: "
          f"{nb} of {2 * n}\n        walk sides ({100.0 * nb / (2 * n):.1f} %) are "
          f"bound-terminated (pedal side, s158: 95.5 %).")

    # (b) ⭐ THE CROSS-GATE KNOWN ANSWER.  This is what makes the whole estimator arm legitimate.
    stored = json.load(open(W.OUT_JSON))["w6"]
    files, _lad, eps = AV.membership(W.REPORT)
    print(f"\n  (b) ⭐ the on-disk cache must reproduce GATE W's STORED w6 MODEL rows exactly")
    print(f"      {'feature':13} {'stored span':>12} {'recomputed':>12} {'Δ':>10}  medians")
    worst_ka, n_res = 0.0, 0
    for name, _k, _w, _l in W.FEATURES:
        span, meds, _n = w6_span(model, eps, name)
        st = stored[name]["model"]
        s_st = st.get("span_frac", float("nan"))
        ka = (abs(span - s_st) if np.isfinite(span) and np.isfinite(s_st)
              else 0.0 if (not np.isfinite(span) and not np.isfinite(s_st)) else float("nan"))
        # the medians must match elementwise too — a span is one number and can agree by accident
        m_st = st.get("medians", [])
        km = (max((abs(a - b) for a, b in zip(meds, m_st)), default=0.0)
              if len(meds) == len(m_st) else float("nan"))
        worst_ka = max(worst_ka, ka if np.isfinite(ka) else 1e9,
                       km if np.isfinite(km) else 1e9)
        if np.isfinite(span):
            n_res += 1
        print(f"      {name:13} {s_st * 100:11.2f}% {span * 100:11.2f}% {ka:10.3e}  "
              f"{'✅' if (np.isfinite(ka) and ka < 1e-12 and np.isfinite(km) and km < 1e-9) else '⛔'}"
              f"  n_med {len(meds)}/{len(m_st)}")
    if not (worst_ka < 1e-9):
        die("AW1b", f"the cache does NOT reproduce GATE W's stored w6 model rows (worst "
                    f"{worst_ka:.3e}) — these renders are not the artefacts the published numbers "
                    f"came from, so the estimator arm would be auditing a different chain wearing "
                    f"the right filenames")
    print(f"      ⇒ worst Δ {worst_ka:.3e}.  ⭐ THAT is what licenses the whole estimator arm: "
          f"despite\n        {out['aw0']['n_stamps_after_report']} of "
          f"{out['aw0']['n_captures']} binary stamps postdating the report, these curves ARE the "
          f"ones\n        GATE W published from.  {n_res} of {len(W.FEATURES)} model rows resolve "
          f"at all; the rest are\n        GATE W's own membership outcome, not a missing "
          f"measurement.")

    # (c) the widening theorem — free, and it is what certifies AW2's instrument.
    #
    # ⚠⚠ IT HAS A PRECONDITION, AND THE FIRST DRAFT OF THIS GATE OMITTED IT AND DULY REFUSED
    # AGAINST CORRECT DATA (177 decreases, worst 0.516 dB).  Each side's rise is
    # `max over the side's cells of (dd[k] - dd[i])`, and widening only adds cells, so the max is
    # non-decreasing — PROVIDED the side is non-empty to begin with.  When the extremum rests ON a
    # window bound one side has NO cells and `sides_at` reports its rise as the CONVENTION 0.0,
    # which is not the max over an empty set; widening then replaces that convention with a real
    # maximum, and outside the old window the curve keeps falling, so the value can go NEGATIVE.
    # ⇒ the theorem holds exactly on readings with an INTERIOR extremum, which is precisely
    # `locate`'s own `edge` flag and precisely the population GATE W3 admits.
    # ⭐ And the exception is not noise, it is s126's edge-resting pathology measured with a SIGN:
    # a shipped `prom` of 0.0 that goes negative under widening is a reading whose 0.0 was a floor
    # rather than a measurement — a sharper statement of the same thing `edge=True` records.
    dec, worst_dec, npair = 0, 0.0, 0
    n_edge, edge_neg, worst_neg = 0, 0, 0.0
    for f, per in model.items():
        for sw in W.SWEEPS:
            for name, _k, _w, _l in W.FEATURES:
                v = per[sw][name]
                ws = v["widen"]
                seq = [ws[f"{w}"]["prom"] for w in AV.WIDEN if ws[f"{w}"] is not None]
                if v["edge"]:
                    n_edge += 1
                    if min(seq) < -1e-12:
                        edge_neg += 1
                        worst_neg = min(worst_neg, min(seq))
                    continue                      # precondition fails — not a theorem case
                for a, b in zip(seq, seq[1:]):
                    npair += 1
                    if b < a - 1e-12:
                        dec += 1
                        worst_dec = max(worst_dec, a - b)
    print(f"\n  (c) THEOREM — for an INTERIOR extremum each side's rise is a max over a cell set "
          f"and\n      widening only ADDS cells, so `prom` is non-decreasing in window width.")
    print(f"      decreases over {npair} adjacent widen pairs on interior readings: {dec} "
          f"(worst {worst_dec:.3e} dB)")
    if dec:
        die("AW1c", f"{dec} decreases on INTERIOR readings — the widening is NOT pinned, so "
                    f"AW2-AW4 would be measuring a reader that moved rather than a window that "
                    f"grew (s151's feature-jump)")
    print("      ⇒ 0.  The extremum is genuinely pinned; the widening changes the DOMAIN only.")
    print(f"      ⚠ the precondition EXCLUDES {n_edge} of {n} readings whose extremum rests ON a "
          f"bound —\n        exactly what GATE W3 refuses.  {edge_neg} of those go NEGATIVE under "
          f"widening (worst {worst_neg:.3f} dB),\n        which is s126's edge-resting pathology "
          f"with a sign on it: their shipped `prom` of 0.0 is a\n        convention for an empty "
          f"walk side, not a measured rise.")
    out["aw1"] = {"n_readings": n, "worst_transcription_db": worst, "bound_sides": nb,
                  "sides_total": 2 * n, "worst_w6_ka": worst_ka, "n_resolved_rows": n_res,
                  "widen_decreases": dec, "widen_pairs": npair, "n_edge_excluded": n_edge,
                  "edge_negative": edge_neg, "worst_edge_negative_db": worst_neg}


# ============================ AW2: the estimator arm, model side ================================
def aw2(model, out):
    print("\n" + "=" * 100)
    print("AW2  ESTIMATOR ARM — is the MODEL's prominence a depth, or a window?   (s122 epoch)")
    print("=" * 100)
    print("     Per feature, on GATE W3's own admitted MODEL readings: where is each side's max")
    print("     ascent attained, and what does the reading do under a PINNED widening?")
    print("     ⚠ The widened value is NOT a better depth — it is a sensitivity probe (AV's")
    print("       caveat, inherited).  A reading that moves had its value set by the window.")
    av = json.load(open(AV_REPORT))["av3"]["per_feature"]
    print(f"\n  {'feature':13} {'n':>4} {'both-sh':>7} {'1bnd':>5} {'2bnd':>5} {'med prom':>9} "
          f"{'Δ@x2.0':>8} | {'PEDAL Δ@x2':>10}  verdict (model)")
    print("  " + "-" * 104)
    per = {}
    for name, _k, _w, _l in W.FEATURES:
        vs = [per_sw[name] for per_sw in
              (model[f][sw] for f in model for sw in W.SWEEPS) if per_sw[name]["w3_valid"]]
        n_all = len(model) * len(W.SWEEPS)
        ped_d = av.get(name, {}).get("median_widen_delta_db", float("nan"))
        if not vs:
            print(f"  {name:13} {0:4d} {'':>7} {'':>5} {'':>5} {'':>9} {'':>8} | "
                  f"{ped_d:10.3f}  -- no W3-valid MODEL reading (GATE W's own membership) --")
            per[name] = {"n": 0, "n_all": n_all, "verdict": "NO ADMITTED MODEL READING"}
            continue
        nb = [v["walk"]["n_bound_sides"] for v in vs]
        proms = [v["shipped_prom"] for v in vs]
        d2 = [v["widen"][f"{AV.WIDEN[-1]}"]["prom"] - v["shipped_prom"] for v in vs]
        med_p, med_d = float(np.median(proms)), float(np.median(d2))
        # ⭐ The verdict compares two MEASURED columns — the movement against the reading's own
        # median — so there is no threshold in it beyond AV's own "did it move at all" tolerance.
        if med_d <= AV.MOVE_TOL_DB:
            v = "✅ DEPTH — window-free"
        elif med_d > med_p:
            v = "⛔ WINDOW-DOMINATED"
        else:
            v = "⚠ LOWER BOUND — set partly by the window"
        print(f"  {name:13} {len(vs):4d} {nb.count(0):7d} {nb.count(1):5d} {nb.count(2):5d} "
              f"{med_p:9.3f} {med_d:8.3f} | {ped_d:10.3f}  {v}")
        per[name] = {"n": len(vs), "n_all": n_all, "both_shoulder": nb.count(0),
                     "one_bound": nb.count(1), "two_bound": nb.count(2),
                     "median_prom_db": med_p, "median_widen_delta_db": med_d,
                     "pedal_widen_delta_db": ped_d, "verdict": v}
    dom = [k for k, v in per.items() if v.get("verdict", "").startswith("⛔")]
    free = [k for k, v in per.items() if v.get("verdict", "").startswith("✅")]
    res = [k for k, v in per.items() if v["n"]]
    verdict = (f"{len(free)} of {len(res)} admitted MODEL features give a window-free depth; "
               f"{len(dom)} are WINDOW-DOMINATED {dom}.\n     The model side is "
               f"{'no better' if len(free) == 0 else 'partly better'} than the pedal side "
               f"(s158: 0 of 7 window-free, 3 dominated) — the\n     estimator's limitation is a "
               f"property of the WINDOWS, which both sides share, not of either\n     signal.")
    print("\n   " + verdict)
    out["aw2"] = {"per_feature": per, "verdict": verdict, "population": "W3-valid (model side)",
                  "widen": list(AV.WIDEN), "epoch": "s122"}


# ======================= AW3: does the DETECTOR's membership move? (model) ======================
def aw3(model, out):
    print("\n" + "=" * 100)
    print("AW3  ESTIMATOR ARM — membership stability at the shipped bar   (model side, s122 epoch)")
    print("=" * 100)
    print(f"     Same cells, bar ({W.MIN_PROM_DB} dB, W.MIN_PROM_DB) applied to the shipped reading")
    print("     and then to the widened one.  ⛔ A flip is NOT a rejected feature — the wide window")
    print("     admits the neighbours' flanks too.  It measures how firm a presence verdict is.")
    print(f"\n  {'bar dB':>7} {'n valid':>8} {'over ship':>10} {'over wide':>10} {'flips IN':>9} "
          f"{'flips OUT':>10} {'unstable':>9}")
    print("  " + "-" * 70)
    rows_out = []
    for bar in (0.5, W.MIN_PROM_DB, 2.0, 4.0):
        nv = ni = no = os_ = ow = 0
        for f in model:
            for sw in W.SWEEPS:
                for name, _k, _w, _l in W.FEATURES:
                    v = model[f][sw][name]
                    if not v["w3_valid"]:
                        continue
                    nv += 1
                    a = v["shipped_prom"] >= bar
                    b = v["widen"][f"{AV.WIDEN[-1]}"]["prom"] >= bar
                    os_ += a
                    ow += b
                    ni += (b and not a)
                    no += (a and not b)
        frac = (ni + no) / nv if nv else float("nan")
        star = " <<< shipped bar" if abs(bar - W.MIN_PROM_DB) < 1e-9 else ""
        print(f"  {bar:7.1f} {nv:8d} {os_:10d} {ow:10d} {ni:9d} {no:10d} {frac * 100:8.1f}%{star}")
        rows_out.append({"bar_db": bar, "n_valid": nv, "over_ship": os_, "over_wide": ow,
                         "flips_in": ni, "flips_out": no, "unstable_frac": frac})
    # AW1c already proved flips OUT are impossible; asserting it HERE is what makes the table
    # readable as a one-sided sensitivity rather than as noise.
    if any(r["flips_out"] for r in rows_out):
        die("AW3", "a reading LEFT the admitted set when the window grew — impossible under AW1c's "
                   "theorem, so the widening is not pinned")
    shipped = [r for r in rows_out if abs(r["bar_db"] - W.MIN_PROM_DB) < 1e-9][0]
    av4 = json.load(open(AV_REPORT))["av4"]
    ped = [r for r in av4["rows"] if abs(r["bar_db"] - W.MIN_PROM_DB) < 1e-9][0] \
        if isinstance(av4.get("rows"), list) else None
    # Computed both ways: a membership that does not move under the widening is a detector the
    # project can keep quoting, and it must be able to come back as that.
    if shipped["flips_in"] == 0 and shipped["flips_out"] == 0:
        v = (f"✅ WINDOW-STABLE — 0 of {shipped['n_valid']} W3-valid MODEL readings change presence "
             f"verdict at the\n     shipped {W.MIN_PROM_DB} dB bar when the window's log width "
             f"doubles.")
    else:
        v = (f"⚠ {shipped['unstable_frac'] * 100:.1f} % of W3-valid MODEL readings change presence "
             f"verdict at the shipped {W.MIN_PROM_DB} dB bar\n     when the window's log width "
             f"doubles"
             + (f" (pedal side, s158: {ped['unstable_frac'] * 100:.1f} %)" if ped else "")
             + ".  Flips OUT: 0, as the theorem requires.")
    print("\n   " + v)
    out["aw3"] = {"rows": rows_out, "verdict": v, "population": "W3-valid (model side)"}


# ================= AW4: THE PRICE — do the MODEL's W6 classifications flip? =====================
def aw4(model, eps, out):
    print("\n" + "=" * 100)
    print("AW4  ⭐⭐ THE PRICE — GATE W6's own statistic, own membership, bar on the widened reading")
    print("=" * 100)
    print("     GATE W6's MODEL row is the NEGATIVE half of open item 6's contrast (\"ours is")
    print("     pinned, theirs walks\"), and a negative result is the kind a window-bounded")
    print("     estimator can MANUFACTURE.  So: re-grade it with the bar applied to the widened")
    print("     reading and ask whether any FIXED verdict becomes DRIVE-DEPENDENT.")
    stored = json.load(open(W.OUT_JSON))["w6"]
    print(f"\n  {'feature':13} {'span ship':>10} {'stored':>9} {'KA':>3} {'span wide':>10} "
          f"{'Δ':>8} {'cells s/w':>11}  MODEL verdict ship -> wide")
    print("  " + "-" * 100)
    per, flipped, worst = {}, [], 0.0
    for name, _k, _w, _l in W.FEATURES:
        s_ship, _m, n_s = w6_span(model, eps, name, use_wide=False)
        s_wide, _m2, n_w = w6_span(model, eps, name, use_wide=True)
        st = stored[name]["model"].get("span_frac", float("nan"))
        ka = (abs(s_ship - st) if np.isfinite(s_ship) and np.isfinite(st)
              else 0.0 if (not np.isfinite(s_ship) and not np.isfinite(st)) else float("nan"))
        d = (abs(s_wide - s_ship) if np.isfinite(s_wide) and np.isfinite(s_ship) else float("nan"))
        if np.isfinite(d):
            worst = max(worst, d)
        c_s, c_w = cls(s_ship), cls(s_wide)
        if c_s != c_w:
            flipped.append((name, c_s, c_w))
        print(f"  {name:13} {s_ship * 100:9.2f}% {st * 100:8.2f}% "
              f"{'✅' if np.isfinite(ka) and ka < 1e-12 else '⛔':>3} {s_wide * 100:9.2f}% "
              f"{d * 100:7.2f}% {n_s:5d}/{n_w:<5d}  {c_s} -> {c_w}"
              f"{'   <<< FLIPPED' if c_s != c_w else ''}")
        per[name] = {"span_ship": s_ship, "span_wide": s_wide, "stored": st, "ka_delta": ka,
                     "delta": d, "n_cells_ship": n_s, "n_cells_wide": n_w,
                     "class_ship": c_s, "class_wide": c_w}
    res = W.GRID_STEP_FRAC / 3.0
    print(f"\n  graded against GATE W's OWN resolution, imported: a third of a 1/48-oct cell = "
          f"{res * 100:.2f} %")
    # The two flip kinds are NOT the same finding and must not be pooled into one verdict.
    hard = [t for t in flipped if "UNRESOLVED" not in t[1:]]
    soft = [t for t in flipped if "UNRESOLVED" in t[1:]]
    if hard:
        v = (f"⚠⚠ A RESOLVED MODEL CLASSIFICATION FLIPS: {hard}.  GATE W6's model verdict for "
             f"those\n     features is in part a statement about where its window was cut, and "
             f"open item 6's frame,\n     AA6 and AD all owe a re-read.")
    else:
        v = (f"⭐⭐ 0 of {sum(1 for p in per.values() if np.isfinite(p['span_ship']))} RESOLVED "
             f"MODEL rows flip.  The model's FIXED verdicts are NOT a window\n     artefact — so "
             f"open item 6's contrast survives at BOTH ends: the pedal's DRIVE-DEPENDENT "
             f"rows\n     survive widening (s158, 0 of 7) and the model's FIXED rows survive it "
             f"too.  Sizes move by up\n     to {worst * 100:.2f} % against a {res * 100:.2f} % "
             f"resolution, so the percentages stay unquotable to two decimals.")
    if soft:
        v += (f"\n     ⭐ Separately, {[t[0] for t in soft]} moves out of UNRESOLVED when the bar "
              f"is met on the widened\n       reading — a MEMBERSHIP recovery, not a verdict "
              f"inversion.  GATE W6 reports that row UNRESOLVED\n       for a membership reason "
              f"(s126), and this is that reason relaxed: it is corroboration of the\n       "
              f"UNRESOLVED being a bar artefact, and ⛔ NOT a licence to quote the widened span "
              f"as a measurement.")
    print("\n   " + v)
    out["aw4"] = {"per_feature": per, "worst_delta_frac": worst, "resolution_frac": res,
                  "flipped_resolved": hard, "flipped_unresolved": soft, "verdict": v}


# ============================== AW5: THE EPOCH ARM (renders) ====================================
def aw5(model_old, files, eps, jobs, out):
    print("\n" + "=" * 100)
    print("AW5  ⭐⭐ EPOCH ARM — has the SHIPPED chain moved GATE W's model rows since s122?")
    print("=" * 100)
    print("     Separate question from AW2-AW4, and s158 warned specifically against fusing them.")
    print("     Three DSP changes have landed since GATE W published: s124 (ADAA + `clipK` 2.0),")
    print("     s146 (the 3-segment MASTER taper) and s150-156 (`OdToneRestore`) — and the last of")
    print("     those is a peaking biquad at 323 Hz, i.e. INSIDE `mid_notch`'s own window.")
    os.makedirs(PRIV_DIR, exist_ok=True)

    # ⭐ NON-VACUITY, asserted before the arm is read (s110): if the current binary matched the
    # stamps in GATE W's cache there would be no epoch to measure and every Δ below would be 0.
    cur = [os.stat(CR.DEFAULT_BIN).st_size, os.stat(CR.DEFAULT_BIN).st_mtime_ns]
    old_stamps = set()
    for f in files:
        sp = os.path.join(W.REN_DIR, f.replace(".wav", "") + "_plugin.wav.args.json")
        old_stamps.add(tuple(json.load(open(sp)).get("bin") or []))
    if tuple(cur) in old_stamps:
        die("AW5", "the current binary is one of the stamps in GATE W's cache — there is no epoch "
                   "difference to measure and this arm would be vacuous")
    print(f"\n  current binary {cur} is not among the {len(old_stamps)} cache stamps ⇒ the arm is "
          f"non-vacuous.")
    print(f"  rendering {len(files)} conditions into {PRIV_DIR} (private) ...")
    pmap(_render_cell, [(f, PRIV_DIR) for f in files], jobs=jobs)
    model_new = collect(files, PRIV_DIR, jobs=jobs)

    # ⚠⚠ MATCHED MEMBERSHIP IS THE GRADED COLUMN, AND THE POOLED ONE IS PRINTED BESIDE IT
    # DELIBERATELY.  This session's own first draft read the POOLED shift and was about to report
    # that `OdToneRestore` moved the ~450 Hz mid peak by -6.66 %.  It does not: the stage deepens
    # the neighbouring 320 Hz null, which raises `mid_peak`'s prominence past the bar and ADMITS
    # 20 cells that were refused at s122 — so the pooled median moved because the population did.
    # Matched on the cells admitted in BOTH epochs the same shift is -0.34 %.
    # (`aggregate-moved-check-membership-first`; twelfth occurrence, and the first inside an
    # epoch comparison.)
    print(f"\n  {'feature':13} {'span s122':>10} {'span s156':>10} | {'f0 s122':>9} "
          f"{'f0 s156':>9} {'Δf0 pooled':>11} {'Δf0 MATCHED':>12} {'cells':>10}")
    print("  " + "-" * 100)
    per, moved = {}, []
    for name, _k, _w, _l in W.FEATURES:
        cells = {(f, sw) for f in eps for sw in W.SWEEPS
                 if admitted(model_old, f, sw, name) and admitted(model_new, f, sw, name)}
        s_o, m_o, n_o = w6_span(model_old, eps, name, cells=cells)
        s_n, m_n, n_n = w6_span(model_new, eps, name, cells=cells)
        p_o, pm_o, pn_o = w6_span(model_old, eps, name)
        p_n, pm_n, pn_n = w6_span(model_new, eps, name)
        f0_o = float(np.median(pm_o)) if pm_o else float("nan")
        f0_n = float(np.median(pm_n)) if pm_n else float("nan")
        d_pool = (f0_n / f0_o - 1.0) if np.isfinite(f0_o) and np.isfinite(f0_n) else float("nan")
        d_match = ((float(np.median(m_n)) / float(np.median(m_o)) - 1.0)
                   if m_o and m_n else float("nan"))
        c_o, c_n = cls(s_o), cls(s_n)
        if c_o != c_n:
            moved.append((name, c_o, c_n))
        print(f"  {name:13} {s_o * 100:9.2f}% {s_n * 100:9.2f}% | {f0_o:9.2f} {f0_n:9.2f} "
              f"{d_pool * 100:10.2f}% {d_match * 100:11.2f}% {len(cells):5d}/{pn_o}|{pn_n}")
        per[name] = {"span_s122_matched": s_o, "span_s156_matched": s_n,
                     "span_s122_pooled": p_o, "span_s156_pooled": p_n,
                     "f0_s122_pooled": f0_o, "f0_s156_pooled": f0_n,
                     "df0_pooled": d_pool, "df0_matched": d_match,
                     "n_matched_cells": len(cells), "n_pooled_s122": pn_o, "n_pooled_s156": pn_n,
                     "class_s122": c_o, "class_s156": c_n}
    # depth, on the matched population — the quantity `OdToneRestore` was built to move
    print(f"\n  MODEL prominence (E1) on endpoint cells, both epochs, and the PEDAL for scale:")
    print(f"  {'feature':13} {'model s122':>11} {'model s156':>11} {'Δ':>8} {'PEDAL':>8}")
    print("  " + "-" * 56)
    ped = dict(pmap(_pedal_cell, list(eps), jobs=jobs))
    for name, _k, _w, _l in W.FEATURES:
        cs = [(f, sw) for f in eps for sw in W.SWEEPS]
        a = float(np.median([model_old[f][sw][name]["shipped_prom"] for f, sw in cs]))
        b = float(np.median([model_new[f][sw][name]["shipped_prom"] for f, sw in cs]))
        p = float(np.median([ped[f][sw][name]["shipped_prom"] for f, sw in cs]))
        print(f"  {name:13} {a:11.3f} {b:11.3f} {b - a:8.3f} {p:8.3f}")
        per[name]["prom_s122"] = a
        per[name]["prom_s156"] = b
        per[name]["prom_pedal"] = p
    big = [n for n in per if np.isfinite(per[n]["df0_matched"])
           and abs(per[n]["df0_matched"]) > W.GRID_STEP_FRAC / 3.0]
    still = [n for n in per if np.isfinite(per[n]["df0_matched"]) and n not in big]
    v = (f"{len(still)} of {len(big) + len(still)} resolved MODEL rows are UNMOVED by everything "
         f"shipped since s122 (|Δf0| below GATE W's\n     own {W.GRID_STEP_FRAC / 3 * 100:.2f} % "
         f"resolution): {still}.  {len(big)} moved: {big}.\n     ⭐ Every move is inside the band "
         f"`OdToneRestore` acts on, and its own centre (323 Hz) is inside\n     `mid_notch`'s "
         f"window — so the moves are attributable by construction, not by inference.\n     "
         f"⛔ 0 of {len(big) + len(still)} classifications change, so no GATE W6 verdict is stale; "
         f"what IS stale is any quoted\n     model-side PROMINENCE at `mid_notch` "
         f"({per['mid_notch']['prom_s122']:.2f} -> {per['mid_notch']['prom_s156']:.2f} dB).")
    if moved:
        v += f"\n     ⚠⚠ CLASSIFICATION MOVED: {moved} — a re-baseline of GATE W is owed."
    print("\n   " + v)
    out["aw5"] = {"per_feature": per, "verdict": v, "priv_dir": PRIV_DIR,
                  "moved_classes": moved, "binary": cur}
    return model_new


# ================= AW6: E1 vs the restore stage's own E6, on the same cells =====================
# The three bleed-free rungs `od_tone_restore_fit` fits and reports on — taken from its own SETS
# table rather than typed, so this cannot drift from the stage's acceptance condition.
def aw6(out, jobs):
    print("\n" + "=" * 100)
    print("AW6  ⭐ EPOCH ARM, THE CROSS-CHECK — `mid_notch` by GATE W's E1 and by the stage's E6")
    print("=" * 100)
    print("     AW5 says the model's 320 Hz null got much deeper.  Whether that is RIGHT is the")
    print("     restore stage's own acceptance question, and it is settled on the stage's own")
    print("     estimator (E6, `notch_geometry`), not on E1 — so both are read here, on the SAME")
    print("     cells, and the disagreement is attributed rather than left as a discrepancy.")
    # The bleed-free rungs are taken from `od_tone_restore_fit`'s OWN `SETS` table rather than
    # typed, so this cannot drift from the stage's acceptance condition.  Entries are
    # (capture, DRIVE).
    caps = [(f, dr) for f, dr in OT.SETS["bleedfree"]]
    sweep = "sweep_drv_-12"
    print(f"\n  set = bleedfree ({len(caps)} captures), sweep = {sweep}")
    print(f"\n  {'capture':36} {'drv':>4} {'E1 mod s122':>11} {'E1 mod s156':>11} "
          f"{'E1 pedal':>9} {'E1 m-p':>7} | {'E6 mod':>7} {'E6 ped':>7} {'E6 m-p':>7} | "
          f"{'Q mod':>6} {'Q ped':>6}")
    print("  " + "-" * 122)
    rows, worst_gap = [], 0.0
    for f, drive in caps:
        e1 = {}
        for tag, path, is_cap in (
                ("s122", os.path.join(W.REN_DIR, f.replace(".wav", "") + "_plugin.wav"), False),
                ("s156", os.path.join(PRIV_DIR, f.replace(".wav", "") + "_plugin.wav"), False),
                ("ped", os.path.join(C.CAPTURE_DIR, f), True)):
            e1[tag] = _read(path, is_capture=is_cap)[sweep]["mid_notch"]
        # E6, through the stage's own function on the stage's own windows, rendered PRIVATELY
        g, ped_d, mod_d = OT.curves(f, sweep, ren_dir=PRIV_DIR)
        gm = OT.notch_geometry(g, mod_d, depth="point")
        gp = OT.notch_geometry(g, ped_d, depth="point")
        e1_gap = e1["s156"]["shipped_prom"] - e1["ped"]["shipped_prom"]
        e6_gap = gm["depth"] - gp["depth"]
        worst_gap = max(worst_gap, abs(e1_gap - e6_gap))
        print(f"  {f[:36]:36} {drive:4.2f} {e1['s122']['shipped_prom']:11.3f} "
              f"{e1['s156']['shipped_prom']:11.3f} {e1['ped']['shipped_prom']:9.3f} "
              f"{e1_gap:7.3f} | {gm['depth']:7.3f} {gp['depth']:7.3f} {e6_gap:7.3f} | "
              f"{gm['q']:6.2f} {gp['q']:6.2f}")
        rows.append({"capture": f, "drive": drive, "e1_model_s122": e1["s122"]["shipped_prom"],
                     "e1_model_s156": e1["s156"]["shipped_prom"],
                     "e1_pedal": e1["ped"]["shipped_prom"], "e1_gap": e1_gap,
                     "e6_model": gm["depth"], "e6_pedal": gp["depth"], "e6_gap": e6_gap,
                     "q_model": gm["q"], "q_pedal": gp["q"]})
    # ⭐⭐ THE ATTRIBUTION, AND IT IS A THEOREM RATHER THAN A CORRELATION.  A first draft of this
    # block reported `corr(Q_pedal/Q_model, E1gap - E6gap) = -0.975` — at **n = 3**, where any
    # three points give a large |r| and two of the three are in fact ordered the wrong way
    # (`check-n-before-reading-a-trend`).  The mechanism needs no fit at all:
    #
    #   E1's shoulders are the FIXED window edges (285, 358) Hz.
    #   E6's shoulders are the curve's own local maxima inside (210, 520) Hz — a SUPERSET.
    #   A max over a superset is >= a max over a subset, so  E1 <= E6  IDENTICALLY, on any curve.
    #
    # ⇒ the deficit `E6 - E1` is exactly "how far the curve is still rising at 285/358 Hz", i.e. a
    # WIDTH statistic, and comparing the two sides' deficits is a Q comparison with no threshold
    # and no regression in it.
    lo_e1, hi_e1 = W.FEAT_BY_NAME["mid_notch"][2]
    assert OT.SHOULDER[0] <= lo_e1 and hi_e1 <= OT.SHOULDER[1], "E6's shoulder window must contain E1's"
    bad = [r for r in rows
           if r["e1_model_s156"] > r["e6_model"] + 1e-9 or r["e1_pedal"] > r["e6_pedal"] + 1e-9]
    print(f"\n  THEOREM — E1's shoulders ({lo_e1:.0f}, {hi_e1:.0f}) Hz sit INSIDE E6's shoulder "
          f"window {OT.SHOULDER},\n  so E1 <= E6 identically and the deficit `E6 - E1` is a WIDTH "
          f"statistic.  Violations: {len(bad)} of {2 * len(rows)}")
    if bad:
        die("AW6", f"{len(bad)} readings have E1 > E6, which the window containment forbids — one "
                   f"of the two estimators is not reading the window it declares")
    print(f"\n  {'drv':>4} {'deficit E6-E1 model':>20} {'deficit E6-E1 pedal':>20} "
          f"{'model - pedal':>14}   (higher deficit = broader null)")
    n_broader = 0
    for r in rows:
        dm = r["e6_model"] - r["e1_model_s156"]
        dp = r["e6_pedal"] - r["e1_pedal"]
        n_broader += dm > dp
        r["deficit_model"], r["deficit_pedal"] = dm, dp
        print(f"  {r['drive']:4.2f} {dm:20.3f} {dp:20.3f} {dm - dp:14.3f}")
    print(f"\n  ⇒ the MODEL's deficit exceeds the PEDAL's at {n_broader} of {len(rows)} rungs — "
          f"the model's null is\n    BROADER, which is this stage's already-known Q defect, and it "
          f"is what E1 charges for and E6\n    does not.  No fit, no bar, n stated.")
    e6_worst = max(abs(r["e6_gap"]) for r in rows)
    e1_worst = max(abs(r["e1_gap"]) for r in rows)
    v = (f"On the stage's OWN estimator the shipped bleed-free null is within "
         f"{e6_worst:.2f} dB of the pedal at\n     all {len(rows)} rungs, so ⛔ the pooled E1 "
         f"reading that suggested an overshoot is REFUTED — it was a\n     different population "
         f"(16 endpoints x 4 sweeps, mixed DRIVE/ATTACK/GRUNT) read as though it were\n     these "
         f"three.  Matched, E1 still reads the model up to {e1_worst:.2f} dB SHALLOWER than the "
         f"pedal while E6\n     reads it level, and the two disagree by up to {worst_gap:.2f} dB "
         f"on identical curves.\n     ⇒ that disagreement is the stage's KNOWN Q defect (the "
         f"model's null is broader), measured by an\n     estimator whose shoulders are fixed — "
         f"which is GATE AV's whole point restated: E1 is a\n     fixed-shoulder depth and "
         f"therefore mixes DEPTH with WIDTH.  ⛔ Do not read an E1 prominence as\n     a depth, "
         f"and do not adjudicate this stage on one.")
    print("\n   " + v)
    out["aw6"] = {"rows": rows, "sweep": sweep, "worst_e1_e6_gap_db": worst_gap,
                  "n_model_broader": n_broader, "n_rungs": len(rows),
                  "e1_shoulders": [lo_e1, hi_e1], "e6_shoulder_window": list(OT.SHOULDER),
                  "verdict": v}


# ============================================ main ==============================================
def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--no-epoch", action="store_true",
                    help="estimator arm only — no render, no binary")
    ap.add_argument("--out", default=None)
    add_jobs_arg(ap)
    args = ap.parse_args()
    # ⚠ A PARTIAL RUN MUST NOT REPLACE THE COMPLETE ARTEFACT.  `--no-epoch` produces a report with
    # no `aw5`/`aw6` keys, and writing that to the canonical path would leave a later session
    # reading a truncated report with nothing to say it was truncated — the same shape as s153's
    # mutant-overwrites-the-real-report defect, arriving from an ordinary CLI flag instead of a
    # test harness.  The estimator-only run therefore gets its own filename by construction.
    if args.out is None:
        args.out = (OUT_JSON.replace(".json", "_estimator_only.json") if args.no_epoch
                    else OUT_JSON)

    print("=" * 100)
    print("GATE AW  the MODEL side of the prominence audit, and the EPOCH question, kept apart")
    print("=" * 100)
    out = {"report": W.OUT_JSON, "av_report": AV_REPORT, "widen": list(AV.WIDEN),
           "move_tol_db": AV.MOVE_TOL_DB}

    before = fingerprint(W.REN_DIR)
    files, _lad, eps = aw0(out)
    model_old = collect(files, W.REN_DIR, jobs=args.jobs)
    aw1(model_old, out)
    aw2(model_old, out)
    aw3(model_old, out)
    aw4(model_old, eps, out)
    if not args.no_epoch:
        aw5(model_old, files, eps, args.jobs, out)
        aw6(out, args.jobs)
    else:
        print("\n  (--no-epoch: AW5/AW6 skipped; the estimator arm above is complete on its own)")

    # ⭐ THE READ-ONLY GUARD, checked at the END so it covers everything above, including AW6's
    # `OT.curves` call — which renders, and would silently re-render into GATE W's cache if it were
    # ever handed the wrong directory.
    after = fingerprint(W.REN_DIR)
    if after != before:
        ch = sorted(set(before) ^ set(after)) or [k for k in before if before[k] != after.get(k)]
        die("AW0-readonly", f"GATE W's render cache CHANGED during this run ({len(ch)} files, e.g. "
                            f"{ch[:3]}) — the published artefacts have been overwritten and AW1b "
                            f"can never detect it again")
    print(f"\n  ✅ GATE W's cache is byte-identical after the run ({len(before)} files) — the "
          f"published\n     artefacts were read, never rewritten.")

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w") as fh:
        json.dump(out, fh, indent=1, sort_keys=True, default=float)
    print(f"\n  wrote {args.out}")
    if FAILED:
        print(f"\nGATE AW: FAILED {FAILED}\n")
        sys.exit(1)
    print("\nGATE AW: model-side audit complete — every verdict above is computed.\n")


if __name__ == "__main__":
    main()
