#!/usr/bin/env python3
"""Mutation control for GATE BO (analysis/mix_membership_gate.py).

Scores exit code AND a required output token (s128).  BO's load-bearing statements are COMPUTED
VERDICTS that deliberately leave the exit code at 0 — the ordering comparison, the argmax
reduction, the censoring attribution — so a runner scoring `rc != 0` alone could only test the
plumbing.  An arm with expect_rc = 0 breaks the data behind a verdict and requires the gate to
print the OPPOSITE one, so a conclusion that has quietly become narration fails here.

⭐⭐ THREE ARMS REPRODUCE REAL DEFECTS IN THIS GATE'S OWN DRAFTS, which is the only reason they
earn their lines:
  `bo2-signedrank`  the first draft ranked by the SIGNED correction while labelling the result
                    "worst -> best", which put a cell needing -2.1 dB ahead of one needing -9.8.
                    `computed-verdicts-not-narrated`, committed in the one line the gate is graded
                    on.  The shipped gate ASSERTS that its ordering is sorted by |corr| descending.
  `bo5-overlap`     a draft attributed the sign disagreement to censoring on a COUNT of cells
                    "within 3 dB of the residue" — a bar that flags 11 of 11 here, so the verdict
                    fired on `6 > 5`, which is a difference in how many cells each arm has and not
                    a rate (`check-n-before-reading-a-trend`).  The shipped gate grades the
                    complete SEPARATION of the margins and says so when they overlap instead.
  `bo0c-vacuous`    the two arms of the whole comparison must be shown to render DIFFERENTLY; an
                    equality-only guard set cannot detect a broken comparison (s183), and a
                    self-comparison would print a perfect ordering agreement.

⚠ RENDER DIRECTORY: redirected to ONE PID-unique path shared by every arm.  `OT.curves`' `ren_dir`
default binds at DEF time, so patching `OT.REN_DIR` after import does nothing — the gate therefore
passes `ren_dir=REN_DIR` explicitly at every call site and this runner rewrites that one constant.
The curves are a function of their argv, so the first arm pays the renders and the rest hit cache.
⛔ Arms that exit inside BO0/BO1 are ordered first — they cost no renders at all.
"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SRC = os.path.join(HERE, "mix_membership_gate.py")
MUTANT = os.path.join(HERE, f"_mutated_gate_bo_{os.getpid()}.py")
PY = "/opt/homebrew/bin/python3.11"
REN = f"build/_mut_bo_{os.getpid()}_renders"
JSON = f"build/_mut_bo_{os.getpid()}.json"

# (name, [(pattern, replacement), ...], expect_rc, must_contain, why)
ARMS = [
    ("control", [], 0, "THE ARGMAX ITSELF MOVES",
     "unmutated: every guard passes AND the graded comparison reaches its real, COMPUTED answer. "
     "If this does not hold, no arm below is attributable."),

    # ---- BO0 / BO1: guards that must REFUSE (no renders reached) -----------------------------
    ("bo0a-grunt",
     [('"flat":  {0.0: "drive-0700_level-1700_grunt-flat_base-od.wav",',
       '"flat":  {0.0: "drive-0700_level-1700_grunt-boost_base-od.wav",')],
     1, "BO0a",
     "put a GRUNT-BOOST capture in the flat slot.  Every capture without a `grunt-` token is GRUNT "
     "= CUT and a mislabelled row is invisible in a filename, so membership must be resolved from "
     "the capture's OWN parsed settings and REFUSE on drift (s114, s151)."),

    ("bo0b-notonlylevel",
     [('        "cut":   {0.0: "drive-0700_base-od.wav",\n                  0.5: "ref-od.wav"},',
       '        "cut":   {0.0: "drive-0700_base-od.wav",\n'
       '                  0.5: "level-1700_blend-1430_base-od.wav"},')],
     1, "BO0b",
     "swap a mix cell for one that differs from its bleed-free twin in BLEND rather than LEVEL. "
     "The whole comparison rests on the arms differing in the mix ALONE — otherwise a rank change "
     "is attributable to whatever else moved — so the gate must refuse."),

    ("bo1-premise",
     [('r[0] in ("grunt_flat", "grunt_boost", "grunt_hot", "grunt_cold")',
       'r[0] in ("grunt_flat", "grunt_boost", "grunt_hot", "grunt_cold", "listen")')],
     1, "BO1",
     "admit a MIXED group into the set BO1 measures as the bleed-free GRUNT axis.  BO1's premise "
     "— that the axis is 12/12 bleed-free — is what the whole framing rests on, so it must be "
     "measured and must refuse when it stops holding, not asserted in a docstring."),

    ("bo4-gap",
     [("if prev_cf is not None and prev_cf - cf > 0.15:",
       "if prev_cf is not None and prev_cf - cf > 5.0:")],
     1, "BO4",
     "raise the LEVEL-ladder gap bar past anything reachable.  BO4's free corroboration of s185 "
     "is that the detents jump cf 0.244 -> 0.024 with no capture between; if that gap is not "
     "found, the corroboration is not there to claim and the gate must say so."),

    # ---- computed verdicts: rc stays 0, the CONCLUSION must invert ---------------------------
    ("bo0c-vacuous",
     [('    _, pb, mb = OT.curves(ARMS["mix"]["cut"][0.5], PLAY_SWEEP, ren_dir=REN_DIR)',
       '    _, pb, mb = OT.curves(ARMS["bleedfree"]["cut"][0.5], PLAY_SWEEP, ren_dir=REN_DIR)')],
     1, "BO0c",
     "compare the bleed-free arm against ITSELF.  A comparison whose two arms are the same audio "
     "confirms nothing and would print a perfect ordering agreement; only a guard that requires "
     "the arms to DIFFER can catch it (s183 — an equality-only guard set cannot)."),

    ("bo2-signedrank",
     [("order = sorted(ok, key=lambda k: -abs(ok[k]))",
       "order = sorted(ok, key=lambda k: -ok[k])")],
     1, "BO2",
     "reproduce this gate's own first-draft defect: rank by the SIGNED correction while the label "
     "says 'furthest off'.  The shipped assertion that the ordering is sorted by |corr| descending "
     "must fire."),

    ("bo2-narrated",
     [('                got[gname] = None if c["refused"] else float(c["corr_area"])',
       '                got[gname] = None if c["refused"] else float(\n'
       '                    cells[("bleedfree", gname, GRADE_DRIVE, sw)]["corr_area"])')],
     0, "the GRUNT ordering SURVIVES the mix",
     "feed BOTH arms the bleed-free corrections, so the two orderings become identical.  The "
     "verdict must then read SURVIVES.  This is the arm that proves 'DOES NOT SURVIVE' is computed "
     "from the data rather than hard-coded — the failure mode s128 built this runner shape for."),

    ("bo2-argmax",
     [('        firsts = [ranks[(arm, sw)][0] for sw in SWEEPS if ranks.get((arm, sw))]',
       '        firsts = [ranks[(arm, sw)][0] for sw in SWEEPS if ranks.get((arm, sw))]\n'
       '        firsts = ["boost"] * len(firsts)')],
     0, "the argmax SURVIVES the mix",
     "force both arms' rank-1 position to agree while leaving the full ordering alone.  The "
     "reduction must then report agreement — so the two statements ('the full ordering differs' "
     "and 'the argmax moves') are shown to be independently computed, not one narrated twice."),

    ("bo5-overlap",
     [('                flip = (cp * ca) < 0',
       '                flip = ((cp * ca) < 0) or (arm == "mix" and gname == "cut")')],
     0, "UNATTRIBUTED",
     "make one MIX cell sign-opposed at a margin that sits inside the agreeing population.  The "
     "margins then overlap, and the gate must withdraw the censoring attribution rather than "
     "keeping it on the rate alone — the defect a draft committed by counting a 3 dB bar that "
     "flags every cell."),
]


def run(name, subs, expect_rc, must, why):
    src = open(SRC).read()
    for pat, rep in subs:
        if pat not in src:
            return "PATCH DID NOT APPLY", f"pattern not found: {pat[:70]}"
        src = src.replace(pat, rep, 1)
    # Redirect the report AND the render dir so an arm cannot overwrite the real artefacts (s153:
    # a faithful copy of a tool inherits that tool's side effects, and the last arm's output would
    # otherwise be left on disk wearing the real gate's filename).
    before = src
    src = src.replace('REPORT = "analysis/reports/s186_mix_membership.json"', f'REPORT = "{JSON}"')
    src = src.replace("REN_DIR = OT.REN_DIR", f'REN_DIR = "{REN}"')
    if src == before:
        return "REDIRECT FAILED", "neither REPORT nor REN_DIR was rewritten — a redirect that "\
                                  "silently no-ops restores the bug it was added to prevent"
    open(MUTANT, "w").write(src)
    try:
        p = subprocess.run([PY, MUTANT], cwd=ROOT, capture_output=True, text=True, timeout=5400)
    finally:
        if os.path.exists(MUTANT):
            os.remove(MUTANT)
    out = p.stdout + p.stderr
    if p.returncode != expect_rc:
        return "WRONG RC", f"rc {p.returncode}, expected {expect_rc}"
    if must not in out:
        return "NARRATED", f"rc ok but output lacks {must!r}"
    return "PASS", ""


def main():
    only = sys.argv[1:] or None
    npass = 0
    arms = [a for a in ARMS if not only or a[0] in only]
    for name, subs, rc, must, why in arms:
        status, detail = run(name, subs, rc, must, why)
        print(f"  [{status:>18}]  {name}")
        if status != "PASS":
            print(f"       {detail}")
        print(f"       {why}")
        npass += status == "PASS"
    print(f"\n  {npass}/{len(arms)} arms")
    sys.exit(0 if npass == len(arms) else 1)


if __name__ == "__main__":
    main()
