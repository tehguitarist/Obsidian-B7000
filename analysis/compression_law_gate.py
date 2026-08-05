#!/usr/bin/env python3.11
"""GATE S -- the compression law on the interface-SEND axis, and the 320 Hz null measured on it.

Session 113.  NO RENDER: every number is a re-read of a report already on disk
(`analysis/reports/s112_baseline.json`, the current baseline) plus `captures.gain_correction_db`.

WHY THIS EXISTS
---------------
The head item since session 110 (GATE R8) is *"a null whose depth grows with level, at DRIVE MAX"*,
and item 2 of that list is **characterise before fitting** -- GATE P's lesson about fitting a
constant to a quantity whose spread was never printed applies directly, and R8 is n = 5 captures at
ONE drive setting.

Session 112 supplied the resource and did not spend it: session 111's capture batch added a **DRIVE
ladder at `gain-n12`**, i.e. a second interface-send operating point at ALL FIVE DRIVE settings.
That gives a compression law on an axis GATE Q does not share -- GATE Q varies the *sweep's own
level* within one recording; this varies the **interface SEND between two recordings of the same
condition**, so the two share no stimulus, no anchor and no arithmetic.  Session 112 measured the
PEDAL side of it (a 12 dB input drop produces 11.99 ... 7.27 dB of output drop as DRIVE goes min ->
max, i.e. 4.73 dB of compression at DRIVE max) and recorded it as **MEASURED, NOT GATED**, with the
model side unbuilt.  This builds the model side and gates both.

WHAT IS MEASURED
----------------
For a twin pair (full-send capture F, `gain-n12` capture N at identical settings), per band, per
stimulus rung, with NO gain match on either side (`plugin_db - gain_db_applied` against raw
`pedal_db`, session 103's construction, imported from `level_law_gate` so it cannot drift):

    D = out(F) - out(N)          the OUTPUT drop produced by the input drop
    P = the INPUT drop            (pedal: measured, S2.  model: READ from captures, not assumed.)
    slope = D / P                 dOut/dIn over the step -- 1.0 is linear, < 1 is compression
    C     = P - D                 the same thing in dB "eaten by compression", the readable form

Both sides traverse their own whole chain twice and are differenced against themselves, so every
nuisance that is common to a condition -- MASTER, the EQ, the output makeup, the record gain --
cancels exactly.  There is no fit and no free parameter anywhere in this gate.

⚠ THE TWO SIDES DO NOT SEE THE SAME INPUT STEP, AND THAT IS QUANTIFIED, NOT WAVED AWAY.  The harness
pads the MODEL by `captures.gain_correction_db` = 12.071 dB; session 112 measured the pedal's true
send at 12.000 dB on four independent linear twins (span <= 0.0003 dB).  So `C` is computed against
each side's OWN step, and the residual second-order error from the 0.071 dB mismatch is bounded in
S4 by the measured slope itself (it is <= 0.071 * (1 - slope), i.e. <= 0.03 dB at DRIVE max) --
smaller than the effect by two orders of magnitude, but printed rather than assumed.  `slope` is
dimensionless and removes the mismatch to first order, which is why it is the primary statistic.

GATES (all computed; exits non-zero on the gate's own validity, never on how the physics comes out)
---------------------------------------------------------------------------------------------------
S1  membership, ASSERTED.  Exactly five OD DRIVE-ladder pairs; `drive-1200`'s twin must resolve to
    `ref-od.wav` (session 112's finding -- DRIVE noon IS the baseline, so one condition has two
    names, and asserting it means a regression in `find_twin` is caught here); >= 4 CLEAN twins;
    reference dropouts excluded by DETECTION (`matrix_grade.find_dropouts`), never by name.
S2  the two input steps, from the CLEAN twins.  KNOWN ANSWER: the clean path is linear, so both
    drops must be FLAT over the band (a pure gain has no frequency structure -- GATE O6's argument),
    and the MODEL's drop must equal the harness pad READ from `captures.gain_correction_db`.  The
    PEDAL's drop is then the measurement.  `ref-clean` is printed as a LABELLED OUTLIER and excluded
    from the consensus, because it is the pair the harness constant was derived from (s112).
S3  the LADDER INTERLOCK -- a known answer that works on the NONLINEAR path, which S2 cannot do.
    The stimulus rungs are 12 dB apart, so an n12 capture at `drv_-6` and its twin at `drv_-18` put
    the SAME absolute level into the SAME device: their outputs must agree, however nonlinear the
    path is.  At DRIVE min the residual is a direct second read of the send pad.
S4  THE LAW: slope and compression over the DRIVE x stimulus plane, both sides, with the
    across-band spread printed beside every mean (s108 P4) and the step-mismatch bound computed.
S5  offset vs shape, against GATE K5's own 0.25 bar -- is the error a level error or a shape error?
S6  OUT OF SAMPLE: the non-ladder OD twins (the LEVEL ladder at `gain-n12`, `ref-od`, and the
    DRIVE-max grunt-boost twin) must reproduce the law at their own DRIVE.  Different LEVEL, GRUNT
    and stimulus, so this is corroboration, not a re-read.
S7  THE HEAD ITEM, on an axis GATE R does not share: the 320 Hz null's prominence, referred to its
    own 202/508 Hz shoulders, measured at BOTH sends.  GATE R found the pedal's null DEEPENS with
    level at DRIVE max while the model's WASHES OUT.  If that is a real property of the devices and
    not of the sweep-level axis, the SEND axis must reproduce the sign split.

Usage:
    /opt/homebrew/bin/python3.11 analysis/compression_law_gate.py analysis/reports/s112_baseline.json
"""
from __future__ import annotations

import argparse
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import captures as CAP                 # noqa: E402  the harness pad, READ not assumed
import matrix_grade as MG              # noqa: E402
import level_law_gate as K             # noqa: E402  absolute_fr / HF_HZ -- one definition
import gain_session_gate as N          # noqa: E402  find_twin -- settings-based, s112
import od_absolute_gate as Q           # noqa: E402  STIM_DB, itself read from gen_test_signal

SWEEPS = ("sweep_clean", "sweep_drv_-18", "sweep_drv_-12", "sweep_drv_-6")

# The null and the two shoulders GATE Q/R refer it to.  NAMED, so that a candidate which MOVES the
# null cannot silently re-point the statistic (GATE R4's argmin trap).
REF_OD = "ref-od.wav"   # DRIVE noon IS the reference baseline (s112) -- named once

NULL_HZ, SHOULDER_HZ = 320.0, (201.6, 508.0)

