#!/usr/bin/env python3
"""Mutation control for GATE BM (analysis/mix_grid_anchor_gate.py).

Scores exit code AND a required output token (s128): BM's load-bearing statements are COMPUTED
VERDICTS that deliberately do not change the exit code, so an `rc != 0` runner could only ever test
the plumbing.  An arm with expect_rc = 0 breaks the data behind a verdict and requires the gate to
print the OPPOSITE one — so a conclusion that has quietly become narration fails here.

⭐⭐ THREE ARMS REPRODUCE REAL DEFECTS IN THIS GATE'S OWN DRAFTS, WHICH IS THE ONLY REASON THEY ARE
WORTH THE LINES:
  `bm0g-broadband`  the first draft gated the notch arm's localisation as a RATIO
                    (out-of-window / in-window peak < 1).  It FAILED at 3.38x — against a cell
                    whose in-window peak is 0.0020 dB, i.e. one where the arm does nothing.  All 37
                    offending cells had in-window peaks <= 0.0137 dB: the statistic divided noise
                    by noise (`ratio-statistics-need-a-denominator-guard`).  The shipped test
                    regresses both peaks on |Δcut| instead, so the intervention is the REGRESSOR
                    rather than the divisor.
  `bm2-direction`   the first draft NARRATED "THE CORNER OVERSTATES THE WORST PLAYED CELL BY 0.5x"
                    directly above the two numbers that refute it (12.25 dB corner vs 25.03 dB
                    played) — `computed-verdicts-not-narrated`, in the sentence that decides the
                    session's whole priority ordering.
  `bm4-attribution` a draft inferred the notch's contribution to the null's depth by SUBTRACTING
                    TWO MEDIANS (total − mix-only), got −0.696 dB, and would have published it.
                    A median is not linear; the PAIRED column reads −0.090 dB
                    (`paired-cells-need-paired-differences`).

⚠ RENDER/CURVE DIRECTORY: redirected to one PID-unique path SHARED BY EVERY ARM of a run, not per
arm.  The curves are a function of their argv, so an arm that does not change a render's argv is a
cache hit; only the arms that deliberately change one pay for it.  Per-arm dirs would re-render the
whole 432-condition grid once per arm for no added coverage.

⛔ THE FIRST RUN OF ANY ARM THAT CHANGES AN ARGV PAYS ~5.5 s PER CONDITION.  Arms are ordered so
the cheap guard arms (which exit inside BM0, before the grid renders) come first.
"""
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SRC = os.path.join(HERE, "mix_grid_anchor_gate.py")
MUTANT = os.path.join(HERE, f"_mutated_gate_bm_{os.getpid()}.py")
PY = "/opt/homebrew/bin/python3.11"

