#!/usr/bin/env python3.11
"""GATE U -- the matched-bleed LEVEL instrument: is GATE J10's LEVEL effect LEVEL, or dilution?

    /opt/homebrew/bin/python3.11 analysis/level_bleed_gate.py analysis/reports/s114_baseline.json

No render.  A re-read of a stored matrix report plus a closed-form evaluation of the shipped
`LevelBlend` stage.  Imports `release_gate` (and through it `matrix_grade`) for the deltas, the
membership and the dropout set, `od_residual_localise` for the GATED statistic itself, and
`level_law_gate` for the stage's closed form and its FitParams-checked taper exponent -- so this
tool cannot drift from any of the four it is adjudicating.

WHAT THIS IS FOR
----------------
GATE J (s102) found the OD residual depends on LEVEL: conditioned on `blend = 1.0`, band-RMS ex-HF
runs 2.343 -> 4.873, a 2.08x spread, and recorded it as REAL on the argument that at blend max the
clean tap is out of circuit so LEVEL is a plain post-OD attenuator -- invisible to a per-row
gain-matched statistic by construction.

GATE K2 (s103) refuted that premise.  The BLEND pot's body bridges the LEVEL wiper to the clean
source at EVERY blend position, so bleed vanishes only where the wiper's source impedance is zero,
i.e. at LEVEL max.  Inside J's "bleed-free" set r(LEVEL, clean fraction) = -0.961: LEVEL and
dilution are collinear BY CONSTRUCTION.  GATE K6 therefore REFUSED a verdict on the size of the
LEVEL effect and said what would settle it -- rows with EQUAL BLEED and DIFFERENT LEVEL.

Those rows exist.  Session 112's 12 `level x blend` captures put four LEVELs on each of three
intermediate BLEND settings, and together with the blend-max ladder they give three families of
captures at matched clean fraction spanning up to 0.875 of LEVEL travel.  This gate builds that.

WHY MATCHING THE CLEAN FRACTION IS SUFFICIENT (the enabling argument)
--------------------------------------------------------------------
The stage's output is  a(B,L)*OD + b(B,L)*CLEAN  (GATE K2, two independent derivations).
`comprehensive_report` fits a per-row broadband null gain and applies it before anything is
differenced, so any pure scalar on a row is removed.  Therefore a graded row depends on (B, L)
ONLY through the RATIO b/a -- equivalently through the clean fraction b/(a+b).  Two captures with
equal clean fraction have IDENTICAL mixing up to a scalar the gain match deletes.

=> if band-RMS still moves with LEVEL among captures at matched clean fraction, LEVEL is doing
   something the mixing network does not account for.

⚠ AND THE HONEST LIMIT ON THAT, STATED UP FRONT: the clean fraction here is the MODEL's, computed
from the shipped stage.  The PEDAL's mixing at the same knob settings is NOT the same -- GATE K7
measures the model's clean bleed running 3.1-4.9 dB hot, and GATE L proved the shipped network
cannot express the pedal's LEVEL law under any taper and any bleed.  So matched MODEL bleed is only
approximately matched PEDAL bleed, and a surviving LEVEL dependence has two possible carriers:

    (a) a genuine LEVEL-dependent defect outside the mixing network, or
    (b) the model's bleed LAW being wrong, so that matched-model-bleed is mismatched-pedal-bleed.

(b) is the already-known LEVEL-law defect (GATE K3/L), not a new item.  U7 tests which, by asking
whether the surviving effect tracks GATE K3's independently measured per-detent law.

SUB-GATES
---------
U1  known answers: the clean fraction reproduces GATE K2's own recorded clean-re-OD table, and the
    statistic reproduces `release_gate`'s OD band-RMS.  Plus the MUTATION that matters here --
    omitting the taper must BREAK the K2 table (it is the s113 defect, and it is what invalidates
    session 112's recorded pairs).
U2  asserted membership: the settings-matched family, duplicate CONDITIONS collapsed with an
    assertion that they agree (a free known answer -- three duplicate pairs exist), dropouts and
    silent rows excluded, and the (LEVEL x BLEND) grid asserted rather than assumed.
U3  the premise correction: session 112's four recorded clean fractions, recomputed both ways.
U4  THE MEASUREMENT: band-RMS against LEVEL at matched bleed, as pairs and as families.
U5  the CONFOUNDED control: the same statistic on the blend-max ladder alone (what GATE J read),
    over the same settings-matched family, so the contrast is attributable to the matching.
U6  the dilution law measured directly (bleed varied at FIXED LEVEL), and the decomposition check:
    confounded effect = dilution + LEVEL, with the two halves measured on disjoint comparisons.
U7  does the surviving LEVEL effect track GATE K3's measured LEVEL-law error?  (a) vs (b) above.
U8  tolerance sweep, with the pair count asserted to move.

Hard exits cover the gate's own validity only (membership, known answers, empty populations).
Physics outcomes get COMPUTED verdicts and never a `sys.exit` -- session 108's P5 lesson.
"""

import argparse
import json
import sys

import numpy as np

import level_law_gate as K
import matrix_grade as MG
import od_residual_localise as J
import release_gate as RG

# --------------------------------------------------------------------------------------------
# Constants.  Every one of these is either recorded elsewhere in the project (and gated against
# its source here) or a stated analysis choice that U8 sweeps.
# --------------------------------------------------------------------------------------------

HF_HZ = 8000.0          # GATE I's split: at and above this the region is ND's artefact, not ours

# GATE K2's own recorded clean-re-OD table at BLEND max, indexed by the LEVEL KNOB (taper applied).
# Transcribed from CLAUDE.md's session-103 block so U1 is a check against the RECORD, not against
# a re-run of the same code.  LEVEL 1.0 is -inf (the clean coefficient is exactly zero) and is
# handled separately.
K2_CLEAN_RE_OD_DB = {0.125: -0.08, 0.25: -0.39, 0.375: -1.01, 0.5: -2.05,
                     0.625: -3.71, 0.75: -6.44, 0.875: -11.72}
K2_TOL_DB = 0.01        # the table is recorded to 2 dp