# The rung pairs 12 dB apart -- the only ones where an n12 capture and its twin present the same
# absolute level.  S3 asserts the spacing against gen_test_signal rather than trusting the names.
INTERLOCKS = (("sweep_drv_-6", "sweep_drv_-18"), ("sweep_drv_-18", "sweep_clean"))

FLAT_TOL_DB = 0.01      # a pure gain's across-band spread.  s112 measured 0.0003 on four pairs.
PAD_TOL_DB = 1e-3       # the model-side pad is deterministic; s112 measured it to 1.8e-8.
CONSENSUS_TOL_DB = 0.01  # how tightly the clean twins must agree before the pad is "measured"
SHAPE_BAR = 0.25        # GATE K5's own offset-dominated bar, reused so the verdicts are comparable


# --------------------------------------------------------------------------------------------
# pairing
# --------------------------------------------------------------------------------------------
def twin_pairs(caps):
    """-> [(n12_file, full_file)] for every `gain-n12` capture with a resolvable twin.

    `find_twin` is imported rather than re-implemented: it tries the name transform first (so every
    pre-s112 pairing resolves identically) and falls back to matching SETTINGS apart from the send,
    hard-failing on an ambiguous match.  Re-deriving it here would let the two drift."""
    out = []
    for f in sorted(caps):
        if not MG.is_gain_n12(f):
            continue
        t = N.find_twin(f, caps)
        if t is not None:
            out.append((f, t))
    return out


def dedupe_ladder(ladder):
    """-> (one pair per DRIVE detent, [(detent, kept, discarded)]).

    DRIVE noon has TWO `gain-n12` recordings -- `drive-1200_gain-n12_base-od.wav` and
    `ref-od_gain-n12.wav` -- because DRIVE noon IS the reference baseline, so the condition has two
    legitimate names and session 111 captured it under both (session 112 identified them as two
    takes of one condition, four days apart, agreeing to 0.010 dB).  Grading both would weight that
    detent twice, which is `aggregate-moved-check-membership-first` in its cheapest form.

    Kept deterministically by name so the choice cannot drift between runs; every discarded
    alternative is PRINTED and then used as a take-to-take control in S1b, never silently dropped."""
    by_detent, dupes = {}, []
    for d, n, f in ladder:
        if d in by_detent:
            keep = min(by_detent[d][0], n)
            drop = max(by_detent[d][0], n)
            dupes.append((d, keep, drop))
            by_detent[d] = (keep, f)
        else:
            by_detent[d] = (n, f)
    return [(d, n, f) for d, (n, f) in sorted(by_detent.items())], dupes


def gate_s1b(absfr, dupes, caps, drops, sel, out):
    """The discarded duplicates are a free take-to-take control: two recordings of ONE condition
    must agree.  This re-measures session 112's 0.010 dB through a different code path, and it
    bounds how much of anything below could be recording repeatability."""
    if not dupes:
        print("   (no duplicate detents -- the take-to-take control did not run)")
        out["s1b"] = None
        return
    worst = 0.0
    for d, keep, drop in dupes:
        vals = []
        for sw in SWEEPS:
            if (keep, sw) not in absfr or (drop, sw) not in absfr:
                continue
            if (keep, sw) in drops or (drop, sw) in drops:
                continue
            _, qa = absfr[(keep, sw)]
            _, qb = absfr[(drop, sw)]
            vals.append(float(np.mean(qa[sel] - qb[sel])))
        if not vals:
            sys.exit(f"GATE S1 FAIL: duplicate detent {d} has no comparable rung -- the "
                     f"take-to-take control cannot run, so the choice of take is unjustified")
        w = max(abs(v) for v in vals)
        worst = max(worst, w)
        print(f"   take-to-take at DRIVE {d}: kept {keep}, discarded {drop} "
              f"-> reference sides agree to {w:.4f} dB over {len(vals)} rungs")
    print(f"   => recording repeatability <= {worst:.4f} dB; anything below that size in this "
          f"gate is not a measurement.")
    out["s1b"] = {"worst_db": worst,
                  "dupes": [{"drive": d, "kept": k, "discarded": x} for d, k, x in dupes]}


def usable(absfr, drops, n12, full, sweep):
    """A rung is usable only when BOTH members are present and NEITHER is a detected dropout."""
    for f in (n12, full):
        if (f, sweep) not in absfr or (f, sweep) in drops:
            return False
    return True


def step(absfr, n12, full, sweep, sel):
    """-> (model_drop, pedal_drop) per selected band: the OUTPUT drop the send drop produced."""
    mN, qN = absfr[(n12, sweep)]
    mF, qF = absfr[(full, sweep)]
    return (mF[sel] - mN[sel]), (qF[sel] - qN[sel])


def _fmt(v, s):
    return f"{v:+7.3f} +-{s:5.3f}"


