#!/usr/bin/env python3.11
"""Mutation runner for GATE BJ (analysis/bass_null_frontier_gate.py), session 180, open item 17.

Disciplines: mutant LIVES in analysis/ and RUNS from the repo root (s110); PID-unique mutant path
(s139) and PID-unique output (s153); unmutated CONTROL first; arms check GUARD IDENTITY not just
rc (s117); `expect_rc == 0` arms break the data behind a conclusion and require the OPPOSITE
verdict to print (s128).

Run: /opt/homebrew/bin/python3.11 analysis/_mutate_gate_bj.py
"""
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
GATE = os.path.join(HERE, "bass_null_frontier_gate.py")
MUTANT = os.path.join(HERE, f"_mutated_gate_bj_{os.getpid()}.py")

ARMS = [
    ("bj0-guard-control",
     r'    if len\(kept\) != 15:',
     '    if False:',
     0, "matched cells: 15",
     "disable the membership guard with the membership CORRECT.  The gate must still pass, which "
     "proves the guard is not what is producing the pass."),

    ("bj0a-membership",
     r'    kept, dropped = BH\.matched_cells\(FEAT, "cell"\)',
     '    kept, dropped = BH.matched_cells(FEAT, "cell"); kept = kept[:14]',
     1, "BJ0a",
     "drop a cell from the matched membership.  BJ0a must refuse — s178's verdict only transfers "
     "on the population it was measured on, and an unmatched pool is self-serving here (an arm "
     "whose null is too shallow to read drops the cell, and shallow is the outcome scored)."),

    ("bj0b-inert-arm",
     r'    "300/6\.0/S0\.9":      shelf\(300, 6\.0, 0\.9\),',
     '    "300/6.0/S0.9":      (),',
     1, "BJ0b",
     "make an arm a no-op.  The non-vacuity guard must catch it: a --fit that never reaches the "
     "DSP reads as a clean result (s110)."),

    ("bj0c-known-answer",
     r'            e\.append\(BH\.geom\(g, mod, FEAT\)\[DEPTH_CTL\] - BH\.geom\(g, ped, FEAT\)\[DEPTH_CTL\]\)',
     '            e.append(BH.geom(g, mod, FEAT)[DEPTH_CTL] - BH.geom(g, ped, FEAT)[DEPTH_CTL] + 0.3)',
     1, "BJ0c",
     "bias the depth difference by 0.3 dB.  The cross-session known answer against s178 BH6's "
     "recorded +2.34 / +0.03 must refuse — without it this gate's target is not s178's target."),

    # ---- computed-verdict arms -----------------------------------------------------------------
    ("bj0d-censoring",
     r'    if cens_nd > len\(kept\) // 2:',
     '    if cens_nd > 99:',
     0, "both estimators are usable",
     "tell the gate the reference is resolved.  BJ0d must then say both estimators are usable "
     "instead of forcing the area depth — the estimator choice is the correction this session "
     "makes to s178 and it must come from the audit, not from the docstring."),

    ("bj1-inflation",
     r'            ectl\.append\(gm\[DEPTH_CTL\] - gp\[DEPTH_CTL\]\)',
     '            ectl.append(gm[DEPTH] - gp[DEPTH])',
     0, "inflates the WORST-CELL column by up to 1.0x",
     "make the censored control identical to the graded estimator.  BJ1's inflation factor must "
     "collapse to 1.0x — if it still reports a large factor it is not reading the two columns."),

    ("bj2-best-lf",
     r'    best_lf = min\(ARMS, key=lambda a: out\[a\]\["lf"\]\)',
     '    best_lf = max(ARMS, key=lambda a: out[a]["lf"])',
     0, "INTERIOR MINIMUM at 's173 130/3.5/S0.9'",
     "invert the LF selector.  BJ2 must then name the INCUMBENT (the LF worst arm, 2.61) instead of "
     "160/6.0 — the interior minimum is a measurement, not a sentence.  ⚠ A first draft expected "
     "'pre-s172' here and reported NARRATED against a working gate: pre-s172's LF rms is 2.35, not "
     "the maximum.  `suspect the mutation before the guard` (s110)."),

    ("bj4-licence",
     r'HW_320 = \{"cut": \(1\.6, 1\.6\), "flat": \(3\.5, 4\.8\), "boost": \(None, None\)\}',
     'HW_320 = {"cut": (0.0, 9.9), "flat": (0.0, 9.9), "boost": (None, None)}',
     0, "under / inside / far under",
     "widen §3's licence so every arm stays inside at flat.  BJ4's 'EVERY candidate gives back a "
     "cell' warning must stand down — the trade is the session's headline and must be computed."),

    ("bj5-mechanism",
     r'    if worst > 2\.0 and signs > 1:',
     '    if worst > 99.0 and signs > 1:',
     0, "magnitude is sufficient",
     "raise BJ5's departure bar out of reach.  It must then conclude magnitude is sufficient — "
     "the PHASE finding is this gate's mechanism claim and cannot be narration."),

    # ⚠ REACHABILITY arm, not a data arm.  A first draft dropped ONLY the ~320 Hz axis and
    # reported NARRATED — vacuously, because the worst-cell and MID axes still bind on every
    # candidate (250/6.0 fails MID by 0.12, 200/6.0 fails worst-cell by 0.85).  `suspect the
    # mutation before the guard` (s110).  What this arm can honestly prove is that the DOMINATING
    # branch is reachable and prints, so a future edit cannot leave it unreachable.
    ("bj6-dominance",
     r'    dom = \[a for a in ARMS if a != INCUMBENT\n(?:.*\n)*?           and n_inside\[a\] >= n_inside\[INCUMBENT\]\]',
     '    dom = [a for a in ARMS if a != INCUMBENT and bass[a]["median"] < bass[INCUMBENT]["median"]]',
     0, "DOMINATING on every axis",
     "relax the dominance test to the bass axis alone.  The DOMINATING branch must then be "
     "reached and printed — otherwise BJ6's 'no arm dominates' is a sentence with no live "
     "alternative, which is the shape `computed-verdicts-not-narrated` describes."),
]