# (name, [(pattern, replacement), ...], expect_rc, must_contain, why)
ARMS = [
    ("control", [], 0, "IS CONFIRMED",
     "unmutated: every guard passes AND the censoring verdict reaches its real, COMPUTED answer.  "
     "If this does not hold, no arm below is attributable."),

    # ---- BM0a: the two epoch guards on the transcribed mix law ---------------------------
    ("bm0a-depthoff",
     [(r"SHIPPED_DEPTH_OFFSET_DB = 3\.0", "SHIPPED_DEPTH_OFFSET_DB = 3.5")],
     1, "odNotchDepthDb",
     "claim a shipped depth offset FitParams.h does not carry.  The gate must refuse: the third "
     "arm is `shipped + delta`, so a stale base value silently moves the notch in the one arm "
     "whose whole purpose is to hold the notch fixed."),

    ("bm0a-pin",
     # ⚠ THE NODE MATTERS (s110's third shape of a vacuous mutation, and BL's runner hit it):
     # S(0.441) interpolates between nodes 3 and 4, so perturbing node 1 CANNOT move the pinning.
     # kMixS[3] is the node the pinning is made of.
     [(r"MIX_S = \(0\.951, -0\.525, -0\.195, 0\.000,",
       "MIX_S = (0.951, -0.525, -0.195, 0.100,")],
     1, "not pinned at kMixCfRef",
     "perturb the transcribed mix shape AT THE NODE THAT SETS THE PINNING.  The gate must refuse "
     "rather than compute the third arm's `odNotchDepthDb` — and therefore the entire two-"
     "mechanism split — from a stale copy of OdToneRestore.h (s149)."),

    # ---- BM0b: the mirror check that licenses the split off the corner -------------------
    ("bm0b-mirror",
     [(r"b = K\.coef_nodal\(bv, L, endstop=es\)",
       "b = tuple(1.001 * v for v in K.coef_nodal(bv, L, endstop=es))")],
     1, "BM0b FAILED",
     "detune one of GATE K's two coefficient mirrors on the INTERIOR of the grid.  BM0b must "
     "refuse — off the corner is exactly where s182 found both mirrors stale while they still "
     "agreed with each other, and BM1's whole analytic bracket rests on them."),

    # ---- BM0c/BM0d/BM0e: the render-level scope and plumbing controls --------------------
    ("bm0c-scope",
     [(r'BL\.render\("scope_blend0_ship", BL\.cond_args\(0\.5, 1, blend=0\.0\)\)',
       'BL.render("scope_blend0_ship_mut", BL.cond_args(0.5, 1, blend=0.5))')],
     1, "BM0c FAILED",
     "move ONE side of the scope pair to BLEND = 0.5, where the end stop genuinely acts.  BM0c "
     "must fire — otherwise 'the clean path is untouched' is asserted, not measured."),

    ("bm0d-vacuous",
     [(r'BL\.render\("bm0_listen_e0", arm_args\(LISTENING, 0\.5, 1, "e0"\)\)',
       'BL.render("bm0_listen_e0_vac", arm_args(LISTENING, 0.5, 1, "ship"))')],
     1, "BM0d FAILED",
     "make the e0 arm the shipped stage AT THE LISTENING CELL.  BM0d must fire — this gate's "
     "entire question is whether anything moves OFF the corner, so a non-vacuity arm at the "
     "corner (which is all GATE BL has) would prove nothing here."),

    ("bm0e-clean",
     [(r'BL\.render\("bl0_clean_alt", BL\.cond_args\(1\.0, 0, blend=0\.0\)\)',
       'BL.render("bl0_clean_alt_od", BL.cond_args(1.0, 0, blend=1.0))')],
     1, "BM0e FAILED",
     "make the second 'clean' render carry the OD path.  BM0e must fire."),

    # ---- BM0f: the cross-gate known answer ----------------------------------------------
    ("bm0f-crossgate",
     [(r"flat_bl, flat_me = blr\[\"flat_db\"\], 20\.0 \* math\.log10\(1\.0 - e_hi\)",
       "flat_bl, flat_me = blr[\"flat_db\"], 20.0 * math.log10(1.0 - 2.0 * e_hi)")],
     1, "BM0f FAILED",
     "compute the flat term from 2e instead of e, so it no longer reproduces GATE BL's STORED "
     "value.  BM0f must refuse — it is what licenses quoting this gate's corner column beside "
     "s183's published one (s159's AW1b)."),

    # ---- BM0g: the three-arm decomposition ----------------------------------------------
    ("bm0g-inert",
     [(r'extra = \("--fit", "blendEndStop=0",\n                 "--fit", '
       r'f"odNotchDepthDb=\{SHIPPED_DEPTH_OFFSET_DB \+ dcut:\.9f\}"\)',
       'extra = ("--fit", "blendEndStop=0")')],
     1, "never moves in-window",
     "drop `odNotchDepthDb` from the third arm so `mixfroz` IS `e0`.  BM0g must fire — otherwise "
     "the whole change is attributed to the mix coefficients for a plumbing reason (s100), which "
     "is precisely the wrong half of BM4's attribution."),

    # ⚠⚠ THIS ARM'S FIRST FORM EXPECTED **BM0g** TO CATCH THE PERMUTATION AND IT READ GUARD DEAD —
    # correctly, and the GATE's claim was the thing that was wrong, not the arm.  Permuting
    # GRUNT_ENUM changes the INTERVENTION (the third arm's `odNotchDepthDb`) and the PREDICTION
    # (−K[g][d]) through the SAME table, so BM0g's sign test moves both sides together and still
    # passes 539/539.  That is s182's own defect and the fourth occurrence of s145 AM1a / s149 AO2:
    # a known answer cannot validate what both of its sides take as INPUT.  ⇒ BM0h was built to be
    # the independent check (it uses `kNotchGainDb` and the RENDER, neither of which the mutation
    # touches), the gate's false claim was withdrawn, and this arm now targets BM0h.
    ("bm0h-permute",
     [(r"GRUNT_ENUM = \{0: 2, 1: 0, 2: 1\}", "GRUNT_ENUM = {0: 0, 1: 1, 2: 2}")],
     1, "BM0h FAILED",
     "index the notch tables with the RAW APVTS GRUNT order instead of the enum order.  BM0h must "
     "fire: the render is produced by the C++'s own `gruntEnum()`, so the MEASURED notch depths "
     "keep the true order while the gate's row assignment does not — the s151 trap made "
     "mechanically detectable, which BM0g structurally cannot do."),

    ("bm0h-rowlabel",
     [(r"NOTCH_BASE_DRIVE0 = \(1\.16, 18\.33, 17\.15\)",
       "NOTCH_BASE_DRIVE0 = (1.16, 18.33, 17.99)")],
     1, "no kNotchGainDb row labelled",
     "claim a Boost DRIVE-0 base cut the header does not carry.  The row-label pin must refuse — "
     "BM0h reads that table's ORDER, so a stale transcription would silently invert the only "
     "guard that can catch a permuted GRUNT row."),

    ("bm0g-broadband",
     [(r"inw = \(g >= OT\.SHOULDER\[0\]\) & \(g <= OT\.SHOULDER\[1\]\)\n    outw = "
       r"\(\(g >= F_LO_GRADE\) & \(g <= F_HI_GRADE\)\) & ~inw\n    go = g\[outw\]",
       "outw = (g >= OT.SHOULDER[0]) & (g <= OT.SHOULDER[1])\n    inw = "
       "((g >= F_LO_GRADE) & (g <= F_HI_GRADE)) & ~outw\n    go = g[outw]")],
     1, "is NOT localised",
     "swap the in-window and out-of-window masks, so the notch's own band is scored as the "
     "'outside'.  The localisation slope test must fire.  ⚠ This is the arm whose FIRST form (a "
     "raw peak RATIO) failed against correct code at 3.38x on a cell where |Δcut| = 0.017 dB — "
     "the shipped test regresses on |Δcut| so a near-inert cell cannot move it."),

    # ---- BM4: the empty-gate guard ------------------------------------------------------
    ("bm4-empty",
     [(r"a = OT\.notch_geometry\(g, c\[\"e0\"\]\)",
       "raise RuntimeError('forced — no reading here')\n            "
       "a = OT.notch_geometry(g, c[\"e0\"])")],
     1, "empty-gate-must-fail",
     "make every E6 reading refuse.  BM4 must EXIT rather than print medians over nothing — an "
     "empty gate that narrates is the failure mode `empty-gate-must-fail` names, and here it "
     "would silently answer s183 §10's hypothesis with no data at all."),

    # ---- COMPUTED VERDICTS (expect_rc 0): the half an exit-code runner cannot reach ------
    ("bm2-direction",
     # Force the played cells' shape maxima below the corner's, leaving the corner untouched, so
     # the corner really IS the worst cell and the verdict must say the opposite of what it says.
     [(r'"shape_max": float\(np\.abs\(ss\)\.max\(\)\),',
       '"shape_max": float(np.abs(ss).max()) * (1.0 if (lv, bv) == CORNER else 0.1),')],
     0, "THE CORNER IS THE WORST CELL",
     "shrink every PLAYED cell's shape maximum so the corner genuinely becomes the worst.  The "
     "verdict MUST flip.  This gate's first draft NARRATED the direction — it printed 'THE CORNER "
     "OVERSTATES THE WORST PLAYED CELL BY 0.5x' above numbers saying the opposite, which is the "
     "sentence the session's priority ordering was drawn from."),

    ("bm3-membership-computed",
     [(r"ok_a = not a\[\"edge\"\] and a\[\"prom\"\] >= W\.MIN_PROM_DB", "ok_a = True"),
      (r"ok_b = not b\[\"edge\"\] and b\[\"prom\"\] >= W\.MIN_PROM_DB", "ok_b = True")],
     0, "0.0 % ->   0.0%",
     "admit every reading on both arms, removing BOTH mechanisms by which membership can move "
     "(W3 admits on a prominence bar AND an edge test — BL's runner learned that the hard way).  "
     "Every membership RATE must fall to zero."),

    ("bm4-censoring-computed",
     # Make the PLAYED point-depth deltas as large as the corner's, so the "corner-only"
     # hypothesis is false in the data and the gate must report it refuted.
     [(r'"dp": b\["depth_point"\] - a\["depth_point"\],',
       '"dp": (b["depth_point"] - a["depth_point"]) '
       '* (1.0 if tuple(c["mix"]) == CORNER else 40.0),')],
     0, "IS REFUTED",
     "scale the PLAYED point-depth deltas up so the censoring plainly persists off the corner.  "
     "The verdict MUST flip from CONFIRMED to REFUTED — s183 §10 handed 'this is corner-only' "
     "forward as a WORKING HYPOTHESIS, and a gate that cannot print the refutation is not "
     "testing it."),

    ("bm4-attribution",
     [(r'"dp_mixonly": b\["depth_point"\] - f\["depth_point"\],',
       '"dp_mixonly": (b["depth_point"] - f["depth_point"]) * 0.05,')],
     0, "IS NOT SUPPORTED",
     "shrink the bleed's own (paired) contribution to the null's depth.  The attribution verdict "
     "MUST flip to NOT SUPPORTED.  A draft of this gate inferred that contribution by subtracting "
     "two MEDIANS and got -0.696 dB where the paired value is -0.090 "
     "(`paired-cells-need-paired-differences`)."),
]