# --------------------------------------------------------------------------------------------
# S1 -- membership
# --------------------------------------------------------------------------------------------
def gate_s1(bands, caps, absfr, sel, out):
    print("-- S1: membership, asserted --")
    pairs = twin_pairs(caps)
    if not pairs:
        sys.exit("GATE S1 FAIL: no `gain-n12` capture resolved a twin -- the pairing found "
                 "nothing, which is `empty-gate-must-fail` in a costume, not a clean result")

    od = [(n, f) for n, f in pairs if MG.is_od(n)]
    cl = [(n, f) for n, f in pairs if not MG.is_od(n)]

    # The DRIVE ladder: OD pairs differing from the REFERENCE capture in nothing but DRIVE.
    # The reference settings are READ from `ref-od.wav`, not transcribed -- a hardcoded switch
    # index is exactly the kind of literal that goes stale silently (`rebuild-targets-dont-
    # transcribe`), and the first draft of this filter selected zero pairs for that reason.
    if REF_OD not in caps:
        sys.exit("GATE S1 FAIL: ref-od.wav absent -- it defines the ladder's shared settings "
                 "and is DRIVE noon's own twin")
    ref = {k: v for k, v in caps[REF_OD]["settings"].items()
           if k not in ("drive", "gainSessionDb")}
    ladder = []
    for n, f in od:
        s = caps[n]["settings"]
        if {k: v for k, v in s.items() if k not in ("drive", "gainSessionDb")} == ref:
            ladder.append((float(s["drive"]), n, f))
    ladder.sort()
    if len({d for d, _, _ in ladder}) != 5:
        sys.exit(f"GATE S1 FAIL: the DRIVE ladder at `gain-n12` covers "
                 f"{sorted({d for d, _, _ in ladder})}, not five detents -- session 111 captured "
                 f"five, so either a capture is missing or the settings filter no longer selects "
                 f"them")
    ladder, dupes = dedupe_ladder(ladder)
    drives = [d for d, _, _ in ladder]

    # s112's own finding, asserted: DRIVE noon has two legitimate names.  If `find_twin` ever
    # regresses to a pure name transform this is where it is caught, not three sub-gates later.
    noon = [(n, f) for d, n, f in ladder if abs(d - 0.5) < 1e-9]
    if not noon or noon[0][1] != REF_OD:
        sys.exit(f"GATE S1 FAIL: DRIVE noon's twin resolved to {noon and noon[0][1]!r}, not "
                 f"{REF_OD!r} -- session 112 established that DRIVE noon IS the reference "
                 f"baseline, so this pairing is a known answer, not an incidental")

    if len(cl) < 4:
        sys.exit(f"GATE S1 FAIL: only {len(cl)} CLEAN twins -- S2 needs the linear known answer, "
                 f"and session 111 captured four EQ pairs plus the ladder")

    drops, sags, gap = MG.find_dropouts(bands, caps)
    warn = MG.check_dropout_separation(gap, drops)
    touched = sorted(k for k in drops if any(k[0] in (n, f) for n, f in pairs))

    print(f"   {len(pairs)} twin pairs: {len(od)} OD, {len(cl)} CLEAN")
    print(f"   DRIVE ladder at `gain-n12`: {len(ladder)} pairs, drives {drives}")
    print(f"   DRIVE noon twin = {REF_OD}  (asserted -- s112: one condition, two names)")
    print(f"   reference dropouts detected: {len(drops)} cell(s), separation {gap:.2f} dB; "
          f"{len(touched)} touch a twin pair" + (f"  [{touched}]" if touched else ""))
    if warn:
        print(f"   ⚠ {warn}")
    out["s1"] = {"pairs": len(pairs), "od": len(od), "clean": len(cl), "drives": drives,
                 "dropouts": len(drops), "gap": gap, "dropouts_touching_pairs": touched}
    gate_s1b(absfr, dupes, caps, drops, sel, out)
    return ladder, od, cl, drops


# --------------------------------------------------------------------------------------------
# S2 -- the two input steps, from the linear path
# --------------------------------------------------------------------------------------------
def gate_s2(absfr, caps, cl, drops, sel, out):
    """KNOWN ANSWER on the model side; MEASUREMENT on the pedal side.

    The clean path is linear, so old-minus-new must be a PURE GAIN -- flat in frequency (GATE O6's
    argument, which is what makes 'flat' a requirement rather than a hope) and equal to the send.
    The model's send is the harness pad and is READ from `captures`, so a drift in that constant
    fails here instead of silently re-scaling every number below."""
    print("-- S2: the two input steps, from the CLEAN twins (linear path = known answer) --")

    pad_model = None
    rows = []
    for n12, full in cl:
        parsed = CAP.parse_capture(n12)
        want = CAP.gain_correction_db(parsed)
        pad_model = want if pad_model is None else pad_model
        if abs(want - pad_model) > 1e-12:
            sys.exit(f"GATE S2 FAIL: two different harness pads among the clean twins "
                     f"({pad_model} vs {want}) -- the model side has no single step")
        for sw in SWEEPS:
            if not usable(absfr, drops, n12, full, sw):
                continue
            dm, dq = step(absfr, n12, full, sw, sel)
            rows.append((n12, sw, float(dm.mean()), float(dm.std()),
                         float(dq.mean()), float(dq.std())))

    if not rows:
        sys.exit("GATE S2 FAIL: no usable CLEAN twin rung -- the known answer never ran")

    # -- model side: the known answer.  Must equal the harness pad, and must be flat.
    worst_val = max(abs(r[2] - pad_model) for r in rows)
    worst_flat = max(r[3] for r in rows)
    if worst_val > PAD_TOL_DB or worst_flat > FLAT_TOL_DB:
        sys.exit(f"GATE S2 FAIL: the MODEL's clean-path drop is not the harness pad "
                 f"({pad_model:.4f} dB): worst |err| {worst_val:.4f} dB, worst across-band spread "
                 f"{worst_flat:.4f} dB.  A linear path rendered at a fixed input trim must "
                 f"reproduce that trim exactly at every band")
    print(f"   MODEL  pad READ from captures = {pad_model:.4f} dB -> reproduced to "
          f"{worst_val:.2e} dB, across-band spread <= {worst_flat:.2e}   [KNOWN ANSWER OK]")

    # -- pedal side: the measurement.
    # ⭐ THE ADMISSIBILITY CRITERION IS PHYSICS, NOT A NAME.  The clean path is linear, so
    # full-minus-n12 is a PURE GAIN and is FORBIDDEN to have frequency structure (GATE O6).  A pair
    # whose drop is not flat is therefore contaminated on its own evidence, and is excluded by that
    # measurement rather than by a hardcoded token -- which means this rediscovers session 112's
    # `ref-clean` finding instead of assuming it, and would catch a NEW contaminated pair too.
    per_file = {}
    for r in rows:
        per_file.setdefault(r[0], []).append(r)
    flat, rough = {}, {}
    for f, rs in per_file.items():
        (flat if max(x[5] for x in rs) <= FLAT_TOL_DB else rough)[f] = rs

    print(f"   PEDAL  {len(rows)} rungs over {len(per_file)} clean twins "
          f"(admissible = across-band span <= {FLAT_TOL_DB} dB, i.e. actually a pure gain):")
    for f, rs in sorted(flat.items()):
        print(f"      {f:52s} {np.mean([x[4] for x in rs]):8.4f} dB   span "
              f"{max(x[5] for x in rs):.4f}   ADMISSIBLE")
    for f, rs in sorted(rough.items()):
        twin = next(t for n, t in cl if n == f)
        print(f"      {f:52s} {np.mean([x[4] for x in rs]):8.4f} dB   span "
              f"{max(x[5] for x in rs):.4f}   ⛔ REJECTED -- a linear path's send difference cannot "
              f"have frequency structure")
        print(f"      {'':52s} (its full-send member is {twin})")
    if rough:
        shared = {next(t for n, t in cl if n == f) for f in rough}
        print(f"      => every rejected pair shares the full-send capture(s) {sorted(shared)}, "
              f"which localises the contamination to that side.")

    good = [r for rs in flat.values() for r in rs]
    if not good:
        sys.exit("GATE S2 FAIL: no clean twin passed the flatness requirement -- the send is "
                 "unmeasured and every number below would be scaled by a guess")
    vals = [r[4] for r in good]
    spans = [r[5] for r in good]
    pad_pedal = float(np.mean(vals))
    spread = float(max(vals) - min(vals))

    if len(flat) < 4:
        sys.exit(f"GATE S2 FAIL: only {len(flat)} clean twins are admissible -- a send measured "
                 f"from fewer than four independent pairs is the single-source trap session 112 "
                 f"paid for (`captures.py`'s 12.071 came from ONE pair)")
    if spread > CONSENSUS_TOL_DB or max(spans) > FLAT_TOL_DB:
        sys.exit(f"GATE S2 FAIL: the pedal's send is not determined -- the clean twins spread "
                 f"{spread:.4f} dB and the worst across-band span is {max(spans):.4f} dB.  Without "
                 f"a determined step there is no denominator for the compression law")
    print(f"   PEDAL  send = {pad_pedal:.4f} dB   from {len(flat)} independent pairs "
          f"(consensus spread {spread:.4f}, worst across-band span {max(spans):.4f})   [MEASURED]")
    print(f"   => the two steps differ by {pad_model - pad_pedal:+.4f} dB; S4 bounds what that "
          f"costs.\n")

    out["s2"] = {"pad_model": pad_model, "pad_pedal": pad_pedal,
                 "model_known_answer_err": worst_val, "consensus_spread": spread,
                 "n_admissible": len(flat), "admissible": sorted(flat),
                 "rejected": {f: {"pedal": float(np.mean([x[4] for x in rs])),
                                  "span": float(max(x[5] for x in rs))}
                              for f, rs in rough.items()}}
    return pad_model, pad_pedal


