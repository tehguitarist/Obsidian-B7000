#!/usr/bin/env python3
"""Mutation control for GATE BL (analysis/bleedfree_anchor_gate.py).

Scores exit code AND a required output token (s128): BL's load-bearing statements are COMPUTED
VERDICTS that deliberately do not change the exit code, so an `rc != 0` runner could only ever
test the plumbing.  An arm with expect_rc = 0 breaks the data behind a verdict and requires the
gate to print the OPPOSITE one — so a conclusion that has quietly become narration fails here.

⭐ THE ARM THAT EARNED ITS PLACE BEFORE THIS FILE EXISTED: `bl0d-one-sample` reproduces a real
defect in this gate's own first draft.  It wrote `A.load(p)[1]` inline in four places; `A.load`
returns the ARRAY, so `[1]` is SAMPLE 1, and both "bit-identity" scope checks were comparing one
sample of leading silence and PASSING vacuously.  Only BL0d — the arm that requires a DIFFERENCE —
went red.  That is defence in depth working (s119), and it is why the guards must run in both
directions rather than as a row of reassuring zeros.

⚠ RENDER DIRECTORY: redirected to one PID-unique path SHARED BY EVERY ARM of a run, not per arm.
The renders are a function of their argv, so an arm that does not change a render's argv is a
cache hit; only the arms that deliberately change one pay for it.  Per-arm dirs would re-render
the whole 22-file grid nine times for no added coverage.
"""
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SRC = os.path.join(HERE, "bleedfree_anchor_gate.py")
MUTANT = os.path.join(HERE, f"_mutated_gate_bl_{os.getpid()}.py")
PY = "/opt/homebrew/bin/python3.11"