# Two captures count as bleed-matched when their clean fractions differ by no more than this, and
# as a LEVEL contrast when their LEVEL knobs differ by at least this.  U8 sweeps both.
BLEED_TOL = 0.03
MIN_DLEVEL = 0.20

# Settings that must match for two captures to differ in LEVEL and BLEND alone.  Taken from
# GATE K's own list minus the two axes under test, so the two tools cannot disagree about what
# "everything else equal" means.  Read from the report's stored `settings`, never from a filename.
MATCH_KEYS = tuple(k for k in K.MATCH_KEYS if k != "blend") + ("blend",)
FREE_KEYS = ("level", "blend")
OTHER_KEYS = tuple(k for k in MATCH_KEYS if k not in FREE_KEYS)

# Two captures at the same (LEVEL, BLEND) must produce the same MODEL render, because the model is
# a deterministic function of the settings.  That is the known answer, and the bar is a storage
# floor.  ⚠ It must be checked on the RAW render (`plugin_db - gain_db_applied`), NOT on
# `plugin_db`: the per-row null gain is fitted against that row's PEDAL capture, so a pedal-side
# difference propagates into the model column and an identical render reads as a 0.7 dB
# disagreement.  A first draft checked `plugin_db` and refused for exactly that reason.
DUP_MODEL_TOL_DB = 1e-9

# The PEDAL side of the same comparison is not a known answer -- it is two separate recordings, so
# it MEASURES the re-dial error, and it is reported rather than gated.
EXPECT_DUP_PAIRS = 3    # asserted, not inferred: blend-{0930,1200,1430} == level-1200_blend-*

# Which capture represents a duplicated condition.  A real choice that moves the numbers, so it is
# a named constant with its cost printed (s112's PREFER_FULL_SEND_NOON pattern).  True keeps the
# `level-*_blend-*` member, so the whole 4x3 grid comes from ONE capture session (2026-08-02) and
# the grid carries no internal session confound; the `blend-*` originals are 2026-07-21/22 and are
# printed as the discarded alternative every run.
PREFER_GRID_SESSION = True


# --------------------------------------------------------------------------------------------
# The mixing network, evaluated the way the shipped stage actually runs
# --------------------------------------------------------------------------------------------
def clean_fraction(settings, taper=True):
    """The clean tap's share of the output, from the SHIPPED stage's closed form (GATE K2).

    ⚠ `coef_closed` takes the TAPERED level; a capture's `settings` store the KNOB.  Omitting the
    taper is the session-113 defect and it is not subtle: at LEVEL noon it returns clean/OD =
    -6.02 dB where the stage delivers -2.05.  `taper=False` exists ONLY so U1 can mutate it and
    U3 can reproduce what session 112 actually computed."""
    L = float(settings["level"])
    if taper:
        L = L ** K.SHIPPED_LEVEL_TAPER_EXP
    od, cl = K.coef_closed(float(settings["blend"]), L)
    if od + cl <= 0.0:
        return float("nan")             # LEVEL 0 at BLEND max: the model mutes (GATE L7)
    return cl / (od + cl)


def clean_re_od_db(settings, taper=True):
    """The clean coefficient relative to the OD coefficient, in dB -- GATE K2's own quantity."""
    L = float(settings["level"])
    if taper:
        L = L ** K.SHIPPED_LEVEL_TAPER_EXP
    od, cl = K.coef_closed(float(settings["blend"]), L)
    if od <= 0.0:
        return float("nan")
    if cl <= 0.0:
        return float("-inf")
    return 20.0 * np.log10(cl / od)


# --------------------------------------------------------------------------------------------
# U1 -- known answers, and the mutation that proves the taper check is not vacuous
# --------------------------------------------------------------------------------------------
def gate_u1(od_rows, bands, idx, report, out):
    print("-- U1: known answers --")

    # (a) the clean fraction path must reproduce GATE K2's RECORDED clean-re-OD table
    worst, worst_at = 0.0, None
    for knob, want in sorted(K2_CLEAN_RE_OD_DB.items()):
        got = clean_re_od_db({"level": knob, "blend": 1.0})
        e = abs(got - want)
        if e > worst:
            worst, worst_at = e, knob
    if worst > K2_TOL_DB:
        sys.exit(f"GATE U1 FAIL: the clean-re-OD table disagrees with GATE K2's record by "
                 f"{worst:.4f} dB at LEVEL {worst_at} -- this tool's mixing algebra has drifted "
                 f"from level_law_gate.coef_closed, or the taper exponent moved")
    inf_ok = clean_re_od_db({"level": 1.0, "blend": 1.0}) == float("-inf")
    if not inf_ok:
        sys.exit("GATE U1 FAIL: the clean coefficient is not EXACTLY zero at LEVEL max -- K2's "
                 "exact-zero endpoint is what makes the bleed-free rows bleed-free")
    print(f"  U1a OK  clean-re-OD reproduces GATE K2's recorded table to {worst:.4f} dB "
          f"over 7 detents, and is exactly -inf at LEVEL max")

    # (a-mutation) omitting the taper must BREAK it.  This is the session-113 defect, and it is
    # also exactly what session 112 did when it recorded its "tight pairs" -- so the mutation is
    # not synthetic, it reproduces a real recorded error.
    mut = max(abs(clean_re_od_db({"level": k, "blend": 1.0}, taper=False) - w)
              for k, w in K2_CLEAN_RE_OD_DB.items())
    if mut <= K2_TOL_DB:
        sys.exit("GATE U1 FAIL: dropping the LEVEL taper did NOT break the K2 table -- U1a is "
                 "vacuous and cannot catch the s113 taper-domain defect")
    print(f"  U1b OK  dropping the taper breaks it by {mut:.3f} dB, so U1a is not vacuous "
          f"(this IS the s113 defect, and s112's recorded pairs carry it)")

    # (b) the statistic itself must be release_gate's.  `band_rms_headline` is imported from
    # GATE J, so this pins the shared definition rather than re-implementing it.
    d_all = J.stack(od_rows)
    mine = J.band_rms_headline(d_all)
    theirs = RG.band_rms(od_rows, bands, idx)
    if abs(mine - theirs) > 1e-9:
        sys.exit(f"GATE U1 FAIL: band-RMS via od_residual_localise ({mine:.9f}) disagrees with "
                 f"release_gate.band_rms ({theirs:.9f}) -- the statistic has drifted")
    print(f"  U1c OK  band-RMS = {mine:.3f} dB reproduces release_gate.band_rms exactly "
          f"({len(od_rows)} OD rows)")
    out["u1"] = {"k2_table_worst_db": worst, "k2_mutation_db": mut, "band_rms_all_od": mine}


