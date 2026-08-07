#!/usr/bin/env python3.11
"""Mutation runner for GATE BG (analysis/c31_corner_gate.py), session 177.

Disciplines carried in (measurement-discipline.md §3):
  * the mutant LIVES in analysis/ (sibling imports resolve) and RUNS from the repo root
    (data paths resolve) -- s110, both halves.
  * the mutant path is PID-unique -- s139, so two concurrent runs cannot score each
    other's file.
  * an UNMUTATED control runs first; if it does not pass, no arm below is attributable.
  * arms check GUARD IDENTITY (a token the failure must contain), not just rc != 0 -- s117.
  * arms with expect_rc == 0 test a COMPUTED VERDICT: they break the data behind a
    conclusion and require the gate to print the OPPOSITE one.  s128's rule -- without
    these, a conclusion that has silently become hard-coded narration passes.

Run: /opt/homebrew/bin/python3.11 analysis/_mutate_gate_bg.py
"""
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
GATE = os.path.join(HERE, "c31_corner_gate.py")
MUTANT = os.path.join(HERE, f"_mutated_gate_bg_{os.getpid()}.py")

# (name, pattern, replacement, expect_rc, must_contain, why)
ARMS = [
    ("bg1-no-divergence",
     r'drawn = dict\(Rp=100e3, R38=2\.2e3, R39=2\.2e3, R40=220e3, R41=220e3, C32=22e-9, Rw=0\.0\)',
     'drawn = dict(Rp=v["Rp"], R38=v["R38"], R39=v["R39"], R40=v["R40"], R41=v["R41"],\n'
     '                 C32=v["ratio"] * v["caps"]["250 Hz"], Rw=v["Rw"])',
     1, "BG1",
     "make the 'drawn' set equal the shipped set: the divergence guard must REFUSE, "
     "because BG1b's transfer known answer would then be blind to the value set (s149)."),

    ("bg1b-wrong-node",
     r'A\[0, 0\] = yC31 \+ 1 / R38 \+ 1 / R41',
     'A[0, 0] = yC31 + 1 / R38',
     1, "BG1b",
     "drop the R41 leg from the Vin KCL row: the 5-unknown solve no longer reduces to "
     "the shipped 4-unknown oracle when C31 is shorted."),

    ("bg2-wrong-miller",
     r'zin_cf = 1\.0 / \(1\.0 / v\["R41"\] \+ \(1\.0 - g0\) / \(v\["R38"\] \+ v\["Rp"\] \+ v\["R39"\]\)\)',
     'zin_cf = 1.0 / (1.0 / v["R41"] + 1.0 / (v["R38"] + v["Rp"] + v["R39"]))',
     1, "BG2",
     "drop the (1-G0) Miller factor -- the single step the whole derivation turns on. "
     "Both independent numerical extractions must reject it."),

    ("bg3-freeze-zin",
     r'zin_by_cap\[cname\] = zin_direct\(f_z, 0\.5, c33, C32=v\["ratio"\] \* c33, \*\*kw_mid\)',
     'zin_by_cap[cname] = zin_direct(f_z, 0.5, c33, C32=1e-18, **kw_mid)',
     1, "BG3",
     "remove C32 (the element that collapses Zin). |Zin| then stays ~flat and BG3 must "
     "REFUSE its own refutation as vacuous rather than publishing it."),

    # --- computed-verdict arms: expect_rc 0, and the OPPOSITE verdict must be printed ---
    ("bg6-verdict-one-pole",
     r'C31_SCHEMATIC = 2\.2e-6',
     'C31_SCHEMATIC = 2.2e-1',
     0, "ONE POLE SUFFICES",
     "make C31 enormous so its insertion is ~0 dB everywhere: BG6's verdict must FLIP to "
     "'ONE POLE SUFFICES'.  If it still says 'NOT ENOUGH', that line is narration."),

    ("bg6-verdict-invisible",
     r"one_pole_ok = worst_db < 0\.05",
     "one_pole_ok = worst_db < 0.05\n    worst_band_db = 0.001",
     0, "invisible to",
     "force the graded-band magnitude under the 0.05 dB bar: BG6 must print 'invisible "
     "to release_gate.py' instead of 'VISIBLE to'."),
]


def run(path):
    return subprocess.run([sys.executable, path], cwd=ROOT,
                          capture_output=True, text=True, timeout=900)


def main():
    src = open(GATE).read()

    print("CONTROL (unmutated copy, run from the repo root):")
    open(MUTANT, "w").write(src)
    try:
        r = run(MUTANT)
        if r.returncode != 0:
            print(r.stdout[-3000:] + r.stderr[-3000:])
            print("  => CONTROL FAILED — no arm below is attributable. Stopping.")
            return 1
        print("  => PASS\n")

        bad = 0
        for name, pat, rep, exp_rc, token, why in ARMS:
            mutated, n = re.subn(pat, rep, src, count=1)
            if n != 1:
                print(f"[{name}] PATCH DID NOT APPLY (pattern matched {n}x) — arm is broken, "
                      f"not the gate.")
                bad += 1
                continue
            open(MUTANT, "w").write(mutated)
            r = run(MUTANT)
            out = r.stdout + r.stderr
            ok_rc = (r.returncode == exp_rc)
            ok_tok = token in out
            verdict = "PASS" if (ok_rc and ok_tok) else (
                "GUARD DEAD" if r.returncode == 0 and exp_rc != 0 else
                "NARRATED" if ok_rc and not ok_tok else "WRONG GUARD")
            if verdict != "PASS":
                bad += 1
            print(f"[{name}] rc={r.returncode} (want {exp_rc}), token {token!r} "
                  f"{'found' if ok_tok else 'MISSING'} => {verdict}")
            print(f"    why: {why}")
        print(f"\n{len(ARMS) - bad}/{len(ARMS)} arms PASS.")
        return 1 if bad else 0
    finally:
        if os.path.exists(MUTANT):
            os.remove(MUTANT)


if __name__ == "__main__":
    sys.exit(main())
