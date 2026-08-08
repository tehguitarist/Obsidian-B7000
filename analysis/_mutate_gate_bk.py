#!/usr/bin/env python3
"""Mutation control for GATE BK (analysis/level_min_residual_gate.py).

Scores exit code AND a required output token, per s128: BK's load-bearing statements are
COMPUTED VERDICTS that deliberately do not change the exit code, so an `rc != 0` runner
could only ever test the plumbing. An arm with expect_rc = 0 breaks the data behind a
verdict and requires the gate to print the OPPOSITE verdict — so a conclusion that has
quietly become hard-coded narration FAILS here instead of surviving.

Mechanics, all learned the hard way and all load-bearing:
  * the mutant LIVES in analysis/ (sibling imports) and RUNS from the repo root (data
    paths) — s110, two different requirements that break each other if you satisfy one.
  * the mutant's path is PID-unique — s139, two concurrent runs otherwise share one file.
  * the mutant's REPORT and RENDER dir are redirected to PID-unique paths, and the
    redirect REFUSES if its pattern does not apply — s153, or the last arm's deliberately
    falsified output is left on disk wearing the real gate's filename.
  * the CONTROL runs through the same redirect as the arms — s110.
"""
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SRC = os.path.join(HERE, "level_min_residual_gate.py")
MUTANT = os.path.join(HERE, f"_mutated_gate_bk_{os.getpid()}.py")
PY = "/opt/homebrew/bin/python3.11"

# (name, [(pattern, replacement), ...], expect_rc, must_contain, why)
ARMS = [
    ("control", [], 1, "CLEAN-SIDE BLEED",
     "unmutated: BK0 must convict the known-defective capture (rc 1) AND BK4 must reach "
     "its real verdict. If this does not hold, no arm below is attributable."),

    # ---- BK0: the capture-validity guard --------------------------------------------
    ("bk0-sign-dead",
     [(r"for k, v in neg\.items\(\):", "for k, v in {}.items():")],
     0, "GATE BK",
     "kill the negative-pad conviction: the defective capture must stop being named, "
     "so the gate must now exit 0. Proves BK0's refusal is doing the work."),

    ("bk0-mono-blind",
     [(r"rows\[i\]\[j\] < rows\[i - 1\]\[j\] - 0\.05",
       "rows[i][j] < rows[i - 1][j] - 1e9")],
     1, "GATE BK",
     "blind the monotonicity walk. BK0's OTHER limb (the pad sign) must still convict, "
     "i.e. the two limbs are independent and not one guard counted twice."),

    # ---- BK4: THE discriminator ------------------------------------------------------
    ("bk4-swap-sources",
     [(r'\("resid", RESID\), \("od", OD\), \("clean", CLEAN\)\)\}\n    span_in',
       '("resid", RESID), ("od", CLEAN), ("clean", OD))}\n    span_in')],
     1, "OD-SIDE LEAK",
     "swap which capture is called OD and which CLEAN. The verdict MUST invert. This is "
     "the s130 test: if the target can be deleted from the predicate and the "
     "classification still runs, it is narration."),

    ("bk4-degenerate",
     [(r"ratio = span_od / span_cl", "ratio = 1.0")],
     1, "UNRESOLVED",
     "force the two spans equal. The gate must report UNRESOLVED rather than picking a "
     "side — a classifier with no third outcome is a coin flip with a verdict on it."),

    # ---- BK1: the known answers ------------------------------------------------------
    ("bk1a-nonzero",
     [(r"peak = float\(np\.max\(np\.abs\(y\)\)\)", "peak = float(np.max(np.abs(y))) + 1e-9")],
     1, "no longer mutes",
     "make the model's LEVEL-0 render non-silent. BK1a must refuse — item 12's whole "
     "premise is that this is EXACTLY zero."),

    ("bk1b-clean-routes",
     [(r"if spread > 1\.5:", "if spread > -1.0:")],
     1, "clean routes disagree",
     "tighten the clean-route agreement bar past what the data can meet. BK1b must fire, "
     "proving it is reachable at all (it passes at 0.011 dB, which could be vacuous)."),

    # ---- BK2: the floor guard (the trap this gate's own first draft fell into) --------
    ("bk2-floor",
     [(r"if float\(margins\.min\(\)\) < 20\.0:", "if float(margins.min()) < 1e9:")],
     1, "not safely a signal",
     "demand an unreachable margin over the quiet-gap depth. BK2 must refuse — otherwise "
     "the 'the residual is a signal, not a floor' line is narration."),

    # ---- BK5: the model-side refutation ----------------------------------------------
    ("bk5-taper",
     [(r'for name in \("levelTaperBreak1", "levelTaperFrac1"\):',
       'for name in ("notAConstant1", "notAConstant2"):')],
     1, "REFUSES",
     "break the FitParams.h read. BK5 must REFUSE rather than fall back to a transcribed "
     "slope — s149: a correction is not complete until the gate that USES the value can "
     "refuse."),
]