def run(path, out_json):
    return subprocess.run([sys.executable, path, "--json", out_json],
                          cwd=ROOT, capture_output=True, text=True)


def main():
    src = open(GATE).read()
    out_json = f"analysis/reports/_mutate_bj_{os.getpid()}.json"
    print("=" * 92)
    print("MUTATION RUNNER — GATE BJ (bass_null_frontier_gate.py)")
    print("=" * 92)
    open(MUTANT, "w").write(src)
    ctl = run(MUTANT, out_json)
    if ctl.returncode != 0:
        print("⛔ CONTROL FAILED — no arm below is attributable.\n")
        print(ctl.stdout[-3000:], ctl.stderr[-2000:])
        os.remove(MUTANT)
        sys.exit(1)
    print("control (unmutated): PASS\n")

    fails = []
    for name, pat, rep, exp_rc, must, why in ARMS:
        mutated, n = re.subn(pat, rep, src, count=1)
        if n != 1:
            print(f"  {name:20s} ⛔ PATCH DID NOT APPLY (matched {n})")
            fails.append(name)
            continue
        open(MUTANT, "w").write(mutated)
        r = run(MUTANT, out_json)
        blob = r.stdout + r.stderr
        if r.returncode != exp_rc:
            print(f"  {name:20s} ⛔ rc {r.returncode}, expected {exp_rc}"
                  + (" — GUARD DEAD" if exp_rc else " — crashed where a verdict was wanted"))
            tail = blob.strip().splitlines()
            print(f"        tail: {tail[-1][:150] if tail else '(no output)'}")
            fails.append(name)
        elif must not in blob:
            print(f"  {name:20s} ⛔ {'WRONG GUARD' if exp_rc else 'NARRATED'} — never printed {must!r}")
            fails.append(name)
        else:
            print(f"  {name:20s} ✅ rc={r.returncode}, matched {must!r}")

    os.remove(MUTANT)
    p = os.path.join(ROOT, out_json)
    if os.path.exists(p):
        os.remove(p)
    print()
    print(f"{len(ARMS) - len(fails)}/{len(ARMS)} arms behaved as specified")
    if fails:
        print("⛔ " + ", ".join(fails))
        sys.exit(1)
    print("✅ every guard fires on its own defect and every graded verdict is computed")


if __name__ == "__main__":
    main()