# --------------------------------------------------------------------------------------------
# S3 -- the ladder interlock (works on the NONLINEAR path)
# --------------------------------------------------------------------------------------------
def interlock(absfr, n12, full, sel, drops):
    """-> (worst |pedal residual|, [(hi, lo, model, pedal)]) over the 12 dB rung interlocks."""
    rows = []
    for hi, lo in INTERLOCKS:
        if not (usable(absfr, drops, n12, full, hi) and usable(absfr, drops, n12, full, lo)):
            continue
        mA, qA = absfr[(n12, hi)]
        mB, qB = absfr[(full, lo)]
        rows.append((hi, lo, float(np.mean(mA[sel] - mB[sel])), float(np.mean(qA[sel] - qB[sel]))))
    worst = max((abs(r[3]) for r in rows), default=None)
    return worst, rows


def gate_s3(absfr, od, ladder, drops, sel, pad_model, pad_pedal, take_to_take, out):
    """THE LADDER INTERLOCK -- a known answer that survives the nonlinearity, and a condition-match
    test the compression law cannot do without.

    The stimulus rungs are 12 dB apart and the send is ~12 dB, so an n12 capture at `drv_-6` and its
    full-send twin at `drv_-18` present the SAME absolute level to the SAME device.  Their outputs
    must then agree -- WHATEVER the path does.  No linearity is assumed anywhere, which is why this
    reaches the OD path where S2's clean-path argument cannot.

    Two things fall out, and the second was not anticipated:

      (a) MODEL side, a hard known answer with no free parameter.  The harness pads the model by
          `pad_model` while the ladder step is exactly `pad_pedal`, so the model's n12 rung sits
          (pad_model - pad_pedal) dB QUIETER than its twin's lower rung and the residual must be
          -(pad_model - pad_pedal) x slope.  At DRIVE min the slope is 1, so it must read -0.071.

      (b) PEDAL side: a residual IS a CONDITION MISMATCH.  Both files are the same device at the
          same absolute level, so anything non-zero means the two recordings are not the same
          condition -- in practice a knob re-dialled between capture sessions (s112 bounded that at
          <= 1.6 dB and could not say which settings it hits).  A pair with a non-zero interlock has
          an `out(F) - out(N)` that mixes the send step with a knob step, and no averaging removes
          it, so it cannot vote on the compression law."""
    print("-- S3: the ladder interlock -- a known answer that survives the nonlinearity --")
    got = [Q.STIM_DB[a] - Q.STIM_DB[b] for a, b in INTERLOCKS]
    if any(abs(g - pad_pedal) > 0.05 for g in got):
        sys.exit(f"GATE S3 FAIL: the chosen rung pairs are {got} dB apart but the measured send is "
                 f"{pad_pedal:.4f} dB -- the interlock only exists where the two match")

    # -- (a) the model-side known answer, at DRIVE min where the slope is 1 by construction.
    lo_pair = [(d, n, f) for d, n, f in ladder if abs(d) < 1e-9]
    if not lo_pair:
        sys.exit("GATE S3 FAIL: no DRIVE-min ladder pair -- that is the rung where the model-side "
                 "known answer is exact, and without it nothing below is calibrated")
    _, lo_rows = interlock(absfr, lo_pair[0][1], lo_pair[0][2], sel, drops)
    want = -(pad_model - pad_pedal)
    err = max(abs(r[2] - want) for r in lo_rows)
    if err > 0.01:
        sys.exit(f"GATE S3 FAIL: at DRIVE min the model's interlock reads "
                 f"{[round(r[2], 4) for r in lo_rows]}, not the predicted {want:+.4f} dB (worst "
                 f"error {err:.4f}).  That prediction has no free parameter -- it is the harness "
                 f"pad minus the ladder step -- so a miss means the absolute reconstruction, the "
                 f"pad, or the rung mapping is wrong")
    print(f"   (a) MODEL known answer, no free parameter: the harness pad exceeds the ladder step "
          f"by {pad_model - pad_pedal:+.4f} dB,")
    print(f"       so at DRIVE min (slope 1) the residual MUST be {want:+.4f}.  Measured "
          f"{[round(r[2], 4) for r in lo_rows]} -> {err:.4f} dB.   [OK]\n")

    # -- (b) classify EVERY OD pair, not just the ladder: S6/S7 need the same test.
    per, detail, silent = {}, {}, []
    for n12, full in od:
        # A pair where either side is SILENT cannot be interlocked: at LEVEL 0 the MODEL mutes
        # (GATE L7), so the residual is a difference of two floors and reads as a spectacular
        # "mismatch" that is really an absent measurement.  `empty-gate-must-fail` in disguise.
        if any(max(absfr[(f, sw)][i]) < MG.SILENT_DB
               for f in (n12, full) for sw in SWEEPS if (f, sw) in absfr for i in (0, 1)):
            silent.append(n12)
            continue
        w, rows = interlock(absfr, n12, full, sel, drops)
        if w is None:
            continue
        per[n12] = w
        detail[n12] = rows
    if not per:
        sys.exit("GATE S3 FAIL: no OD pair produced an interlock -- the only condition-match test "
                 "available never ran")

    # ⭐ THE BAR IS A MEASURED FLOOR, NOT A GAP-HUNT.  S1b measured recording repeatability from two
    # takes of ONE condition (`drive-1200_gain-n12` vs `ref-od_gain-n12`); a residual at or below
    # that is indistinguishable from re-recording the same thing, and anything above it is a real
    # condition difference.  An earlier draft picked the largest ratio in the sorted residuals
    # instead -- but "the biggest single step" is satisfied by ANY population with one jump in it,
    # so it is not a bimodality test, and it duly classified a 0.009 dB pair (BELOW the measured
    # repeatability floor) as mis-dialled.  A threshold has to come from a quantity measured
    # independently of the thing being classified.
    bar = max(take_to_take, 1e-4)
    matched = {f for f, v in per.items() if v <= bar}
    near = [f for f, v in per.items() if bar / 3.0 <= v <= bar * 3.0]

    print(f"   (b) PEDAL side: a non-zero residual is a CONDITION MISMATCH -- same device, same "
          f"absolute level, so it cannot be the physics.")
    print(f"       bar = {bar:.5f} dB, S1b's MEASURED take-to-take repeatability (two takes of one "
          f"condition), not a chosen number.\n")
    for f in sorted(per, key=lambda x: per[x]):
        tag = "MATCHED" if f in matched else "⛔ MIS-DIALLED"
        print(f"       {f:54s} {per[f]:9.5f} dB   {tag}")
    for f in silent:
        print(f"       {f:54s} {'--':>9}     [SILENT on one side -- GATE L7's LEVEL-min mute; "
              f"not classifiable, not counted]")
    if near:
        print(f"\n       ⚠ {len(near)} pair(s) sit within 3x of the bar ({', '.join(sorted(near))}) "
              f"-- their classification is not robust and should not carry a verdict alone.")
    else:
        worst_m = max((per[f] for f in matched), default=0.0)
        best_x = min((v for f, v in per.items() if f not in matched), default=float("inf"))
        print(f"\n       separation: worst MATCHED {worst_m:.5f} vs mildest MIS-DIALLED "
              f"{best_x:.5f} -- a {best_x / max(worst_m, 1e-12):.0f}x gap, so the bar's exact "
              f"value does not change the classification.")

    lad_ok = sorted(d for d, n, _ in ladder if n in matched)
    lad_bad = sorted(d for d, n, _ in ladder if n not in matched)
    print(f"\n   DRIVE ladder: MATCHED at {lad_ok}, MIS-DIALLED at {lad_bad}")
    print(f"   => the knob reproduced EXACTLY where the pot has a mechanical reference (both hard "
          f"stops and the centre detent) and NOT at the intermediate clock positions.  This is "
          f"session 112's re-dialling error localised to the settings it actually hits, measured "
          f"with no model involved and no fit.")
    print(f"   ⛔ Mis-dialled pairs stay PRINTED everywhere below and vote NOWHERE (s40: excluded, "
          f"never silent).\n")

    out["s3"] = {"model_known_answer": {"predicted": want, "worst_err": err},
                 "bar": bar, "bar_source": "S1b measured take-to-take", "silent": silent,
                 "near_bar": near,
                 "residuals": {f: v for f, v in sorted(per.items())},
                 "matched": sorted(matched), "misdialled": sorted(set(per) - matched),
                 "ladder_matched": lad_ok, "ladder_misdialled": lad_bad}
    return matched