# --------------------------------------------------------------------------------------------
# U2 -- asserted membership
# --------------------------------------------------------------------------------------------
def build_family(caps, od_rows, non_hf):
    """-> {file: {...}} for every OD capture at the DEFAULT on everything except LEVEL and BLEND.

    The reference condition is `ref-od.wav`'s own settings, read from the report -- not a
    hand-written dict, which is how s114 found three membership defects at once."""
    if "ref-od.wav" not in caps:
        sys.exit("GATE U2 FAIL: ref-od.wav is not in this report -- it defines the reference "
                 "condition every family member must match")
    base = {k: caps["ref-od.wav"]["settings"][k] for k in OTHER_KEYS}

    fam = {}
    for f, c in caps.items():
        st = c.get("settings") or {}
        if not st or not st.get("distEngage"):
            continue
        if any(st.get(k) != v for k, v in base.items()):
            continue
        rows = {sw: v[0] for (ff, sw), v in od_rows.items() if ff == f}
        if not rows:
            continue                    # silent, dropout, or not graded -- excluded upstream
        cf = clean_fraction(st)
        if cf != cf:
            continue                    # LEVEL 0: the model mutes (GATE L7)
        fam[f] = {"level": float(st["level"]), "blend": float(st["blend"]), "cf": cf,
                  "rows": rows,
                  "band_rms": float(np.mean([np.sqrt(np.mean(v[non_hf] ** 2))
                                             for v in rows.values()]))}
    return fam, base


def raw_model(caps, f, sw, idx):
    """The model's own render at the graded bands, with the per-row null gain REMOVED.

    `plugin_db` carries `gain_db_applied`, which `comprehensive_report` fits against that row's
    PEDAL capture.  Two takes of one condition therefore have different `plugin_db` even though the
    render is identical -- so the model-side known answer must be asked of this, not of that."""
    fr = caps[f]["fr"][sw]
    g = fr.get("gain_db_applied") or 0.0
    return np.array([fr["plugin_db"][i] - g for i in idx])


def collapse_duplicates(fam, caps, idx, out):
    """Two files at the same (LEVEL, BLEND) are ONE condition and must vote once.

    ⭐ THE MODEL SIDE IS A KNOWN ANSWER: the render is a deterministic function of the settings, so
    two files with identical settings must give a BIT-IDENTICAL raw render.  If they ever do not,
    `OTHER_KEYS` is missing a setting and every "matched" comparison in this gate is unfounded.

    ⭐⭐ THE PEDAL SIDE IS A MEASUREMENT, NOT A KNOWN ANSWER, and it is the one that matters for the
    error bar: these are two separate RECORDINGS, so their disagreement is the re-dial error of the
    BLEND knob -- which is exactly what limits how tightly any pair in this gate is really matched.
    Session 113's S3 found the same thing on DRIVE and LEVEL (exact at the mechanical references,
    not at the intermediate clock positions); this is a third axis saying it independently."""
    groups = {}
    for f, r in fam.items():
        groups.setdefault((round(r["level"], 6), round(r["blend"], 6)), []).append(f)

    dups = {k: sorted(v) for k, v in groups.items() if len(v) > 1}
    if len(dups) != EXPECT_DUP_PAIRS:
        sys.exit(f"GATE U2 FAIL: expected {EXPECT_DUP_PAIRS} duplicate conditions in the "
                 f"settings-matched family, found {len(dups)}: "
                 f"{ {f'L{k[0]}/B{k[1]}': v for k, v in dups.items()} } -- the constant is "
                 f"asserted, not inferred, so it stops catching things if it is auto-fitted")

    worst_model, rows = 0.0, []
    print(f"{'':4}{'condition':<14}{'model raw |Δ|':>15}{'PEDAL |Δ| dB':>14}{'Δ band-RMS':>12}"
          f"   detent?")
    for (L, B), files in sorted(dups.items()):
        a, b = fam[files[0]], fam[files[1]]
        shared = sorted(set(a["rows"]) & set(b["rows"]))
        if not shared:
            sys.exit(f"GATE U2 FAIL: duplicate condition L={L} B={B} shares no graded sweep")
        em = max(float(np.max(np.abs(raw_model(caps, files[0], sw, idx)
                                     - raw_model(caps, files[1], sw, idx)))) for sw in shared)
        ep = max(float(np.max(np.abs(np.array([caps[files[0]]["fr"][sw]["pedal_db"][i] for i in idx])
                                     - np.array([caps[files[1]]["fr"][sw]["pedal_db"][i]
                                                 for i in idx])))) for sw in shared)
        worst_model = max(worst_model, em)
        det = "yes (noon)" if abs(B - 0.5) < 1e-9 else "no"
        rows.append({"level": L, "blend": B, "files": files, "model_db": em, "pedal_db": ep,
                     "d_band_rms": b["band_rms"] - a["band_rms"], "detent": det})
        print(f"{'':4}L={L:.2f} B={B:.2f}{em:15.2e}{ep:14.4f}"
              f"{b['band_rms'] - a['band_rms']:12.3f}   {det}")

    if worst_model > DUP_MODEL_TOL_DB:
        sys.exit(f"GATE U2 FAIL: duplicate conditions give DIFFERENT model renders "
                 f"({worst_model:.3g} dB) -- OTHER_KEYS is missing a setting, so nothing in this "
                 f"gate is really settings-matched")
    print(f"  U2b OK  the raw MODEL render is bit-identical across all {len(dups)} duplicate "
          f"conditions ({worst_model:.1e} dB) -- so they ARE the same condition")

    det = [r for r in rows if r["detent"].startswith("yes")]
    non = [r for r in rows if not r["detent"].startswith("yes")]
    if det and non:
        print(f"\n  ⭐ MEASURED, and it is the instrument's error bar: the PEDAL side disagrees by")
        print(f"     {min(r['pedal_db'] for r in det):.2e} dB at the BLEND centre detent and "
              f"{min(r['pedal_db'] for r in non):.3f}-{max(r['pedal_db'] for r in non):.3f} dB at "
              f"the intermediate")
        print(f"     clock positions -- a {max(r['pedal_db'] for r in non) / max(min(r['pedal_db'] for r in det), 1e-12):.0e}x")
        print( "     separation.  The knob reproduced EXACTLY where the pot has a mechanical")
        print( "     reference and not otherwise: session 113's S3 finding, on a third axis.")
        print( "     ⚠ Every pair below re-dials BOTH knobs by design, so this is the noise floor")
        print( "       the effect has to clear -- not a nuisance that averages away.")

    keep_grid = PREFER_GRID_SESSION
    kept = dict(fam)
    for files in dups.values():
        drop = [f for f in files if ("_blend-" in f) != keep_grid]
        for f in drop:
            kept.pop(f, None)
        print(f"    kept {[f for f in files if f not in drop][0]}   (discarded {drop[0]})")
    out["u2_duplicates"] = rows
    out["u2_dup_worst_model_db"] = worst_model
    out["prefer_grid_session"] = PREFER_GRID_SESSION
    return kept


