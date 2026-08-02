#!/usr/bin/env python3.11
"""Mutation test for GATE I (`hf_artefact_gate.py`), session 114.

Every guard must be shown ABLE TO FIRE, or it is decoration. Three traps this runner exists to
avoid, each paid for by an earlier session:

  * **s107** -- a patched copy written to /tmp returns "PASS" for a `ModuleNotFoundError` that
    never reaches a guard. The copy must LIVE in `analysis/` so its sibling imports resolve.
  * **s110** -- ...and must RUN from the repo root so its repo-relative data paths resolve. Those
    are two different requirements and satisfying one is the natural way to break the other.
  * **s110** -- a mutation can be VACUOUS (patch a module constant that a worker re-imports, or a
    needle that does not appear). Each needle is asserted present EXACTLY ONCE, so a vacuous
    mutation reports as vacuous rather than as a dead guard.

The unmutated CONTROL runs first: if it does not PASS, no failure below is attributable.

    python3.11 analysis/_mutate_gate_i.py [report.json]
"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SRC = os.path.join(HERE, "hf_artefact_gate.py")
TMP = os.path.join(HERE, "_mutated_gate_i.py")          # MUST live here (s107)

REPORT = sys.argv[1] if len(sys.argv) > 1 else "analysis/reports/s113_baseline.json"

MUTATIONS = [
    # ⚠ these two are DATA-level mutations (make the class genuinely empty), not `if False:`.
    # The first draft disabled the guards instead of making them fire and duly reported two
    # "GUARD DEAD" results -- s110's lesson, suspect the mutation before the guard.
    ("G0  empty OD class must refuse",
     '    if drv == 0.0:\n        return CLASSES[1]',
     '    if drv == 0.0:\n        return None'),
    ("G0  missing CLEAN class must refuse",
     '        if all(abs(s.get(k, 0.5) - 0.5) < 1e-9 for k in EQ_POTS):\n            return CLASSES[0]',
     '        if all(abs(s.get(k, 0.5) - 0.5) < 1e-9 for k in EQ_POTS):\n            return None'),
    ("G0  a bled / gain-session OD row must refuse",
     'if "gain-n12" in f or "gain-n18" in f or "blend-" in f]',
     'if True]'),
    ("dedup: disagreeing MASTER duplicates must refuse",
     'if worst > DUP_TOL:',
     'if worst > -1.0:'),
    ("band_octave: a non-2:1 pair must refuse",
     'if abs(ratio - 2.0) > 0.02:',
     'if abs(ratio - 2.0) > -1.0:'),
    ("G1a  clean-path level tolerance",
     'G1_LEVEL_TOL = 1.5',
     'G1_LEVEL_TOL = 0.01'),
    ("G1b  clean-path stimulus invariance",
     'G1_INVARIANCE_TOL = 0.5',
     'G1_INVARIANCE_TOL = -1.0'),
    ("G2a  model must never gain with frequency",
     'a = max(m_all) <= 0.0',
     'a = max(m_all) <= -99.0'),
    ("G2b  complete pedal/model separation at the hottest stimulus",
     'b = min(hot_p) > max(hot_m)',
     'b = min(hot_p) > max(hot_m) + 99.0'),
    ("G2c  separation must grow with stimulus",
     'c = all(gaps[i] < gaps[i + 1] for i in range(len(gaps) - 1))',
     'c = all(gaps[i] > gaps[i + 1] for i in range(len(gaps) - 1))'),
]


def run(path):
    p = subprocess.run([sys.executable, path, REPORT, "--skip-fine"],
                       cwd=ROOT, capture_output=True, text=True)   # cwd = repo root (s110)
    out = (p.stdout + p.stderr).strip().splitlines()
    hard = [l for l in out if l.startswith("hf_artefact_gate:")]
    soft = [l for l in out if "**FAIL**" in l]
    why = (hard or soft or [l for l in out if l.strip()] or ["<no output>"])[-1]
    return p.returncode, why.strip()[:100]


def main():
    src = open(SRC).read()
    fails = 0

    open(TMP, "w").write(src)
    rc, last = run(TMP)
    print(f"CONTROL (unmutated)                                       rc={rc}  "
          f"{'PASS' if rc == 0 else '**CONTROL FAILED**'}")
    if rc != 0:
        print(f"    {last}")
        print("\n⛔ the control does not pass -- no mutation result below is attributable")
        os.remove(TMP)
        return 1
    print()

    for name, needle, repl in MUTATIONS:
        n = src.count(needle)
        if n != 1:
            print(f"{name:<58} **VACUOUS** needle appears {n}x, expected 1")
            fails += 1
            continue
        open(TMP, "w").write(src.replace(needle, repl))
        rc, last = run(TMP)
        good = rc != 0
        print(f"{name:<58} rc={rc}  {'fires' if good else '**GUARD DEAD**'}")
        if not good:
            fails += 1
        else:
            print(f"    {last}")

    os.remove(TMP)
    print(f"\n{len(MUTATIONS) - fails}/{len(MUTATIONS)} guards fire; control passes."
          if not fails else f"\n**{fails} PROBLEM(S)**")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