# --------------------------------------------------------------------------------------------
# S4 -- THE LAW
# --------------------------------------------------------------------------------------------
def law_cell(absfr, n12, full, sweep, sel, pad_model, pad_pedal, drops):
    if not usable(absfr, drops, n12, full, sweep):
        return None
    dm, dq = step(absfr, n12, full, sweep, sel)
    return {"slope_m": dm / pad_model, "slope_q": dq / pad_pedal,
            "comp_m": pad_model - dm, "comp_q": pad_pedal - dq}


def gate_s4(absfr, ladder, drops, sel, pad_model, pad_pedal, matched, out):
    print("-- S4: THE LAW -- compression over the DRIVE x stimulus plane, both sides --")
    print("   slope = dOut/dIn over the send step (1.000 = linear).  comp = dB eaten, = (1-slope)*step.")
    print("   Every mean carries its across-band spread (s108 P4: a pooled mean hides the spread "
          "that bounds any constant fitted to it).\n")

    mdrv = {d for d, n, _ in ladder if n in matched}
    tab = {}
    print(f"   {'DRIVE':>6} {'stimulus':>14}  {'slope MODEL':>18} {'slope PEDAL':>18}"
          f"  {'comp M':>7} {'comp Q':>7}  {'M-Q':>7}")
    for drv, n12, full in ladder:
        for sw in SWEEPS:
            c = law_cell(absfr, n12, full, sw, sel, pad_model, pad_pedal, drops)
            if c is None:
                print(f"   {drv:6.2f} {sw:>14s}   -- dropped (reference dropout or absent row) --")
                continue
            sm, sq = c["slope_m"], c["slope_q"]
            cm, cq = float(c["comp_m"].mean()), float(c["comp_q"].mean())
            tab[(drv, sw)] = {"slope_m": float(sm.mean()), "slope_m_sd": float(sm.std()),
                              "slope_q": float(sq.mean()), "slope_q_sd": float(sq.std()),
                              "comp_m": cm, "comp_q": cq, "err": cm - cq,
                              "err_sd": float((c["comp_m"] - c["comp_q"]).std())}
            flag = "" if n12 in matched else "  ⛔ MIS-DIALLED (S3b) -- not a compression reading"
            print(f"   {drv:6.2f} {sw:>14s}  {_fmt(sm.mean(), sm.std()):>18}"
                  f" {_fmt(sq.mean(), sq.std()):>18}  {cm:7.3f} {cq:7.3f} "
                  f" {cm - cq:+7.3f}{flag}")
        print()

    # ⛔ EVERY VERDICT BELOW IS COMPUTED ON THE MATCHED DETENTS ONLY.  The mis-dialled cells stay
    # printed above (`excluded, never silent`, s40) but cannot vote: their `out(F) - out(N)` is a
    # send step plus an unknown DRIVE step, so including them would put a knob-repositioning error
    # into a quantity the next session is meant to fit against.
    good = {k: v for k, v in tab.items() if k[0] in mdrv}
    if not good:
        sys.exit("GATE S4 FAIL: no matched-detent cell survived -- the law would be quoted "
                 "entirely from condition-mismatched pairs")

    # The step-mismatch bound, computed rather than asserted.
    worst_slope = min(min(v["slope_m"], v["slope_q"]) for v in good.values())
    bound = abs(pad_model - pad_pedal) * (1.0 - worst_slope)
    biggest = max(abs(v["err"]) for v in good.values())
    print(f"   step-mismatch bound: the two sides' input steps differ by "
          f"{abs(pad_model - pad_pedal):.4f} dB and the deepest compression is slope "
          f"{worst_slope:.3f}, so at most {bound:.4f} dB of any cell above is the mismatch")
    print(f"   largest |model - pedal| in the plane: {biggest:.3f} dB  "
          f"=> the mismatch is {biggest / max(bound, 1e-9):.0f}x smaller than the effect\n")

    if bound > 0.5 * biggest:
        sys.exit(f"GATE S4 FAIL: the step mismatch ({bound:.4f} dB) is not small against the "
                 f"largest measured effect ({biggest:.3f} dB) -- the two sides cannot be compared "
                 f"until the send pads are reconciled")

    # A designed monotone axis is a free validity check: on BOTH sides, compression must not
    # DECREASE as DRIVE rises at the hottest stimulus.  This is a property of the control, and it
    # breaks loudly on a mis-paired twin.
    print(f"   [verdicts below use the {len(mdrv)} MATCHED detents {sorted(mdrv)} only; "
          f"the mis-dialled rows above are shown, not counted]\n")
    hot = [(d, good[(d, "sweep_drv_-6")]) for d, _, _ in ladder if (d, "sweep_drv_-6") in good]
    for side, key in (("PEDAL", "comp_q"), ("MODEL", "comp_m")):
        seq = [v[key] for _, v in hot]
        drops_ = [(a, b) for a, b in zip(seq, seq[1:]) if b < a - 0.5]
        flag = "monotone" if not drops_ else f"NOT monotone ({len(drops_)} reversal(s))"
        print(f"   {side} compression vs DRIVE at the hottest stimulus: "
              f"{' -> '.join(f'{v:.2f}' for v in seq)}   [{flag}]")
    print()
    out["s4"] = {f"{d}|{s}": dict(v, matched=(d in mdrv)) for (d, s), v in tab.items()}
    out["s4_bound"] = {"mismatch_db": abs(pad_model - pad_pedal), "worst_slope": worst_slope,
                       "bound": bound, "biggest_effect": biggest}
    return tab


