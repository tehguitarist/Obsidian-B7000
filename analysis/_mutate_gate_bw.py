#!/usr/bin/env python3.11
"""Mutation test for GATE BW (analysis/n2_window_gate.py).

GATE BW resolves s201's owed step: whether the model's N2 has MOVED out of GATE W's fixed window
or is GONE at played GRUNT-cut settings.  Its answer CORRECTS a published reading (s201's
"absence dominates migration 3:1"), so every arm below exists to make sure the correction is a
measurement rather than a differently-worded assertion.

⚠⚠ THE THREE ARMS THAT CARRY THE RESULT:

  * `bw3-vacuous` -- THE LOAD-BEARING ONE.  This gate's headline is a NEGATIVE-shaped claim about
    8 cells ("no feature at any depth") resting on a POSITIVE claim about 104 ("there is one").
    s126/s133: a silent estimator and an absent feature are indistinguishable until the estimator
    is shown to find the feature when it IS there.  The arm blinds `_best_interior` and requires
    BW3 to REFUSE against the 36 bleed-free corner cells where GATE BV independently measured the
    model resolving N2 36 of 36.  If this arm ever goes GUARD DEAD, no ABSENT count in this gate
    is readable and the whole verdict must be withdrawn.

  * `bw5-bar-order` -- the gate's central correction is that ABSENT (no interior minimum at all)
    and BELOW-BAR (a real minimum, shallower than a threshold) are DIFFERENT findings with
    different owners, and `classify` enforces that by testing `n_interior` FIRST.  The arm swaps
    the two tests and requires the bar sweep to report ABSENT collapsing to 0 -- i.e. it proves the
    ORDER is doing work and the three-way split is not decoration.

  * `bw1b-census` -- everything here is quoted against GATE BV's finding, so this gate must be
    reading BV's population through BV's predicate.  The arm perturbs the validity rule and
    requires the cross-gate census check to fail.  Without it, "0 of 112" here and "0 of 112"
    there could be two different populations agreeing by luck (s149: re-implementing a shared
    helper is how gates start to disagree).

⚠ WHAT NO ARM CAN TEST, stated rather than left to be discovered:
  * **Whether `_best_interior` is the right estimator.**  It is E2 in GATE AV0's census, chosen
    because it requires a two-sided interior minimum and therefore refuses a monotone flank -- but
    that is a DESIGN choice imported from s126's repair, and a mutation test cannot validate a
    definition (`_mutate_gate_bv`'s own limitation, same wording).
  * **The search domain.**  `od_tone_restore_fit.SHOULDER` is imported from the stage that owns
    this feature.  `bw0-shoulder-*` prove BW0's two structural assertions FIRE, not that (210,520)
    is the correct territory for N2.
  * **The pedal/model asymmetry.**  BW7 names it as unexplained; no arm can test an open question.
  * **Anything about N2's DEPTH.**  This gate grades presence only, and says so.

⛔ GATE BW RENDERS NOTHING -- it reads GATE BV's cache -- so no arm can damage a render epoch, and
there is no render-dir redirect below.  Only the output JSON is made PID-unique.

Mechanics (s110/s139/s153/s107/s117): the mutant lives in analysis/ and runs from the repo root,
its path and output JSON are PID-unique, each redirect REFUSES if its pattern stops applying, an
unmutated CONTROL runs first, and failures are scored on the guard's own tag rather than on a bare
non-zero exit.

Run:  python3.11 analysis/_mutate_gate_bw.py
"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SRC = os.path.join(HERE, "n2_window_gate.py")
PID = os.getpid()
MUT = os.path.join(HERE, f"_mutated_gate_bw_{PID}.py")
OUTJ = f"analysis/reports/_mut_bw_{PID}.json"

OUT_LINE = 'OUT_JSON = "analysis/reports/s202_n2_window.json"'
FEAT_LINE = 'FEATURE = "mid_notch"                      # item 19\'s N2'

# Arms whose point is that a line the CONTROL prints must STOP being printed.  Requiring the needle
# to APPEAR would score a working guard as broken.
DISAPPEARS = set()

ARMS = [
    # ---- refusals: provenance and the structural assertions -------------------------------------
    ("bw0-stale-bin", 1, "GATE BW0",
     "    bmt = os.stat(binp).st_mtime",
     "    bmt = 0.0",
     "make every src file postdate the render binary.  BW0 must refuse -- this gate reads GATE "
     "BV's renders and every model number is a claim about the SHIPPED build specifically (s152; "
     "s185 hit the same-second version of this for real)"),

    ("bw0-shoulder-reaches-bt", 1, "s151's feature jump is REACHABLE",
     FEAT_LINE,
     "F.SHOULDER = (210.0, 700.0)\n" + FEAT_LINE,
     "widen the search domain until it reaches `bt_notch`'s window.  BW0 must refuse: s151 MEASURED "
     "that a window wide enough to hold this null's right shoulder puts the global minimum at "
     "~550 Hz (f0 550.8, depth 0.000), so the reader tracks the bridged-T instead.  This gate's "
     "whole search is only sound because that is structurally impossible"),

    ("bw0-no-contain", 1, "does not strictly contain",
     FEAT_LINE,
     "F.SHOULDER = (300.0, 340.0)\n" + FEAT_LINE,
     "shrink the search domain inside GATE W's own window.  BW0 must refuse: a search that cannot "
     "look OUTSIDE the shipped window cannot answer 'did the feature move out of it', and would "
     "report MOVED = 0 by construction while looking like a measurement"),

    ("bw2-empty-population", 1, "GATE BW2",
     'POP_GRUNT = "cut"',
     'POP_GRUNT = "nonesuch"',
     "empty the population.  BW2 must refuse rather than crash -- BW5's shares divide by n and "
     "BW7 would print a verdict over nothing (`empty-gate-must-fail`, and s117's rule that a gate "
     "should REFUSE where it would otherwise hand the next session a stack trace)"),

    # ---- refusals: the known answers ------------------------------------------------------------
    ("bw1a-walk", 1, "BW1a",
     '            "prom": s["prom"], "n_bound_sides": s["n_bound_sides"],',
     '            "prom": s["prom"] + 0.5, "n_bound_sides": s["n_bound_sides"],',
     "offset the pinned walk.  BW1a must fail: the widening column is only readable because the "
     "imported walk at widen 1.0 IS the shipped statistic, so if that binding rots, BW4 is "
     "widening some other number"),

    ("bw1b-census", 1, "BW1b",
     '            "valid": bool(BV.valid(shipped)), "why": BV.refusal_reason(shipped),',
     '            "valid": bool(shipped["prom"] >= 0.1), "why": BV.refusal_reason(shipped),',
     "perturb the validity predicate.  BW1b must fail: this gate's numbers are quoted against GATE "
     "BV's finding, so it has to be reading BV's population through BV's rule and not a second "
     "opinion that happens to land nearby"),

    ("bw3-vacuous", 1, "BW3",
     "    bi = Y._best_interior(d, F.SHOULDER, KIND)",
     '    bi = {"f0": float("nan"), "prom": 0.0, "n_interior": 0}',
     "⭐ blind the interior-minimum finder so it reports NO feature anywhere.  BW3 must refuse "
     "against the 36 corner cells GATE BV measured the model resolving 36 of 36.  This is the arm "
     "that makes an ABSENT count mean anything at all -- without it, 'the feature is gone' and "
     "'this gate cannot see features' are the same output"),

    # ---- computed verdicts (rc == 0): the conclusions must be MEASURED --------------------------
    ("bw5-search-domain", 0, "0 sit ABOVE W's upper bound",
     "    bi = Y._best_interior(d, F.SHOULDER, KIND)",
     "    bi = Y._best_interior(d, WIN, KIND)",
     "restrict the search to GATE W's own window.  The 'MOVED HIGH' cells must vanish and BW5 must "
     "COMPUTE that 0 now sit above the bound -- proving the widened domain is what finds them and "
     "the number is not narrated"),

    ("bw5-bar-order", 0, "⇒ ABSENT is 0 at every bar",
     '    if r["bi_n_interior"] == 0:\n        return "ABSENT"\n    if r["bi_prom"] < bar:\n'
     '        return "BELOW-BAR"',
     '    if r["bi_prom"] < bar:\n        return "BELOW-BAR"\n    if r["bi_n_interior"] == 0:\n'
     '        return "ABSENT"',
     "⭐ swap the two tests in `classify`.  A cell with no feature has prominence 0, so testing the "
     "BAR first swallows every ABSENT cell into BELOW-BAR and the bar sweep must report ABSENT "
     "collapsing to 0.  This proves the three-way split -- the gate's central correction -- is "
     "enforced by the ORDER and is not decoration"),

    ("bw6-monotone", 0, "are NOT monotone",
     "        vals = [m[sw] for sw in W.SWEEPS if sw in m]",
     "        vals = [m[sw] for sw in W.SWEEPS if sw in m]; vals = vals[::2] + vals[1::2]",
     "scramble the stimulus order.  BW6 must COMPUTE that the sequences are no longer monotone -- "
     "the continuity claim (one feature migrating, not a reader alternating between two dimples) "
     "is the only thing licensing the MOVED reading, and it must be falsifiable"),

    ("bw4-bound-sides", 0, "0 of 0 of these cells have BOTH walk",
     "    base = AV.sides_at(d, i, WIN, KIND)",
     "    base = None",
     "drop the walk-termination record.  BW4 must COMPUTE the bound-sides count rather than "
     "asserting AV3's criterion -- '84 of 84 terminate on a bound' is what says the shipped "
     "prominence is a window statement, and a hard-coded version of it would be narration"),
]


def build(find, repl):
    src = open(SRC).read()
    if find not in src:
        return None
    src = src.replace(find, repl, 1)
    if OUT_LINE not in src:
        return "REDIRECT-FAILED -- the output-path line has moved; refusing to clobber the real report"
    return src.replace(OUT_LINE, f'OUT_JSON = "{OUTJ}"', 1)


def run(mut_src):
    open(MUT, "w").write(mut_src)
    p = subprocess.run([sys.executable, MUT, "--jobs", "8"], cwd=ROOT,
                       capture_output=True, text=True, timeout=3600)
    return p.returncode, p.stdout + p.stderr


def cleanup():
    for p in (MUT, os.path.join(ROOT, OUTJ)):
        if os.path.exists(p):
            os.remove(p)


def main():
    print("=" * 92)
    print("MUTATION TEST -- GATE BW")
    print("=" * 92)
    ctl_src = open(SRC).read()
    assert OUT_LINE in ctl_src, "control redirect no longer applies"
    ctl_src = ctl_src.replace(OUT_LINE, f'OUT_JSON = "{OUTJ}"', 1)
    rc, out = run(ctl_src)
    if rc != 0:
        print("CONTROL FAILED -- no arm below is attributable\n")
        print(out[-4000:])
        cleanup()
        sys.exit(1)
    print("  CONTROL ok (rc=0)\n")
    ctl_out = out

    npass = 0
    for name, exp_rc, needle, find, repl, why in ARMS:
        src = build(find, repl)
        if src is None:
            print(f"  {name:<24s} PATCH DID NOT APPLY -- the arm targets code that has moved")
            print(f"      why: {why}")
            continue
        if isinstance(src, str) and src.startswith("REDIRECT-FAILED"):
            print(f"  {name:<24s} {src}")
            print(f"      why: {why}")
            continue
        rc, out = run(src)
        ok_rc = (rc != 0) if exp_rc else (rc == 0)
        if name in DISAPPEARS:
            hit = (needle in ctl_out) and (needle not in out)
        else:
            hit = needle in out
        if ok_rc and hit:
            print(f"  {name:<24s} PASS   (rc={rc})")
            npass += 1
        elif not ok_rc:
            tag = "GUARD DEAD" if exp_rc else "CRASHED (expected a computed verdict)"
            print(f"  {name:<24s} {tag}   (rc={rc}, wanted {'non-zero' if exp_rc else '0'})")
            if out.strip():
                print("      " + out.strip().splitlines()[-1][:150])
        else:
            print(f"  {name:<24s} WRONG GUARD / NARRATED -- needle absent: {needle[:60]!r}")
        print(f"      why: {why}")
    print(f"\n  {npass} / {len(ARMS)} arms pass")
    cleanup()
    sys.exit(0 if npass == len(ARMS) else 1)


if __name__ == "__main__":
    main()