def gate_u2(caps, od_rows, non_hf, idx, out):
    print("\n-- U2: asserted membership --")
    fam, base = build_family(caps, od_rows, non_hf)
    if len(fam) < 12:
        sys.exit(f"GATE U2 FAIL: only {len(fam)} settings-matched OD captures -- the matched-bleed "
                 f"design needs the s112 level x blend grid, which this report does not have")
    print(f"  U2a OK  {len(fam)} OD captures at the ref-od condition on every setting except "
          f"LEVEL and BLEND")
    print(f"          matched on: {', '.join(OTHER_KEYS)}")

    fam = collapse_duplicates(fam, caps, idx, out)

    levels = sorted({round(r['level'], 3) for r in fam.values()})
    blends = sorted({round(r['blend'], 3) for r in fam.values()})
    grid = {(round(r['level'], 3), round(r['blend'], 3)) for r in fam.values()}
    want_grid = {(L, B) for L in (0.25, 0.5, 0.75, 1.0) for B in (0.25, 0.5, 0.75)}
    missing = sorted(want_grid - grid)
    if missing:
        sys.exit(f"GATE U2 FAIL: the s112 4x3 level x blend grid is incomplete, missing {missing}")
    print(f"  U2c OK  the s112 4x3 grid is complete; LEVEL {levels}")
    print(f"          BLEND {blends}")
    out["u2_n"] = len(fam)
    out["u2_levels"] = levels
    out["u2_blends"] = blends
    return fam


# --------------------------------------------------------------------------------------------
# U3 -- session 112's recorded pairs, recomputed
# --------------------------------------------------------------------------------------------
S112_CLAIMS = [(0.4286, 1.00, 0.25), (0.4375, 0.75, 0.75),
               (0.8462, 0.50, 0.25), (0.8333, 0.25, 0.75)]


def gate_u3(out):
    """⛔ SESSION 112's RECORDED TIGHT PAIRS DO NOT SURVIVE, TWO WAYS AT ONCE.

    A computed verdict, not a hard exit: this is a finding about the RECORD, not about this gate's
    validity.  Both defects are checkable in one line each and neither was."""
    print("\n-- U3: session 112's recorded clean fractions, recomputed --")
    print(f"{'recorded':>9}{'as (L,B)':>12}{'tapered':>10}{'untapered':>11}"
          f"{'untap(B,L)':>12}   verdict")
    rec = []
    for val, L, B in S112_CLAIMS:
        st = {"level": L, "blend": B}
        tap = clean_fraction(st)
        unt = clean_fraction(st, taper=False)
        swap = clean_fraction({"level": B, "blend": L}, taper=False)
        hit = ("untapered" if abs(unt - val) < 5e-4 else
               "untapered + L/B TRANSPOSED" if abs(swap - val) < 5e-4 else "no match")
        rec.append({"recorded": val, "level": L, "blend": B, "tapered": tap,
                    "untapered": unt, "untapered_transposed": swap, "matches": hit})
        print(f"{val:9.4f}{f'L{L:.2f}/B{B:.2f}':>12}{tap:10.4f}{unt:11.4f}{swap:12.4f}   {hit}")

    n_tap = sum(1 for r in rec if abs(r["tapered"] - r["recorded"]) < 5e-4)
    n_swap = sum(1 for r in rec if r["matches"].endswith("TRANSPOSED"))
    print(f"\n  => {4 - n_tap} of 4 do NOT reproduce with the taper applied; {n_swap} reproduce "
          f"only with LEVEL and BLEND TRANSPOSED.")
    print("     Both defects are in the RECORD, not in the captures: the 4x3 grid is real and the")
    print("     pairs it supports are BETTER than the ones recorded (see U4).  ⚠ Do not quote")
    print("     session 112's '0.4286 vs 0.4375' or '0.8462 vs 0.8333' as matched pairs.")
    out["u3"] = rec


# --------------------------------------------------------------------------------------------
# U4 -- the measurement
# --------------------------------------------------------------------------------------------
def admissible_pairs(fam, bleed_tol=BLEED_TOL, min_dl=MIN_DLEVEL):
    """Every (lo-LEVEL, hi-LEVEL) pair at matched clean fraction."""
    fs = sorted(fam)
    out = []
    for i in range(len(fs)):
        for j in range(len(fs)):
            a, b = fam[fs[i]], fam[fs[j]]
            if b["level"] - a["level"] < min_dl:
                continue
            if abs(a["cf"] - b["cf"]) > bleed_tol:
                continue
            out.append({"lo": fs[i], "hi": fs[j], "dlevel": b["level"] - a["level"],
                        "dcf": abs(a["cf"] - b["cf"]),
                        "lo_level": a["level"], "hi_level": b["level"],
                        "lo_cf": a["cf"], "hi_cf": b["cf"],
                        "lo_rms": a["band_rms"], "hi_rms": b["band_rms"],
                        "d_rms": b["band_rms"] - a["band_rms"]})
    out.sort(key=lambda r: -r["dlevel"])
    return out