def run(name, subs, expect_rc, token, why):
    src = open(SRC).read()

    # Redirect the mutant's outputs FIRST, and refuse if the redirect does not apply.
    redirects = [
        (r'REPORT = "analysis/reports/s181_level_min\.json"',
         f'REPORT = "analysis/reports/_mut_bk_{os.getpid()}.json"'),
        (r'RENDER_DIR = "build/s181_level_min"',
         f'RENDER_DIR = "build/_mut_bk_{os.getpid()}"'),
    ]
    for pat, rep in redirects:
        src, n = re.subn(pat, rep, src)
        if n == 0:
            print(f"  {name:18s} RUNNER BROKEN: output redirect {pat!r} did not apply")
            return False

    for pat, rep in subs:
        src, n = re.subn(pat, rep, src)
        if n == 0:
            print(f"  {name:18s} PATCH DID NOT APPLY: {pat!r}")
            return False

    open(MUTANT, "w").write(src)
    try:
        res = subprocess.run([PY, MUTANT], cwd=ROOT, capture_output=True, text=True)
    finally:
        for p in (MUTANT,):
            if os.path.exists(p):
                os.remove(p)

    out = res.stdout + res.stderr
    rc_ok = res.returncode == expect_rc
    tok_ok = token in out
    if rc_ok and tok_ok:
        print(f"  {name:18s} PASS   (rc={res.returncode}, saw {token!r})")
        return True
    kind = "GUARD DEAD" if not rc_ok else "NARRATED"
    print(f"  {name:18s} {kind}  (rc={res.returncode} want {expect_rc}; "
          f"token {token!r} {'seen' if tok_ok else 'MISSING'})")
    print(f"      why this arm exists: {why}")
    tail = [l for l in out.splitlines() if l.strip()][-6:]
    for l in tail:
        print(f"      | {l}")
    return False


def cleanup():
    """Sweep by PATTERN, not by this run's pid, and in a finally — a runner that crashes
    part-way (this one did, on its first draft) otherwise leaves a deliberately falsified
    report on disk for someone else to find."""
    import glob
    import shutil
    for p in glob.glob(os.path.join(ROOT, "analysis/reports/_mut_bk_*.json")):
        os.remove(p)
    for d in glob.glob(os.path.join(ROOT, "build/_mut_bk_*")):
        shutil.rmtree(d, ignore_errors=True)
    for m in glob.glob(os.path.join(HERE, "_mutated_gate_bk_*.py")):
        os.remove(m)


def main():
    print(f"mutation control for GATE BK — {len(ARMS)} arms\n")
    try:
        ok = sum(run(*a) for a in ARMS)
    finally:
        cleanup()
    print(f"\n{ok}/{len(ARMS)} arms behaved as required")
    return 0 if ok == len(ARMS) else 1


if __name__ == "__main__":
    sys.exit(main())