# (name, [(pattern, replacement), ...], expect_rc, must_contain, why)
ARMS = [
    ("control", [], 0, "MEMBERSHIP MOVES at 2 of 7 features",
     "unmutated: every guard passes AND the membership verdict reaches its real, COMPUTED "
     "answer.  If this does not hold, no arm below is attributable."),

    # ---- BL0b: the analytic prediction the whole 'pure gain' half rests on --------------
    ("bl0b-coef",
     [(r"pred = \(1\.0 - e_hi, e_hi\)", "pred = (1.0, e_hi)")],
     1, "BL0b FAILED",
     "assert the corner's OD coefficient is 1 rather than (1-e).  BL0b must refuse — if it "
     "does not, BL1's 'the OD half is a PURE GAIN of -0.2126 dB' is unchecked arithmetic."),

    # ---- BL0c: the scope control -------------------------------------------------------
    ("bl0c-scope",
     [(r'cond_args\(0\.5, 1, blend=0\.0\)\)\n    b = render\("scope_blend0_e0"',
       'cond_args(0.5, 1, blend=0.5))\n    b = render("scope_blend0_e0"')],
     1, "BL0c FAILED",
     "move ONE side of the scope pair to BLEND = 0.5, where the end stop genuinely acts.  "
     "BL0c must fire — otherwise 'the clean path is untouched' is asserted, not measured."),

    # ---- BL0d: the plumbing control ----------------------------------------------------
    ("bl0d-vacuous",
     [(r'render\("bl0_corner_e0", cond_args\(0\.5, 1, extra=\["--fit", "blendEndStop=0"\]\)\)',
       'render("bl0_corner_e0_vac", cond_args(0.5, 1))')],
     1, "BL0d FAILED",
     "drop `--fit blendEndStop=0` from the e0 arm so both arms are the shipped stage.  BL0d "
     "must fire — this is the s100 control: a --fit flag that silently never reaches the DSP "
     "makes every difference below read as zero for a plumbing reason."),

    ("bl0d-one-sample",
     [(r"return float\(np\.max\(np\.abs\(a\[:n\] - b\[:n\]\)\)\)",
       "return float(abs(a[1] - b[1]))")],
     1, "BL0d FAILED",
     "compare ONE SAMPLE instead of the whole render — the gate's own first-draft defect, "
     "reproduced.  The two scope arms then pass vacuously and only BL0d can catch it."),

    # ---- BL0e: the one-clean-arm-serves-all assumption ---------------------------------
    ("bl0e-clean",
     [(r'render\("bl0_clean_alt", cond_args\(1\.0, 0, blend=0\.0\)\)',
       'render("bl0_clean_alt_od", cond_args(1.0, 0, blend=1.0))')],
     1, "BL0e FAILED",
     "make the second 'clean' render carry the OD path.  BL0e must fire — BL2/BL3 reuse ONE "
     "clean render for all nine cells and that is only legitimate while this holds."),

    # ---- BL5: the transcription's own known answer -------------------------------------
    # ⚠ THE NODE MATTERS.  The first version of this arm perturbed `kMixS[1]` (the -0.525) and
    # read GUARD DEAD against a working guard: S(0.441) interpolates between nodes 3 and 4, so
    # node 1 CANNOT move it — a VACUOUS mutation (s110, and the third documented shape of it).
    # `kMixS[3]` is the node the pinning is actually made of.
    ("bl5-pin",
     [(r"mix_s = \(0\.951, -0\.525, -0\.195, 0\.000,",
       "mix_s = (0.951, -0.525, -0.195, 0.100,")],
     1, "BL5 FAILED",
     "perturb the transcribed mix shape AT THE NODE THAT SETS THE PINNING so it is no longer "
     "pinned at kMixCfRef.  BL5 must refuse rather than print a cut-delta table off a stale "
     "copy of OdToneRestore.h — s149: a transcription needs a guard that can refuse."),

    # ---- COMPUTED VERDICTS (expect_rc 0): the half an exit-code runner cannot reach -----
    # ⚠⚠ AND THIS ARM'S FIRST VERSION DROPPED ONLY THE PROMINENCE BAR, ON THE STATED PREMISE THAT
    # IT IS "the only mechanism by which membership can move".  It read GUARD DEAD — and the
    # premise, not the guard, was wrong: W3 admits a reading on TWO conditions, and the EDGE test
    # flips too.  `bass_notch` at DRIVE min / GRUNT cut rests ON the 30 Hz window bound on the e0
    # arm and becomes an INTERIOR minimum at 31.6 Hz on the shipped one in 4 of 4 sweeps, because
    # the added clean term puts a floor under a curve that was otherwise monotone to the bound.
    # ⇒ a vacuous mutation, found by asking what else the verdict depends on — and the answer was
    # a second, previously uncounted mechanism, which is now reported separately by the gate.
    ("bl3-membership-computed",
     [(r"ok_a = not a\[\"edge\"\] and a\[\"prom\"\] >= W\.MIN_PROM_DB", "ok_a = True"),
      (r"ok_b = not b\[\"edge\"\] and b\[\"prom\"\] >= W\.MIN_PROM_DB", "ok_b = True")],
     0, "MEMBERSHIP is UNCHANGED",
     "admit every reading on both arms, which removes BOTH mechanisms by which membership can "
     "move.  The verdict MUST flip to UNCHANGED.  If it still says MOVED, that sentence is "
     "hard-coded — and the first draft of this gate DID narrate it, wrongly (it said "
     "'unchanged' while treble_peak loses 9 of 36 readings)."),

    ("bl3b-walk-computed",
     [(r'f0s\.append\(W\.locate\(c\[arm\], \(1800\.0, 4200\.0\), "max"\)\["f0"\]\)',
       'f0s.append(W.locate(c["e0"], (1800.0, 4200.0), "max")["f0"])')],
     0, "-3.54 % -> -3.54 %",
     "read BOTH walk arms off the e0 curve.  The verdict's own numbers must collapse to "
     "equal — s130: if the target can be deleted from the computation and the sentence still "
     "reads the same, it is narration, not a measurement."),
]


def run(name, subs, expect_rc, token, why):
    src = open(SRC).read()

    # Redirect the mutant's outputs FIRST, and REFUSE if a redirect does not apply — s153: a
    # redirect that silently no-ops restores the exact bug it was added to prevent, and the last
    # arm's deliberately falsified report is then left on disk wearing the real gate's filename.
    redirects = [
        (r'REN_DIR = "build/s183_bleedfree_anchor"',
         f'REN_DIR = "build/_mut_bl_{os.getpid()}"'),
        (r'default="analysis/reports/s183_bleedfree_anchor\.json"',
         f'default="analysis/reports/_mut_bl_{os.getpid()}.json"'),
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
    for p in glob.glob(os.path.join(ROOT, "analysis/reports/_mut_bl_*.json")):
        os.remove(p)
    for d in glob.glob(os.path.join(ROOT, "build/_mut_bl_*")):
        shutil.rmtree(d, ignore_errors=True)
    for m in glob.glob(os.path.join(HERE, "_mutated_gate_bl_*.py")):
        os.remove(m)


def main():
    print(f"mutation control for GATE BL — {len(ARMS)} arms\n")
    try:
        ok = sum(run(*a) for a in ARMS)
    finally:
        cleanup()
    print(f"\n{ok}/{len(ARMS)} arms behaved as required")
    return 0 if ok == len(ARMS) else 1


if __name__ == "__main__":
    sys.exit(main())