def gate_u4(fam, out):
    print("\n-- U4: THE MEASUREMENT -- band-RMS vs LEVEL at MATCHED BLEED (ex HF) --")
    pairs = admissible_pairs(fam)
    if not pairs:
        sys.exit("GATE U4 FAIL: no admissible matched-bleed pairs -- refusing to summarise "
                 "nothing (empty-gate-must-fail)")
    print(f"    |Δ clean fraction| <= {BLEED_TOL}, ΔLEVEL >= {MIN_DLEVEL};  {len(pairs)} pairs\n")
    print(f"{'ΔLEVEL':>7}{'Δcf':>8}{'lo band-RMS':>13}{'hi band-RMS':>13}{'Δ dB':>8}"
          f"{'per unit L':>12}   lo -> hi")
    for p in pairs:
        print(f"{p['dlevel']:7.3f}{p['dcf']:8.4f}{p['lo_rms']:13.3f}{p['hi_rms']:13.3f}"
              f"{p['d_rms']:8.3f}{p['d_rms'] / p['dlevel']:12.3f}   "
              f"L{p['lo_level']:.3f}/B{fam[p['lo']]['blend']:.2f} -> "
              f"L{p['hi_level']:.3f}/B{fam[p['hi']]['blend']:.2f}")

    d = np.array([p["d_rms"] for p in pairs])
    slope = np.array([p["d_rms"] / p["dlevel"] for p in pairs])
    print(f"\n  median Δ band-RMS over {len(pairs)} matched-bleed pairs : {np.median(d):+.3f} dB")
    print(f"  median Δ per unit LEVEL                          : {np.median(slope):+.3f} dB")
    print(f"  same-signed                                      : "
          f"{int(np.sum(d > 0))} up / {int(np.sum(d < 0))} down")
    out["u4"] = {"n_pairs": len(pairs), "median_d_rms": float(np.median(d)),
                 "median_slope": float(np.median(slope)),
                 "n_up": int(np.sum(d > 0)), "n_down": int(np.sum(d < 0)),
                 "pairs": pairs}
    return pairs


def gate_u4b(fam, out):
    """The single cleanest contrast in the design: ONE low-LEVEL anchor, TWO high-LEVEL captures
    that differ only in bleed.  Same LEVEL step in both arms, so the arms differ in nothing else."""
    print("\n-- U4b: the anchored three-way -- same LEVEL step, bleed held vs bleed released --")
    anchor = min(fam.items(), key=lambda kv: kv[1]["level"])
    af, ar = anchor
    hi = [(f, r) for f, r in fam.items() if r["level"] >= ar["level"] + MIN_DLEVEL]
    if len(hi) < 2:
        print("  (skipped: fewer than two high-LEVEL captures)")
        return
    matched = min(hi, key=lambda kv: abs(kv[1]["cf"] - ar["cf"]))
    released = min(hi, key=lambda kv: kv[1]["cf"])
    if matched[0] == released[0]:
        print("  (skipped: the matched and released arms are the same capture)")
        return
    print(f"    anchor          L={ar['level']:.3f} B={ar['blend']:.2f} cf={ar['cf']:.4f}  "
          f"band-RMS {ar['band_rms']:.3f}   {af}")
    for tag, (f, r) in (("bleed HELD", matched), ("bleed RELEASED", released)):
        print(f"    {tag:<15} L={r['level']:.3f} B={r['blend']:.2f} cf={r['cf']:.4f}  "
              f"band-RMS {r['band_rms']:.3f}   Δ {r['band_rms'] - ar['band_rms']:+.3f} dB   {f}")
    dm = matched[1]["band_rms"] - ar["band_rms"]
    dr = released[1]["band_rms"] - ar["band_rms"]
    print(f"\n  Both arms take the SAME LEVEL step ({ar['level']:.3f} -> "
          f"{matched[1]['level']:.3f}); they differ in nothing but the bleed.")
    print(f"    bleed RELEASED (= what GATE J10 read) : {dr:+.3f} dB")
    print(f"    bleed HELD     (= LEVEL alone)        : {dm:+.3f} dB")
    # ⚠ A percentage share is only meaningful when the two moves have the SAME SIGN.  An earlier
    # draft printed "LEVEL's share = -42%, dilution carries 142%", which is arithmetic noise
    # dressed as a decomposition.  State the signs instead and let U6 do the real split.
    if dm * dr > 0:
        print(f"  => LEVEL's own share of the confounded effect: {100.0 * dm / dr:.0f}%")
    else:
        print(f"  => the two arms move in OPPOSITE directions: releasing the bleed RAISES the "
              f"residual by\n     {dr:+.3f} dB while the same LEVEL step at held bleed "
              f"{'lowers' if dm < 0 else 'raises'} it by {dm:+.3f} dB.")
        print("     A percentage share is not defined here and is not quoted; U6 splits it "
              "additively instead.")
    out["u4b"] = {"anchor": af, "matched": matched[0], "released": released[0],
                  "d_matched": dm, "d_released": dr,
                  "same_sign": bool(dm * dr > 0)}