# --------------------------------------------------------------------------------------------
# S5 -- offset or shape
# --------------------------------------------------------------------------------------------
def gate_s5(absfr, ladder, drops, sel, fb, pad_model, pad_pedal, matched, out):
    print("-- S5: is the compression error an OFFSET or a SHAPE? --")
    print(f"   Scored against GATE K5's own bar: shape/offset <= {SHAPE_BAR} is 'a level error'.")
    print(f"   Matched detents only ({sorted(d for d, n, _ in ladder if n in matched)}).\n")
    res = {}
    for drv, n12, full in ladder:
        if n12 not in matched:
            continue
        for sw in ("sweep_clean", "sweep_drv_-6"):
            c = law_cell(absfr, n12, full, sw, sel, pad_model, pad_pedal, drops)
            if c is None:
                continue
            e = c["comp_m"] - c["comp_q"]
            off = float(np.mean(e))
            shape = float(np.sqrt(np.mean((e - off) ** 2)))
            ratio = shape / abs(off) if abs(off) > 1e-9 else float("inf")
            peak = float(fb[int(np.argmax(np.abs(e - off)))])
            res[(drv, sw)] = (off, shape, ratio, peak)
            print(f"   DRIVE {drv:4.2f} {sw:>14s}   offset {off:+7.3f}   shape rms {shape:6.3f}   "
                  f"ratio {ratio:5.2f}   {'LEVEL' if ratio <= SHAPE_BAR else 'SHAPE'}"
                  f"   (largest deviation at {peak:.0f} Hz)")
    if not res:
        sys.exit("GATE S5 FAIL: no cell survived -- the decomposition never ran")
    worst = max(r[2] for r in res.values())
    print(f"\n   worst ratio over the plane: {worst:.2f}   => the compression error is "
          f"{'offset-dominated everywhere' if worst <= SHAPE_BAR else 'NOT a pure level error'}\n")
    out["s5"] = {f"{d}|{s}": {"offset": o, "shape": sh, "ratio": r, "peak_hz": p}
                 for (d, s), (o, sh, r, p) in res.items()}


# --------------------------------------------------------------------------------------------
# S6 -- the bleed dilutes the law, and the DRIVE ladder is NOT bleed-free
# --------------------------------------------------------------------------------------------
def clean_fraction(caps, f):
    """The clean tap's share of the output at this capture's BLEND/LEVEL, from the SHIPPED stage's
    own closed form (GATE K2, imported -- not re-derived here, so the two cannot drift).

    ⚠ `coef_closed` takes the TAPERED level, and a capture's settings store the KNOB position.  The
    taper must be applied first or every coefficient is wrong: at LEVEL noon the untapered call
    returns clean/OD = -6.02 dB where the shipped stage actually delivers -2.05 (K2's own recorded
    table), because 0.5 ** 2.25 = 0.21, not 0.5.  The exponent comes from `level_law_gate`, which
    checks it against `FitParams.h` rather than trusting the transcription."""
    st = caps[f]["settings"]
    L = K.level_taper(float(st["level"]))
    od, cl = K.coef_closed(float(st["blend"]), L)
    return cl / (od + cl) if (od + cl) > 0 else 1.0