def run(name, subs, expect_rc, token, why):
    src = open(SRC).read()

    # Redirect the mutant's outputs FIRST, and REFUSE if a redirect does not apply — s153: a
    # redirect that silently no-ops restores the exact bug it was added to prevent, and the last
    # arm's deliberately falsified report is then left on disk wearing the real gate's filename.
    redirects = [
        (r'CURVE_DIR = "build/s184_mix_grid_curves"',
         f'CURVE_DIR = "build/_mut_bm_{os.getpid()}"'),
        (r'default="analysis/reports/s184_mix_grid_anchor\.json"',
         f'default="analysis/reports/_mut_bm_{os.getpid()}.json"'),
    ]
    for pat, rep in redirects:
        src, n = re.subn(pat, rep, src)
        if n == 0:
            print(f"  {name:24s} RUNNER BROKEN: output redirect {pat!r} did not apply")
            return False

    for pat, rep in subs:
        src, n = re.subn(pat, rep, src)
        if n == 0:
            print(f"  {name:24s} PATCH DID NOT APPLY: {pat!r}")
            return False

    open(MUTANT, "w").write(src)
    try:
        res = subprocess.run([PY, MUTANT], cwd=ROOT, capture_output=True, text=True)
    finally:
        if os.path.exists(MUTANT):
            os.remove(MUTANT)

    out = res.stdout + res.stderr
    rc_ok = res.returncode == expect_rc
    tok_ok = token in out
    if rc_ok and tok_ok:
        print(f"  {name:24s} PASS   (rc={res.returncode}, saw {token!r})")
        return True
    kind = "GUARD DEAD" if not rc_ok else "NARRATED"
    print(f"  {name:24s} {kind}  (rc={res.returncode} want {expect_rc}; "
          f"token {token!r} {'seen' if tok_ok else 'MISSING'})")
    print(f"      why this arm exists: {why}")
    for line in [l for l in out.splitlines() if l.strip()][-6:]:
        print(f"      | {line}")
    return False


def cleanup():
    """Sweep by PATTERN in a finally, not by this run's pid — a runner that crashes part-way
    otherwise leaves a deliberately falsified report on disk for someone else to find (s153)."""
    import glob
    import shutil
    for p in glob.glob(os.path.join(ROOT, "analysis/reports/_mut_bm_*.json")):
        os.remove(p)
    for d in glob.glob(os.path.join(ROOT, "build/_mut_bm_*")):
        shutil.rmtree(d, ignore_errors=True)
    for m in glob.glob(os.path.join(HERE, "_mutated_gate_bm_*.py")):
        os.remove(m)


def main():
    print(f"mutation control for GATE BM — {len(ARMS)} arms\n")
    try:
        ok = sum(run(*a) for a in ARMS)
    finally:
        cleanup()
    print(f"\n{ok}/{len(ARMS)} arms behaved as required")
    return 0 if ok == len(ARMS) else 1


if __name__ == "__main__":
    sys.exit(main())