# --------------------------------------------------------------------------------------------
# U5 -- the confounded control (what GATE J actually read)
# --------------------------------------------------------------------------------------------
def gate_u5(fam, out):
    print("\n-- U5: the CONFOUNDED control -- the blend-max ladder, i.e. GATE J10's own reading --")
    lad = sorted([(r["level"], r["cf"], r["band_rms"], f)
                  for f, r in fam.items() if abs(r["blend"] - 1.0) < 1e-9])
    if len(lad) < 3:
        sys.exit("GATE U5 FAIL: fewer than 3 blend-max captures -- cannot reproduce the "
                 "confounded reading the whole gate exists to adjudicate")
    print(f"{'LEVEL':>7}{'cleanFrac':>11}{'band-RMS':>11}   file")
    for L, cf, br, f in lad:
        print(f"{L:7.3f}{cf:11.4f}{br:11.3f}   {f}")
    lo, hi = lad[0], lad[-1]
    span = hi[2] / lo[2] if lo[2] else float("nan")
    print(f"\n  LEVEL {lo[0]:.3f} -> {hi[0]:.3f}:  band-RMS {lo[2]:.3f} -> {hi[2]:.3f}  "
          f"({span:.2f}x, {hi[2] - lo[2]:+.3f} dB)")
    print(f"  ⚠ over that span the clean fraction runs {lo[1]:.4f} -> {hi[1]:.4f}, i.e. LEVEL and")
    print("    dilution move TOGETHER -- this is exactly the collinearity GATE K6 refused on.")
    out["u5"] = {"ladder": [{"level": L, "cf": cf, "band_rms": br, "file": f}
                            for L, cf, br, f in lad],
                 "span_ratio": span, "d_rms": hi[2] - lo[2]}
    return lad


# --------------------------------------------------------------------------------------------
# U6 -- the dilution law, measured directly, and the decomposition check
# --------------------------------------------------------------------------------------------
def gate_u6(fam, pairs, out):
    """Bleed varied at FIXED LEVEL is a direct measurement of the dilution slope, with no LEVEL
    contrast in it at all.  Four such ladders exist (one per LEVEL in the s112 grid), which is what
    lets the confounded effect be decomposed rather than merely bracketed."""
    print("\n-- U6: the dilution law measured directly (bleed varied at FIXED LEVEL) --")
    by_level = {}
    for f, r in fam.items():
        by_level.setdefault(round(r["level"], 3), []).append((r["cf"], r["band_rms"], f))
    ladders = {L: sorted(v) for L, v in by_level.items() if len(v) >= 3}
    if not ladders:
        sys.exit("GATE U6 FAIL: no fixed-LEVEL bleed ladder with >= 3 points")

    fits = {}
    for L, pts in sorted(ladders.items()):
        cf = np.array([p[0] for p in pts])
        br = np.array([p[1] for p in pts])
        m, c = np.polyfit(cf, br, 1)
        fits[L] = {"slope": float(m), "intercept": float(c), "n": len(pts),
                   "cf_lo": float(cf.min()), "cf_hi": float(cf.max())}
        print(f"    LEVEL {L:.3f}  n={len(pts)}  cf {cf.min():.3f}-{cf.max():.3f}   "
              f"band-RMS {br.max():.3f} -> {br.min():.3f}   slope {m:+.3f} dB per unit cf")
    slopes = np.array([v["slope"] for v in fits.values()])
    print(f"\n  dilution slope across {len(fits)} independent fixed-LEVEL ladders: "
          f"median {np.median(slopes):+.3f}, spread {slopes.max() - slopes.min():.3f} dB/unit cf")
    print("  ⚠ a slope measured at ONE LEVEL contains no LEVEL contrast by construction, which is")
    print("    what makes it usable as the dilution term below.")
    out["u6_dilution"] = fits

    print("  ⚠ AND THE SLOPE IS NOT ONE NUMBER: it runs -1.84 to -3.83 across the four ladders,")
    print("    which cover DIFFERENT cf ranges -- so this relation is curved, LEVEL-dependent, or")
    print("    both, and a single fitted slope must not carry the decomposition.  It does not:")
    print("    the split below is a PATH IDENTITY with no fit in it at all.")

    # ---- the decomposition, fit-free ------------------------------------------------------
    # The confounded move (lo LEVEL, high bleed) -> (hi LEVEL, no bleed) can be walked in two legs
    # through the matched-bleed capture that sits at hi LEVEL and the lo capture's own bleed:
    #
    #     A = (L_lo, cf~x)  --leg 1: LEVEL, bleed HELD-->  B = (L_hi, cf~x)
    #                       --leg 2: bleed, LEVEL FIXED->  C = (L_hi, cf=0)
    #
    # Each leg is measured on a disjoint comparison and holds the other factor fixed, and the two
    # must sum to the measured total EXACTLY.  That exactness is a free known answer: it is an
    # identity only if all three band-RMS values come from the membership this gate actually used,
    # so a dropped or double-counted row breaks it.
    lad = sorted([(r["level"], r["cf"], r["band_rms"], f) for f, r in fam.items()
                  if abs(r["blend"] - 1.0) < 1e-9])
    if len(lad) < 2:
        return
    A_L, A_cf, A_rms, A_f = lad[0]
    C_L, C_cf, C_rms, C_f = lad[-1]
    hi_pool = [(f, r) for f, r in fam.items() if abs(r["level"] - C_L) < 1e-9]
    B_f, B_r = min(hi_pool, key=lambda kv: abs(kv[1]["cf"] - A_cf))
    if abs(B_r["cf"] - A_cf) > BLEED_TOL:
        print(f"\n  (no bleed-matched capture at LEVEL {C_L:.3f} within {BLEED_TOL} of "
              f"cf {A_cf:.4f} -- decomposition skipped)")
        return

    leg1 = B_r["band_rms"] - A_rms          # LEVEL, bleed held
    leg2 = C_rms - B_r["band_rms"]          # bleed, LEVEL fixed
    total = C_rms - A_rms
    resid = total - (leg1 + leg2)
    if abs(resid) > 1e-9:
        sys.exit(f"GATE U6 FAIL: the two legs do not sum to the measured total "
                 f"({leg1:+.6f} + {leg2:+.6f} != {total:+.6f}, residual {resid:.3g}) -- the three "
                 f"band-RMS values are not from one consistent membership")

    print(f"\n  ⭐ THE DECOMPOSITION, with NO FIT -- confounded LEVEL {A_L:.3f} -> {C_L:.3f}:")
    print(f"    A  L={A_L:.3f} cf={A_cf:.4f}  band-RMS {A_rms:.3f}   {A_f}")
    print(f"    B  L={C_L:.3f} cf={B_r['cf']:.4f}  band-RMS {B_r['band_rms']:.3f}   {B_f}")
    print(f"    C  L={C_L:.3f} cf={C_cf:.4f}  band-RMS {C_rms:.3f}   {C_f}")
    print(f"\n{'':4}{'leg':<34}{'Δ band-RMS':>12}{'share':>9}")
    print(f"{'':4}{'1  LEVEL, bleed HELD':<34}{leg1:12.3f}{100.0 * leg1 / total:8.0f}%")
    print(f"{'':4}{'2  bleed, LEVEL FIXED':<34}{leg2:12.3f}{100.0 * leg2 / total:8.0f}%")
    print(f"{'':4}{'   = measured total (GATE J10)':<34}{total:12.3f}{100:8.0f}%")
    print(f"    identity check: legs sum to the total to {abs(resid):.1e} dB")
    print(f"\n  => DILUTION carries {100.0 * leg2 / total:.0f}% of what GATE J10 read as a LEVEL "
          f"effect.\n     LEVEL's own contribution is {leg1:+.3f} dB -- and it has the OPPOSITE "
          f"sign." if leg1 * total < 0 else
          f"\n  => DILUTION carries {100.0 * leg2 / total:.0f}%; LEVEL {100.0 * leg1 / total:.0f}%.")
    out["u6_decomp"] = {"A": {"file": A_f, "level": A_L, "cf": A_cf, "band_rms": A_rms},
                        "B": {"file": B_f, "level": C_L, "cf": B_r["cf"],
                              "band_rms": B_r["band_rms"]},
                        "C": {"file": C_f, "level": C_L, "cf": C_cf, "band_rms": C_rms},
                        "leg1_level": leg1, "leg2_bleed": leg2, "total": total,
                        "identity_residual": resid}
    gate_u6b(fam, pairs, out)