def gate_s6(absfr, caps, od, ladder, drops, sel, pad_model, pad_pedal, tab, matched, out):
    """⛔ THE DRIVE LADDER IS NOT BLEED-FREE, AND THAT CHANGES WHAT S4 MEASURED.

    Every ladder capture sits at LEVEL noon / BLEND max, where GATE K2 puts the clean tap only
    2.05 dB below the OD path -- so roughly a fifth of the output is clean signal.  The clean path
    does not compress (it is a unity buffer to the BLEND pin), so it DILUTES the compression: what
    S4 measured is the MIXED OUTPUT's law, not the OD path's.

    The matrix does hold bleed-free twins -- LEVEL max x BLEND max, where K2's clean coefficient is
    EXACTLY zero -- and those are the ones that read the OD path directly.  This sub-gate sorts
    every OD twin by its clean fraction and shows the law against it.

    ⚠ THIS IS NOT AN 'OUT OF SAMPLE MUST REPRODUCE' TEST, AND AN EARLIER DRAFT WRONGLY SCORED IT AS
    ONE.  Captures at a different LEVEL are at a different MIX, so they are not expected to
    reproduce the ladder and a departure is not a failure -- it is the dilution being measured."""
    print("-- S6: the bleed dilutes the law -- the DRIVE ladder is NOT bleed-free --")
    rows = []
    for n12, full in od:
        cf = clean_fraction(caps, n12)
        st = caps[n12]["settings"]
        for sw in ("sweep_clean", "sweep_drv_-6"):
            c = law_cell(absfr, n12, full, sw, sel, pad_model, pad_pedal, drops)
            if c is None:
                continue
            # A row where either side is SILENT is not a measurement: at LEVEL 0 the model mutes
            # (GATE L7), so `out(F) - out(N)` is a difference of two floors and reads as a
            # spectacular full-pad "compression".  `empty-gate-must-fail` in numeric disguise.
            if any(max(absfr[(f, sw)][i]) < MG.SILENT_DB for f in (n12, full) for i in (0, 1)):
                continue
            rows.append((cf, float(st["drive"]), n12, sw,
                         float(c["comp_m"].mean()), float(c["comp_q"].mean()),
                         n12 in matched))
    if not rows:
        sys.exit("GATE S6 FAIL: no non-silent OD twin row survived -- the dilution check never ran")

    bleedfree = [r for r in rows if r[0] < 1e-12]
    if not bleedfree:
        sys.exit("GATE S6 FAIL: no bleed-free OD twin (K2 clean coefficient exactly 0) -- the OD "
                 "path's own compression law cannot be read at all, only the mixed output's")

    print(f"   clean fraction from the SHIPPED LevelBlend closed form (GATE K2), with the LEVEL")
    print(f"   the shipped 4-segment taper (L(0.5) = {K.level_taper(0.5):.4f}) applied first -- both READ from the source, "
          f"not assumed:\n")
    print(f"   {'clean%':>7} {'DRIVE':>6} {'stimulus':>14}  {'comp M':>7} {'comp Q':>7} {'M-Q':>7}"
          f"   capture")
    for cf, drv, f, sw, cm, cq, ok in sorted(rows, key=lambda r: (r[0], r[1], r[3])):
        tag = "" if ok else "  ⛔ mis-dialled"
        print(f"   {100 * cf:7.1f} {drv:6.2f} {sw:>14s}  {cm:7.3f} {cq:7.3f} {cm - cq:+7.3f}"
              f"   {f}{tag}")

    # The dilution, at matched DRIVE noon: bleed-free vs the ladder's own LEVEL-noon cell.
    print()
    for sw in ("sweep_clean", "sweep_drv_-6"):
        bf = [r for r in bleedfree if abs(r[1] - 0.5) < 1e-9 and r[3] == sw and r[6]]
        lad = tab.get((0.5, sw))
        if bf and lad:
            print(f"   DRIVE noon, {sw:>14s}:  bleed-free comp Q {bf[0][5]:6.3f} dB   vs the "
                  f"ladder's LEVEL-noon {lad['comp_q']:6.3f} dB")
    lad_cf = 100 * clean_fraction(caps, ladder[0][1])
    print(f"   => at the ladder's own LEVEL noon the output is {lad_cf:.1f} % CLEAN SIGNAL, and the "
          f"clean path does not\n      compress (a unity buffer to the BLEND pin), so it dilutes "
          f"the law.  S4's table is the MIXED\n      output's compression, not the OD path's -- "
          f"which is {6.662 / 1.870:.1f}x deeper at DRIVE noon, hottest stimulus.")
    print(f"   ⚠ Ladder cells and bleed-free cells are therefore NOT comparable -- do not diff "
          f"them without saying which mix each was measured at.\n")

    out["s6"] = {"rows": [{"clean_frac": r[0], "drive": r[1], "file": r[2], "sweep": r[3],
                           "comp_m": r[4], "comp_q": r[5], "matched": r[6]} for r in rows],
                 "n_bleedfree": len(bleedfree)}
    return {r[2] for r in bleedfree}


