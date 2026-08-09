#!/usr/bin/env python3.11
"""Mutation test for GATE BR (analysis/hf_region_breakdown.py).  Session 191.

GATE BR decomposes a published matrix cost, and its output is read as a SEQUENCING decision (does
the OD 8-16.3 kHz p90 cost overlap item 17's treble notch, or not?).  Everything it prints is
either an order statistic recomputed from `release_gate`'s own pool or a membership count, so the
arms below fall into three groups:

  * REFUSALS — the guards that stop it decomposing a statistic other than the one it names.
  * COMPUTED VERDICTS (`expect_rc == 0`) — the two sentences a reader would actually quote (the
    carrier/DISTRIBUTED line and the in/outside-the-notch line).  Neither may be a printed string:
    `computed-verdicts-not-narrated` has eight prior occurrences in this project, one of them
    committed INSIDE a gate written to apply the rule, and one (s184) in exactly this position —
    the one sentence a session's priority order is drawn from.
  * DISAPPEARS — arms whose point is that a line the control prints must STOP being printed.

⚠ WHAT NO ARM HERE CAN TEST, stated rather than left to be discovered:
  * **Whether the overlap is a shared MECHANISM.**  BR3's verdict is a band-membership statement
    and the gate says so on every run.  Nothing here measures a carrier.
  * **Whether the two reports are the right two.**  They are NAMED (`DEF_BEFORE`/`DEF_AFTER`)
    precisely so the comparison cannot silently re-point, which means a wrong pair is a wrong
    invocation, not a defect this runner can catch.
  * **The treble notch's own window.**  4200-12000 Hz and 6150-10708 Hz are imported facts from
    GATE W and item 19's N4; if THOSE are wrong, every overlap verdict is wrong with them.

Mechanics (s110/s139/s153/s107/s117): the mutant lives in analysis/ and runs from the repo root,
its path and its output JSON are PID-unique, an unmutated CONTROL runs first, and each failure is
scored on the guard's own tag rather than on a bare non-zero exit.

Run:  python3.11 analysis/_mutate_gate_br.py
"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SRC = os.path.join(HERE, "hf_region_breakdown.py")
PID = os.getpid()
MUT = os.path.join(HERE, f"_mutated_gate_br_{PID}.py")
OUTJ = f"analysis/reports/_mut_br_{PID}.json"

ARMS = [
    # ---- refusals ------------------------------------------------------------------------------
    ("br0-band-grid", 1, "do not share a band grid",
     "    if bandsB != bandsA:",
     "    if bandsB == bandsA:",
     "invert the band-grid check.  Two reports on different grids cannot be differenced band for "
     "band, and the resulting table would look entirely normal — every column would just be "
     "comparing different frequencies"),

    ("br0-method", 1, "FR method differs",
     "    if usedB != usedA:",
     "    if usedB == usedA:",
     "invert the FR-method check.  `the instrument is part of the number` (s90): csd, h1 and "
     "h1band are three different reads of the same renders, and differencing across them measures "
     "the instrument"),

    ("br1-known-answer", 1, "does not reproduce release_gate",
     "        for stat, mine in ((\"median\", float(np.median(vals))), (\"p90\", p90(vals))):",
     "        for stat, mine in ((\"median\", float(np.median(vals)) + 0.5), (\"p90\", p90(vals))):",
     "break the recomputed pool by half a dB.  The known answer must refuse — without it this tool "
     "could decompose a DIFFERENT statistic than the release-gate number it claims to be "
     "explaining, and every per-band column below would still look plausible"),

    ("br0-empty-region", 1, "selects no graded band",
     "    sel = RG.region_sel(bandsA, idxA, region)",
     "    sel = []",
     "empty the region selection.  A region that matches nothing must refuse rather than print a "
     "table of NaNs (`empty-gate-must-fail`)"),

    ("br0-no-shared-row", 1, "share no graded row",
     "    shared = sorted(set(subB) & set(subA))",
     "    shared = []",
     "empty the matched membership.  Every statistic below is paired, so an empty intersection "
     "makes all of them vacuous — and the p90 of an empty array is a NaN that no threshold catches "
     "(s106's `nan` trap)"),

    # ---- computed verdicts (expect_rc == 0) -----------------------------------------------------
    ("br3-distributed", 0, "DISTRIBUTED: no single band carries",
     '        dominant = (sub[top]["share_pct"] > 50.0\n'
     '                    and (runner is None or sub[top]["share_pct"] - sub[runner]["share_pct"] > 20.0))',
     "        dominant = True  # MUTANT",
     "make ANY leading band count as dominant.  The DISTRIBUTED branch must stop being taken and a "
     "single CARRIER must be named instead — if the control's DISTRIBUTED line survives this, it "
     "is narration rather than a reading of the share column"),

    ("br3-overlap", 0, "MOSTLY by bands outside",
     "        inside = (TREBLE_NOTCH_WINDOW[0] <= f < TREBLE_NOTCH_WINDOW[1]\n"
     "                  or TREBLE_NOTCH_MEASURED[0] <= f <= TREBLE_NOTCH_MEASURED[1])",
     "        inside = False  # MUTANT",
     "move every band OUTSIDE the treble notch's territory.  The in/outside verdict must flip — "
     "this is the single sentence the action list's sequencing decision is drawn from, and s184 "
     "shipped exactly this kind of line with the direction word hard-coded above the two numbers "
     "that refuted it"),

    ("br3-substitution", 1, "GATE BR3 FAIL [vacuous]",
     "        M[:, j] = B[:, j]",
     "        M[:, j] = A[:, j]",
     "make the substitution counterfactual a no-op (revert a band to ITSELF).  Every share must "
     "collapse to 0 %, so the attribution line must stop claiming any band carries anything — an "
     "attribution that survives a null intervention is measuring nothing (s185's own vacuous "
     "sub-gate, which printed a confident PASS while comparing 0 to 0)"),

    ("br6-sign-change", 0, "THE SIGN CHANGES INSIDE THE WINDOW",
     "    if len(set(signs)) > 1:",
     "    if len(set(signs)) > 99:",
     "disable the in-window sign-change branch.  Its verdict must vanish — that line is the whole "
     "reason BR6 exists (a feature MOVING reads as two gated regions moving oppositely), so it "
     "must be a reading of the per-band signs and not a sentence"),

    ("br0-membership-note", 0, "membership is IDENTICAL",
     "    if unmatched != (0, 0):",
     "    if unmatched == (0, 0):",
     "invert the membership branch.  The reassuring IDENTICAL line must stop being printed and the "
     "warning must take its place — `aggregate-moved-check-membership-first` has fired twelve "
     "times, once (s159) inside an epoch comparison exactly like this one"),
]

#: Arms whose needle must be PRESENT in the control and ABSENT in the mutant.
DISAPPEARS = {"br3-distributed", "br6-sign-change", "br0-membership-note"}

JSON_ARG = ["--json", OUTJ]


def run(src):
    open(MUT, "w").write(src)
    p = subprocess.run([sys.executable, MUT] + JSON_ARG, cwd=ROOT,
                       capture_output=True, text=True, timeout=1800)
    return p.returncode, p.stdout + p.stderr


def cleanup():
    for p in (MUT, os.path.join(ROOT, OUTJ)):
        if os.path.exists(p):
            os.remove(p)


def main():
    print("=" * 92)
    print("MUTATION TEST -- GATE BR")
    print("=" * 92)
    ctl = open(SRC).read()
    rc, ctl_out = run(ctl)
    if rc != 0:
        print("CONTROL FAILED -- no arm below is attributable\n")
        print(ctl_out[-4000:])
        cleanup()
        sys.exit(1)
    print("  CONTROL ok (rc=0)\n")

    npass = 0
    for name, exp_rc, needle, find, repl, why in ARMS:
        src = open(SRC).read()
        if find not in src:
            print(f"  {name:<22s} PATCH DID NOT APPLY -- the arm targets code that has moved")
            print(f"      why: {why}")
            continue
        rc, out = run(src.replace(find, repl, 1))
        ok_rc = (rc != 0) if exp_rc else (rc == 0)
        if name in DISAPPEARS:
            hit = (needle in ctl_out) and (needle not in out)
        else:
            hit = needle in out
        if ok_rc and hit:
            print(f"  {name:<22s} PASS   (rc={rc})")
            npass += 1
        elif not ok_rc:
            tag = "GUARD DEAD" if exp_rc else "CRASHED (expected a computed verdict)"
            print(f"  {name:<22s} {tag}   (rc={rc}, wanted {'non-zero' if exp_rc else '0'})")
            tail = out.strip().splitlines()
            if tail:
                print("      " + tail[-1][:150])
        else:
            print(f"  {name:<22s} WRONG GUARD / NARRATED -- {needle!r} not as required")
        print(f"      why: {why}")

    print(f"\n  {npass} / {len(ARMS)} arms pass")
    cleanup()
    sys.exit(0 if npass == len(ARMS) else 1)


if __name__ == "__main__":
    main()