def gate_u6b(fam, pairs, out):
    """The same split run from EVERY matched pair that supports it, so its spread is printed.

    One decomposition is an anecdote -- and its anchor here (`level-0815`, LEVEL 0.125) is the one
    rung where the blend-max ladder is non-monotone, so it is exactly the point that should not be
    trusted alone.  s108's P4 rule: print the spread across the conditions the device itself sets,
    never a single cell.

    Generalised path: for a matched pair A=(L_lo, cf~x), B=(L_hi, cf~x), the CONFOUNDED comparison
    is A against C=(L_hi, same BLEND as A) -- the move GATE J's marginal actually pools.  The split
    is then leg1 = B-A (LEVEL, bleed held) and leg2 = C-B (bleed, LEVEL fixed), which sum to C-A
    identically."""
    by_lb = {(round(r["level"], 6), round(r["blend"], 6)): (f, r) for f, r in fam.items()}
    rows = []
    for p in pairs:
        A_f, B_f = p["lo"], p["hi"]
        A, B = fam[A_f], fam[B_f]
        key = (round(B["level"], 6), round(A["blend"], 6))
        if key not in by_lb:
            continue                    # no capture at (hi LEVEL, lo's BLEND): path not closable
        C_f, C = by_lb[key]
        if C_f == B_f:
            continue                    # degenerate: B and C are the same capture
        leg1 = B["band_rms"] - A["band_rms"]
        leg2 = C["band_rms"] - B["band_rms"]
        total = C["band_rms"] - A["band_rms"]
        if abs(total) < 1e-6:
            continue
        rows.append({"A": A_f, "B": B_f, "C": C_f, "dlevel": p["dlevel"],
                     "blend_A": A["blend"], "leg1_level": leg1, "leg2_bleed": leg2,
                     "total": total, "level_share": 100.0 * leg1 / total,
                     "bleed_share": 100.0 * leg2 / total})
    if not rows:
        print("\n  (no pair closes the decomposition path -- U6b skipped)")
        return
    print(f"\n  U6b: the same split from all {len(rows)} pairs that close the path --")
    print(f"{'':4}{'ΔLEVEL':>7}{'B_A':>6}{'LEVEL leg':>11}{'bleed leg':>11}{'total':>9}"
          f"{'LEVEL %':>9}")
    for r in sorted(rows, key=lambda r: -r["dlevel"]):
        print(f"{'':4}{r['dlevel']:7.3f}{r['blend_A']:6.2f}{r['leg1_level']:11.3f}"
              f"{r['leg2_bleed']:11.3f}{r['total']:9.3f}{r['level_share']:8.0f}%")
    sh = np.array([r["level_share"] for r in rows])
    l1 = np.array([r["leg1_level"] for r in rows])
    print(f"\n    LEVEL's share: median {np.median(sh):.0f}%, range {sh.min():.0f}% to "
          f"{sh.max():.0f}%   (n = {len(rows)})")
    print(f"    LEVEL's leg in dB: median {np.median(l1):+.3f}, "
          f"range {l1.min():+.3f} to {l1.max():+.3f}")
    out["u6b"] = {"n": len(rows), "median_level_share_pct": float(np.median(sh)),
                  "median_level_leg_db": float(np.median(l1)), "rows": rows}