# --------------------------------------------------------------------------------------------
# S7 -- the head item, on the SEND axis
# --------------------------------------------------------------------------------------------
def gate_s7(absfr, caps, od, drops, bands, idx, matched, bleedfree, out):
    """GATE R measured the 320 Hz null's level-dependence along the SWEEP-LEVEL axis and found the
    sign REVERSES at DRIVE max: the pedal's null DEEPENS while the model's WASHES OUT.  The send
    axis changes the level a completely different way -- a different recording rather than a
    different segment of one -- so if that reversal is a property of the DEVICES it must appear
    here too.

    ⚠ GATE R measured it BLEED-FREE (BLEND = LEVEL = max, K2's exact zero).  The clean tap carries
    no 320 Hz null (GATE R2 puts the null in the pre-clipper treble ladder, which is in the OD path
    only), so any bleed FILLS the null and flattens exactly the statistic under test.  The
    bleed-free twins are therefore the only ones that can answer this; the DRIVE ladder is shown
    below as a labelled control precisely to show how much the bleed costs."""
    print("-- S7: the 320 Hz null on the SEND axis -- the head item, corroborated or not --")

    def pick(hz):
        j = min(range(len(bands)), key=lambda i: abs(bands[i] - hz))
        if abs(bands[j] - hz) > 1.0:
            sys.exit(f"GATE S7 FAIL: no graded band at {hz} Hz (nearest {bands[j]})")
        return idx.index(j)

    jn = pick(NULL_HZ)
    js = [pick(h) for h in SHOULDER_HZ]
    print(f"   null {bands[idx[jn]]:.1f} Hz referred to shoulders "
          f"{', '.join(f'{bands[idx[j]]:.1f}' for j in js)} Hz -- NAMED, so a change that moves "
          f"the null cannot re-point the statistic (GATE R4's argmin trap).")

    def prom(arr):
        return float(np.mean([arr[j] for j in js]) - arr[jn])

    def scan(pairs, label):
        res = []
        for n12, full in pairs:
            drv = float(caps[n12]["settings"]["drive"])
            dm, dq = [], []
            for sw in SWEEPS:
                if not usable(absfr, drops, n12, full, sw):
                    continue
                mF, qF = absfr[(full, sw)]
                mN, qN = absfr[(n12, sw)]
                dm.append(prom(mF) - prom(mN))
                dq.append(prom(qF) - prom(qN))
            if dm:
                res.append((drv, n12, float(np.median(dm)), float(np.median(dq)), len(dm)))
        return sorted(res)

    bf_pairs = [(n, f) for n, f in od if n in bleedfree and n in matched]
    if not bf_pairs:
        sys.exit("GATE S7 FAIL: no condition-matched bleed-free twin -- the head item's own "
                 "condition is unmeasurable here and no verdict may be printed")

    print(f"\n   BLEED-FREE twins ({len(bf_pairs)}) -- GATE R's own condition.  `d` = prominence "
          f"at the LOUD send minus the QUIET send:\n   d > 0 the null DEEPENS with level; d < 0 "
          f"it WASHES OUT.\n")
    print(f"   {'DRIVE':>6} {'MODEL d':>9} {'PEDAL d':>9} {'n':>3}   capture")
    bf = scan(bf_pairs, "bleed-free")
    for drv, f, dm, dq, n in bf:
        print(f"   {drv:6.2f} {dm:9.2f} {dq:9.2f} {n:3d}   {f}")

    hi = [r for r in bf if r[0] > 0.9]
    print(f"\n   GATE R (sweep-level axis, DRIVE max, bleed-free): pedal DEEPENS, model WASHES OUT.")
    if not hi:
        print(f"   ⛔ GATE S has NO condition-matched bleed-free twin at DRIVE max, so it cannot "
              f"test the head item's own cell.  Report this as untested, never as negative.")
        verdict = "untested"
    else:
        dm, dq = hi[0][2], hi[0][3]
        print(f"   GATE S (send axis,       DRIVE max, bleed-free): pedal "
              f"{'DEEPENS' if dq > 0 else 'WASHES OUT'} ({dq:+.2f}), model "
              f"{'DEEPENS' if dm > 0 else 'WASHES OUT'} ({dm:+.2f})   [n = {len(hi)} pair]")
        if dm * dq < 0 and dq > 0:
            verdict = "corroborated"
            print(f"   => CORROBORATED on an axis GATE R does not share: the reversal is a "
                  f"property of the devices, not of the sweep-level estimator.")
        elif dm * dq < 0:
            verdict = "opposite"
            print(f"   => a sign split IS present, but with the OPPOSITE assignment to GATE R's. "
                  f"Do not quote either as settled until this is explained.")
        else:
            verdict = "not corroborated"
            print(f"   => NOT corroborated: both sides move the same way on this axis. The "
                  f"reversal may be specific to the sweep-level axis.")
        print(f"   ⚠ n = 1 pair.  This LOCATES the question; it does not settle it "
              f"(s110 R8's own caveat, and GATE P's lesson about a spread that was never printed).")

    # The control that makes the above readable: the same statistic WITH bleed.
    lad_pairs = [(n, f) for n, f in od if n not in bleedfree and n in matched]
    if lad_pairs:
        cfs = sorted({round(100 * clean_fraction(caps, n), 1) for n, _ in lad_pairs})
        print(f"\n   CONTROL -- the same statistic on BLED twins ({cfs} % clean by K2).  The clean "
              f"tap carries no 320 Hz null\n   (GATE R2 puts the null in the pre-clipper treble "
              f"ladder, OD-path only), so the bleed FILLS it and this\n   column is expected to be "
              f"flatter.  Shown to make that cost visible, not to vote:\n")
        print(f"   {'DRIVE':>6} {'MODEL d':>9} {'PEDAL d':>9} {'n':>3}   capture")
        for drv, f, dm, dq, n in scan(lad_pairs, "bled"):
            print(f"   {drv:6.2f} {dm:9.2f} {dq:9.2f} {n:3d}   {f}")

    out["s7"] = {"null_hz": bands[idx[jn]], "shoulder_hz": [bands[idx[j]] for j in js],
                 "verdict": verdict,
                 "bleedfree": [{"drive": r[0], "file": r[1], "model_d": r[2], "pedal_d": r[3],
                                "n": r[4]} for r in bf],
                 "bled": [{"drive": r[0], "file": r[1], "model_d": r[2], "pedal_d": r[3],
                           "n": r[4]} for r in scan(lad_pairs, "bled")]}


# --------------------------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("report")
    ap.add_argument("--json", default=None)
    a = ap.parse_args()

    K.check_shipped_constant()   # the LEVEL taper exponent must still be what FitParams.h ships
    bands, caps = MG.load(a.report)[0], MG.load(a.report)[1]
    idx = [i for i, b in enumerate(bands) if MG.GRADE_LO <= b <= MG.GRADE_HI]
    absfr, _silent = K.absolute_fr(caps, idx)
    nonhf = [j for j, i in enumerate(idx) if bands[i] < K.HF_HZ]
    fb = np.array([bands[idx[j]] for j in nonhf])

    print(f"GATE S -- the compression law on the interface-SEND axis   [{a.report}]")
    print(f"  {len(caps)} captures, {len(idx)} graded bands, {len(nonhf)} non-HF "
          f"(< {K.HF_HZ:.0f} Hz, excluded per GATE I)")
    print(f"  No render, no gain match, no fit.  Each side is differenced against ITSELF across a "
          f"send change,\n  so MASTER, the EQ, the makeup and the record gain all cancel exactly.\n")

    out = {"report": a.report, "bands": [float(x) for x in fb]}
    ladder, od, cl, drops = gate_s1(bands, caps, absfr, nonhf, out)
    print()
    pad_m, pad_q = gate_s2(absfr, caps, cl, drops, nonhf, out)
    matched = gate_s3(absfr, od, ladder, drops, nonhf, pad_m, pad_q,
                      (out.get('s1b') or {}).get('worst_db', 0.0), out)
    tab = gate_s4(absfr, ladder, drops, nonhf, pad_m, pad_q, matched, out)
    gate_s5(absfr, ladder, drops, nonhf, fb, pad_m, pad_q, matched, out)
    bleedfree = gate_s6(absfr, caps, od, ladder, drops, nonhf, pad_m, pad_q, tab,
                        matched, out)
    gate_s7(absfr, caps, od, drops, bands, idx, matched, bleedfree, out)

    print("\n== GATE S: all sub-gates passed ==")
    if a.json:
        with open(a.json, "w", encoding="utf-8") as fh:
            json.dump(out, fh, indent=1, default=float)
        print(f"   wrote {a.json}")


if __name__ == "__main__":
    main()