# --------------------------------------------------------------------------------------------
# U7 -- (a) or (b): does what survives track the KNOWN LEVEL-law error?
# --------------------------------------------------------------------------------------------
def gate_u7(pairs, out):
    """A surviving matched-bleed LEVEL effect has two candidate carriers (see the header).  If it
    is (b) -- the model's bleed law being wrong, so matched-model-bleed is mismatched-pedal-bleed --
    then it should grow with the model's own LEVEL-law error, which GATE K3 measured per detent
    with NO gain match.  If it is (a), a defect outside the network, it need not."""
    print("\n-- U7: does the surviving effect track GATE K3's measured LEVEL-law error? --")
    # GATE K3's recorded MODEL - PEDAL non-HF band mean, dB re noon, at the clean stimulus.
    # Transcribed from CLAUDE.md's session-103 table; LEVEL 0.5 is the reference and is 0 by
    # construction.  Used only as a REGRESSOR here, never as a target.
    k3 = {0.125: -8.2, 0.25: -2.9, 0.375: -1.5, 0.5: 0.0, 0.75: -0.4, 1.0: -1.6}
    usable = [p for p in pairs
              if round(p["lo_level"], 3) in k3 and round(p["hi_level"], 3) in k3]
    if len(usable) < 4:
        print(f"  (skipped: only {len(usable)} pairs have a GATE K3 entry at both LEVELs)")
        out["u7"] = {"n": len(usable), "skipped": True}
        return
    x = np.array([abs(k3[round(p["hi_level"], 3)] - k3[round(p["lo_level"], 3)]) for p in usable])
    y = np.array([p["d_rms"] for p in usable])
    r = float(np.corrcoef(x, y)[0, 1]) if x.std() > 0 and y.std() > 0 else float("nan")
    surviving = float(np.median(np.abs(y)))
    print(f"    n = {len(usable)} matched-bleed pairs;  median |Δ band-RMS| = {surviving:.3f} dB")
    print(f"    |Δ GATE-K3 law error| across the pair vs the pair's Δ band-RMS:  r = {r:+.3f}")

    # ⚠ The attribution question only has content if something SURVIVED to attribute.  With the
    # matched-bleed effect at ~0.1 dB against a re-dial noise floor U2 measured at 0.28-2.56 dB,
    # "which carrier" is not answerable and must not be answered -- an earlier draft printed a
    # confident "carrier (b)" off r alone, with the effect size unread.
    if surviving < 0.25:
        verdict = (f"NOT ANSWERABLE: only {surviving:.3f} dB survives the bleed match, which is "
                   f"below the re-dial noise floor -- there is no effect left to attribute, and "
                   f"the correlation is not evidence of one")
    elif r == r and abs(r) >= 0.6:
        verdict = ("carrier (b): what survives TRACKS the known LEVEL-law error, so it is the "
                   "model's bleed law, NOT a new defect")
    elif r == r and abs(r) < 0.3:
        verdict = ("carrier (a): what survives does NOT track the known LEVEL-law error -- a "
                   "LEVEL-dependent defect outside the mixing network")
    else:
        verdict = "UNRESOLVED at this n -- do not attribute"
    print(f"    => {verdict}")
    print("    ⚠ n is small and GATE K3's column is a transcribed record, so read the SIGN and "
          "the\n       magnitude class, never the coefficient.")
    out["u7"] = {"n": len(usable), "r": r, "median_abs_d": surviving, "verdict": verdict}


# --------------------------------------------------------------------------------------------
# U8 -- tolerance sweep, with membership asserted to move
# --------------------------------------------------------------------------------------------
def gate_u8(fam, out):
    print("\n-- U8: robustness -- sweep the bleed-match tolerance --")
    print(f"{'bleed tol':>10}{'pairs':>7}{'median Δ dB':>13}{'median Δ/L':>12}")
    rows, counts = [], []
    for tol in (0.005, 0.01, 0.02, 0.03, 0.05, 0.08):
        ps = admissible_pairs(fam, bleed_tol=tol)
        counts.append(len(ps))
        if not ps:
            print(f"{tol:10.3f}{0:7d}{'—':>13}{'—':>12}")
            rows.append({"tol": tol, "n": 0})
            continue
        d = np.array([p["d_rms"] for p in ps])
        s = np.array([p["d_rms"] / p["dlevel"] for p in ps])
        print(f"{tol:10.3f}{len(ps):7d}{np.median(d):13.3f}{np.median(s):12.3f}")
        rows.append({"tol": tol, "n": len(ps), "median_d": float(np.median(d)),
                     "median_slope": float(np.median(s))})
    if len(set(counts)) < 2:
        sys.exit(f"GATE U8 FAIL: the tolerance never changes the pair count ({counts[0]} at every "
                 f"setting) -- the knob is not turning, so this is a constant printed six times "
                 f"(s106 GATE N5)")
    print(f"  U8 OK   the tolerance binds: pair count moves {min(counts)} -> {max(counts)}")
    out["u8"] = rows


# --------------------------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("report")
    ap.add_argument("--method", default=None, help="re-grade from a stored FR read (csd|h1|h1band)")
    ap.add_argument("--json", help="write the result to this path")
    args = ap.parse_args()

    K.check_shipped_constant()

    bands, idx, rows, used = RG.deltas(args.report, args.method)
    caps = MG.load(args.report)[1]
    drops, _, gap = MG.find_dropouts(bands, caps, args.method)
    MG.check_dropout_separation(gap, drops)
    subs = RG.subsets(rows, drops)
    od_rows = subs["OD"]
    non_hf = [j for j, i in enumerate(idx) if bands[i] < HF_HZ]

    print(f"=== GATE U -- the matched-bleed LEVEL instrument: {args.report.split('/')[-1]} ===")
    print(f"    FR read: {used}   graded {MG.GRADE_LO:g}-{MG.GRADE_HI:g} Hz   "
          f"OD rows {len(od_rows)}   ex-HF bands {len(non_hf)} of {len(idx)}")
    print(f"    dropouts excluded: {len(drops)}   LEVEL taper exponent "
          f"{K.SHIPPED_LEVEL_TAPER_EXP}\n")

    out = {"report": args.report, "method": used, "n_od_rows": len(od_rows),
           "bleed_tol": BLEED_TOL, "min_dlevel": MIN_DLEVEL}

    gate_u1(od_rows, bands, idx, args.report, out)
    fam = gate_u2(caps, od_rows, non_hf, idx, out)
    gate_u3(out)
    pairs = gate_u4(fam, out)
    gate_u4b(fam, out)
    gate_u5(fam, out)
    gate_u6(fam, pairs, out)
    gate_u7(pairs, out)
    gate_u8(fam, out)

    if args.json:
        with open(args.json, "w", encoding="utf-8") as fh:
            json.dump(out, fh, indent=1, default=float)
        print(f"\nwrote {args.json}")
    print("\nGATE U complete.")


if __name__ == "__main__":
    main()
